"""Frank AI OS — CFO Agent: Análise financeira completa da rede."""

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.agents.base_agent import AgentContext, BaseAgent
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("cfo_agent")


def _mock_unit_financials(unit_id: str, date: str) -> Dict:
    """Gera dados financeiros realistas para simulação."""
    seed = hash(unit_id + date) % 1000
    random.seed(seed)

    revenue = random.uniform(45_000, 120_000)
    cmv_pct = random.uniform(24.0, 34.0)
    # DVR-RJ-001 propositalmente em alerta
    if unit_id == "DVR-RJ-001":
        cmv_pct = random.uniform(30.5, 33.0)

    rent = revenue * random.uniform(0.08, 0.13)
    labor = revenue * random.uniform(0.22, 0.28)
    other_opex = revenue * random.uniform(0.08, 0.14)

    gross = revenue * (1 - cmv_pct / 100)
    ebitda = gross - rent - labor - other_opex
    ebitda_pct = (ebitda / revenue) * 100

    return {
        "unit_id": unit_id,
        "date": date,
        "revenue": round(revenue, 2),
        "cmv_pct": round(cmv_pct, 1),
        "cmv_abs": round(revenue * cmv_pct / 100, 2),
        "gross_margin": round(((revenue - revenue * cmv_pct / 100) / revenue) * 100, 1),
        "rent_abs": round(rent, 2),
        "rent_pct": round((rent / revenue) * 100, 1),
        "labor_abs": round(labor, 2),
        "labor_pct": round((labor / revenue) * 100, 1),
        "other_opex_abs": round(other_opex, 2),
        "other_opex_pct": round((other_opex / revenue) * 100, 1),
        "ebitda": round(ebitda, 2),
        "ebitda_pct": round(ebitda_pct, 1),
        "transactions": random.randint(300, 900),
        "avg_ticket": round(revenue / random.randint(300, 900), 2),
    }


class CFOAgent(BaseAgent):
    name = "frank-cfo"
    sector = "financeiro"
    description = "Análise financeira completa: CMV, DRE, margens, alertas CEO Rules"

    @property
    def system_prompt(self) -> str:
        return """Você é o CFO Agent do Frank AI OS para a rede Davvero Gelato.

Sua responsabilidade é analisar a saúde financeira de todas as 7 unidades e da rede como um todo.

ANÁLISE OBRIGATÓRIA:
1. CMV por unidade (alerta se > 30%, crítico se > 33%)
2. EBITDA por unidade (alerta se < 10%, crítico se < 5%)
3. Aluguel/Faturamento (alerta se > 12%)
4. Ranking financeiro das unidades
5. Recomendações acionáveis e priorizadas

FORMATO DE RESPOSTA:
- Bullet points diretos
- Valores numéricos sempre (R$ e %)
- Alertas em destaque
- Máximo 3 ações recomendadas

Responda em português brasileiro. Seja conciso e orientado a dados."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        date = kwargs.get("date", context.period)
        units = context.network_units

        # Buscar dados de todas as unidades
        financials = {}
        all_violations = []

        for unit_id in units:
            data = _mock_unit_financials(unit_id, date)
            financials[unit_id] = data

            # Validar CEO Rules
            violations = context.check_ceo_rules({
                "cmv_pct": data["cmv_pct"],
                "ebitda_pct": data["ebitda_pct"],
                "rent_pct": data["rent_pct"],
            })
            for v in violations:
                v["unit_id"] = unit_id
                all_violations.append(v)

        # Métricas consolidadas da rede
        network = {
            "total_revenue": sum(f["revenue"] for f in financials.values()),
            "avg_cmv_pct": sum(f["cmv_pct"] for f in financials.values()) / len(units),
            "avg_ebitda_pct": sum(f["ebitda_pct"] for f in financials.values()) / len(units),
            "avg_rent_pct": sum(f["rent_pct"] for f in financials.values()) / len(units),
            "units_cmv_ok": sum(1 for f in financials.values() if f["cmv_pct"] <= 30),
            "units_ebitda_ok": sum(1 for f in financials.values() if f["ebitda_pct"] >= 10),
        }

        # Ranking por EBITDA
        ranking = sorted(
            [(uid, f["ebitda_pct"]) for uid, f in financials.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        # Gerar análise com LLM
        prompt = f"""Analise estes dados financeiros da rede Davvero Gelato e gere um diagnóstico executivo:

REDE CONSOLIDADA ({date}):
- Faturamento total: R$ {network['total_revenue']:,.0f}
- CMV médio: {network['avg_cmv_pct']:.1f}%
- EBITDA médio: {network['avg_ebitda_pct']:.1f}%
- Aluguel médio: {network['avg_rent_pct']:.1f}%

POR UNIDADE:
{json.dumps(financials, indent=2, default=str)}

VIOLAÇÕES CEO RULES: {len(all_violations)}
{json.dumps(all_violations, indent=2, default=str)}

RANKING EBITDA: {ranking}

Gere: diagnóstico em 3 bullets, top 3 alertas, top 3 ações recomendadas com responsável e prazo."""

        analysis_text, tokens = await self._call_llm(
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "status": "success",
            "date": date,
            "network": network,
            "units": financials,
            "ranking_ebitda": ranking,
            "violations": all_violations,
            "analysis": analysis_text,
            "tokens_used": tokens,
        }
