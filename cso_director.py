"""
CSO Director — Frank AI OS | Davvero Gelato
Commercial / Sales / Expansion director: routes to MarketAgent, LeadsAgent, ExpansionAgent.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_MASTER, OPERATIONAL_TARGETS, BRAND, CEO_HARD_RULES

from core.base_agent import BaseAgent
from market_agent import MarketAgent
from leads_agent import LeadsAgent
from expansion_agent import ExpansionAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o Diretor Comercial (CSO) do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Sua função é coordenar as frentes de crescimento e expansão da rede:
- MarketAgent: análise de mercado, mapeamento de oportunidades, white space, concorrência
- LeadsAgent: pipeline comercial de franqueados, qualificação, follow-up, fechamento
- ExpansionAgent: viabilidade de novas unidades, ROI, ponto comercial, regras do CEO

Visão estratégica de expansão:
- Meta: 50 unidades em 5 anos (atual ~15 unidades)
- Ritmo necessário: ~7 inaugurações/ano
- Critérios de mercado: cidades com IDH ≥ 0,75, população ≥ 300.000, sem canibalismo interno
- Investimento total por unidade: R$ 400.000–600.000
- Payback target: ≤ 36 meses

Regras inegociáveis (CEO Hard Rules): {CEO_HARD_RULES}

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""

ROUTING_RULES: list[tuple[list[str], str]] = [
    (["mercado", "oportunidade", "cidade", "região", "white space", "concorrência",
      "análise de mercado", "mapeamento", "praça"], "market"),
    (["lead", "pipeline", "prospecção", "follow-up", "fechamento", "proposta",
      "reunião", "qualificação", "franqueado", "contrato", "venda"], "leads"),
    (["expansão", "nova unidade", "roi", "viabilidade", "ponto comercial",
      "inauguração", "payback", "investimento", "retorno"], "expansion"),
]


class CSODirector(BaseAgent):
    """
    Chief Sales Officer director agent.
    Analyses the incoming request and delegates to the correct commercial specialist.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_MASTER
        self.system_prompt = SYSTEM_PROMPT
        self._agents: dict[str, BaseAgent] = {}

    def _get_agent(self, key: str) -> BaseAgent:
        if key not in self._agents:
            mapping = {
                "market": MarketAgent,
                "leads": LeadsAgent,
                "expansion": ExpansionAgent,
            }
            self._agents[key] = mapping[key]()
        return self._agents[key]

    def _route(self, query: str) -> str | None:
        q = query.lower()
        scores: dict[str, int] = {}
        for keywords, agent_key in ROUTING_RULES:
            hit = sum(1 for kw in keywords if kw in q)
            if hit:
                scores[agent_key] = scores.get(agent_key, 0) + hit
        return max(scores, key=scores.__getitem__) if scores else None

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[CSODirector] query=%s", query[:120])

        # ---- Commercial overview: pipeline + expansion status ----
        pipeline_rows = await self.db_fetch(
            """
            SELECT
                status,
                COUNT(*)                                    AS total,
                ROUND(AVG(score)::numeric, 1)               AS avg_score,
                ROUND(AVG(available_capital)::numeric, 0)   AS avg_capital
            FROM leads_b2b
            GROUP BY status
            ORDER BY
                CASE status
                    WHEN 'novo'        THEN 1
                    WHEN 'qualificado' THEN 2
                    WHEN 'reuniao'     THEN 3
                    WHEN 'proposta'    THEN 4
                    WHEN 'contrato'    THEN 5
                    WHEN 'inaugurado'  THEN 6
                    WHEN 'perdido'     THEN 7
                    ELSE 8
                END
            """
        )

        expansion_rows = await self.db_fetch(
            """
            SELECT
                COUNT(*)                                            AS total_units,
                COUNT(*) FILTER (
                    WHERE opening_date >= NOW() - INTERVAL '12 months'
                )                                                   AS opened_last_12m,
                COUNT(DISTINCT state)                               AS states_covered,
                COUNT(DISTINCT city)                                AS cities_covered
            FROM units
            """
        )

        pipeline_ctx = self.format_kpi_context(pipeline_rows, "Pipeline Comercial")
        expansion_ctx = self.format_kpi_context(expansion_rows, "Status de Expansão da Rede")

        agent_key = self._route(query)
        if agent_key:
            logger.info("[CSODirector] routing to agent=%s", agent_key)
            specialist_response = await self._get_agent(agent_key).analyze(query, context)
        else:
            specialist_response = None

        routing_note = (
            f"\n\n[Agente especialista consultado: {agent_key.upper()}]\n{specialist_response}"
            if specialist_response
            else "\n\n[Nenhum agente especialista identificado — respondendo diretamente como CSO.]"
        )

        meta_units = OPERATIONAL_TARGETS.get("target_units", 50)
        meta_years = OPERATIONAL_TARGETS.get("expansion_years", 5)

        prompt = (
            f"Consulta recebida pelo CSO:\n{query}\n\n"
            f"{pipeline_ctx}\n\n"
            f"{expansion_ctx}\n\n"
            f"Meta de expansão: {meta_units} unidades em {meta_years} anos\n"
            f"Contexto adicional: {context}\n"
            f"{routing_note}\n\n"
            "Sintetize a visão estratégica comercial, valide ou complemente a análise do agente especialista "
            "e apresente a decisão executiva no formato padrão."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
