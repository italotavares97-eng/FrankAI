"""
Paid Media Agent — Frank AI OS | Davvero Gelato
Meta Ads and paid media performance: ROAS, CPL, budget optimization.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_AGENT, OPERATIONAL_TARGETS, BRAND

from core.base_agent import BaseAgent
from integrations.social import SocialConnector

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o especialista em Mídia Paga do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Suas responsabilidades:
- Gerenciar e otimizar campanhas de Meta Ads (Facebook e Instagram)
- Analisar performance: CPL, CPC, CTR, ROAS, frequência, alcance
- Segmentar campanhas por objetivo: B2C (tráfego para loja) e B2B (leads franqueados)
- Recomendar ajustes de verba, criativos, públicos e bidding
- Identificar fadiga de anúncios e recomendar rotação de criativos
- Monitorar CPA e comparar com metas de negócio

Metas de mídia paga:
- CPL B2B (Meta Ads): < R$ {OPERATIONAL_TARGETS.get('cpl_meta_max', 200)} por lead de franqueado
- CAC por franqueado inaugurado: < R$ {OPERATIONAL_TARGETS.get('cac_franchisee_max', 15000)}
- CTR mínimo esperado: ≥ 1,5 %
- Frequência máxima: ≤ 3,5 (evitar fadiga)
- ROAS B2C mínimo: ≥ 4x

Canais monitorados:
- Meta Ads (Facebook + Instagram): principal canal pago B2B e B2C
- Google Ads: campanhas de busca para termos de franquia e gelato (quando aplicável)
- LinkedIn Ads: campanhas B2B para executivos e empreendedores

Regras de otimização:
- Pausar anúncios com CTR < 0,8 % após 3 dias de veiculação
- Aumentar verba em 20 % nos grupos com CPA < meta após 5 dias
- Testar no mínimo 3 criativos por campanha sempre que possível

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class PaidMediaAgent(BaseAgent):
    """Handles paid media performance analysis and optimization recommendations."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT
        self.social = SocialConnector()

    async def _fetch_campaign_data(self) -> dict[str, Any]:
        """Fetch campaign insights from Meta Ads via SocialConnector."""
        try:
            campaigns = await self.social.get_campaign_insights(
                date_preset="last_30d",
                fields=["campaign_name", "spend", "impressions", "clicks", "ctr",
                        "cpc", "cpm", "reach", "frequency", "actions", "cost_per_action_type"],
            )
            return {"status": "ok", "campaigns": campaigns}
        except Exception as exc:
            logger.warning("[PaidMediaAgent] SocialConnector error: %s", exc)
            return {"status": "error", "message": str(exc), "campaigns": []}

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[PaidMediaAgent] query=%s", query[:120])

        # Fetch live campaign data from Meta Ads
        campaign_data = await self._fetch_campaign_data()

        # ---- B2B leads attributed to paid media ----
        paid_leads_rows = await self.db_fetch(
            """
            SELECT
                source,
                COUNT(*)                                        AS leads,
                ROUND(AVG(score)::numeric, 1)                   AS avg_score,
                COUNT(*) FILTER (WHERE status = 'qualificado') AS qualified,
                COUNT(*) FILTER (WHERE status = 'reuniao')     AS meetings,
                COUNT(*) FILTER (WHERE status IN ('contrato', 'inaugurado')) AS converted,
                ROUND(AVG(available_capital)::numeric, 0)       AS avg_capital
            FROM leads_b2b
            WHERE
                first_contact >= NOW() - INTERVAL '30 days'
                AND (
                    source ILIKE '%meta%'
                    OR source ILIKE '%facebook%'
                    OR source ILIKE '%instagram%'
                    OR source ILIKE '%google%'
                    OR source ILIKE '%linkedin%'
                    OR source ILIKE '%ads%'
                    OR source ILIKE '%pago%'
                    OR source ILIKE '%paid%'
                )
            GROUP BY source
            ORDER BY leads DESC
            """
        )

        # ---- Monthly paid lead volume trend ----
        trend_rows = await self.db_fetch(
            """
            SELECT
                TO_CHAR(DATE_TRUNC('month', first_contact), 'YYYY-MM')  AS month,
                COUNT(*)                                                 AS leads,
                COUNT(*) FILTER (WHERE status IN ('contrato', 'inaugurado')) AS converted
            FROM leads_b2b
            WHERE first_contact >= NOW() - INTERVAL '6 months'
              AND (
                    source ILIKE '%meta%'
                    OR source ILIKE '%ads%'
                    OR source ILIKE '%pago%'
                )
            GROUP BY month
            ORDER BY month
            """
        )

        paid_ctx = self.format_kpi_context(paid_leads_rows, "Leads B2B via Mídia Paga (30 dias)")
        trend_ctx = self.format_kpi_context(trend_rows, "Tendência Mensal de Leads Pagos (6 meses)")

        # Format campaign data summary
        if campaign_data["status"] == "ok" and campaign_data["campaigns"]:
            camp_summary_lines = []
            for c in campaign_data["campaigns"][:15]:  # limit to top 15
                camp_summary_lines.append(str(c))
            campaign_ctx = "=== Campanhas Meta Ads (últimos 30 dias) ===\n" + "\n".join(camp_summary_lines)
        else:
            campaign_ctx = (
                f"=== Campanhas Meta Ads ===\n"
                f"Status: {campaign_data.get('status')} | "
                f"Motivo: {campaign_data.get('message', 'dados não disponíveis')}"
            )

        cpl_target = OPERATIONAL_TARGETS.get("cpl_meta_max", 200)
        cac_target = OPERATIONAL_TARGETS.get("cac_franchisee_max", 15000)

        prompt = (
            f"Consulta de Mídia Paga:\n{query}\n\n"
            f"{campaign_ctx}\n\n"
            f"{paid_ctx}\n\n"
            f"{trend_ctx}\n\n"
            f"Metas: CPL < R$ {cpl_target} | CAC < R$ {cac_target:,.0f} | CTR ≥ 1,5 % | Freq ≤ 3,5 | ROAS B2C ≥ 4x\n\n"
            f"Contexto adicional: {context}\n\n"
            "Analise a performance das campanhas pagas, compare com as metas, "
            "identifique campanhas que precisam de ajuste (pause, escala ou reformulação), "
            "e recomende alocação de verba e mudanças criativas/de segmentação para o próximo ciclo."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
