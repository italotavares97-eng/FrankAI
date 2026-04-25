# =============================================================================
# FORECAST_AGENT.PY — Frank AI OS · BI Sector
# Agente de Forecast de Receita e Tendências
# =============================================================================

from __future__ import annotations
from typing import Dict, List, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT


class ForecastAgent(BaseAgent):
    AGENT_NAME = "Forecast Agent"
    AGENT_ROLE = "Especialista em Previsão e Análise de Tendências"
    DIRECTOR   = "BI"
    MODEL      = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de Forecast do Frank AI OS — Davvero Gelato.

MISSÃO:
Projetar receita, CMV e KPIs operacionais para os próximos 3-6 meses,
considerando tendências históricas, sazonalidade e variáveis de negócio.

ESPECIALIDADES:
• Forecast de receita por unidade e rede consolidada
• Projeção de CMV com base em tendências de custo
• Análise de sazonalidade (verão = alta, inverno = baixa para gelato)
• Cenários: pessimista / base / otimista
• Rolling forecast (atualização mensal)
• Break-even analysis para novas unidades

SAZONALIDADE GELATO (Brasil):
• Alta estação: Out–Mar (verão) → receita +20-35% vs. média
• Baixa estação: Jun–Ago (inverno) → receita -15-25% vs. média
• Datas-chave: Carnaval, Páscoa, Dia dos Namorados, Natal

METODOLOGIA:
1. Base: média móvel 3 meses
2. Tendência: regressão linear simples (slope mensal)
3. Sazonalidade: índice por mês (histórico 2 anos)
4. Ajuste manual: eventos especiais, inaugurações, fechamentos
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        # Histórico de 12 meses para base do forecast
        history = await self.db_fetch("""
            SELECT
                uf.month,
                SUM(uf.gross_revenue)               AS network_revenue,
                ROUND(AVG(uf.cmv_pct)*100, 2)       AS avg_cmv_pct,
                ROUND(AVG(uf.ebitda_pct)*100, 2)    AS avg_ebitda_pct,
                COUNT(DISTINCT uf.unit_id)           AS active_units
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id AND u.status != 'encerrado'
            WHERE uf.month >= DATE_TRUNC('month', NOW() - INTERVAL '12 months')
            GROUP BY uf.month
            ORDER BY uf.month ASC
        """)

        # Média de ticket diário para projeção
        daily_trend = await self.db_fetch("""
            SELECT
                DATE_TRUNC('month', date) AS month,
                ROUND(AVG(avg_ticket)::numeric, 2)  AS avg_ticket,
                ROUND(AVG(productivity)::numeric, 2) AS avg_productivity,
                COUNT(DISTINCT unit_id)              AS reporting_units
            FROM unit_daily_kpis
            WHERE date >= NOW() - INTERVAL '6 months'
            GROUP BY DATE_TRUNC('month', date)
            ORDER BY month ASC
        """)

        # Calcula tendência linear simples
        trend_summary = self._calc_trend(history)

        kpi_str     = self.format_kpi_context(kpi_context)
        history_str = self.format_db_data(history, "Histórico 12 Meses (Rede Consolidada)")
        daily_str   = self.format_db_data(daily_trend, "Tendência de Ticket e Produtividade")

        prompt = (
            f"{kpi_str}\n\n{history_str}\n{daily_str}\n\n"
            f"📈 ANÁLISE DE TENDÊNCIA:\n{trend_summary}\n\n"
            f"Pergunta de {user}: {question}\n\n"
            "Gere forecast para os próximos 3-6 meses com cenários pessimista, base e otimista. "
            "Inclua impacto de sazonalidade e recomendações estratégicas."
        )
        return await self.call_claude(prompt)

    def _calc_trend(self, history: List[Dict]) -> str:
        """Calcula tendência de receita (slope mensal)."""
        if len(history) < 3:
            return "Dados insuficientes para calcular tendência."
        revenues = [float(h.get("network_revenue") or 0) for h in history]
        n = len(revenues)
        avg = sum(revenues) / n
        last_3_avg = sum(revenues[-3:]) / 3
        first_3_avg = sum(revenues[:3]) / 3

        if first_3_avg > 0:
            growth_pct = ((last_3_avg - first_3_avg) / first_3_avg) * 100
            monthly_slope = (revenues[-1] - revenues[0]) / max(n - 1, 1)
        else:
            growth_pct = 0
            monthly_slope = 0

        direction = "📈 CRESCENDO" if growth_pct > 2 else ("📉 CAINDO" if growth_pct < -2 else "➡️ ESTÁVEL")
        return (
            f"  • Direção: {direction}\n"
            f"  • Crescimento período: {growth_pct:+.1f}%\n"
            f"  • Slope mensal: R$ {monthly_slope:+,.0f}\n"
            f"  • Média 3 meses mais recentes: R$ {last_3_avg:,.0f}\n"
            f"  • Receita mais recente: R$ {revenues[-1]:,.0f}\n"
        )
