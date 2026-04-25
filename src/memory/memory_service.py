"""Frank AI OS — Serviço de memória: agent memory, decisions log, insights."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.core.redis_client import cache
from app.core.logging import get_logger
from app.memory.models import AgentMemory, DecisionLog, InsightHistory

logger = get_logger("memory_service")

MEMORY_CACHE_TTL = 3600  # 1 hora


class MemoryService:
    """CRUD para AgentMemory, DecisionLog e InsightHistory."""

    # ─── Agent Memory ──────────────────────────────────────────────

    async def store_memory(
        self,
        agent_name: str,
        memory_key: str,
        memory_value: Any,
        memory_type: str = "insight",
        confidence: float = 0.8,
        context: Optional[Dict] = None,
        expires_in_days: Optional[int] = None,
    ) -> AgentMemory:
        """Armazena ou atualiza uma memória de agente."""
        import json
        value_str = json.dumps(memory_value) if not isinstance(memory_value, str) else memory_value

        async with get_db_context() as db:
            # Verifica se já existe
            result = await db.execute(
                select(AgentMemory).where(
                    AgentMemory.agent_name == agent_name,
                    AgentMemory.memory_key == memory_key,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.memory_value = value_str
                existing.confidence = confidence
                existing.usage_count += 1
                existing.last_used_at = datetime.utcnow()
                if context:
                    existing.context = context
                if expires_in_days:
                    existing.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
                memory = existing
            else:
                memory = AgentMemory(
                    agent_name=agent_name,
                    memory_key=memory_key,
                    memory_value=value_str,
                    memory_type=memory_type,
                    confidence=confidence,
                    context=context or {},
                    expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
                )
                db.add(memory)

            await db.flush()
            logger.info("memory_stored", agent=agent_name, key=memory_key, type=memory_type)

            # Invalidar cache
            await cache.delete(f"memory:{agent_name}:{memory_key}")
            return memory

    async def recall(
        self,
        agent_name: str,
        memory_key: str,
    ) -> Optional[Any]:
        """Recupera uma memória específica do agente (com cache Redis)."""
        import json
        cache_key = f"memory:{agent_name}:{memory_key}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        async with get_db_context() as db:
            result = await db.execute(
                select(AgentMemory).where(
                    AgentMemory.agent_name == agent_name,
                    AgentMemory.memory_key == memory_key,
                    (AgentMemory.expires_at == None) | (AgentMemory.expires_at > datetime.utcnow()),
                )
            )
            memory = result.scalar_one_or_none()
            if not memory:
                return None

            # Atualizar uso
            memory.usage_count += 1
            memory.last_used_at = datetime.utcnow()

            try:
                value = json.loads(memory.memory_value)
            except (json.JSONDecodeError, TypeError):
                value = memory.memory_value

            await cache.set(cache_key, value, ttl=MEMORY_CACHE_TTL)
            return value

    async def get_agent_memories(
        self,
        agent_name: str,
        memory_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> List[Dict]:
        """Busca todas as memórias de um agente."""
        async with get_db_context() as db:
            query = select(AgentMemory).where(
                AgentMemory.agent_name == agent_name,
                AgentMemory.confidence >= min_confidence,
                (AgentMemory.expires_at == None) | (AgentMemory.expires_at > datetime.utcnow()),
            )
            if memory_type:
                query = query.where(AgentMemory.memory_type == memory_type)
            query = query.order_by(AgentMemory.confidence.desc()).limit(limit)
            result = await db.execute(query)
            memories = result.scalars().all()

            import json
            output = []
            for m in memories:
                try:
                    value = json.loads(m.memory_value)
                except Exception:
                    value = m.memory_value
                output.append({
                    "key": m.memory_key,
                    "value": value,
                    "type": m.memory_type,
                    "confidence": m.confidence,
                    "usage_count": m.usage_count,
                    "last_used_at": m.last_used_at.isoformat() if m.last_used_at else None,
                })
            return output

    async def forget(self, agent_name: str, memory_key: str) -> bool:
        """Remove uma memória específica."""
        async with get_db_context() as db:
            result = await db.execute(
                select(AgentMemory).where(
                    AgentMemory.agent_name == agent_name,
                    AgentMemory.memory_key == memory_key,
                )
            )
            memory = result.scalar_one_or_none()
            if memory:
                await db.delete(memory)
                await cache.delete(f"memory:{agent_name}:{memory_key}")
                return True
        return False

    # ─── Decision Log ──────────────────────────────────────────────

    async def log_decision(
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
        """Registra uma decisão do agente."""
        async with get_db_context() as db:
            decision = DecisionLog(
                agent_name=agent_name,
                decision_type=decision_type,
                unit_id=unit_id,
                sector=sector,
                input_summary=input_summary,
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
            logger.info("decision_logged", agent=agent_name, verdict=verdict, tokens=tokens_used)
            return decision

    async def get_recent_decisions(
        self,
        agent_name: Optional[str] = None,
        verdict: Optional[str] = None,
        unit_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Busca decisões recentes para aprendizado de padrões."""
        async with get_db_context() as db:
            query = select(DecisionLog).order_by(DecisionLog.created_at.desc())
            if agent_name:
                query = query.where(DecisionLog.agent_name == agent_name)
            if verdict:
                query = query.where(DecisionLog.verdict == verdict)
            if unit_id:
                query = query.where(DecisionLog.unit_id == unit_id)
            query = query.limit(limit)
            result = await db.execute(query)
            decisions = result.scalars().all()

            return [
                {
                    "id": d.id,
                    "agent": d.agent_name,
                    "type": d.decision_type,
                    "unit_id": d.unit_id,
                    "verdict": d.verdict,
                    "confidence": d.confidence,
                    "recommendation": d.recommendation[:200],
                    "created_at": d.created_at.isoformat(),
                }
                for d in decisions
            ]

    async def get_decision_patterns(self, agent_name: str) -> Dict[str, Any]:
        """Analisa padrões de decisão de um agente (para aprendizado)."""
        async with get_db_context() as db:
            # Contar decisões por veredito
            result = await db.execute(
                select(DecisionLog.verdict, func.count(DecisionLog.id).label("count"))
                .where(DecisionLog.agent_name == agent_name)
                .group_by(DecisionLog.verdict)
            )
            verdict_counts = {row.verdict: row.count for row in result}

            # Confiança média
            result2 = await db.execute(
                select(func.avg(DecisionLog.confidence))
                .where(DecisionLog.agent_name == agent_name)
            )
            avg_confidence = result2.scalar() or 0.0

            # Tokens totais
            result3 = await db.execute(
                select(func.sum(DecisionLog.tokens_used))
                .where(DecisionLog.agent_name == agent_name)
            )
            total_tokens = result3.scalar() or 0

        return {
            "agent_name": agent_name,
            "verdict_distribution": verdict_counts,
            "avg_confidence": round(float(avg_confidence), 3),
            "total_tokens_used": total_tokens,
            "total_decisions": sum(verdict_counts.values()),
        }

    # ─── Insight History ───────────────────────────────────────────

    async def store_insight(
        self,
        agent_name: str,
        insight_type: str,
        title: str,
        description: str,
        impact_score: float = 5.0,
        unit_id: Optional[str] = None,
        sector: Optional[str] = None,
        tags: Optional[List[str]] = None,
        supporting_data: Optional[Dict] = None,
    ) -> InsightHistory:
        """Armazena um insight gerado por um agente."""
        async with get_db_context() as db:
            insight = InsightHistory(
                agent_name=agent_name,
                insight_type=insight_type,
                unit_id=unit_id,
                sector=sector,
                title=title,
                description=description,
                impact_score=impact_score,
                tags=tags or [],
                supporting_data=supporting_data or {},
            )
            db.add(insight)
            await db.flush()
            logger.info("insight_stored", agent=agent_name, title=title[:50], impact=impact_score)
            return insight

    async def get_top_insights(
        self,
        sector: Optional[str] = None,
        unit_id: Optional[str] = None,
        acted_upon: Optional[bool] = None,
        days_back: int = 30,
        limit: int = 10,
    ) -> List[Dict]:
        """Busca os insights de maior impacto."""
        async with get_db_context() as db:
            since = datetime.utcnow() - timedelta(days=days_back)
            query = (
                select(InsightHistory)
                .where(InsightHistory.created_at >= since)
                .order_by(InsightHistory.impact_score.desc())
            )
            if sector:
                query = query.where(InsightHistory.sector == sector)
            if unit_id:
                query = query.where(InsightHistory.unit_id == unit_id)
            if acted_upon is not None:
                query = query.where(InsightHistory.acted_upon == acted_upon)
            query = query.limit(limit)

            result = await db.execute(query)
            insights = result.scalars().all()

            return [
                {
                    "id": i.id,
                    "agent": i.agent_name,
                    "type": i.insight_type,
                    "title": i.title,
                    "description": i.description[:300],
                    "impact_score": i.impact_score,
                    "sector": i.sector,
                    "unit_id": i.unit_id,
                    "tags": i.tags,
                    "acted_upon": i.acted_upon,
                    "created_at": i.created_at.isoformat(),
                }
                for i in insights
            ]

    async def mark_insight_acted(self, insight_id: str) -> bool:
        """Marca um insight como aplicado."""
        async with get_db_context() as db:
            result = await db.execute(select(InsightHistory).where(InsightHistory.id == insight_id))
            insight = result.scalar_one_or_none()
            if insight:
                insight.acted_upon = True
                return True
        return False


memory_service = MemoryService()
