# =============================================================================
# CORE/MEMORY.PY — Frank AI OS
# Sistema de Memória: contexto de curto prazo (Redis) e longo prazo (PostgreSQL)
# =============================================================================

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("frank.memory")

MAX_SHORT_TERM = 20   # máximo de mensagens no contexto de sessão
TTL_SESSION    = 3600  # 1 hora em segundos


class Memory:
    """
    Memória do Frank AI OS.

    Curto prazo  → Redis  (sessão atual, contexto da conversa)
    Longo prazo  → PostgreSQL (lições, histórico, padrões aprendidos)
    """

    def __init__(self, redis_client=None, db_pool=None):
        self.redis  = redis_client
        self.db     = db_pool

    # =========================================================================
    # CURTO PRAZO — Contexto da Sessão (Redis)
    # =========================================================================

    async def add_to_session(
        self,
        session_id: str,
        role: str,          # "user" | "assistant"
        content: str,
        director: str = "",
    ) -> None:
        """Adiciona mensagem ao contexto da sessão."""
        if not self.redis:
            return
        key = f"frank:session:{session_id}"
        entry = json.dumps({
            "role":      role,
            "content":   content[:2000],  # trunca para não explodir Redis
            "director":  director,
            "ts":        datetime.now().isoformat(),
        })
        try:
            await self.redis.rpush(key, entry)
            await self.redis.ltrim(key, -MAX_SHORT_TERM, -1)  # mantém só últimas N
            await self.redis.expire(key, TTL_SESSION)
        except Exception as e:
            logger.warning(f"Memory.add_to_session: {e}")

    async def get_session_history(self, session_id: str) -> List[Dict]:
        """Retorna histórico da sessão atual."""
        if not self.redis:
            return []
        key = f"frank:session:{session_id}"
        try:
            raw_list = await self.redis.lrange(key, 0, -1)
            return [json.loads(r) for r in raw_list]
        except Exception as e:
            logger.warning(f"Memory.get_session_history: {e}")
            return []

    async def get_session_as_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Retorna histórico no formato [{"role": ..., "content": ...}] para Anthropic."""
        history = await self.get_session_history(session_id)
        return [{"role": h["role"], "content": h["content"]} for h in history]

    async def clear_session(self, session_id: str) -> None:
        if not self.redis:
            return
        try:
            await self.redis.delete(f"frank:session:{session_id}")
        except Exception:
            pass

    # =========================================================================
    # CONTEXTO GLOBAL — Cache de KPIs e estado da empresa
    # =========================================================================

    async def set_kpi_cache(self, kpis: Dict, ttl: int = 300) -> None:
        """Cacheia snapshot de KPIs."""
        if not self.redis:
            return
        try:
            await self.redis.setex(
                "frank:kpi_snapshot", ttl,
                json.dumps(kpis, default=str)
            )
        except Exception:
            pass

    async def get_kpi_cache(self) -> Optional[Dict]:
        """Retorna KPI snapshot do cache."""
        if not self.redis:
            return None
        try:
            raw = await self.redis.get("frank:kpi_snapshot")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set_context(self, key: str, value: Any, ttl: int = 600) -> None:
        """Armazena qualquer contexto temporário."""
        if not self.redis:
            return
        try:
            await self.redis.setex(
                f"frank:ctx:{key}", ttl,
                json.dumps(value, default=str)
            )
        except Exception:
            pass

    async def get_context(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            raw = await self.redis.get(f"frank:ctx:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    # =========================================================================
    # LONGO PRAZO — Lições Aprendidas (PostgreSQL)
    # =========================================================================

    async def save_lesson(
        self,
        error_desc: str,
        correction: str,
        rule: str,
        example: Optional[str] = None,
        director: Optional[str] = None,
    ) -> Optional[str]:
        """Salva lição aprendida no banco."""
        if not self.db:
            logger.info(f"[LESSON] {rule}: {correction}")
            return None
        try:
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO frank_lessons (error_desc, correction, rule, example, director)
                    VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    error_desc, correction, rule, example, director,
                )
                return str(row["id"])
        except Exception as e:
            logger.warning(f"Memory.save_lesson: {e}")
            return None

    async def get_lessons(
        self,
        director: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Busca lições relevantes para injetar no contexto."""
        if not self.db:
            return []
        try:
            async with self.db.acquire() as conn:
                if director:
                    rows = await conn.fetch(
                        "SELECT rule, correction, example FROM frank_lessons "
                        "WHERE is_active=true AND (director=$1 OR director IS NULL) "
                        "ORDER BY created_at DESC LIMIT $2",
                        director, limit,
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT rule, correction, example FROM frank_lessons "
                        "WHERE is_active=true ORDER BY created_at DESC LIMIT $1",
                        limit,
                    )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Memory.get_lessons: {e}")
            return []

    def format_lessons_for_prompt(self, lessons: List[Dict]) -> str:
        """Formata lições para incluir no system prompt."""
        if not lessons:
            return ""
        lines = ["📚 LIÇÕES APRENDIDAS (aplicar nesta resposta):"]
        for l in lessons:
            lines.append(f"  • REGRA: {l.get('rule', '')}")
            if l.get("correction"):
                lines.append(f"    CORREÇÃO: {l['correction']}")
            if l.get("example"):
                lines.append(f"    EXEMPLO: {l['example']}")
        return "\n".join(lines)

    # =========================================================================
    # RESUMO DE CONTEXTO PARA NOVOS DIRETORES
    # =========================================================================

    async def get_enriched_context(
        self,
        session_id: str,
        director: str,
    ) -> str:
        """
        Monta contexto enriquecido para um diretor:
        - KPIs atuais
        - Histórico da sessão (resumido)
        - Lições do diretor
        """
        parts = []

        # KPIs
        kpis = await self.get_kpi_cache()
        if kpis:
            kpi_lines = ["📊 KPIs ATUAIS:"]
            for k, v in kpis.items():
                if v is not None:
                    kpi_lines.append(f"  • {k}: {v}")
            parts.append("\n".join(kpi_lines))

        # Histórico resumido (últimas 5 trocas)
        history = await self.get_session_history(session_id)
        if len(history) > 2:
            parts.append(
                f"🔄 CONTEXTO DA SESSÃO ({len(history)} trocas — mostrando últimas 3):\n"
                + "\n".join(
                    f"  [{h['role'].upper()}]: {h['content'][:150]}..."
                    for h in history[-3:]
                )
            )

        # Lições do diretor
        lessons = await self.get_lessons(director=director, limit=5)
        if lessons:
            parts.append(self.format_lessons_for_prompt(lessons))

        return "\n\n".join(parts)
