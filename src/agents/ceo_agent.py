"""Frank AI OS — CEO Agent: Orquestrador central de todos os setores."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.base_agent import AgentContext, BaseAgent, ParallelSwarm
from app.agents.financial.cfo_agent import CFOAgent
from app.agents.operations.coo_agent import COOAgent
from app.agents.marketing.cmo_agent import CMOAgent
from app.agents.legal.legal_agent import LegalAgent
from app.agents.hr.hr_agent import HRAgent
from app.agents.expansion.cso_agent import CSOAgent
from app.agents.supply.supply_agent import SupplyAgent
from app.agents.intelligence.bi_agent import BIAgent
from app.agents.implementation.impl_agent import ImplantacaoAgent
from app.core.logging import get_logger

logger = get_logger("ceo_agent")


class CEOAgent(BaseAgent):
    """
    CEO Master Agent — Frank AI OS.

    Orquestra todos os 9 diretores em paralelo (GOLDEN RULE),
    valida todas as CEO Hard Rules, gera relatório executivo e
    define lista de ações automáticas a executar.
    """

    name = "frank-master"
    sector = "estrategico"
    description = "Orquestrador central — consolida todos os setores, valida CEO Rules, define ações"

    def __init__(self):
        super().__init__()
        # Instanciar todos os agentes diretores
        self.cfo = CFOAgent()
        self.coo = COOAgent()
        self.cmo = CMOAgent()
        self.legal = LegalAgent()
        self.rh = HRAgent()
        self.cso = CSOAgent()
        self.supply = SupplyAgent()
        self.bi = BIAgent()
        self.implantacao = ImplantacaoAgent()

    @property
    def system_prompt(self) -> str:
        return """Você é o CEO Agent do Frank AI OS para a rede Davvero Gelato.

Você recebe análises de 9 diretores especializados e sua função é:

1. CONSOLIDAR: Identificar o tema central e os 3 principais problemas da rede
2. VALIDAR: Checar todas as CEO Hard Rules e destacar violações
3. PRIORIZAR: Ordenar ações por impacto × urgência
4. DECIDIR: Emitir veredito executivo com GO/WAIT/NO-GO
5. ACIONAR: Definir quais ações automáticas devem ser executadas

CEO HARD RULES (absolutos — nunca negociar):
- CMV ≤ 30% | EBITDA ≥ 10% | Aluguel ≤ 12% | Payback ≤ 30m | ROI ≥ 1.5x

FORMATO DO RELATÓRIO EXECUTIVO:

🎯 DIAGNÓSTICO GERAL
[1 parágrafo: saúde geral da rede, principais pontos]

⚠️ CEO RULES STATUS
[5 semáforos: ✅ OK / 🔴 VIOLADO — com valores]

📊 TOP 3 ALERTAS CRÍTICOS
[Os 3 alertas mais urgentes, com unidade e ação imediata]

🏆 RANKING DE UNIDADES
[Melhor e pior unidade desta semana com métricas-chave]

📋 PLANO DE AÇÃO (próximas 72h)
[3 ações concretas com responsável, prazo e impacto esperado]

⚡ AÇÕES AUTOMÁTICAS EXECUTADAS
[Lista do que o sistema já disparou automaticamente]

💡 INSIGHT COPILOT
[1 observação proativa que nenhum diretor individual viu]"""

    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        """
        Executa análise completa: 9 agentes em paralelo + síntese CEO.
        GOLDEN RULE: asyncio.gather() — nunca sequencial.
        """
        date = kwargs.get("date", context.period)
        report_type = kwargs.get("report_type", "daily")

        logger.info("ceo_analysis_start", date=date, report_type=report_type)

        # ─── GOLDEN RULE: 9 agentes em paralelo ────────────────
        results = await asyncio.gather(
            self.cfo.run(context, date=date),
            self.coo.run(context, date=date),
            self.cmo.run(context, date=date),
            self.legal.run(context),
            self.rh.run(context),
            self.cso.run(context),
            self.supply.run(context, date=date),
            self.bi.run(context, date=date),
            self.implantacao.run(context),
            return_exceptions=True,
        )

        sector_results = {}
        all_alerts = []
        all_violations = context.violations
        total_tokens = 0

        agent_list = [
            self.cfo, self.coo, self.cmo, self.legal, self.rh,
            self.cso, self.supply, self.bi, self.implantacao
        ]

        for agent, result in zip(agent_list, results):
            if isinstance(result, Exception):
                logger.error("sector_agent_failed", agent=agent.name, error=str(result))
                sector_results[agent.sector] = {"error": str(result)}
            else:
                sector_results[agent.sector] = result
                total_tokens += result.get("tokens_used", 0)
                # Coletar alertas de cada setor
                alerts = result.get("alerts", []) + result.get("violations", [])
                for a in alerts:
                    a["sector"] = agent.sector
                    all_alerts.append(a)

        # ─── Síntese CEO via LLM ────────────────────────────────
        # Preparar resumo compacto dos resultados para o LLM
        summary_for_llm = {
            "date": date,
            "report_type": report_type,
            "total_alerts": len(all_alerts),
            "critical_alerts": [a for a in all_alerts if a.get("severity") == "critical"],
            "warning_alerts": [a for a in all_alerts if a.get("severity") == "warning"],
            "financial_network": sector_results.get("financeiro", {}).get("network", {}),
            "ops_network": sector_results.get("operacoes", {}).get("network", {}),
            "marketing_data": sector_results.get("marketing", {}).get("data", {}).get("meta_ads", {}),
            "ceo_rule_violations": all_violations,
            "expansion_pipeline": sector_results.get("expansao", {}).get("data", {}).get("pipeline", {}),
            "bi_forecast": sector_results.get("inteligencia", {}).get("data", {}).get("forecast_30d", {}),
        }

        # Análises textuais dos diretores
        director_analyses = {}
        for sector, result in sector_results.items():
            if "analysis" in result:
                director_analyses[sector] = result["analysis"][:500]  # compactar

        ceo_prompt = f"""Você recebeu análises de todos os 9 diretores da rede Davvero Gelato.

