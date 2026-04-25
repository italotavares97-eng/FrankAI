"""Frank AI OS — Implantação Agent: Abertura de unidades, checklist GO-LIVE."""

import json
import random
from typing import Any, Dict
from app.agents.base_agent import AgentContext, BaseAgent


def _mock_implementation_data() -> Dict:
    random.seed(55)
    projects = [
        {
            "unit_id": "DVR-PR-001",
            "city": "Curitiba-PR",
            "franchisee": "Carlos Mendes",
            "week": random.randint(6, 14),
            "total_weeks": 14,
            "phase": "Montagem",
            "checklist_pct": round(random.uniform(40, 85), 0),
            "critical_items_pending": random.randint(0, 5),
            "opening_forecast": "2026-07-15",
            "risk_level": random.choice(["low", "medium", "high"]),
            "budget_spent_pct": round(random.uniform(35, 80), 1),
        }
    ]

    return {
        "active_projects": projects,
        "completed_ytd": random.randint(1, 3),
        "avg_opening_days": random.randint(85, 110),
        "avg_deviation_days": random.randint(-5, 15),
        "go_live_queue": random.randint(0, 2),
    }


class ImplantacaoAgent(BaseAgent):
    name = "frank-implantacao"
    sector = "implantacao"
    description = "Abertura de novas unidades, timeline 14 semanas, checklist GO-LIVE"

    @property
    def system_prompt(self) -> str:
        return """Você é o Implantação Agent do Frank AI OS para a rede Davvero Gelato.

Gerencia: abertura de novas unidades (timeline 14 semanas), checklist de 30 itens GO-LIVE,
acompanhamento de obras, equipamentos e onboarding de franqueados.

Alertas críticos:
- Atraso > 1 semana no cronograma: escalar
- Itens críticos pendentes na semana -2 do GO-LIVE: intervenção imediata
- Budget > 110%: aprovação do CEO

Responda em português, foco em cronograma e risco de abertura."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        data = _mock_implementation_data()

        alerts = []
        for p in data["active_projects"]:
            if p["risk_level"] == "high":
                alerts.append({"type": "HIGH_RISK_PROJECT", "unit_id": p["unit_id"], "severity": "critical"})
            if p["critical_items_pending"] > 3:
                alerts.append({"type": "CRITICAL_ITEMS_PENDING", "unit_id": p["unit_id"],
                                "count": p["critical_items_pending"], "severity": "warning"})

        prompt = f"""Analise o status de implantação da rede Davvero Gelato:

{json.dumps(data, indent=2, default=str)}

ALERTAS: {json.dumps(alerts, indent=2, default=str)}

Gere: status geral das aberturas, riscos críticos e próximas 3 ações de campo."""

        analysis_text, tokens = await self._call_llm(
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "status": "success",
            "data": data,
            "alerts": alerts,
            "analysis": analysis_text,
            "tokens_used": tokens,
        }
