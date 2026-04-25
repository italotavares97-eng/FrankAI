# =============================================================================
# BI_DIRECTOR.PY — Frank AI OS · BI Sector
# Diretor de Business Intelligence & Dados
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_MASTER


class BIDirector(BaseAgent):
    AGENT_NAME = "BI Director"
    AGENT_ROLE = "Diretor de Business Intelligence"
    DIRECTOR   = "BI"
    MODEL      = MODEL_MASTER

    SYSTEM_PROMPT = """Você é o Diretor de BI do Frank AI OS — Davvero Gelato.

MISSÃO:
Transformar dados operacionais e financeiros em inteligência acionável —
alertas proativos, forecasts precisos e dashboards executivos.

RESPONSABILIDADES:
• Dashboard executivo (Frank Command Center)
• Monitoramento de KPIs vs. metas em tempo real
• Geração de alertas automáticos
• Forecasting de receita e CMV (rolling 3 meses)
• Análise de tendências e sazonalidade
• Benchmarking entre unidades
• Relatórios semanais/mensais automáticos
"""

    def __init__(self):
        super().__init__()
        from kpi_agent      import KPIAgent
        from forecast_agent import ForecastAgent
        from alert_agent    import AlertAgent
        self.kpi_agent      = KPIAgent()
        self.forecast_agent = ForecastAgent()
        self.alert_agent    = AlertAgent()

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        q = question.lower()
        agent = None

        if any(kw in q for kw in ["alerta", "crítico", "problema", "monitorar"]):
            agent = self.alert_agent
        elif any(kw in q for kw in ["forecast", "previsão", "projeção", "tendência", "próximo"]):
            agent = self.forecast_agent
        else:
            agent = self.kpi_agent  # KPIs e dashboards como default

        agent.db_pool      = self.db_pool
        agent.redis_client = self.redis_client
        return await agent.analyze(question, user, kpi_context, extra_context)
