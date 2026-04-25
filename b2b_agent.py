"""
B2B Agent — Frank AI OS | Davvero Gelato
Franchisee acquisition marketing: lead generation, qualification, and pipeline analysis.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_AGENT, OPERATIONAL_TARGETS, BRAND, CEO_HARD_RULES

from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o especialista em Marketing B2B (Captação de Franqueados) do {BRAND["name"]}.

Suas responsabilidades:
- Estratégias de geração de leads para captação de novos franqueados
- Análise e otimização do funil B2B: Novo → Qualificado → Reunião → Proposta → Contrato → Inaugurado
- Qualificação de perfil de franqueado ideal: operador com capital disponível ≥ R$ 350.000
- Campanhas de mídia paga e orgânica direcionadas a empreendedores (LinkedIn, Meta, portais de franquia)
- Análise de CAC por canal, qualidade dos leads e taxa de conversão

Perfil ideal de franqueado (ICP):
- Capital disponível: ≥ R$ 350.000 (investimento total ~R$ 400.000–600.000)
- Preferência por operadores (quem vai gerir a loja diretamente)
- Experiência em food & beverage é diferencial, não obrigatório
- Localização: capitais e cidades com IDH alto, população ≥ 300.000 hab.

Metas:
- CAC por franqueado inaugurado: < R$ {OPERATIONAL_TARGETS.get('cac_franchisee_max', 15000)}
- Taxa de conversão funil completo: ≥ 8 %
- Meta de novos contratos: 7 por ano (para atingir 50 unidades em 5 anos)

Regras inegociáveis (CEO Hard Rules): {CEO_HARD_RULES}

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class B2BAgent(BaseAgent):
    """Handles franchisee acquisition marketing, funnel analysis, and lead quality."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[B2BAgent] query=%s", query[:120])

        # ---- Full funnel overview ----
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

        # ---- Recent leads (last 60 days) ----
        recent_rows = await self.db_fetch(
            """
            SELECT
                source,
                COUNT(*)                                    AS total,
                ROUND(AVG(score)::numeric, 1)               AS avg_score,
                ROUND(AVG(available_capital)::numeric, 0)   AS avg_capital,
                COUNT(*) FILTER (WHERE is_operator)         AS operators,
                COUNT(*) FILTER (WHERE status = 'perdido')  AS lost
            FROM leads_b2b
            WHERE first_contact >= NOW() - INTERVAL '60 days'
            GROUP BY source
            ORDER BY total DESC
            """
        )

        # ---- Conversion velocity (days in pipeline) ----
        velocity_rows = await self.db_fetch(
            """
            SELECT
                status,
                ROUND(
                    AVG(
                        EXTRACT(EPOCH FROM (last_contact - first_contact)) / 86400
                    )::numeric,
                    1
                ) AS avg_days_in_stage
            FROM leads_b2b
            WHERE status NOT IN ('perdido')
            GROUP BY status
            ORDER BY avg_days_in_stage DESC
            """
        )

        # ---- High-score leads ready for outreach ----
        hot_leads = await self.db_fetch(
            """
            SELECT
                name,
                city,
                state,
                status,
                score,
                available_capital,
                is_operator,
                has_experience,
                next_action,
                last_contact
            FROM leads_b2b
            WHERE score >= 70
              AND status IN ('novo', 'qualificado', 'reuniao')
            ORDER BY score DESC
            LIMIT 10
            """
        )

        funnel_ctx = self.format_kpi_context(funnel_rows, "Funil B2B Completo")
        recent_ctx = self.format_kpi_context(recent_rows, "Leads por Canal (60 dias)")
        velocity_ctx = self.format_kpi_context(velocity_rows, "Velocidade do Funil (dias por etapa)")
        hot_ctx = self.format_kpi_context(hot_leads, "Leads Quentes (score ≥ 70)")

        cac_target = OPERATIONAL_TARGETS.get("cac_franchisee_max", 15000)

        prompt = (
            f"Consulta de Marketing B2B:\n{query}\n\n"
            f"{funnel_ctx}\n\n"
            f"{recent_ctx}\n\n"
            f"{velocity_ctx}\n\n"
            f"{hot_ctx}\n\n"
            f"Meta de CAC: < R$ {cac_target:,.0f} por franqueado inaugurado\n"
            f"Meta de contratos/ano: {OPERATIONAL_TARGETS.get('contracts_per_year', 7)}\n\n"
            f"Contexto adicional: {context}\n\n"
            "Analise o funil de captação B2B, identifique gargalos de conversão, qualidade dos leads "
            "por canal e recomende ações de marketing e qualificação para atingir as metas."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
