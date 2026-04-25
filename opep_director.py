"""
OPEP Director — Operações e Expansão de Pessoas
COO-level agent that routes requests to TrainingAgent, ImplantationAgent, and HRAgent.
"""

import json
import logging
from typing import Any

from core.base_agent import BaseAgent
from config import MODEL_MASTER, CEO_HARD_RULES, OPERATIONAL_TARGETS

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = f"""Você é o Diretor de OPEP (Operações e Expansão de Pessoas) da Davvero Gelato,
equivalente a um COO sênior. Sua responsabilidade abrange:

1. OPERAÇÕES: Garantir excelência operacional em todas as ~15 unidades da rede
2. EXPANSÃO: Supervisionar abertura de novas lojas e projetos de implantação
3. PESSOAS: Cuidar do capital humano — recrutamento, treinamento, retenção, cultura

REGRAS INVIOLÁVEIS DO CEO:
{json.dumps(CEO_HARD_RULES, ensure_ascii=False, indent=2)}

METAS OPERACIONAIS:
{json.dumps(OPERATIONAL_TARGETS, ensure_ascii=False, indent=2)}

Você roteia demandas para os agentes especializados:
- TrainingAgent: análise de gaps de treinamento, desenvolvimento de programas
- ImplantationAgent: abertura de novas lojas, cronograma, checklist pré-abertura
- HRAgent: gestão de equipes, dimensionamento, retenção

Sempre responda no formato estruturado:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO

Seja direto, estratégico e orientado a resultados. Priorize sempre a experiência do franqueado e do cliente final."""


class OPEPDirector(BaseAgent):
    """
    COO/OPEP Director. Orchestrates Training, Implantation, and HR agents.
    Uses MODEL_MASTER for strategic decisions; sub-agents use MODEL_AGENT.
    """

    def __init__(self):
        super().__init__(
            agent_name="OPEPDirector",
            model=MODEL_MASTER,
            system_prompt=SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Internal routing helpers
    # ------------------------------------------------------------------

    async def _route_to_training(self, context: str) -> str:
        from training_agent import TrainingAgent
        agent = TrainingAgent()
        return await agent.analyze(context)

    async def _route_to_implantation(self, context: str) -> str:
        from implantation_agent import ImplantationAgent
        agent = ImplantationAgent()
        return await agent.analyze(context)

    async def _route_to_hr(self, context: str) -> str:
        from hr_agent import HRAgent
        agent = HRAgent()
        return await agent.analyze(context)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        """
        Classify the query and route to the appropriate sub-agent,
        then synthesize a director-level response.
        """
        logger.info(f"[OPEPDirector] analyze called | query={query[:80]!r}")

        # Fetch network-wide snapshot for context enrichment
        units_summary = await self._fetch_units_summary()
        implantation_units = await self._fetch_implantation_units()

        routing_prompt = f"""
CONSULTA RECEBIDA:
{query}

CONTEXTO DA REDE:
{units_summary}

UNIDADES EM IMPLANTAÇÃO:
{implantation_units}

Classifique a consulta em uma ou mais categorias e devolva JSON:
{{
  "routing": ["training" | "implantation" | "hr" | "direct"],
  "summary": "<resumo da demanda em 1 linha>",
  "priority": "alta" | "media" | "baixa"
}}
Responda SOMENTE com o JSON, sem markdown.
"""
        routing_raw = await self.call_claude(
            user_message=routing_prompt,
            system_override="Você é um roteador inteligente. Devolva apenas JSON válido.",
            model_override=MODEL_MASTER,
        )

        try:
            routing_data = json.loads(routing_raw.strip())
        except json.JSONDecodeError:
            logger.warning("[OPEPDirector] Routing JSON parse failed, defaulting to direct")
            routing_data = {"routing": ["direct"], "summary": query, "priority": "media"}

        routes: list[str] = routing_data.get("routing", ["direct"])
        sub_results: dict[str, str] = {}

        for route in routes:
            if route == "training":
                sub_results["training"] = await self._route_to_training(query)
            elif route == "implantation":
                sub_results["implantation"] = await self._route_to_implantation(query)
            elif route == "hr":
                sub_results["hr"] = await self._route_to_hr(query)

        # Build synthesis prompt
        sub_context = ""
        for agent_name, result in sub_results.items():
            sub_context += f"\n\n=== RESULTADO DO AGENTE {agent_name.upper()} ===\n{result}"

        synthesis_prompt = f"""
CONSULTA ORIGINAL: {query}

PRIORIDADE: {routing_data.get('priority', 'media').upper()}

ANÁLISES DOS AGENTES ESPECIALIZADOS:
{sub_context if sub_context else '(análise direta — sem sub-agentes acionados)'}

DADOS DA REDE:
{units_summary}

Com base em todas essas informações, elabore uma resposta estratégica no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""
        final_response = await self.call_claude(
            user_message=synthesis_prompt,
        )

        logger.info("[OPEPDirector] analyze completed")
        return final_response

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _fetch_units_summary(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT code, name, city, format, status, color_status,
                   manager_name, team_count
            FROM units
            WHERE status != 'encerrada'
            ORDER BY status, name
            """
        )
        return self.format_db_data(rows, title="Unidades Ativas da Rede")

    async def _fetch_implantation_units(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT code, name, city, format, opening_date, manager_name
            FROM units
            WHERE status = 'em_implantacao'
            ORDER BY opening_date
            """
        )
        return self.format_db_data(rows, title="Unidades em Implantação")

    # ------------------------------------------------------------------
    # Operational overview (used by FrankMaster or scheduled tasks)
    # ------------------------------------------------------------------

    async def get_opep_dashboard(self) -> str:
        """Return a full OPEP operational overview for C-suite consumption."""
        logger.info("[OPEPDirector] get_opep_dashboard called")
        return await self.analyze(
            "Gere um dashboard executivo completo de OPEP: status operacional de todas as unidades, "
            "gaps de treinamento críticos, status das implantações em andamento, e principais alertas de RH."
        )
