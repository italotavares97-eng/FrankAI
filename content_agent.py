"""
Content Agent — Frank AI OS | Davvero Gelato
Content strategy for social media, digital channels, and brand storytelling.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from config import MODEL_AGENT, BRAND

from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Seasonal content calendar reference
SEASONAL_MOMENTS = [
    {"month": 1,  "moment": "Verão pleno — gelato no calor, campanhas de consumo diário"},
    {"month": 2,  "moment": "Carnaval — sabores especiais, promoções de grupo"},
    {"month": 3,  "moment": "Início de outono — transição, conteúdo de lifestyle"},
    {"month": 4,  "moment": "Páscoa — sabores de chocolate, edições limitadas"},
    {"month": 5,  "moment": "Dia das Mães — presentes, experiências, embalagens especiais"},
    {"month": 6,  "moment": "Festa Junina — sabores regionais, conteúdo cultural"},
    {"month": 7,  "moment": "Férias escolares — família, crianças, promoções de combo"},
    {"month": 8,  "moment": "Agosto — mês do gelato artesanal, educação de produto"},
    {"month": 9,  "moment": "Primavera — lançamento de sabores florais/cítricos"},
    {"month": 10, "moment": "Início do verão — retomada de volume, campanhas agressivas"},
    {"month": 11, "moment": "Novembro — Black Friday gelato, programas de fidelidade"},
    {"month": 12, "moment": "Natal e Réveillon — presentes, festas, edições premium"},
]

SYSTEM_PROMPT = f"""
Você é o especialista em Conteúdo e Branding do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Identidade da marca:
- Estética italiana autêntica: cores da bandeira italiana, tipografia clássica, imagens artesanais
- Tom de voz: sofisticado mas acolhedor, apaixonado pela cultura do gelato, educativo
- Pilares de conteúdo: (1) Artesanalidade e qualidade, (2) Cultura italiana, (3) Momentos de prazer, (4) Oportunidade de negócio

Canais prioritários:
- Instagram: principal canal visual, foco em feed estético e Reels curtos
- TikTok: conteúdo de processo (fazendo gelato), ASMR, bastidores
- LinkedIn: conteúdo B2B para captação de franqueados, cases de sucesso
- Google Business: fotos de produtos, respostas a avaliações, posts de oferta

Diretrizes criativas:
- Nunca comparar com sorvete comum — o gelato é superior e distinto
- Sempre mostrar a origem italiana dos sabores e técnicas
- Usar storytelling de franqueados como prova social B2B
- Consistência visual: paleta restrita (verde, branco, vermelho, dourado)

Sazonalidade atual e calendário editorial serão fornecidos em cada consulta.

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class ContentAgent(BaseAgent):
    """Handles content strategy, social media planning, and brand storytelling."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT

    def _current_season_context(self) -> str:
        current_month = date.today().month
        for entry in SEASONAL_MOMENTS:
            if entry["month"] == current_month:
                return entry["moment"]
        return "Período sem sazonalidade específica identificada."

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[ContentAgent] query=%s", query[:120])

        season_ctx = self._current_season_context()

        # ---- Units with brand presence (for geo-targeted content) ----
        units_rows = await self.db_fetch(
            """
            SELECT
                u.code,
                u.name,
                u.city,
                u.state,
                u.format,
                COUNT(c.unit_id)                        AS customer_count,
                ROUND(AVG(c.nps_score)::numeric, 1)     AS avg_nps
            FROM units u
            LEFT JOIN customers c ON c.unit_id = u.id
            GROUP BY u.id, u.code, u.name, u.city, u.state, u.format
            ORDER BY customer_count DESC
            """
        )

        # ---- VIP customers (for social proof and UGC campaigns) ----
        vip_rows = await self.db_fetch(
            """
            SELECT
                COUNT(*)                                AS vip_count,
                ROUND(AVG(nps_score)::numeric, 1)       AS avg_nps,
                ROUND(AVG(visit_count)::numeric, 1)     AS avg_visits,
                ROUND(AVG(total_spent)::numeric, 2)     AS avg_spent
            FROM customers
            WHERE segment = 'vip'
            """
        )

        # ---- B2B leads from digital channels (content ROI proxy) ----
        digital_lead_rows = await self.db_fetch(
            """
            SELECT
                source,
                COUNT(*)                                AS leads,
                ROUND(AVG(score)::numeric, 1)           AS avg_score,
                COUNT(*) FILTER (
                    WHERE status IN ('contrato', 'inaugurado')
                )                                       AS converted
            FROM leads_b2b
            WHERE source ILIKE '%instagram%'
               OR source ILIKE '%facebook%'
               OR source ILIKE '%google%'
               OR source ILIKE '%linkedin%'
               OR source ILIKE '%tiktok%'
               OR source ILIKE '%organico%'
               OR source ILIKE '%content%'
            GROUP BY source
            ORDER BY leads DESC
            """
        )

        units_ctx = self.format_kpi_context(units_rows, "Unidades Ativas (presença de marca)")
        vip_ctx = self.format_kpi_context(vip_rows, "Base VIP para Social Proof")
        digital_ctx = self.format_kpi_context(digital_lead_rows, "Leads por Canal Digital (B2B)")

        prompt = (
            f"Consulta de Conteúdo e Branding:\n{query}\n\n"
            f"Sazonalidade atual: {season_ctx}\n\n"
            f"{units_ctx}\n\n"
            f"{vip_ctx}\n\n"
            f"{digital_ctx}\n\n"
            f"Contexto adicional: {context}\n\n"
            "Elabore a estratégia de conteúdo solicitada, incluindo: "
            "temas, formatos, frequência de publicação por canal, copy sugerido, "
            "referências visuais alinhadas à estética italiana premium do {BRAND['name']}, "
            "e métricas de acompanhamento (engajamento, alcance, leads gerados)."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