DATA: {date} | TIPO: {report_type.upper()}

RESUMO DOS DADOS:
{json.dumps(summary_for_llm, indent=2, default=str)}

ANÁLISES DOS DIRETORES:
{json.dumps(director_analyses, indent=2, default=str)}

Gere o RELATÓRIO EXECUTIVO CEO completo seguindo exatamente o formato do seu system prompt.
Seja específico com números, direto e acionável. Máximo 600 palavras."""

        executive_report, ceo_tokens = await self._call_llm(
            messages=[{"role": "user", "content": ceo_prompt}],
            max_tokens=2048,
        )

        total_tokens += ceo_tokens

        # ─── Definir ações automáticas ──────────────────────────
        auto_actions = self._define_auto_actions(all_alerts, sector_results)

        return {
            "status": "success",
            "date": date,
            "report_type": report_type,
            "executive_report": executive_report,
            "sector_results": sector_results,
            "all_alerts": all_alerts,
            "all_violations": all_violations,
            "auto_actions": auto_actions,
            "total_tokens_used": total_tokens,
            "agents_executed": len(agent_list),
        }

    def _define_auto_actions(
        self,
        alerts: List[Dict],
        sector_results: Dict,
    ) -> List[Dict]:
        """Define quais ações automáticas disparar baseado nos alertas."""
        actions = []

        for alert in alerts:
            severity = alert.get("severity", "info")
            alert_type = alert.get("type", "")
            unit_id = alert.get("unit_id", "REDE")

            if severity == "critical":
                # Email CEO
                actions.append({
                    "action_type": "send_email",
                    "priority": "high",
                    "recipient": "ceo@davvero.com.br",
                    "subject": f"🔴 ALERTA CRÍTICO: {alert_type} — {unit_id}",
                    "body_template": "critical_alert",
                    "payload": alert,
                    "trigger": f"alert:{alert_type}:{unit_id}",
                })
                # WhatsApp
                actions.append({
                    "action_type": "send_whatsapp",
                    "priority": "high",
                    "recipient": "admin",
                    "message": f"🔴 *FRANK AI OS* — ALERTA CRÍTICO\n{alert_type} em {unit_id}",
                    "trigger": f"alert:{alert_type}:{unit_id}",
                })

            elif severity == "warning" and alert_type in ("CMV_HIGH", "NPS_LOW", "AUDIT_LOW"):
                actions.append({
                    "action_type": "send_email",
                    "priority": "medium",
                    "recipient": "operations@davvero.com.br",
                    "subject": f"⚠️ ATENÇÃO: {alert_type} — {unit_id}",
                    "body_template": "warning_alert",
                    "payload": alert,
                })

        # Deduplicate por trigger
        seen = set()
        unique_actions = []
        for a in actions:
            key = f"{a['action_type']}:{a.get('trigger', '')}"
            if key not in seen:
                seen.add(key)
                unique_actions.append(a)

        return unique_actions[:10]  # máx 10 ações por ciclo

    async def morning_briefing(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Rotina de briefing matinal — entrada principal do CEO."""
        context = AgentContext()
        return await self.run(
            context,
            date=date or datetime.utcnow().strftime("%Y-%m-%d"),
            report_type="daily",
        )

    async def weekly_report(self) -> Dict[str, Any]:
        """Relatório semanal consolidado."""
        context = AgentContext()
        return await self.run(context, report_type="weekly")

    async def monthly_report(self) -> Dict[str, Any]:
        """Relatório mensal estratégico."""
        context = AgentContext()
        return await self.run(context, report_type="monthly")
