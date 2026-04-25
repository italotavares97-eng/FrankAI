"""Frank AI OS — HR Agent: RH, treinamentos, turnover, cultura, folha."""

import json
import random
from typing import Any, Dict
from app.agents.base_agent import AgentContext, BaseAgent


def _mock_hr_data(units: list) -> Dict:
    random.seed(99)
    staff = {}
    for uid in units:
        total = random.randint(5, 12)
        staff[uid] = {
            "total_staff": total,
            "absences_week": random.randint(0, 3),
            "turnover_monthly_pct": round(random.uniform(2.0, 8.5), 1),
            "open_positions": random.randint(0, 2),
            "training_completion_pct": round(random.uniform(55, 98), 1),
            "performance_avg": round(random.uniform(3.0, 4.8), 1),
            "enps_score": random.randint(25, 65),
        }

    return {
        "by_unit": staff,
        "network": {
            "total_headcount": sum(s["total_staff"] for s in staff.values()),
            "avg_turnover_pct": sum(s["turnover_monthly_pct"] for s in staff.values()) / len(units),
            "avg_training_completion": sum(s["training_completion_pct"] for s in staff.values()) / len(units),
            "avg_enps": sum(s["enps_score"] for s in staff.values()) / len(units),
            "total_open_positions": sum(s["open_positions"] for s in staff.values()),
        },
        "academy": {
            "active_courses": 4,
            "completions_this_month": random.randint(8, 35),
            "certifications_pending": random.randint(2, 12),
        },
    }


class HRAgent(BaseAgent):
    name = "frank-rh"
    sector = "rh"
    description = "Gestão de pessoas, treinamentos Davvero Academy, turnover, eNPS e folha"

    @property
    def system_prompt(self) -> str:
        return """Você é o RH Agent do Frank AI OS para a rede Davvero Gelato.

Monitora: headcount, turnover (meta ≤ 4%/mês), treinamentos (meta 100% certificados),
eNPS (meta ≥ 40), ausências e performance da equipe.

Alertas:
- Turnover > 6%: investigar causa raiz
- eNPS < 30: plano de engajamento urgente
- Treinamento < 70%: sprint de capacitação

Responda em português, foco em people analytics e ações de retenção."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        data = _mock_hr_data(context.network_units)

        alerts = []
        for uid, s in data["by_unit"].items():
            if s["turnover_monthly_pct"] > 6:
                alerts.append({"type": "HIGH_TURNOVER", "unit_id": uid, "value": s["turnover_monthly_pct"], "severity": "critical"})
            if s["enps_score"] < 30:
                alerts.append({"type": "LOW_ENPS", "unit_id": uid, "value": s["enps_score"], "severity": "warning"})

        prompt = f"""Analise os dados de RH da rede Davvero Gelato:

{json.dumps(data, indent=2, default=str)}

ALERTAS: {json.dumps(alerts, indent=2, default=str)}

Gere: diagnóstico de pessoas, alertas de retenção e 3 iniciativas de RH prioritárias."""

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
