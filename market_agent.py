"""
Market Agent — Frank AI OS | Davvero Gelato
Market analysis: white space identification, city scoring, competitive landscape.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_AGENT, OPERATIONAL_TARGETS, BRAND

from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Reference: Brazilian cities with high potential (IDH ≥ 0.75, pop ≥ 300k)
# Used to cross-reference against existing presence and pipeline
HIGH_POTENTIAL_STATES = [
    "SP", "RJ", "MG", "RS", "PR", "SC", "DF", "GO", "BA", "PE"
]

SYSTEM_PROMPT = f"""
Você é o especialista em Análise de Mercado do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Suas responsabilidades:
- Mapear oportunidades de expansão por cidade/região (white space analysis)
- Analisar densidade de unidades existentes e riscos de canibalismo
- Identificar praças com alto potencial: IDH ≥ 0,75, população ≥ 300.000, renda per capita elevada
- Avaliar presença de concorrentes (sorveteiros premium, gelaterias, froyo)
- Priorizar mercados para prospecção ativa de franqueados
- Monitorar tendências de consumo premium no segmento gelato/sorvete artesanal no Brasil

Critérios de atratividade de mercado:
1. Demográfico: população, renda, IDH, classe social A/B
2. Competitivo: saturação do mercado, presença de concorrentes diretos
3. Operacional: custo de aluguel comercial, disponibilidade de mão de obra qualificada
4. Estratégico: alinhamento com rotas logísticas de supply chain, presença de leads no pipeline

Metas de expansão:
- {OPERATIONAL_TARGETS.get('target_units', 50)} unidades em {OPERATIONAL_TARGETS.get('expansion_years', 5)} anos
- Prioridade para capitais e cidades satélite de alta renda
- Mínimo 2 estados novos por ano nos próximos 3 anos

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class MarketAgent(BaseAgent):
    """Handles market analysis, white space identification, and opportunity mapping."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[MarketAgent] query=%s", query[:120])

        # ---- Current unit geographic distribution ----
        unit_geo_rows = await self.db_fetch(
            """
            SELECT
                state,
                COUNT(*)                                            AS units,
                COUNT(DISTINCT city)                                AS cities,
                MIN(opening_date)                                   AS first_opening,
                MAX(opening_date)                                   AS last_opening
            FROM units
            GROUP BY state
            ORDER BY units DESC
            """
        )

        # ---- Cities with existing units ----
        city_rows = await self.db_fetch(
            """
            SELECT
                city,
                state,
                COUNT(*)        AS units_in_city,
                format
            FROM units
            GROUP BY city, state, format
            ORDER BY units_in_city DESC
            """
        )

        # ---- Lead pipeline geographic distribution (demand signal) ----
        lead_geo_rows = await self.db_fetch(
            """
            SELECT
                state,
                city,
                COUNT(*)                                            AS leads,
                ROUND(AVG(available_capital)::numeric, 0)           AS avg_capital,
                COUNT(*) FILTER (WHERE status IN ('qualificado',
                    'reuniao', 'proposta', 'contrato'))              AS active_pipeline,
                COUNT(*) FILTER (WHERE is_operator)                 AS operators,
                ROUND(AVG(score)::numeric, 1)                       AS avg_score
            FROM leads_b2b
            WHERE status NOT IN ('perdido', 'inaugurado')
            GROUP BY state, city
            ORDER BY leads DESC
            LIMIT 30
            """
        )

        # ---- States with leads but no units (white space) ----
        white_space_rows = await self.db_fetch(
            """
            SELECT DISTINCT
                l.state,
                COUNT(l.id)                                         AS leads_in_state,
                ROUND(AVG(l.available_capital)::numeric, 0)         AS avg_capital,
                ROUND(AVG(l.score)::numeric, 1)                     AS avg_score
            FROM leads_b2b l
            WHERE l.status NOT IN ('perdido')
              AND l.state NOT IN (SELECT DISTINCT state FROM units)
            GROUP BY l.state
            ORDER BY leads_in_state DESC
            """
        )

        # ---- Cities with multiple leads (demand concentration) ----
        demand_cluster_rows = await self.db_fetch(
            """
            SELECT
                city,
                state,
                COUNT(*)                                            AS lead_count,
                ROUND(AVG(available_capital)::numeric, 0)           AS avg_capital,
                COUNT(*) FILTER (WHERE score >= 70)                 AS hot_leads
            FROM leads_b2b
            WHERE status NOT IN ('perdido')
            GROUP BY city, state
            HAVING COUNT(*) >= 2
            ORDER BY lead_count DESC, hot_leads DESC
            LIMIT 20
            """
        )

        geo_ctx = self.format_kpi_context(unit_geo_rows, "Distribuição Geográfica das Unidades")
        city_ctx = self.format_kpi_context(city_rows, "Cidades com Unidades Ativas")
        lead_geo_ctx = self.format_kpi_context(lead_geo_rows, "Pipeline por Cidade/Estado")
        white_ctx = self.format_kpi_context(white_space_rows, "White Space — Estados com Leads sem Unidades")
        cluster_ctx = self.format_kpi_context(demand_cluster_rows, "Clusters de Demanda (múltiplos leads)")

        high_potential_str = ", ".join(HIGH_POTENTIAL_STATES)

        prompt = (
            f"Consulta de Análise de Mercado:\n{query}\n\n"
            f"{geo_ctx}\n\n"
            f"{city_ctx}\n\n"
            f"{lead_geo_ctx}\n\n"
            f"{white_ctx}\n\n"
            f"{cluster_ctx}\n\n"
            f"Estados de alto potencial para expansão: {high_potential_str}\n"
            f"Meta: {OPERATIONAL_TARGETS.get('target_units', 50)} unidades em "
            f"{OPERATIONAL_TARGETS.get('expansion_years', 5)} anos\n\n"
            f"Contexto adicional: {context}\n\n"
            "Analise as oportunidades de mercado, priorize cidades/estados para expansão imediata, "
            "identifique white spaces com demanda comprovada (leads no pipeline), "
            "e recomende estratégia de entrada com critérios claros de go/no-go por praça."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
