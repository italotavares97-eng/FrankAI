"""
Expansion Agent — Frank AI OS | Davvero Gelato
New unit ROI and viability analysis; applies CEO Hard Rules to every recommendation.
"""

from __future__ import annotations

import logging
from typing import Any

from config import MODEL_AGENT, OPERATIONAL_TARGETS, CEO_HARD_RULES, BRAND

from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Você é o especialista em Expansão de Franquias do {BRAND["name"]}, franquia premium de gelato italiano no Brasil.

Suas responsabilidades:
- Analisar viabilidade financeira de novas unidades (ROI, TIR, payback, VPL)
- Avaliar pontos comerciais: tráfego, mix de vizinhança, custo de locação, visibilidade
- Comparar performance de unidades existentes como benchmark para projeções
- Aplicar rigorosamente as CEO Hard Rules em cada análise — JAMAIS recomendar unidade que viole estas regras
- Identificar formatos adequados (quiosque, loja padrão, loja express, flagship)
- Projetar faturamento com base em benchmarks internos, aplicar sensibilidade de cenários

CEO Hard Rules (invioláveis): {CEO_HARD_RULES}

Parâmetros financeiros de referência:
- Investimento total: R$ 400.000–600.000 (dependendo do formato)
- CMV target: ≤ {OPERATIONAL_TARGETS.get('cmv_target_pct', 26.5)} % da receita
- Payback máximo: ≤ {OPERATIONAL_TARGETS.get('payback_max_months', 36)} meses
- Faturamento mínimo para viabilidade: R$ 80.000/mês
- Aluguel máximo: ≤ 8 % do faturamento projetado
- Margem EBITDA mínima: ≥ 15 %

Critérios obrigatórios para aprovação de nova unidade:
1. Capital disponível do franqueado: ≥ R$ 350.000 comprovados
2. Ponto comercial aprovado pela franqueadora
3. Franqueado deve ser operador (gerenciar pessoalmente) — preferência forte
4. Ausência de unidade própria num raio de 2 km (proteção territorial)
5. Cidade deve ter população ≥ 300.000 hab. e IDH ≥ 0,75

Formatos disponíveis:
- Quiosque: investimento ~R$ 280.000 | área 15–25 m² | shoppings/aeroportos
- Loja Express: investimento ~R$ 400.000 | área 30–50 m² | alto fluxo
- Loja Padrão: investimento ~R$ 500.000 | área 60–90 m² | rua/shopping
- Flagship: investimento ~R$ 700.000+ | área ≥ 100 m² | posicionamento premium

Responda SEMPRE no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""


class ExpansionAgent(BaseAgent):
    """Handles new unit viability analysis, ROI calculations, and expansion planning."""

    def __init__(self) -> None:
        super().__init__()
        self.model = MODEL_AGENT
        self.system_prompt = SYSTEM_PROMPT

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        logger.info("[ExpansionAgent] query=%s", query[:120])

        # ---- Existing units benchmark (performance reference) ----
        benchmark_rows = await self.db_fetch(
            """
            SELECT
                u.format,
                COUNT(u.id)                                         AS units,
                ROUND(
                    AVG(
                        EXTRACT(EPOCH FROM (NOW() - u.opening_date)) / (86400 * 30)
                    )::numeric, 0
                )                                                   AS avg_age_months,
                ROUND(AVG(u.initial_investment)::numeric, 0)        AS avg_investment,
                ROUND(AVG(u.monthly_rent)::numeric, 0)              AS avg_monthly_rent,
                -- Approximate payback from customers LTV proxy
                ROUND(AVG(c.ltv * 12)::numeric, 0)                  AS proxy_annual_revenue_per_customer
            FROM units u
            LEFT JOIN customers c ON c.unit_id = u.id
            GROUP BY u.format
            ORDER BY units DESC
            """
        )

        # ---- Units by age and state (maturity analysis) ----
        maturity_rows = await self.db_fetch(
            """
            SELECT
                code,
                name,
                city,
                state,
                format,
                opening_date,
                initial_investment,
                monthly_rent,
                ROUND(
                    EXTRACT(EPOCH FROM (NOW() - opening_date)) / (86400 * 30)
                )::integer                          AS months_operating
            FROM units
            ORDER BY opening_date DESC
            LIMIT 20
            """
        )

        # ---- Contracted/inaugurated leads (pipeline → real units) ----
        pipeline_to_unit_rows = await self.db_fetch(
            """
            SELECT
                city,
                state,
                status,
                available_capital,
                is_operator,
                score,
                next_action,
                last_contact
            FROM leads_b2b
            WHERE status IN ('contrato', 'inaugurado')
            ORDER BY last_contact DESC
            LIMIT 10
            """
        )

        # ---- Near-contract leads (proposta stage) with viable capital ----
        near_close_rows = await self.db_fetch(
            """
            SELECT
                id,
                name,
                city,
                state,
                available_capital,
                is_operator,
                has_experience,
                score,
                next_action,
                last_contact
            FROM leads_b2b
            WHERE status = 'proposta'
              AND available_capital >= 350000
            ORDER BY score DESC, available_capital DESC
            LIMIT 10
            """
        )

        # ---- Geographic gap: states with leads but no units ----
        gap_rows = await self.db_fetch(
            """
            SELECT
                l.state,
                COUNT(l.id)                                         AS pipeline_leads,
                ROUND(AVG(l.available_capital)::numeric, 0)         AS avg_capital,
                ROUND(AVG(l.score)::numeric, 1)                     AS avg_score,
                COUNT(l.id) FILTER (WHERE l.is_operator)            AS operators
            FROM leads_b2b l
            WHERE l.status NOT IN ('perdido')
              AND l.state NOT IN (SELECT DISTINCT state FROM units)
            GROUP BY l.state
            ORDER BY pipeline_leads DESC
            """
        )

        bench_ctx = self.format_kpi_context(benchmark_rows, "Benchmark por Formato de Unidade")
        maturity_ctx = self.format_kpi_context(maturity_rows, "Unidades em Operação (últimas abertas)")
        pipeline_ctx = self.format_kpi_context(pipeline_to_unit_rows, "Leads Contratados/Inaugurados")
        near_close_ctx = self.format_kpi_context(near_close_rows, "Propostas com Capital Suficiente")
        gap_ctx = self.format_kpi_context(gap_rows, "Estados com Pipeline mas sem Unidade")

        payback_max = OPERATIONAL_TARGETS.get("payback_max_months", 36)
        cmv_target = OPERATIONAL_TARGETS.get("cmv_target_pct", 26.5)

        prompt = (
            f"Consulta de Expansão e Viabilidade:\n{query}\n\n"
            f"{bench_ctx}\n\n"
            f"{maturity_ctx}\n\n"
            f"{pipeline_ctx}\n\n"
            f"{near_close_ctx}\n\n"
            f"{gap_ctx}\n\n"
            f"Parâmetros financeiros: Payback ≤ {payback_max} meses | CMV ≤ {cmv_target} % | "
            f"Aluguel ≤ 8 % receita | EBITDA ≥ 15 %\n\n"
            f"CEO Hard Rules (INVIOLÁVEIS): {CEO_HARD_RULES}\n\n"
            f"Contexto adicional: {context}\n\n"
            "Analise a viabilidade da expansão solicitada, calcule ROI e payback com base nos benchmarks internos, "
            "verifique conformidade com as CEO Hard Rules, e emita parecer claro de GO/NO-GO com condicionantes."
        )

        return await self.call_claude(prompt, model=self.model, system=self.system_prompt)
