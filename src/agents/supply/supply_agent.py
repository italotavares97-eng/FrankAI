"""Frank AI OS — Supply Chain Agent: CMV, estoque, fornecedores, logística."""

import json
import random
from typing import Any, Dict
from app.agents.base_agent import AgentContext, BaseAgent


def _mock_supply_data(units: list, date: str) -> Dict:
    random.seed(hash(date + "supply") % 1000)

    inventory = {}
    for uid in units:
        inventory[uid] = {
            "unit_id": uid,
            "stock_coverage_days": round(random.uniform(3.5, 14.0), 1),
            "stockout_items": random.randint(0, 3),
            "overstock_items": random.randint(0, 5),
            "waste_pct": round(random.uniform(1.5, 6.0), 1),
            "last_delivery_days_ago": random.randint(1, 7),
            "pending_orders": random.randint(0, 2),
        }

    suppliers = [
        {"name": "Laticínios Sul", "category": "laticínios", "score": random.randint(72, 95),
         "on_time_pct": round(random.uniform(80, 98), 1), "price_variance_pct": round(random.uniform(-5, 8), 1)},
        {"name": "Frutas Premium", "category": "frutas", "score": random.randint(65, 90),
         "on_time_pct": round(random.uniform(75, 95), 1), "price_variance_pct": round(random.uniform(-3, 10), 1)},
        {"name": "Embalagens Plus", "category": "embalagens", "score": random.randint(78, 92),
         "on_time_pct": round(random.uniform(88, 99), 1), "price_variance_pct": round(random.uniform(-2, 5), 1)},
    ]

    return {
        "inventory": inventory,
        "suppliers": suppliers,
        "network": {
            "avg_coverage_days": sum(i["stock_coverage_days"] for i in inventory.values()) / len(units),
            "total_stockouts": sum(i["stockout_items"] for i in inventory.values()),
            "avg_waste_pct": sum(i["waste_pct"] for i in inventory.values()) / len(units),
            "avg_supplier_score": sum(s["score"] for s in suppliers) / len(suppliers),
        },
    }


class SupplyAgent(BaseAgent):
    name = "frank-supply"
    sector = "supply_chain"
    description = "CMV, estoque, fornecedores, logística e controle de qualidade de insumos"

    @property
    def system_prompt(self) -> str:
        return """Você é o Supply Chain Agent do Frank AI OS para a rede Davvero Gelato.

Monitora: cobertura de estoque (meta ≥ 5 dias), desperdício (meta ≤ 3%), pontualidade de
fornecedores (meta ≥ 90%), qualidade de insumos e impacto no CMV.

Alertas:
- Cobertura < 3 dias: compra urgente
- Desperdício > 5%: investigação de causa raiz
- Fornecedor score < 70: revisão de contrato

Responda em português, foco em eficiência de cadeia e impacto no CMV."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        date = kwargs.get("date", context.period)
        data = _mock_supply_data(context.network_units, date)

        alerts = []
        for uid, inv in data["inventory"].items():
            if inv["stock_coverage_days"] < 3:
                alerts.append({"type": "LOW_STOCK", "unit_id": uid, "days": inv["stock_coverage_days"], "severity": "critical"})
            if inv["waste_pct"] > 5:
                alerts.append({"type": "HIGH_WASTE", "unit_id": uid, "pct": inv["waste_pct"], "severity": "warning"})

        prompt = f"""Analise a cadeia de suprimentos da rede Davvero Gelato ({date}):

{json.dumps(data, indent=2, default=str)}

ALERTAS: {json.dumps(alerts, indent=2, default=str)}

Gere: status de supply chain, riscos de abastecimento, 3 ações prioritárias para esta semana."""

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
