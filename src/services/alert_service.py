"""Frank AI OS — Serviço de alertas: criação, notificação e resolução."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.redis_client import alert_queue
from app.memory.models import Alert, AlertSeverity, AlertStatus, AgentAction, ActionStatus

logger = get_logger("alert_service")


class AlertService:

    async def create_alert(
        self,
        unit_id: Optional[str],
        sector: str,
        rule: str,
        title: str,
        message: str,
        severity: str = "warning",
        current_val: Optional[float] = None,
        limit_val: Optional[float] = None,
        delta_pct: Optional[float] = None,
    ) -> Alert:
        """Cria um alerta no banco e publica na fila Redis."""
        async with get_db_context() as db:
            alert = Alert(
                unit_id=unit_id,
                sector=sector,
                rule=rule,
                severity=AlertSeverity(severity),
                status=AlertStatus.open,
                title=title,
                message=message,
                current_val=current_val,
                limit_val=limit_val,
                delta_pct=delta_pct,
            )
            db.add(alert)
            await db.flush()

            # Publicar na fila Redis para notificação em tempo real
            await alert_queue.push_to_list({
                "id": alert.id,
                "unit_id": unit_id,
                "sector": sector,
                "rule": rule,
                "severity": severity,
                "title": title,
                "message": message,
                "created_at": datetime.utcnow().isoformat(),
            })

            logger.info("alert_created", id=alert.id, severity=severity, unit=unit_id, rule=rule)
            return alert

    async def bulk_create_from_analysis(
        self,
        sector: str,
        violations: List[dict],
    ) -> List[Alert]:
        """Cria alertas em massa a partir de uma lista de violações de CEO Rules."""
        created = []
        for v in violations:
            alert = await self.create_alert(
                unit_id=v.get("unit_id"),
                sector=sector,
                rule=v.get("rule", "UNKNOWN"),
                title=v.get("message", "CEO Rule violada"),
                message=v.get("message", ""),
                severity=v.get("severity", "warning"),
                current_val=v.get("current"),
                limit_val=v.get("limit"),
            )
            created.append(alert)
        return created

    async def get_open_alerts(
        self,
        severity: Optional[str] = None,
        unit_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """Busca alertas abertos com filtros opcionais."""
        async with get_db_context() as db:
            query = select(Alert).where(Alert.status == AlertStatus.open)
            if severity:
                query = query.where(Alert.severity == AlertSeverity(severity))
            if unit_id:
                query = query.where(Alert.unit_id == unit_id)
            query = query.order_by(Alert.created_at.desc()).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        async with get_db_context() as db:
            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()
            if alert:
                alert.status = AlertStatus.acked
                alert.resolved_by = acknowledged_by
                logger.info("alert_acked", id=alert_id, by=acknowledged_by)
                return True
        return False

    async def resolve_alert(self, alert_id: str, resolved_by: str = "system", note: str = "") -> bool:
        async with get_db_context() as db:
            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()
            if alert:
                alert.status = AlertStatus.resolved
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = resolved_by
                logger.info("alert_resolved", id=alert_id)
                return True
        return False

    async def get_recent_from_cache(self, count: int = 20) -> list:
        """Alertas recentes direto do Redis (mais rápido que DB para dashboard)."""
        return await alert_queue.get_recent(count)


alert_service = AlertService()
