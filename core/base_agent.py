# =============================================================================
# BASE_AGENT.PY — Frank AI OS
# Classe base para todos os agentes e diretores
# =============================================================================

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import anthropic
import asyncpg
import redis.asyncio as redis

from config import ANTHROPIC_API_KEY, MODEL_AGENT, MODEL_MASTER, BRAND, OPERATIONAL_TARGETS

logger = logging.getLogger("frank.agent")


class BaseAgent:
    """
    Classe base para todos os agentes do Frank AI OS.

    Fornece:
    - Cliente Anthropic com prompt caching
    - Acesso ao DB pool e Redis (injetados pelo director)
    - Método padrão de chamada ao Claude
    - Método de formatação de resposta estruturada (10 blocos)
    """

    # Sobrescrever em cada agente
    AGENT_NAME:   str = "Base Agent"
    AGENT_ROLE:   str = "Agente Genérico"
    DIRECTOR:     str = "Frank"
    MODEL:        str = MODEL_AGENT

    # System prompt específico de cada agente (sobrescrever)
    SYSTEM_PROMPT: str = ""

    # Contexto de negócio compartilhado (inserido em todo system prompt)
    _BUSINESS_CONTEXT = f"""
════════════════════════════════════════
CONTEXTO — DAVVERO GELATO
════════════════════════════════════════
Empresa: {BRAND['name']} | {BRAND['segment']}
Sede: {BRAND['headquarters']} | Fundada: {BRAND['founded']}

Metas operacionais:
• CMV target: {OPERATIONAL_TARGETS['cmv_target_pct']}% (mercado: 35%)
• Ticket médio: R${OPERATIONAL_TARGETS['avg_ticket_target']}
• NPS: {OPERATIONAL_TARGETS['nps_target']}
• Auditoria mínima: {OPERATIONAL_TARGETS['audit_score_min']} pts
• Payback máximo: {OPERATIONAL_TARGETS['payback_max_months']} meses

Formatos: quiosque · loja pequena · loja completa · dark kitchen
Royalties: {OPERATIONAL_TARGETS['royalty_pct']}% + Fundo MKT {OPERATIONAL_TARGETS['mkt_fund_pct']}%
════════════════════════════════════════
"""

    def __init__(self):
        self.client       = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.db_pool:     Optional[asyncpg.Pool]  = None
        self.redis_client: Optional[redis.Redis]  = None

    # -------------------------------------------------------------------------
    # MÉTODO PRINCIPAL — Chama Claude com cache no system prompt
    # -------------------------------------------------------------------------

    async def call_claude(
        self,
        user_message: str,
        extra_system: str = "",
        max_tokens: int = 3000,
        model: Optional[str] = None,
    ) -> str:
        """
        Chama o Claude com prompt caching no system prompt.
        Usa o SYSTEM_PROMPT do agente + contexto de negócio compartilhado.
        """
        system_text = (
            self._BUSINESS_CONTEXT
            + "\n"
            + self.SYSTEM_PROMPT
            + ("\n\n" + extra_system if extra_system else "")
        )

        try:
            msg = await self.client.messages.create(
                model=model or self.MODEL,
                max_tokens=max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system_text,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            )
            return msg.content[0].text

        except anthropic.RateLimitError:
            logger.warning(f"{self.AGENT_NAME}: Rate limit — aguardando...")
            import asyncio
            await asyncio.sleep(5)
            return await self.call_claude(user_message, extra_system, max_tokens, model)

        except Exception as e:
            logger.error(f"{self.AGENT_NAME} erro Claude: {e}")
            return f"⚠️ {self.AGENT_NAME} indisponível temporariamente: {str(e)}"

    # -------------------------------------------------------------------------
    # HELPERS DE DB
    # -------------------------------------------------------------------------

    async def db_fetch(self, query: str, *args) -> List[Dict]:
        """Executa query e retorna lista de dicts."""
        if not self.db_pool:
            return []
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"{self.AGENT_NAME} DB query error: {e}")
            return []

    async def db_fetchrow(self, query: str, *args) -> Optional[Dict]:
        """Executa query e retorna primeiro resultado como dict."""
        if not self.db_pool:
            return None
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.warning(f"{self.AGENT_NAME} DB fetchrow error: {e}")
            return None

    async def db_execute(self, query: str, *args) -> bool:
        """Executa DML (INSERT/UPDATE/DELETE)."""
        if not self.db_pool:
            return False
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(query, *args)
                return True
        except Exception as e:
            logger.warning(f"{self.AGENT_NAME} DB execute error: {e}")
            return False

    # -------------------------------------------------------------------------
    # HELPERS DE CACHE
    # -------------------------------------------------------------------------

    async def cache_get(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            return None
        try:
            val = await self.redis_client.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None

    async def cache_set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self.redis_client:
            return
        try:
            await self.redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # FORMATAÇÃO DE CONTEXTO
    # -------------------------------------------------------------------------

    def format_kpi_context(self, kpi_data: Optional[Dict]) -> str:
        """Formata KPIs para incluir no prompt."""
        if not kpi_data:
            return "KPIs: não disponíveis no momento."
        lines = ["📊 KPIs ATUAIS DA REDE:"]
        for k, v in kpi_data.items():
            if v is not None:
                lines.append(f"  • {k}: {v}")
        return "\n".join(lines)

    def format_db_data(self, data: List[Dict], title: str = "Dados") -> str:
        """Formata dados do DB para incluir no prompt."""
        if not data:
            return f"{title}: nenhum dado encontrado."
        lines = [f"📋 {title.upper()}:"]
        for row in data[:20]:  # Limita a 20 linhas
            row_str = " | ".join(f"{k}: {v}" for k, v in row.items() if v is not None)
            lines.append(f"  • {row_str}")
        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # MÉTODO PRINCIPAL DO AGENTE (sobrescrever nos agentes)
    # -------------------------------------------------------------------------

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        """
        Método principal a ser implementado por cada agente.
        Por padrão, chama Claude com o question + KPIs.
        """
        kpi_str = self.format_kpi_context(kpi_context)
        prompt = f"{kpi_str}\n\nPergunta de {user}: {question}"
        return await self.call_claude(prompt)

    async def close(self):
        await self.client.close()
