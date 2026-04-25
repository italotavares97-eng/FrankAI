"""
B2C Agent — Frank AI OS | Davvero Gelato
Consumer marketing: promotions, loyalty programs, and seasonal campaigns.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_AGENT, OPERATIONAL_TARGETS, BRAND

from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o especialista em Marketing B2C do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Suas responsabilidades:
- Criar e otimizar promoções para consumidores finais nas unidades físicas
- Desenvolver programas de fidelidade que aumentem recorrência e ticket médio
- Planejar campanhas sazonais (verão, Carnaval, Dia dos Namorados, Natal, etc.)
- Analisar comportamento do consumidor brasileiro no segmento sorvetes/gelato premium
- Segmentar clientes por perfil (VIP, Recorrente, Novo, Dormente) e propor ações

Contexto do negócio:
- Produto premium com ticket médio elevado; cliente busca experiência, não apenas sorvete
- Público-alvo: classes A e B em regiões com alto IDH
- Sazonalidade forte: verão (out–mar) representa ~65 % do faturamento anual
- Meta NPS: ≥ 80 | Meta LTV por cliente VIP: R$ 2.400/ano

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class B2CAgent(BaseAgent):
    """Handles consumer-facing marketing analysis and campaign planning."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[B2CAgent] query=%s", query[:120])

        # ---- Customer segment breakdown ----
        segment_rows = await self.db_fetch(
            """
            SELECT
                segment,
                COUNT(*)                                AS qty,
                ROUND(AVG(visit_count)::numeric, 1)     AS avg_visits,
                ROUND(AVG(total_spent)::numeric, 2)     AS avg_spent,
                ROUND(AVG(avg_ticket)::numeric, 2)      AS avg_ticket,
                ROUND(AVG(ltv)::numeric, 2)             AS avg_ltv,
                ROUND(AVG(nps_score)::numeric, 1)       AS avg_nps
            FROM customers
            GROUP BY segment
            ORDER BY avg_ltv DESC
            """
        )

        # ---- Top performing units by consumer volume ----
        unit_rows = await self.db_fetch(
            """
            SELECT
                u.code,
                u.name,
                u.city,
                u.state,
                COUNT(c.unit_id)                        AS total_customers,
                ROUND(AVG(c.nps_score)::numeric, 1)     AS avg_nps,
                ROUND(SUM(c.total_spent)::numeric, 2)   AS total_revenue_customers
            FROM units u
            LEFT JOIN customers c ON c.unit_id = u.id
            GROUP BY u.id, u.code, u.name, u.city, u.state
            ORDER BY total_customers DESC
            LIMIT 10
            """
        )

        # ---- Dormant customers (win-back candidates) ----
        dormant_rows = await self.db_fetch(
            """
            SELECT
                COUNT(*)                                AS dormant_total,
                ROUND(AVG(total_spent)::numeric, 2)     AS avg_historical_spend,
                ROUND(AVG(ltv)::numeric, 2)             AS avg_ltv
            FROM customers
            WHERE segment = 'dormente'
            """
        )

        # ---- VIP customer details ----
        vip_rows = await self.db_fetch(
            """
            SELECT
                COUNT(*)                                AS vip_total,
                ROUND(AVG(visit_count)::numeric, 1)     AS avg_visits,
                ROUND(AVG(avg_ticket)::numeric, 2)      AS avg_ticket,
                ROUND(AVG(ltv)::numeric, 2)             AS avg_ltv,
                ROUND(AVG(nps_score)::numeric, 1)       AS avg_nps
            FROM customers
            WHERE segment = 'vip'
            """
        )

        seg_ctx = self.format_kpi_context(segment_rows, "Segmentação de Clientes")
        unit_ctx = self.format_kpi_context(unit_rows, "Performance por Unidade (consumidores)")
        dormant_ctx = self.format_kpi_context(dormant_rows, "Clientes Dormentes")
        vip_ctx = self.format_kpi_context(vip_rows, "Clientes VIP")

        prompt = (
            f"Consulta de Marketing B2C:\n{query}\n\n"
            f"{seg_ctx}\n\n"
            f"{unit_ctx}\n\n"
            f"{dormant_ctx}\n\n"
            f"{vip_ctx}\n\n"
            f"Metas operacionais: NPS ≥ {OPERATIONAL_TARGETS.get('nps_min', 80)} | "
            f"LTV VIP target: R$ {OPERATIONAL_TARGETS.get('ltv_vip_target', 2400)}/ano\n\n"
            f"Contexto adicional: {context}\n\n"
            "Com base nos dados acima, elabore a análise de marketing B2C no formato padrão. "
            "Inclua ações específicas para cada segmento, campanhas sazonais relevantes e métricas de sucesso."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
