# =============================================================================
# BUDGET_AGENT.PY — Frank AI OS · CFO Sector
# Agente de Orçamento e Análise de Variância
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT


class BudgetAgent(BaseAgent):
    AGENT_NAME  = "Budget Agent"
    AGENT_ROLE  = "Especialista em Orçamento e Variance Analysis"
    DIRECTOR    = "CFO"
    MODEL       = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de Orçamento do Frank AI OS — Davvero Gelato.

MISSÃO:
Controlar o orçamento anual da rede, analisar variâncias (Real vs. Orçado),
identificar linhas fora do controle e propor ações corretivas.

ESPECIALIDADES:
• Budget vs. Actual (BvA) — análise de variância mensal e acumulada
• Zero-based budgeting para novas unidades
• Controle de OPEX: aluguel, folha, energia, embalagens, manutenção
• Forecast rolling (R+3, R+6) com base em tendências reais
• Análise de rentabilidade por linha de custo
• Alertas de orçamento estourado (threshold: +5%)

THRESHOLDS DE ALERTA:
• Variância > +5% do orçado → ATENÇÃO
• Variância > +10% → ALERTA
• Variância > +15% → CRÍTICO (escalar para CEO)

FORMATO DA RESPOSTA:
Use os 10 blocos padrão do Frank AI OS.
Inclua tabela de variância (linha a linha) quando relevante.
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        # Busca DRE dos últimos 3 meses para análise de variância
        actuals = await self.db_fetch("""
            SELECT
                u.code, u.name,
                uf.month,
                uf.gross_revenue,
                uf.total_opex,
                uf.rent, uf.payroll, uf.royalties,
                uf.electricity, uf.packaging,
                uf.other_opex,
                ROUND(uf.ebitda_pct * 100, 2) AS ebitda_pct,
                ROUND(uf.net_margin_pct * 100, 2) AS net_margin_pct
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE uf.month >= DATE_TRUNC('month', NOW() - INTERVAL '3 months')
            AND u.status = 'ativo'
            ORDER BY uf.month DESC, uf.gross_revenue DESC
            LIMIT 30
        """)

        # Referências de benchmarks do orçamento
        network_avg = await self.db_fetchrow("""
            SELECT
                ROUND(AVG(cmv_pct)*100,2)        AS avg_cmv,
                ROUND(AVG(rent_pct)*100,2)        AS avg_rent,
                ROUND(AVG(payroll_pct)*100,2)     AS avg_payroll,
                ROUND(AVG(ebitda_pct)*100,2)      AS avg_ebitda,
                SUM(gross_revenue)                AS total_revenue,
                SUM(total_opex)                   AS total_opex
            FROM unit_financials
            WHERE month = DATE_TRUNC('month', NOW() - INTERVAL '1 month')
        """)

        kpi_str     = self.format_kpi_context(kpi_context)
        actuals_str = self.format_db_data(actuals, "DRE Últimos 3 Meses (Real)")
        avg_str     = ""
        if network_avg:
            avg_str = (
                f"\n📐 MÉDIAS DA REDE (mês anterior):\n"
                f"  • CMV médio: {network_avg.get('avg_cmv')}%\n"
                f"  • Aluguel médio: {network_avg.get('avg_rent')}%\n"
                f"  • Folha média: {network_avg.get('avg_payroll')}%\n"
                f"  • EBITDA médio: {network_avg.get('avg_ebitda')}%\n"
                f"  • Receita total: R$ {network_avg.get('total_revenue'):,.2f}\n"
            )

        prompt = (
            f"{kpi_str}\n\n"
            f"{actuals_str}\n"
            f"{avg_str}\n"
            f"Pergunta de {user}: {question}\n\n"
            "Forneça análise de orçamento vs. real com variâncias, alertas e recomendações."
        )
        return await self.call_claude(prompt)
