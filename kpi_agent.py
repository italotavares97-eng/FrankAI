# =============================================================================
# KPI_AGENT.PY — Frank AI OS · BI Sector
# Agente de KPIs e Dashboard Executivo
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, CEO_HARD_RULES


class KPIAgent(BaseAgent):
    AGENT_NAME = "KPI Agent"
    AGENT_ROLE = "Analista de KPIs e Dashboard Executivo"
    DIRECTOR   = "BI"
    MODEL      = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de KPIs do Frank AI OS — Davvero Gelato.

MISSÃO:
Monitorar todos os KPIs da rede, comparar com metas e identificar
desvios que exigem ação imediata.

ESPECIALIDADES:
• Dashboard executivo com 16 KPIs principais
• Análise de desempenho por unidade, cluster e formato
• Benchmarking interno e comparativo com mercado
• Semáforo de performance (verde/amarelo/laranja/vermelho)
• Identificação de top performers e laggards

KPIs MONITORADOS:
Financeiro: CMV%, EBITDA%, Margem Líquida%, Receita, Royalties
Operacional: Ticket Médio, Transações/dia, Produtividade R$/h
CX: NPS, Reclamações, Tempo de Espera
Qualidade: Score Auditoria, Non-Conformities
Expansão: Leads no Funil, Payback Médio, ROI Médio
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        # Dashboard completo
        dashboard = await self.db_fetchrow("SELECT * FROM vw_executive_dashboard")

        # KPIs por unidade (último mês)
        unit_kpis = await self.db_fetch("""
            SELECT u.code, u.name, u.city, u.color_status,
                   ROUND(uf.cmv_pct*100,2)         AS cmv_pct,
                   uf.gross_revenue,
                   ROUND(uf.ebitda_pct*100,2)       AS ebitda_pct,
                   ROUND(uf.net_margin_pct*100,2)   AS net_margin_pct,
                   ROUND(dk.avg_ticket,2)           AS avg_ticket_30d,
                   ROUND(dk.avg_nps,1)              AS nps_30d,
                   dk.stockouts
            FROM units u
            LEFT JOIN unit_financials uf ON uf.unit_id=u.id
                AND uf.month=DATE_TRUNC('month', NOW()-INTERVAL '1 month')
            LEFT JOIN (
                SELECT unit_id,
                       ROUND(AVG(avg_ticket)::numeric,2) AS avg_ticket,
                       ROUND(AVG(nps_score)::numeric,1) AS avg_nps,
                       SUM(stockout_count) AS stockouts
                FROM unit_daily_kpis
                WHERE date >= NOW()-INTERVAL '30 days'
                GROUP BY unit_id
            ) dk ON dk.unit_id=u.id
            WHERE u.status='ativo'
            ORDER BY uf.gross_revenue DESC NULLS LAST
        """)

        # Metas para contexto
        targets_str = (
            f"\n📐 METAS ATIVAS:\n"
            f"  • CMV target: {OPERATIONAL_TARGETS['cmv_target_pct']}% (alerta: {OPERATIONAL_TARGETS['cmv_alert_pct']}%)\n"
            f"  • Ticket médio: R${OPERATIONAL_TARGETS['avg_ticket_target']}\n"
            f"  • NPS: {OPERATIONAL_TARGETS['nps_target']}\n"
            f"  • EBITDA: {OPERATIONAL_TARGETS['ebitda_target_pct']}%\n"
            f"  • Audit score: {OPERATIONAL_TARGETS['audit_score_min']} pts\n"
        )

        kpi_str    = self.format_kpi_context(kpi_context or (dict(dashboard) if dashboard else {}))
        units_str  = self.format_db_data(unit_kpis, "KPIs por Unidade")

        prompt = (
            f"{kpi_str}\n{targets_str}\n{units_str}\n\n"
            f"Pergunta de {user}: {question}\n\n"
            "Gere análise completa de KPIs, ranking de unidades, desvios e recomendações."
        )
        return await self.call_claude(prompt)
