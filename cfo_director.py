"""
CFO Director — Frank AI OS (Davvero Gelato)
Orchestrates all CFO sub-agents: DRE, CMV, Cashflow, Valuation, Royalties, Budget.
"""

import re
import asyncio
from typing import Optional

from core.base_agent import BaseAgent
from config import MODEL_MASTER, CEO_HARD_RULES, OPERATIONAL_TARGETS, BRAND
from dre_agent import DREAgent
from cmv_agent import CMVAgent
from cashflow_agent import CashflowAgent
from valuation_agent import ValuationAgent
from royalties_agent import RoyaltiesAgent
from budget_agent import BudgetAgent


SYSTEM_PROMPT = f"""Você é o CFO (Chief Financial Officer) do {BRAND}, uma rede premium de gelato brasileiro.

MISSÃO
Garantir a saúde financeira de toda a rede franqueada: rentabilidade, conformidade, crescimento sustentável e retorno ao investidor.

AUTORIDADE FINANCEIRA
Você supervisiona e coordena os seguintes especialistas:
- DRE Agent: análise de demonstrativo de resultado por unidade e rede
- CMV Agent: custo de mercadoria vendida, mix de produtos e eficiência operacional
- Cashflow Agent: fluxo de caixa, capital de giro e projeções de liquidez
- Valuation Agent: valuation da rede, análise de ROI, payback e atratividade ao investidor
- Royalties Agent: receitas de royalties e fundo de marketing, adimplência e cobrança
- Budget Agent: orçamento vs realizado, variância e previsões

REGRAS INVIOLÁVEIS (Hard Rules)
{CEO_HARD_RULES}

METAS OPERACIONAIS
{OPERATIONAL_TARGETS}

POSTURA ANALÍTICA
- Pense como um CFO de private equity: rigoroso, orientado a dados, foco em retorno
- Toda recomendação deve ser sustentada por números concretos do banco de dados
- Identifique causas raiz, não apenas sintomas
- Priorize ações de maior impacto financeiro
- Sempre quantifique o impacto financeiro de cada recomendação

FORMATO DE RESPOSTA OBRIGATÓRIO
Toda resposta deve seguir exatamente esta estrutura de 10 blocos:
🎯 DIAGNÓSTICO
📊 DADOS
⚠️ ALERTAS
🔍 ANÁLISE (Causa Raiz)
📋 OPÇÕES
✅ RECOMENDAÇÃO
🚫 RISCOS
📅 PRAZO
🏆 RESULTADO ESPERADO
⚖️ DECISÃO [EXECUTAR | NÃO EXECUTAR | AGUARDAR | ESCALAR]
"""


# Keywords that route to each sub-agent
ROUTING_PATTERNS = {
    "dre": [
        r"dre", r"demonstrativo", r"resultado", r"p&l", r"pl\b",
        r"lucro", r"receita", r"despesa", r"ebitda", r"margem",
        r"faturamento", r"vendas", r"resultado operacional",
    ],
    "cmv": [
        r"\bcmv\b", r"custo de mercadoria", r"custo mercadoria",
        r"custo produto", r"insumo", r"desperdício", r"desperdicio",
        r"fornecedor", r"estoque", r"matéria.prima", r"materia.prima",
        r"food cost", r"eficiência operacional",
    ],
    "cashflow": [
        r"caixa", r"cash", r"fluxo", r"liquidez", r"capital de giro",
        r"pagamento", r"recebimento", r"saldo", r"inadimpl",
        r"projeção.*caixa", r"projecao.*caixa", r"working capital",
    ],
    "valuation": [
        r"valuation", r"valor.*rede", r"valor.*franquia", r"múltiplo",
        r"multiplo", r"payback", r"roi\b", r"retorno sobre invest",
        r"atratividade", r"investidor", r"exit", r"ebitda.*múltiplo",
    ],
    "royalties": [
        r"royalt", r"royalties", r"fundo.*marketing", r"fundo mkt",
        r"taxa.*franquia", r"adimpl", r"cobrança", r"cobranca",
        r"mensalidade.*franquead", r"repasse",
    ],
    "budget": [
        r"orçamento", r"orcamento", r"budget", r"meta.*financeira",
        r"previsão", r"previsao", r"forecast", r"variância", r"variancia",
        r"realizado.*planejado", r"planejado.*realizado", r"desvio",
    ],
}


