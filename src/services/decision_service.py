"""Frank AI OS — Serviço de decisões: logging, padrões e auto-aprendizado."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.core.redis_client import cache
from app.core.logging import get_logger
from app.memory.models import DecisionLog, AgentAction, ActionStatus

logger = get_logger("decision_service")


class DecisionService:

    # ─── Decision Logging ──────────────────────────────────────────────────────

    async def record(
        self,
        agent_name: str,
        decision_type: str,
        input_summary: str,
        analysis: str,
        recommendation: str,
        verdict: str,
        confidence: float = 0.8,
        unit_id: Optional[str] = None,
        sector: Optional[str] = None,
        ceo_rules_checked: Optional[Dict] = None,
        tokens_used: int = 0,
        metadata: Optional[Dict] = None,
    ) -> DecisionLog:
        """Registra uma decisão no banco."""
        async with get_db_context() as db:
            decision = DecisionLog(
                agent_name=agent_name,
                decision_type=decision_type,
                unit_id=unit_id,
                sector=sector,
                input_summary=input_summary[:1000],
                analysis=analysis,
                recommendation=recommendation,
                verdict=verdict,
                confidence=confidence,
                ceo_rules_checked=ceo_rules_checked or {},
                tokens_used=tokens_used,
                metadata=metadata or {},
            )
            db.add(decision)
            await db.flush()
            logger.info("decision_recorded",
                        agent=agent_name, verdict=verdict,
                        sector=sector, unit=unit_id, tokens=tokens_used)
            return decision

    # ─── Action Tracking ───────────────────────────────────────────────────────

    async def create_action(
        self,
        action_type: str,
        triggered_by: str,
        payload: Dict,
        alert_id: Optional[str] = None,
        decision_id: Optional[str] = None,
    ) -> AgentAction:
        """Cria um registro de ação a executar."""
        async with get_db_context() as db:
            action = AgentAction(
                action_type=action_type,
                triggered_by=triggered_by,
                alert_id=alert_id,
                decision_id=decision_id,
                payload=payload,
                status=ActionStatus.pending,
            )
            db.add(action)
            await db.flush()
            logger.info("action_created", type=action_type, by=triggered_by)
            return action

    async def execute_action(self, action_id: str) -> bool:
        """Marca ação como em execução e tenta executá-la."""
        from app.connectors.email_connector import email_connector
        from app.connectors.whatsapp_connector import whatsapp_connector

        async with get_db_context() as db:
            result = await db.execute(select(AgentAction).where(AgentAction.id == action_id))
            action = result.scalar_one_or_none()
            if not action:
                return False

            action.status = ActionStatus.running
            action.started_at = datetime.utcnow()
            await db.flush()

            try:
                payload = action.payload or {}
                action_type = action.action_type

                if action_type == "send_email":
                    success = await email_connector.send_alert(payload)
                elif action_type == "send_whatsapp":
                    success = await whatsapp_connector.send_critical_alert(payload)
                elif action_type == "pause_meta_campaign":
                    from app.connectors.meta_ads_connector import meta_connector
                    success = await meta_connector.pause_campaign(payload.get("campaign_id", ""))
                else:
                    logger.warning("unknown_action_type", type=action_type)
                    success = False

                action.status = ActionStatus.completed if success else ActionStatus.failed
                action.completed_at = datetime.utcnow()
                action.result = {"success": success}
                logger.info("action_executed", id=action_id, type=action_type, success=success)
                return success

            except Exception as e:
                action.status = ActionStatus.failed
                action.retry_count += 1
                action.result = {"error": str(e)}
                logger.error("action_failed", id=action_id, error=str(e))
                return False

    async def get_pending_actions(self, limit: int = 50) -> List[AgentAction]:
        """Busca ações pendentes para execução."""
        async with get_db_context() as db:
            result = await db.execute(
                select(AgentAction)
                .where(AgentAction.status == ActionStatus.pending)
                .order_by(AgentAction.created_at.asc())
                .limit(limit)
            )
            return result.scalars().all()

    async def retry_failed_actions(self, max_retries: int = 3) -> int:
        """Requeue ações com falha que ainda têm tentativas."""
        async with get_db_context() as db:
            result = await db.execute(
                select(AgentAction).where(
                    and_(
                        AgentAction.status == ActionStatus.failed,
                        AgentAction.retry_count < max_retries,
                    )
                )
            )
            actions = result.scalars().all()
            for action in actions:
                action.status = ActionStatus.pending
            logger.info("actions_requeued", count=len(actions))
            return len(actions)

    # ─── Pattern Analysis ──────────────────────────────────────────────────────

    async def get_patterns(
        self,
        days_back: int = 30,
        sector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analisa padrões de decisão dos últimos N dias."""
        cache_key = f"decision_patterns:{sector or 'all'}:{days_back}d"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        since = datetime.utcnow() - timedelta(days=days_back)

        async with get_db_context() as db:
            base_q = select(DecisionLog).where(DecisionLog.created_at >= since)
            if sector:
                base_q = base_q.where(DecisionLog.sector == sector)

            # Distribuição de vereditos
            verdict_q = (
                select(DecisionLog.verdict, func.count(DecisionLog.id).label("cnt"))
                .where(DecisionLog.created_at >= since)
            )
            if sector:
                verdict_q = verdict_q.where(DecisionLog.sector == sector)
            verdict_q = verdict_q.group_by(DecisionLog.verdict)
            v_result = await db.execute(verdict_q)
            verdict_dist = {row.verdict: row.cnt for row in v_result}

            # Confiança média por agente
            conf_q = (
                select(DecisionLog.agent_name, func.avg(DecisionLog.confidence).label("avg_conf"))
                .where(DecisionLog.created_at >= since)
                .group_by(DecisionLog.agent_name)
            )
            c_result = await db.execute(conf_q)
            agent_confidence = {row.agent_name: round(float(row.avg_conf), 3) for row in c_result}

            # Unidades com mais decisões críticas
            unit_q = (
                select(DecisionLog.unit_id, func.count(DecisionLog.id).label("cnt"))
                .where(
                    DecisionLog.created_at >= since,
                    DecisionLog.verdict.in_(["NO-GO", "CRITICAL"]),
                )
                .group_by(DecisionLog.unit_id)
                .order_by(func.count(DecisionLog.id).desc())
                .limit(5)
            )
            u_result = await db.execute(unit_q)
            critical_units = [{"unit_id": row.unit_id, "count": row.cnt} for row in u_result]

            # Total de tokens consumidos
            tokens_q = select(func.sum(DecisionLog.tokens_used)).where(DecisionLog.created_at >= since)
            t_result = await db.execute(tokens_q)
            total_tokens = t_result.scalar() or 0

        patterns = {
            "period_days": days_back,
            "sector": sector,
            "verdict_distribution": verdict_dist,
            "total_decisions": sum(verdict_dist.values()),
            "agent_avg_confidence": agent_confidence,
            "most_critical_units": critical_units,
            "total_tokens_consumed": total_tokens,
            "generated_at": datetime.utcnow().isoformat(),
        }

        await cache.set(cache_key, patterns, ttl=1800)
        return patterns

    async def get_ceo_rules_violations_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Resumo das violações de CEO Rules no período."""
        since = datetime.utcnow() - timedelta(days=days_back)

        async with get_db_context() as db:
            result = await db.execute(
                select(DecisionLog)
                .where(
                    DecisionLog.created_at >= since,
                    DecisionLog.ceo_rules_checked != {},
                )
                .order_by(DecisionLog.created_at.desc())
                .limit(200)
            )
            decisions = result.scalars().all()

        violations_by_rule: Dict[str, int] = {}
        violations_by_unit: Dict[str, int] = {}

        for d in decisions:
            rules = d.ceo_rules_checked or {}
            if isinstance(rules, dict):
                for rule, checked in rules.items():
                    if isinstance(checked, dict) and checked.get("violated"):
                        violations_by_rule[rule] = violations_by_rule.get(rule, 0) + 1
                        if d.unit_id:
                            violations_by_unit[d.unit_id] = violations_by_unit.get(d.unit_id, 0) + 1

        return {
            "period_days": days_back,
            "violations_by_rule": dict(sorted(violations_by_rule.items(), key=lambda x: -x[1])),
            "violations_by_unit": dict(sorted(violations_by_unit.items(), key=lambda x: -x[1])),
            "total_violations": sum(violations_by_rule.values()),
        }

    async def get_action_stats(self) -> Dict[str, Any]:
        """Estatísticas de execução de ações automáticas."""
        async with get_db_context() as db:
            result = await db.execute(
                select(AgentAction.status, func.count(AgentAction.id).label("cnt"))
                .group_by(AgentAction.status)
            )
            stats = {row.status.value if hasattr(row.status, 'value') else str(row.status): row.cnt for row in result}

            result2 = await db.execute(
                select(AgentAction.action_type, func.count(AgentAction.id).label("cnt"))
                .group_by(AgentAction.action_type)
                .order_by(func.count(AgentAction.id).desc())
            )
            by_type = {row.action_type: row.cnt for row in result2}

        return {
            "by_status": stats,
            "by_type": by_type,
            "total": sum(stats.values()),
        }


decision_service = DecisionService()
