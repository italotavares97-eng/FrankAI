"""Frank AI OS — CMO Agent: Campanhas, Meta Ads, LinkedIn, CRM, conteúdo."""

import json
import random
from typing import Any, Dict
from app.agents.base_agent import AgentContext, BaseAgent
from app.core.logging import get_logger

logger = get_logger("cmo_agent")


def _mock_marketing_data(date: str) -> Dict:
    random.seed(hash(date + "mkt") % 1000)
    return {
        "meta_ads": {
            "spend": round(random.uniform(3_000, 8_000), 2),
            "impressions": random.randint(80_000, 250_000),
            "clicks": random.randint(2_000, 8_000),
            "conversions": random.randint(80, 350),
            "roas": round(random.uniform(2.1, 4.8), 2),
            "cpc": round(random.uniform(0.80, 2.50), 2),
            "ctr_pct": round(random.uniform(1.5, 4.2), 2),
            "top_creative": "gelato-pistachio-video-01",
        },
        "instagram": {
            "followers": random.randint(18_000, 22_000),
            "reach_week": random.randint(15_000, 45_000),
            "engagement_pct": round(random.uniform(2.8, 6.5), 2),
            "posts_week": random.randint(4, 8),
            "stories_week": random.randint(10, 25),
            "comments_pending": random.randint(0, 35),
        },
        "crm": {
            "active_customers": random.randint(4_500, 7_000),
            "new_customers_week": random.randint(80, 250),
            "churned_week": random.randint(20, 80),
            "loyalty_members": random.randint(1_200, 2_500),
            "avg_frequency": round(random.uniform(1.8, 3.4), 1),
        },
        "b2b_pipeline": {
            "leads_total": random.randint(18, 45),
            "mql": random.randint(8, 20),
            "sql": random.randint(3, 10),
            "in_viability": random.randint(1, 5),
            "avg_score": round(random.uniform(52, 74), 1),
            "deals_closing_30d": random.randint(0, 3),
        },
    }


class CMOAgent(BaseAgent):
    name = "frank-cmo"
    sector = "marketing"
    description = "Análise de campanhas B2C/B2B, Meta Ads, CRM, engajamento e pipeline de franqueados"

    @property
    def system_prompt(self) -> str:
        return """Você é o CMO Agent do Frank AI OS para a rede Davvero Gelato.

Monitora: Meta Ads (ROAS meta ≥ 3.0x), engajamento Instagram, CRM/fidelidade,
pipeline B2B de novos franqueados e criação de conteúdo.

Alertas automáticos:
- ROAS < 2.5x: pausar criativo imediatamente
- Comentários pendentes > 24h: escalar
- Pipeline B2B parado > 2 semanas: reativar

Responda em português, foco em dados de performance e ações de growth."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        date = kwargs.get("date", context.period)
        data = _mock_marketing_data(date)

        alerts = []
        if data["meta_ads"]["roas"] < 2.5:
            alerts.append({"type": "ROAS_LOW", "value": data["meta_ads"]["roas"], "limit": 2.5, "severity": "critical"})
        if data["instagram"]["comments_pending"] > 20:
            alerts.append({"type": "COMMENTS_PENDING", "value": data["instagram"]["comments_pending"], "severity": "warning"})

        prompt = f"""Analise os dados de marketing da rede Davvero Gelato:

DATA: {date}
{json.dumps(data, indent=2, default=str)}

ALERTAS: {json.dumps(alerts, indent=2, default=str)}

Gere: performance summary (3 bullets), alertas de campanha, 3 ações de marketing para próximos 7 dias."""

        analysis_text, tokens = await self._call_llm(
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "status": "success",
            "date": date,
            "data": data,
            "alerts": alerts,
            "analysis": analysis_text,
            "tokens_used": tokens,
        }
