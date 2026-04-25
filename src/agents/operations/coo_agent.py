"""Frank AI OS — COO Agent: KPIs operacionais, NPS, auditoria, processos."""

import json
import random
from typing import Any, Dict, List
from app.agents.base_agent import AgentContext, BaseAgent
from app.core.logging import get_logger

logger = get_logger("coo_agent")


def _mock_operational_data(unit_id: str, date: str) -> Dict:
    seed = hash(unit_id + date + "ops") % 1000
    random.seed(seed)

    nps = random.uniform(48, 72)
    if unit_id == "DVR-MG-001":
        nps = random.uniform(42, 52)  # MG em alerta de NPS

    audit = random.uniform(72, 94)
    throughput = random.randint(280, 850)
    staff_count = random.randint(4, 9)
    absences = random.randint(0, 3)
    sop_compliance = random.uniform(78, 98)

    return {
        "unit_id": unit_id,
        "date": date,
        "nps_score": round(nps, 1),
        "nps_responses": random.randint(15, 60),
        "audit_score": round(audit, 1),
        "audit_date": date,
        "throughput": throughput,
        "staff_count": staff_count,
        "absences": absences,
        "absence_rate_pct": round((absences / staff_count) * 100, 1),
        "sop_compliance_pct": round(sop_compliance, 1),
        "open_incidents": random.randint(0, 4),
        "resolved_incidents": random.randint(0, 8),
        "avg_service_time_min": round(random.uniform(2.5, 5.5), 1),
    }


class COOAgent(BaseAgent):
    name = "frank-coo"
    sector = "operacoes"
    description = "KPIs operacionais, NPS, auditoria de qualidade, performance de processos"

    @property
    def system_prompt(self) -> str:
        return """Você é o COO Agent do Frank AI OS para a rede Davvero Gelato.

Monitora: NPS (meta ≥ 55), scores de auditoria (meta ≥ 85/100), compliance de SOP,
ausências, produtividade por unidade e incidentes operacionais.

Alertas automáticos:
- NPS < 55: intervenção recomendada
- NPS < 45: intervenção imediata
- Auditoria < 75: visita de campo urgente
- Ausências > 20%: alerta de RH

Responda em português, dados concretos, recomendações práticas."""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        date = kwargs.get("date", context.period)
        units = context.network_units

        ops_data = {uid: _mock_operational_data(uid, date) for uid in units}

        network = {
            "avg_nps": sum(d["nps_score"] for d in ops_data.values()) / len(units),
            "avg_audit": sum(d["audit_score"] for d in ops_data.values()) / len(units),
            "avg_sop_compliance": sum(d["sop_compliance_pct"] for d in ops_data.values()) / len(units),
            "total_throughput": sum(d["throughput"] for d in ops_data.values()),
            "units_nps_ok": sum(1 for d in ops_data.values() if d["nps_score"] >= 55),
            "units_audit_ok": sum(1 for d in ops_data.values() if d["audit_score"] >= 85),
        }

        alerts = []
        for uid, d in ops_data.items():
            if d["nps_score"] < 55:
                alerts.append({
                    "unit_id": uid,
                    "type": "NPS_LOW",
                    "severity": "critical" if d["nps_score"] < 45 else "warning",
                    "value": d["nps_score"],
                    "limit": 55,
                })
            if d["audit_score"] < 85:
                alerts.append({
                    "unit_id": uid,
                    "type": "AUDIT_LOW",
                    "severity": "critical" if d["audit_score"] < 75 else "warning",
                    "value": d["audit_score"],
                    "limit": 85,
                })

        prompt = f"""Analise os dados operacionais da rede Davvero Gelato:

REDE ({date}):
- NPS médio: {network['avg_nps']:.1f} | Unidades OK (≥55): {network['units_nps_ok']}/7
- Auditoria média: {network['avg_audit']:.1f} | OK (≥85): {network['units_audit_ok']}/7
- Throughput total: {network['total_throughput']} atendimentos
- SOP Compliance médio: {network['avg_sop_compliance']:.1f}%

DADOS POR UNIDADE:
{json.dumps(ops_data, indent=2, default=str)}

ALERTAS OPERACIONAIS: {len(alerts)}
{json.dumps(alerts, indent=2, default=str)}

Gere: diagnóstico operacional (3 bullets), alertas prioritários, 3 ações de melhoria imediata."""

        analysis_text, tokens = await self._call_llm(
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "status": "success",
            "date": date,
            "network": network,
            "units": ops_data,
            "alerts": alerts,
            "analysis": analysis_text,
            "tokens_used": tokens,
        }
