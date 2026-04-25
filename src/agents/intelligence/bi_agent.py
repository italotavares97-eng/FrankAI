"""Frank AI OS — BI Agent: Dashboards, forecasts, correlações, inovação."""

import json
import random
from typing import Any, Dict, List
from app.agents.base_agent import AgentContext, BaseAgent


def _mock_bi_data(date: str) -> Dict:
    random.seed(hash(date + "bi") % 1000)

    # Série histórica de 8 semanas
    weeks = []
    revenue_base = 480_000
    for i in range(8):
        seasonal = 1.0 + 0.1 * (i % 4 - 2) * 0.5
        weeks.append({
            "week": f"W{i+1}",
            "revenue": round(revenue_base * seasonal * random.uniform(0.92, 1.08), 0),
            "cmv_pct": round(random.uniform(26, 31), 1),
            "avg_nps": round(random.uniform(54, 68), 1),
            "ebitda_pct": round(random.uniform(9, 15), 1),
        })

    return {
        "trend_8weeks": weeks,
        "forecast_30d": {
            "revenue_projection": round(revenue_base * random.uniform(0.95, 1.15), 0),
            "confidence_pct": round(random.uniform(70, 88), 1),
            "cmv_projection": round(random.uniform(27, 30.5), 1),
            "risk_factors": ["alta sazonalidade inverno", "custo laticínios +3%"],
        },
        "top_correlations": [
            {"factor_a": "CMV", "factor_b": "EBITDA", "correlation": -0.87, "insight": "Cada 1pp de CMV reduz EBITDA ~1.2pp"},
            {"factor_a": "NPS", "factor_b": "Receita_semana+2", "correlation": 0.72, "insight": "NPS alto precede crescimento de receita"},
            {"factor_a": "Auditoria", "factor_b": "NPS", "correlation": 0.65, "insight": "Unidades com auditoria ≥85 têm NPS 8pts maior"},
        ],
        "anomalies_detected": random.randint(0, 3),
        "innovation_pipeline": {
            "ideas_active": random.randint(3, 9),
            "in_pilot": random.randint(1, 3),
            "roi_validated": random.randint(0, 2),
        },
    }


class BIAgent(BaseAgent):
    name = "frank-bi"
    sector = "inteligencia"
    description = "BI, dashboards, forecasting, correlações e pipeline de inovação"

    @property
    def system_prompt(self) -> str:
        return """Você é o BI Agent do Frank AI OS para a rede Davvero Gelato.

Responsabilidade: análise de tendências, forecast, correlações entre KPIs, detecção de
anomalias, projetos estratégicos e pipeline de inovação.

Entregue: insights que nenhum agente individual veria (visão sistêmica).
Use dados históricos para identificar padrões e prever problemas futuros.

Responda em português, linguagem de dados mas acessível para o CEO."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        date = kwargs.get("date", context.period)
        data = _mock_bi_data(date)

        prompt = f"""Analise inteligência de negócios da rede Davvero Gelato:

{json.dumps(data, indent=2, default=str)}

Gere: insight sistêmico principal, forecast 30 dias, correlação mais crítica e 1 oportunidade de inovação."""

        analysis_text, tokens = await self._call_llm(
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "status": "success",
            "date": date,
            "data": data,
            "analysis": analysis_text,
            "tokens_used": tokens,
        }
