"""Frank AI OS — Alert routes: CRUD e notificações em tempo real."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    unit_id: Optional[str] = None
    sector: str
    rule: str
    title: str
    message: str
    severity: str = "warning"
    current_val: Optional[float] = None
    limit_val: Optional[float] = None


class AlertAction(BaseModel):
    resolved_by: str = "user"
    note: str = ""


@router.get("")
async def list_alerts(
    severity: Optional[str] = Query(None, description="critical | warning | info"),
    unit_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """Lista alertas abertos com filtros opcionais."""
    from app.services.alert_service import alert_service
    alerts = await alert_service.get_open_alerts(
        severity=severity,
        unit_id=unit_id,
        limit=limit,
    )
    return [
        {
            "id": a.id,
            "unit_id": a.unit_id,
            "sector": a.sector,
            "rule": a.rule,
            "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "title": a.title,
            "message": a.message,
            "current_val": a.current_val,
            "limit_val": a.limit_val,
            "delta_pct": a.delta_pct,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.get("/recent")
async def get_recent_alerts(count: int = Query(20, le=100)):
    """Alertas recentes do cache Redis (ultra-rápido para dashboard)."""
    from app.services.alert_service import alert_service
    return await alert_service.get_recent_from_cache(count)


@router.post("")
async def create_alert(payload: AlertCreate):
    """Cria um alerta manualmente."""
    from app.services.alert_service import alert_service
    try:
        alert = await alert_service.create_alert(
            unit_id=payload.unit_id,
            sector=payload.sector,
            rule=payload.rule,
            title=payload.title,
            message=payload.message,
            severity=payload.severity,
            current_val=payload.current_val,
            limit_val=payload.limit_val,
        )
        return {"id": alert.id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, body: AlertAction):
    """Reconhece um alerta (muda para acked)."""
    from app.services.alert_service import alert_service
    ok = await alert_service.acknowledge_alert(alert_id, acknowledged_by=body.resolved_by)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "acknowledged"}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: str, body: AlertAction):
    """Resolve um alerta."""
    from app.services.alert_service import alert_service
    ok = await alert_service.resolve_alert(alert_id, resolved_by=body.resolved_by, note=body.note)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "resolved"}


@router.get("/stats")
async def alert_stats():
    """Estatísticas de alertas por severidade e setor."""
    from app.core.database import get_db_context
    from app.memory.models import Alert, AlertStatus, AlertSeverity
    from sqlalchemy import select, func

    async with get_db_context() as db:
        # Por severidade
        by_severity = await db.execute(
            select(Alert.severity, func.count(Alert.id).label("cnt"))
            .where(Alert.status == AlertStatus.open)
            .group_by(Alert.severity)
        )

        # Por setor
        by_sector = await db.execute(
            select(Alert.sector, func.count(Alert.id).label("cnt"))
            .where(Alert.status == AlertStatus.open)
            .group_by(Alert.sector)
            .order_by(func.count(Alert.id).desc())
        )

        # Total por status
        by_status = await db.execute(
            select(Alert.status, func.count(Alert.id).label("cnt"))
            .group_by(Alert.status)
        )

    return {
        "open_by_severity": {
            str(row.severity.value if hasattr(row.severity, "value") else row.severity): row.cnt
            for row in by_severity
        },
        "open_by_sector": {row.sector: row.cnt for row in by_sector},
        "total_by_status": {
            str(row.status.value if hasattr(row.status, "value") else row.status): row.cnt
            for row in by_status
        },
    }
