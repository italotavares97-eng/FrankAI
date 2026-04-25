"""
Leads Agent — Frank AI OS | Davvero Gelato
B2B franchise sales pipeline: qualification, follow-up, and deal management.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_AGENT, OPERATIONAL_TARGETS, BRAND, CEO_HARD_RULES

from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o especialista em Vendas B2B e Gestão de Pipeline do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Suas responsabilidades:
- Gerenciar o pipeline comercial de captação de franqueados do início ao fim
- Qualificar leads com base em capital disponível, perfil operacional e fit com a marca
- Priorizar leads quentes e recomendar próximas ações (ligação, reunião, proposta, contrato)
- Identificar leads estagnados e recomendar estratégias de reativação ou descarte
- Analisar taxas de conversão entre etapas e propor melhorias no processo de vendas
- Garantir SLA de follow-up: contato em até 24h para novos leads

Funil de vendas B2B:
Novo → Qualificado → Reunião → Proposta → Contrato → Inaugurado

Critérios de qualificação (BANT adaptado):
- Budget: capital disponível ≥ R$ 350.000
- Authority: tomador de decisão direto (não intermediário)
- Need: motivação clara (empreender, diversificar renda, lifestyle)
- Timeline: horizonte de 6–18 meses para inauguração
- Bonus: is_operator (vai gerenciar a loja) aumenta score significativamente

Score de qualificação:
- 90–100: lead quente — acionar imediatamente
- 70–89: lead morno — agendar reunião na semana
- 50–69: lead frio — nutrir com conteúdo e re-qualificar em 30 dias
- < 50: lead desqualificado — manter em nurturing passivo

Metas de vendas:
- Contratos fechados/mês: {round(OPERATIONAL_TARGETS.get('contracts_per_year', 7) / 12, 1)}
- Taxa de conversão Qualificado → Contrato: ≥ 25 %
- SLA de 1º contato com lead novo: ≤ 24 horas
- Ciclo médio de vendas: ≤ 90 dias do 1º contato ao contrato

Regras inegociáveis (CEO Hard Rules): {CEO_HARD_RULES}

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class LeadsAgent(BaseAgent):
    """Handles B2B franchise sales pipeline analysis and lead management."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[LeadsAgent] query=%s", query[:120])

        # ---- Full funnel from view ----
        funnel_rows = await self.db_fetch(
            """
            SELECT
                status,
                total,
                avg_capital,
                operators,
                with_experience
            FROM vw_leads_funnel
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

        # ---- Leads requiring immediate action (overdue follow-up) ----
        overdue_rows = await self.db_fetch(
            """
            SELECT
                id,
                name,
                city,
                state,
                status,
                score,
                available_capital,
                is_operator,
                next_action,
                last_contact,
                assigned_to,
                (NOW() - last_contact)::text    AS time_since_contact
            FROM leads_b2b
            WHERE
                status NOT IN ('inaugurado', 'perdido', 'contrato')
                AND last_contact < NOW() - INTERVAL '7 days'
            ORDER BY score DESC, last_contact ASC
            LIMIT 15
            """
        )

        # ---- Hot leads (score ≥ 70, active status) ----
        hot_rows = await self.db_fetch(
            """
            SELECT
                id,
                name,
                city,
                state,
                status,
                score,
                available_capital,
                is_operator,
                has_experience,
                source,
                next_action,
                first_contact,
                last_contact
            FROM leads_b2b
            WHERE score >= 70
              AND status IN ('novo', 'qualificado', 'reuniao', 'proposta')
            ORDER BY score DESC, last_contact DESC
            LIMIT 10
            """
        )

        # ---- Stagnant leads (same status for too long) ----
        stagnant_rows = await self.db_fetch(
            """
            SELECT
                status,
                COUNT(*)                                                AS qty,
                ROUND(
                    AVG(
                        EXTRACT(EPOCH FROM (NOW() - last_contact)) / 86400
                    )::numeric, 1
                )                                                       AS avg_days_stagnant,
                ROUND(AVG(score)::numeric, 1)                           AS avg_score
            FROM leads_b2b
            WHERE
                status NOT IN ('inaugurado', 'perdido', 'contrato')
                AND last_contact < NOW() - INTERVAL '14 days'
            GROUP BY status
            ORDER BY avg_days_stagnant DESC
            """
        )

        # ---- Conversion rate calculation (step by step) ----
        conversion_rows = await self.db_fetch(
            """
            WITH stage_counts AS (
                SELECT
                    status,
                    COUNT(*) AS qty
                FROM leads_b2b
                GROUP BY status
            )
            SELECT
                status,
                qty,
                ROUND(
                    100.0 * qty / NULLIF(
                        LAG(qty) OVER (ORDER BY
                            CASE status
                                WHEN 'novo'        THEN 1
                                WHEN 'qualificado' THEN 2
                                WHEN 'reuniao'     THEN 3
                                WHEN 'proposta'    THEN 4
                                WHEN 'contrato'    THEN 5
                                WHEN 'inaugurado'  THEN 6
                                ELSE 99
                            END
                        ), 0
                    ), 1
                )                                   AS conversion_from_prev_pct
            FROM stage_counts
            ORDER BY
                CASE status
                    WHEN 'novo'        THEN 1
                    WHEN 'qualificado' THEN 2
                    WHEN 'reuniao'     THEN 3
                    WHEN 'proposta'    THEN 4
                    WHEN 'contrato'    THEN 5
                    WHEN 'inaugurado'  THEN 6
                    ELSE 99
                END
            """
        )

        funnel_ctx = self.format_kpi_context(funnel_rows, "Funil Completo")
        overdue_ctx = self.format_kpi_context(overdue_rows, "Leads com Follow-up Atrasado (> 7 dias)")
        hot_ctx = self.format_kpi_context(hot_rows, "Leads Quentes (score ≥ 70)")
        stagnant_ctx = self.format_kpi_context(stagnant_rows, "Leads Estagnados (> 14 dias sem movimento)")
        conv_ctx = self.format_kpi_context(conversion_rows, "Taxas de Conversão por Etapa")

        contracts_per_month = round(OPERATIONAL_TARGETS.get("contracts_per_year", 7) / 12, 1)

        prompt = (
            f"Consulta de Pipeline de Vendas B2B:\n{query}\n\n"
            f"{funnel_ctx}\n\n"
            f"{conv_ctx}\n\n"
            f"{hot_ctx}\n\n"
            f"{overdue_ctx}\n\n"
            f"{stagnant_ctx}\n\n"
            f"Meta: {contracts_per_month} contratos/mês | "
            f"SLA de 1º contato: 24h | Ciclo médio: ≤ 90 dias\n\n"
            f"Contexto adicional: {context}\n\n"
            "Analise o pipeline comercial, priorize as ações de follow-up urgentes, "
            "identifique gargalos de conversão, e elabore o plano de ação semanal da equipe comercial "
            "para maximizar contratos fechados no menor ciclo possível."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
