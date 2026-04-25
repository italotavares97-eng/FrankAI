"""
CRM Agent — Frank AI OS | Davvero Gelato
Customer retention, segmentation, LTV optimization, and win-back campaigns.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_AGENT, OPERATIONAL_TARGETS, BRAND

from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o especialista em CRM e Retenção de Clientes do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Suas responsabilidades:
- Analisar e otimizar o ciclo de vida do cliente (CLV/LTV)
- Desenvolver estratégias de segmentação: VIP, Recorrente, Novo, Dormente
- Criar campanhas de win-back para clientes dormentes
- Recomendar programas de fidelidade e regras de pontuação
- Identificar comportamentos de churn precoce e acionar prevenção
- Monitorar NPS e transformar detratores em promotores

Segmentos e critérios:
- VIP: ≥ 12 visitas/ano ou ticket médio ≥ R$ 80; NPS promotor esperado ≥ 85
- Recorrente: 5–11 visitas/ano; ticket médio ≥ R$ 45
- Novo: até 4 visitas; em fase de educação e formação de hábito
- Dormente: sem visita há ≥ 90 dias; requer campanha de reativação

Metas de CRM:
- NPS geral: ≥ {OPERATIONAL_TARGETS.get('nps_min', 80)}
- Taxa de retenção anual: ≥ 65 %
- Conversão Novo → Recorrente: ≥ 40 %
- LTV médio VIP: R$ {OPERATIONAL_TARGETS.get('ltv_vip_target', 2400)}/ano

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class CRMAgent(BaseAgent):
    """Handles customer retention, segmentation analysis, and loyalty strategy."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[CRMAgent] query=%s", query[:120])

        # ---- Full segment distribution ----
        segment_rows = await self.db_fetch(
            """
            SELECT
                segment,
                COUNT(*)                                    AS qty,
                ROUND(AVG(visit_count)::numeric, 1)         AS avg_visits,
                ROUND(AVG(avg_ticket)::numeric, 2)          AS avg_ticket,
                ROUND(AVG(total_spent)::numeric, 2)         AS avg_spent,
                ROUND(AVG(ltv)::numeric, 2)                 AS avg_ltv,
                ROUND(AVG(nps_score)::numeric, 1)           AS avg_nps,
                ROUND(
                    100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
                    1
                )                                           AS pct_of_total
            FROM customers
            GROUP BY segment
            ORDER BY avg_ltv DESC
            """
        )

        # ---- NPS distribution ----
        nps_rows = await self.db_fetch(
            """
            SELECT
                CASE
                    WHEN nps_score >= 9 THEN 'promotor'
                    WHEN nps_score >= 7 THEN 'neutro'
                    ELSE 'detrator'
                END                                         AS nps_category,
                COUNT(*)                                    AS qty,
                ROUND(AVG(ltv)::numeric, 2)                 AS avg_ltv,
                ROUND(AVG(visit_count)::numeric, 1)         AS avg_visits
            FROM customers
            WHERE nps_score IS NOT NULL
            GROUP BY nps_category
            ORDER BY qty DESC
            """
        )

        # ---- Dormant customers with high historical value ----
        winback_rows = await self.db_fetch(
            """
            SELECT
                u.name                                      AS unit,
                COUNT(c.unit_id)                            AS dormant_count,
                ROUND(AVG(c.total_spent)::numeric, 2)       AS avg_historical_spend,
                ROUND(AVG(c.ltv)::numeric, 2)               AS avg_ltv,
                ROUND(AVG(c.nps_score)::numeric, 1)         AS last_nps
            FROM customers c
            JOIN units u ON u.id = c.unit_id
            WHERE c.segment = 'dormente'
            GROUP BY u.name
            ORDER BY dormant_count DESC
            LIMIT 10
            """
        )

        # ---- LTV distribution by unit ----
        ltv_rows = await self.db_fetch(
            """
            SELECT
                u.code,
                u.name,
                u.city,
                ROUND(AVG(c.ltv)::numeric, 2)               AS avg_ltv,
                ROUND(MAX(c.ltv)::numeric, 2)               AS max_ltv,
                COUNT(c.unit_id)                            AS customers,
                ROUND(AVG(c.nps_score)::numeric, 1)         AS avg_nps
            FROM customers c
            JOIN units u ON u.id = c.unit_id
            GROUP BY u.id, u.code, u.name, u.city
            ORDER BY avg_ltv DESC
            """
        )

        seg_ctx = self.format_kpi_context(segment_rows, "Distribuição por Segmento")
        nps_ctx = self.format_kpi_context(nps_rows, "Distribuição NPS (Promotor/Neutro/Detrator)")
        winback_ctx = self.format_kpi_context(winback_rows, "Dormentes por Unidade (candidatos a win-back)")
        ltv_ctx = self.format_kpi_context(ltv_rows, "LTV Médio por Unidade")

        nps_target = OPERATIONAL_TARGETS.get("nps_min", 80)
        ltv_target = OPERATIONAL_TARGETS.get("ltv_vip_target", 2400)

        prompt = (
            f"Consulta de CRM e Retenção:\n{query}\n\n"
            f"{seg_ctx}\n\n"
            f"{nps_ctx}\n\n"
            f"{winback_ctx}\n\n"
            f"{ltv_ctx}\n\n"
            f"Metas: NPS ≥ {nps_target} | LTV VIP ≥ R$ {ltv_target}/ano | "
            f"Retenção anual ≥ 65 % | Conversão Novo→Recorrente ≥ 40 %\n\n"
            f"Contexto adicional: {context}\n\n"
            "Analise a saúde da base de clientes, identifique segmentos prioritários para ação, "
            "proponha campanhas de win-back específicas, ajustes no programa de fidelidade "
            "e iniciativas para elevar NPS e LTV."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
