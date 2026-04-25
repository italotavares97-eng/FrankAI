"""Frank AI OS — CSO Agent: Expansão, prospecção, GO/NO-GO, pipeline B2B."""

import json
import random
from typing import Any, Dict
from app.agents.base_agent import AgentContext, BaseAgent


def _mock_expansion_data() -> Dict:
    random.seed(77)
    leads = []
    cities = ["Campinas-SP", "São Bernardo-SP", "Niterói-RJ", "Uberlândia-MG", "Curitiba-PR", "Florianópolis-SC"]
    stages = ["MQL", "pre-qual", "SQL", "viability", "contract"]

    for i, city in enumerate(cities[:4]):
        random.seed(i * 7)
        leads.append({
            "id": f"LEAD-{2024 + i:04d}",
            "name": f"Candidato {chr(65+i)}",
            "city": city,
            "stage": random.choice(stages),
            "score": random.randint(45, 88),
            "capital": random.randint(250_000, 600_000),
            "days_in_pipeline": random.randint(5, 90),
            "next_action": random.choice(["Agendar entrevista", "Enviar COF", "Análise de viabilidade", "Assinar contrato"]),
        })

    return {
        "pipeline": {
            "total_leads": len(leads) + random.randint(5, 15),
            "mql": random.randint(8, 18),
            "sql": random.randint(3, 8),
            "in_viability": random.randint(1, 4),
            "contract_stage": random.randint(0, 2),
            "conversion_mql_sql_pct": round(random.uniform(25, 45), 1),
        },
        "leads_sample": leads,
        "target_cities": cities,
        "expansion_map": {
            "units_operating": 7,
            "units_contracted": random.randint(1, 3),
            "target_year": 11,
        },
        "linkedin": {
            "posts_week": random.randint(2, 5),
            "inmail_sent": random.randint(10, 40),
            "response_rate_pct": round(random.uniform(18, 45), 1),
            "qualified_from_linkedin": random.randint(1, 5),
        },
    }


class CSOAgent(BaseAgent):
    name = "frank-cso"
    sector = "expansao"
    description = "Expansão da rede, prospecção de franqueados, GO/NO-GO, análise territorial"

    @property
    def system_prompt(self) -> str:
        return """Você é o CSO Agent do Frank AI OS para a rede Davvero Gelato.

Gerencia: pipeline de novos franqueados, scoring de localização, análise de viabilidade
e expansão estratégica da rede (meta: +4 unidades/ano).

CEO Rules para expansão:
- Payback ≤ 30 meses → GO
- ROI 24m ≥ 1.5x → GO
- Aluguel ≤ 12% → GO
- Score de viabilidade ≥ 70/100 → GO

Responda em português, foco em pipeline, conversão e próximas unidades."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        data = _mock_expansion_data()

        alerts = []
        if data["pipeline"]["contract_stage"] == 0:
            alerts.append({"type": "NO_CONTRACTS_PIPELINE", "severity": "warning",
                            "message": "Nenhum lead em fase de contrato — risco de meta anual"})

        prompt = f"""Analise o pipeline de expansão da rede Davvero Gelato:

{json.dumps(data, indent=2, default=str)}

Gere: status do pipeline, leads prioritários para ação, previsão de abertura e 3 ações de prospecção."""

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
