"""
DRE Agent — Frank AI OS (Davvero Gelato)
Specialist in Demonstrativo de Resultado (P&L) analysis for individual units
and the overall network.
"""

from typing import Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, CEO_HARD_RULES, BRAND


SYSTEM_PROMPT = f"""Você é o Analista de DRE (Demonstrativo de Resultado do Exercício) do {BRAND}.

ESPECIALIDADE
Análise profunda de P&L: leitura, interpretação e diagnóstico de demonstrativos de resultado
por unidade e para a rede consolidada. Você identifica padrões, tendências e desvios críticos.

ESTRUTURA DO DRE — DAVVERO GELATO
Receita Bruta
(-) Impostos (~6% Simples Nacional)
= Receita Líquida
(-) CMV (meta: 26,5% | máximo: 30%)
= Margem Bruta
(-) Despesas Operacionais
    - Aluguel (máximo: 12% da receita líquida)
    - Folha de Pagamento
    - Royalties (8,5%)
    - Fundo de Marketing (1,5%)
    - Outras despesas
= EBITDA Operacional (mínimo: 10%)
(-) Depreciação / Amortização
= EBIT
(-) Resultado Financeiro
= Lucro Líquido

REGRAS INVIOLÁVEIS
{CEO_HARD_RULES}

METAS OPERACIONAIS
{OPERATIONAL_TARGETS}

BENCHMARKS DE MERCADO
- CMV mercado de sorvetes/gelato: 35% | Meta Davvero: 26,5% (vantagem competitiva de 8,5pp)
- Ticket médio meta: R$35
- EBITDA mínimo saudável: 10%
- Aluguel máximo: 12% da receita líquida

METODOLOGIA DE ANÁLISE
1. Compare actual vs meta vs mercado
2. Identifique as 3 principais causas de desvio
3. Calcule o impacto financeiro em R$ de cada desvio
4. Priorize por materialidade
5. Recomende ações com ROI estimado

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


class DREAgent(BaseAgent):
    MODEL = MODEL_AGENT

    async def _fetch_dre_data(
        self,
        unit_id: Optional[int] = None,
        months: int = 6,
    ) -> list[dict]:
        """
        Fetches the last N months of DRE data. If unit_id is provided, fetches
        for that specific unit. Otherwise fetches the network-wide view.
        """
        if unit_id is not None:
            query = """
                SELECT
                    uf.unit_id,
                    u.name          AS unit_name,
                    u.city,
                    u.format,
                    uf.month,
                    uf.gross_revenue,
                    uf.net_revenue,
                    uf.cogs_value,
                    uf.net_cogs,
                    uf.cmv_pct,
                    uf.gross_margin,
                    uf.gross_margin_pct,
                    uf.total_opex,
                    uf.ebitda_operational,
                    uf.ebitda_pct,
                    uf.net_income,
                    uf.net_margin_pct,
                    uf.rent,
                    uf.payroll,
                    uf.royalties,
                    uf.rent_pct
                FROM unit_financials uf
                JOIN units u ON u.id = uf.unit_id
                WHERE uf.unit_id = $1
                ORDER BY uf.month DESC
                LIMIT $2
            """
            return await self.db_fetch(query, unit_id, months)
        else:
            query = """
                SELECT
                    uf.unit_id,
                    u.name          AS unit_name,
                    u.city,
                    u.format,
                    uf.month,
                    uf.gross_revenue,
                    uf.net_revenue,
                    uf.cogs_value,
                    uf.net_cogs,
                    uf.cmv_pct,
                    uf.gross_margin,
                    uf.gross_margin_pct,
                    uf.total_opex,
                    uf.ebitda_operational,
                    uf.ebitda_pct,
                    uf.net_income,
                    uf.net_margin_pct,
                    uf.rent,
                    uf.payroll,
                    uf.royalties,
                    uf.rent_pct
                FROM unit_financials uf
                JOIN units u ON u.id = uf.unit_id
                WHERE u.status = 'active'
                ORDER BY uf.month DESC, uf.gross_revenue DESC
                LIMIT $1
            """
            return await self.db_fetch(query, months * 20)  # up to 20 active units

    async def _fetch_network_dre(self) -> list[dict]:
        """Fetches the consolidated network DRE from the dedicated view."""
        query = "SELECT * FROM vw_network_dre_current ORDER BY month DESC LIMIT 6"
        return await self.db_fetch(query)

    async def _fetch_units_summary(self) -> list[dict]:
        """Fetches a quick summary of active units for context."""
        query = """
            SELECT id, code, name, city, format, status, opening_date
            FROM units
            WHERE status = 'active'
            ORDER BY opening_date
        """
        return await self.db_fetch(query)

    def _build_dre_context(
        self,
        unit_rows: list[dict],
        network_rows: list[dict],
        units_summary: list[dict],
    ) -> str:
        """Formats DB data into a rich text context for the LLM."""
        lines = ["=== DADOS DRE — ÚLTIMOS 6 MESES ===\n"]

        # Network consolidated
        if network_rows:
            lines.append("--- REDE CONSOLIDADA ---")
            for row in network_rows[:6]:
                lines.append(
                    f"Mês: {row.get('month', 'N/A')} | "
                    f"Receita Bruta: R${row.get('gross_revenue', 0):,.2f} | "
                    f"Receita Líquida: R${row.get('net_revenue', 0):,.2f} | "
                    f"CMV%: {row.get('cmv_pct', 0):.1f}% | "
                    f"Margem Bruta: {row.get('gross_margin_pct', 0):.1f}% | "
                    f"EBITDA: {row.get('ebitda_pct', 0):.1f}% | "
                    f"Lucro Líquido: R${row.get('net_income', 0):,.2f}"
                )
            lines.append("")

        # Active units summary
        if units_summary:
            lines.append(f"--- UNIDADES ATIVAS ({len(units_summary)}) ---")
            for u in units_summary:
                lines.append(
                    f"  [{u.get('code', '')}] {u.get('name', '')} — "
                    f"{u.get('city', '')} | Formato: {u.get('format', '')} | "
                    f"Abertura: {u.get('opening_date', 'N/A')}"
                )
            lines.append("")

        # Per-unit DRE
        if unit_rows:
            # Group by unit
            by_unit: dict[int, list[dict]] = {}
            for row in unit_rows:
                uid = row.get("unit_id")
                by_unit.setdefault(uid, []).append(row)

            for uid, rows in by_unit.items():
                latest = rows[0]
                lines.append(
                    f"--- UNIDADE: {latest.get('unit_name', uid)} "
                    f"({latest.get('city', '')}) ---"
                )
                for row in rows:
                    ebitda_flag = (
                        " ⚠️ ABAIXO META"
                        if (row.get("ebitda_pct") or 0) < 10
                        else ""
                    )
                    cmv_flag = (
                        " 🚨 CMV CRÍTICO"
                        if (row.get("cmv_pct") or 0) > 30
                        else (
                            " ⚠️ CMV ELEVADO"
                            if (row.get("cmv_pct") or 0) > 26.5
                            else ""
                        )
                    )
                    rent_flag = (
                        " 🚨 ALUGUEL CRÍTICO"
                        if (row.get("rent_pct") or 0) > 12
                        else ""
                    )
                    lines.append(
                        f"  Mês: {row.get('month', 'N/A')} | "
                        f"Rev. Bruta: R${row.get('gross_revenue', 0):,.2f} | "
                        f"Rev. Líq: R${row.get('net_revenue', 0):,.2f} | "
                        f"CMV: {row.get('cmv_pct', 0):.1f}%{cmv_flag} | "
                        f"Mg Bruta: {row.get('gross_margin_pct', 0):.1f}% | "
                        f"EBITDA: {row.get('ebitda_pct', 0):.1f}%{ebitda_flag} | "
                        f"Aluguel: {row.get('rent_pct', 0):.1f}%{rent_flag} | "
                        f"Royalties: R${row.get('royalties', 0):,.2f} | "
                        f"Folha: R${row.get('payroll', 0):,.2f}"
                    )
                lines.append("")

        return "\n".join(lines)

    async def analyze(
        self,
        question: str,
        user: str,
        kpi_context: str = "",
        extra_context: str = "",
    ) -> str:
        """
        Fetches DRE data for the last 6 months, builds rich context and
        calls Claude for a structured 10-block financial analysis.
        """
        # Fetch data in parallel
        unit_rows, network_rows, units_summary = await self._gather_all_data()

        dre_context = self._build_dre_context(unit_rows, network_rows, units_summary)

        full_context = f"""
PERGUNTA: {question}

USUÁRIO: {user}

{dre_context}

=== KPIs ATUAIS DA REDE ===
{kpi_context}

=== CONTEXTO ADICIONAL ===
{extra_context}
"""

        return await self.call_claude(
            user_message=full_context,
            extra_system=SYSTEM_PROMPT,
            max_tokens=3500,
        )

    async def _gather_all_data(self):
        """Run all DB fetches concurrently."""
        import asyncio
        unit_task = self._fetch_dre_data(unit_id=None, months=6)
        network_task = self._fetch_network_dre()
        summary_task = self._fetch_units_summary()
        return await asyncio.gather(unit_task, network_task, summary_task)
