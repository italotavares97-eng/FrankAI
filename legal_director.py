"""
Legal Director — Diretor Jurídico da Davvero Gelato
Supervisiona contratos (COF), compliance regulatório, renovações e riscos jurídicos da rede.
"""

import json
import logging
from typing import Any

from core.base_agent import BaseAgent
from config import MODEL_MASTER, CEO_HARD_RULES

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = f"""Você é o Diretor Jurídico da Davvero Gelato,
responsável por toda a estrutura legal da franquia, desde contratos até compliance regulatório.

RESPONSABILIDADES ESTRATÉGICAS:
1. CONTRATOS: COF (Circular de Oferta de Franquia), contratos de franquia, renovações, aditivos
2. COMPLIANCE: Lei 13.966/2019 (Lei de Franquias), ANVISA, vigilância sanitária, LGPD, trabalhista
3. PROPRIEDADE INTELECTUAL: proteção da marca, trade dress, segredos industriais
4. CONTENCIOSO: monitoramento de disputas franqueado-franqueador
5. RISCOS JURÍDICOS: mapeamento e mitigação proativa

REGRAS INVIOLÁVEIS:
{json.dumps(CEO_HARD_RULES, ensure_ascii=False, indent=2)}

LEGISLAÇÃO RELEVANTE:
- Lei 13.966/2019 — Nova Lei de Franquias
- Lei 8.078/1990 — Código de Defesa do Consumidor
- Resolução ANVISA RDC 216/2004 — Boas Práticas para Serviços de Alimentação
- LGPD (Lei 13.709/2018) — proteção de dados dos franqueados e clientes
- CLT e legislação trabalhista vigente
- Código Civil Brasileiro (contratos, responsabilidade civil)

AGENTES SUBORDINADOS:
- ContractAgent: gestão do ciclo de vida dos contratos de franquia
- ComplianceAgent: monitoramento de conformidade regulatória e riscos

Formato de resposta obrigatório:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO

IMPORTANTE: Respostas jurídicas são orientações estratégicas. Para atos jurídicos formais,
sempre recomendar validação com advogado habilitado (OAB)."""


class LegalDirector(BaseAgent):
    """
    Legal Director. Routes to ContractAgent and ComplianceAgent,
    and handles direct strategic legal analysis using MODEL_MASTER.
    """

    def __init__(self):
        super().__init__(
            agent_name="LegalDirector",
            model=MODEL_MASTER,
            system_prompt=SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Internal routing helpers
    # ------------------------------------------------------------------

    async def _route_to_contracts(self, context: str) -> str:
        from contract_agent import ContractAgent
        agent = ContractAgent()
        return await agent.analyze(context)

    async def _route_to_compliance(self, context: str) -> str:
        from compliance_agent import ComplianceAgent
        agent = ComplianceAgent()
        return await agent.analyze(context)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        """
        Classify legal query and route to appropriate sub-agents,
        then synthesize a director-level legal response.
        """
        logger.info(f"[LegalDirector] analyze called | query={query[:80]!r}")

        # Fetch key legal metrics for context
        expiring_contracts = await self._fetch_expiring_contracts_summary()
        active_alerts = await self._fetch_legal_alerts()

        routing_prompt = f"""
CONSULTA JURÍDICA: {query}

CONTRATOS EXPIRANDO: {expiring_contracts}
ALERTAS JURÍDICOS: {active_alerts}

Classifique e retorne JSON:
{{
  "routing": ["contracts" | "compliance" | "direct"],
  "legal_area": "<área jurídica: contratual/regulatório/trabalhista/IP/outro>",
  "urgency": "crítica" | "alta" | "media" | "baixa",
  "summary": "<resumo em 1 linha>"
}}
Responda APENAS com JSON válido.
"""
        routing_raw = await self.call_claude(
            user_message=routing_prompt,
            system_override="Você é um classificador jurídico. Retorne apenas JSON válido.",
            model_override=MODEL_MASTER,
        )

        try:
            routing_data = json.loads(routing_raw.strip())
        except json.JSONDecodeError:
            logger.warning("[LegalDirector] Routing JSON parse failed, defaulting to direct")
            routing_data = {
                "routing": ["direct"],
                "legal_area": "geral",
                "urgency": "media",
                "summary": query,
            }

        routes: list[str] = routing_data.get("routing", ["direct"])
        sub_results: dict[str, str] = {}

        for route in routes:
            if route == "contracts":
                sub_results["contracts"] = await self._route_to_contracts(query)
            elif route == "compliance":
                sub_results["compliance"] = await self._route_to_compliance(query)

        # Synthesize at director level
        sub_context = ""
        for agent_name, result in sub_results.items():
            sub_context += f"\n\n=== ANÁLISE {agent_name.upper()} ===\n{result}"

        synthesis_prompt = f"""
CONSULTA JURÍDICA ORIGINAL: {query}

ÁREA JURÍDICA: {routing_data.get('legal_area', 'geral').upper()}
URGÊNCIA: {routing_data.get('urgency', 'media').upper()}

ANÁLISES DOS AGENTES ESPECIALIZADOS:
{sub_context if sub_context else '(análise direta — sem sub-agentes acionados)'}

CONTEXTO DA REDE:
{expiring_contracts}

ALERTAS JURÍDICOS ATIVOS:
{active_alerts}

Elabore uma resposta jurídica estratégica no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO

Inclua sempre: próximos passos concretos, prazos legais relevantes e recomendação de validação com advogado (OAB) quando necessário.
"""
        final_response = await self.call_claude(user_message=synthesis_prompt)

        logger.info("[LegalDirector] analyze completed")
        return final_response

    # ------------------------------------------------------------------
    # Legal dashboard
    # ------------------------------------------------------------------

    async def get_legal_dashboard(self) -> str:
        """Return a full legal status dashboard for C-suite."""
        logger.info("[LegalDirector] get_legal_dashboard called")
        return await self.analyze(
            "Gere um dashboard jurídico executivo completo: status de todos os contratos, "
            "riscos de compliance, contratos próximos ao vencimento e ações legais pendentes."
        )

    async def cof_status_report(self) -> str:
        """Report on COF (Circular de Oferta de Franquia) status and update needs."""
        from contract_agent import ContractAgent
        agent = ContractAgent()
        return await agent.cof_review()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _fetch_expiring_contracts_summary(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT f.name, f.email,
                   f.contract_start, f.contract_end,
                   f.status, f.royalty_pct,
                   (f.contract_end - CURRENT_DATE) AS days_to_expiry
            FROM franchisees f
            WHERE f.status = 'ativo'
              AND f.contract_end <= CURRENT_DATE + INTERVAL '12 months'
            ORDER BY f.contract_end ASC
            """
        )
        return self.format_db_data(rows, title="Contratos Expirando em 12 meses")

    async def _fetch_legal_alerts(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT a.severity, a.title, a.description, a.category,
                   u.code AS unit_code, u.name AS unit_name
            FROM alerts a
            JOIN units u ON u.id = a.unit_id
            WHERE a.is_active = TRUE
              AND a.category IN ('legal', 'compliance', 'contract')
            ORDER BY a.severity DESC, a.id DESC
            LIMIT 15
            """
        )
        return self.format_db_data(rows, title="Alertas Jurídicos Ativos")
