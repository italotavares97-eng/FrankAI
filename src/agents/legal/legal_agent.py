"""Frank AI OS — Legal Agent: Contratos, COF, compliance, riscos jurídicos."""

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict
from app.agents.base_agent import AgentContext, BaseAgent
from app.core.logging import get_logger

logger = get_logger("legal_agent")


def _mock_legal_data(units: list) -> Dict:
    random.seed(42)
    today = datetime.utcnow()

    contracts = []
    for uid in units:
        expiry_days = random.randint(-30, 730)
        expiry_date = today + timedelta(days=expiry_days)
        contracts.append({
            "unit_id": uid,
            "contract_type": "Contrato de Franquia",
            "expires_at": expiry_date.strftime("%Y-%m-%d"),
            "days_to_expiry": expiry_days,
            "status": "expired" if expiry_days < 0 else ("expiring_soon" if expiry_days < 90 else "active"),
            "rent_review_due": random.choice([True, False]),
            "addendum_pending": random.choice([True, False, False]),
        })

    cof_status = {
        "last_update": (today - timedelta(days=random.randint(30, 400))).strftime("%Y-%m-%d"),
        "next_mandatory_update": (today + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d"),
        "compliant": random.choice([True, True, False]),
        "items_pending": random.randint(0, 3),
    }

    return {
        "contracts": contracts,
        "cof": cof_status,
        "open_disputes": random.randint(0, 2),
        "compliance_score": round(random.uniform(72, 96), 1),
        "esocial_ok": random.choice([True, True, True, False]),
        "trademarks": {
            "registered": 3,
            "pending_renewal": random.randint(0, 1),
            "alerts": random.randint(0, 2),
        },
    }


class LegalAgent(BaseAgent):
    name = "frank-legal"
    sector = "juridico"
    description = "Gestão de contratos, COF, compliance, riscos jurídicos e propriedade intelectual"

    @property
    def system_prompt(self) -> str:
        return """Você é o Legal Agent do Frank AI OS para a rede Davvero Gelato.

Monitora: contratos de franquia (vencimento, renovações), COF (Lei 13.966/2019),
compliance trabalhista/tributário, riscos legais e proteção de marca.

Alertas críticos:
- Contrato vencendo em < 30 dias: escalar urgente
- COF desatualizado > 12 meses: risco legal grave
- eSocial irregular: ação imediata

Responda em português, linguagem executiva (não técnico-jurídica)."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        data = _mock_legal_data(context.network_units)

        alerts = []
        for c in data["contracts"]:
            if c["status"] == "expired":
                alerts.append({"type": "CONTRACT_EXPIRED", "unit_id": c["unit_id"], "severity": "critical"})
            elif c["status"] == "expiring_soon":
                alerts.append({"type": "CONTRACT_EXPIRING", "unit_id": c["unit_id"],
                                "days": c["days_to_expiry"], "severity": "warning"})

        if not data["cof"]["compliant"]:
            alerts.append({"type": "COF_NON_COMPLIANT", "severity": "critical",
                            "items_pending": data["cof"]["items_pending"]})

        if not data["esocial_ok"]:
            alerts.append({"type": "ESOCIAL_IRREGULAR", "severity": "critical"})

        prompt = f"""Analise a situação jurídica da rede Davvero Gelato:

{json.dumps(data, indent=2, default=str)}

ALERTAS: {json.dumps(alerts, indent=2, default=str)}

Gere: status jurídico geral, alertas prioritários e 3 ações legais para próximas 2 semanas."""

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
