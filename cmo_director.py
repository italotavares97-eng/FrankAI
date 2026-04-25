"""
CMO Director — Frank AI OS | Davvero Gelato
Routes marketing requests to the appropriate specialist agent.
"""

from __future__ import annotations

import re
import logging
from typing import Any

from config import MODEL_MASTER, BRAND
from core.base_agent import BaseAgent
from b2c_agent import B2CAgent
from b2b_agent import B2BAgent
from content_agent import ContentAgent
from crm_agent import CRMAgent
from paid_media_agent import PaidMediaAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o Diretor de Marketing do {BRAND["name"]}, uma franquia premium de gelato italiano no Brasil.

Sua função é diagnosticar a demanda recebida e direcionar para o agente especialista correto:
- B2CAgent: marketing para consumidores finais, promoções, campanhas sazonais, fidelidade
- B2BAgent: aquisição de novos franqueados, geração de leads B2B, qualificação
- ContentAgent: estratégia de conteúdo, redes sociais, identidade visual, calendário editorial
- CRMAgent: retenção de clientes, segmentação, LTV, campanhas de reativação
- PaidMediaAgent: performance de mídia paga, Meta Ads, CPL, ROAS, otimização de verba

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO

Seja estratégico, orientado a dados e alinhado à visão premium da marca {BRAND["name"]}.
"""

ROUTING_RULES: list[tuple[list[str], str]] = [
    (["consumidor", "b2c", "promoção", "campanha sazonal", "fidelidade", "cliente final", "loja"], "b2c"),
    (["franqueado", "b2b", "lead b2b", "captação", "aquisição", "franquia", "investidor"], "b2b"),
    (["conteúdo", "instagram", "social media", "post", "calendário", "editorial", "brand"], "content"),
    (["crm", "retenção", "segmentação", "ltv", "reativação", "churn", "vip", "recorrente"], "crm"),
    (["meta ads", "anúncio", "paid media", "cpl", "roas", "tráfego pago", "campanha paga", "verba"], "paid_media"),
]


class CMODirector(BaseAgent):
    """
    Chief Marketing Officer director agent.
    Analyses the incoming request and delegates to the correct specialist.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_MASTER
        self.system_prompt = SYSTEM_PROMPT
        self._agents: dict[str, BaseAgent] = {}

    # ------------------------------------------------------------------
    # Lazy agent instantiation
    # ------------------------------------------------------------------
    def _get_agent(self, key: str) -> BaseAgent:
        if key not in self._agents:
            mapping = {
                "b2c": B2CAgent,
                "b2b": B2BAgent,
                "content": ContentAgent,
                "crm": CRMAgent,
                "paid_media": PaidMediaAgent,
            }
            self._agents[key] = mapping[key]()
        return self._agents[key]

    # ------------------------------------------------------------------
    # Routing logic
    # ------------------------------------------------------------------
    def _route(self, query: str) -> str | None:
        """Return the agent key that best matches the query."""
        q = query.lower()
        scores: dict[str, int] = {}
        for keywords, agent_key in ROUTING_RULES:
            hit = sum(1 for kw in keywords if kw in q)
            if hit:
                scores[agent_key] = scores.get(agent_key, 0) + hit
        return max(scores, key=scores.__getitem__) if scores else None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[CMODirector] query=%s", query[:120])

        # Fetch high-level marketing KPIs for the director overview
        kpi_rows = await self.db_fetch(
            """
            SELECT
                COUNT(*)                                            AS total_leads_b2b,
                COUNT(*) FILTER (WHERE status = 'qualificado')     AS leads_qualificados,
                COUNT(*) FILTER (WHERE status = 'reuniao')         AS em_reuniao,
                COUNT(*) FILTER (WHERE status = 'contrato')        AS contratos,
                ROUND(AVG(score)::numeric, 1)                      AS avg_score
            FROM leads_b2b
            WHERE first_contact >= NOW() - INTERVAL '90 days'
            """
        )

        customer_rows = await self.db_fetch(
            """
            SELECT
                segment,
                COUNT(*)                        AS qty,
                ROUND(AVG(ltv)::numeric, 2)     AS avg_ltv,
                ROUND(AVG(nps_score)::numeric, 1) AS avg_nps
            FROM customers
            GROUP BY segment
            ORDER BY avg_ltv DESC
            """
        )

        kpi_ctx = self.format_kpi_context(kpi_rows, "Leads B2B (90 dias)")
        customer_ctx = self.format_kpi_context(customer_rows, "Segmentos de Clientes")

        # Determine which specialist should handle the query
        agent_key = self._route(query)

        if agent_key:
            logger.info("[CMODirector] routing to agent=%s", agent_key)
            specialist_response = await self._get_agent(agent_key).analyze(query, context)
        else:
            specialist_response = None

        # Build director-level synthesis prompt
        routing_note = (
            f"\n\n[Agente especialista consultado: {agent_key.upper()}]\n{specialist_response}"
            if specialist_response
            else "\n\n[Nenhum agente especialista identificado — respondendo diretamente como CMO.]"
        )

        prompt = (
            f"Consulta recebida pelo CMO:\n{query}\n\n"
            f"{kpi_ctx}\n\n"
            f"{customer_ctx}\n\n"
            f"Contexto adicional: {context}\n"
            f"{routing_note}\n\n"
            "Sintetize a visão estratégica de marketing, valide ou complemente a análise do agente especialista "
            "e apresente a decisão executiva no formato padrão."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