class CFODirector(BaseAgent):
    MODEL = MODEL_MASTER

    def __init__(self):
        super().__init__()
        self._sub_agents: dict = {}

    def _get_sub_agents(self) -> dict:
        """Lazy-initialise sub-agents, injecting db/redis from this director."""
        if not self._sub_agents:
            agents = {
                "dre": DREAgent(),
                "cmv": CMVAgent(),
                "cashflow": CashflowAgent(),
                "valuation": ValuationAgent(),
                "royalties": RoyaltiesAgent(),
                "budget": BudgetAgent(),
            }
            for agent in agents.values():
                agent.db_pool = self.db_pool
                agent.redis_client = self.redis_client
            self._sub_agents = agents
        return self._sub_agents

    def _route_question(self, question: str) -> Optional[str]:
        """
        Return the key of the best-matching sub-agent, or None for a
        complex/cross-cutting question that the director should handle itself.
        """
        question_lower = question.lower()
        scores: dict[str, int] = {key: 0 for key in ROUTING_PATTERNS}

        for agent_key, patterns in ROUTING_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    scores[agent_key] += 1

        best_agent = max(scores, key=lambda k: scores[k])
        best_score = scores[best_agent]

        # Count how many agents scored above zero
        active_agents = sum(1 for s in scores.values() if s > 0)

        # If the question touches 3+ domains, handle directly as a cross-cutting query
        if active_agents >= 3:
            return None

        # If nothing matched, handle directly
        if best_score == 0:
            return None

        return best_agent

    async def _handle_complex_query(
        self,
        question: str,
        user: str,
        kpi_context: str,
        extra_context: str,
    ) -> str:
        """
        For cross-cutting financial questions, gather summaries from all
        relevant sub-agents and synthesise a director-level response.
        """
        sub_agents = self._get_sub_agents()

        # Run DRE + CMV + Cashflow in parallel for a broad financial snapshot
        dre_task = sub_agents["dre"].analyze(question, user, kpi_context, extra_context)
        cmv_task = sub_agents["cmv"].analyze(question, user, kpi_context, extra_context)
        cf_task = sub_agents["cashflow"].analyze(question, user, kpi_context, extra_context)

        dre_result, cmv_result, cf_result = await asyncio.gather(
            dre_task, cmv_task, cf_task
        )

        synthesis_context = f"""
ANÁLISE CROSS-FUNCIONAL — PERGUNTA DO USUÁRIO: {question}

USUÁRIO: {user}

KPIs ATUAIS DA REDE:
{kpi_context}

CONTEXTO ADICIONAL:
{extra_context}

=== ANÁLISE DRE (P&L) ===
{dre_result}

=== ANÁLISE CMV ===
{cmv_result}

=== ANÁLISE FLUXO DE CAIXA ===
{cf_result}
"""

        return await self.call_claude(
            user_message=synthesis_context,
            extra_system=(
                "Você está sintetizando análises de múltiplos especialistas financeiros. "
                "Integre as perspectivas em uma visão executiva coesa, priorizando os "
                "pontos de maior impacto financeiro para a rede. "
                "Siga rigorosamente o formato de 10 blocos."
            ),
            max_tokens=4000,
        )

    async def analyze(
        self,
        question: str,
        user: str,
        kpi_context: str = "",
        extra_context: str = "",
    ) -> str:
        """
        Main entry point. Routes the question to the appropriate sub-agent
        or handles it directly if cross-cutting.
        """
        agent_key = self._route_question(question)

        if agent_key is not None:
            sub_agents = self._get_sub_agents()
            agent = sub_agents[agent_key]
            return await agent.analyze(question, user, kpi_context, extra_context)

        # Cross-cutting or general CFO question — handle directly
        return await self._handle_complex_query(question, user, kpi_context, extra_context)
