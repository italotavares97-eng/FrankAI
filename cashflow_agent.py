"""
Cashflow Agent — Frank AI OS (Davvero Gelato)
Specialist in cash flow management, working capital, liquidity forecasting
and financial cycle analysis for the franchise network.
"""

import asyncio
from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, CEO_HARD_RULES, BRAND


SYSTEM_PROMPT = f"""Você é o Analista de Fluxo de Caixa do {BRAND}.

ESPECIALIDADE
Gestão de liquidez, capital de giro, ciclo financeiro e projeções de caixa
para a rede franqueada. Você antecipa problemas de liquidez antes que virem crises.

SEU DOMÍNIO
- Análise de fluxo de caixa operacional por unidade e rede consolidada
- Capital de giro: necessidade, ciclo financeiro e giro de caixa
- Projeções de caixa para 30, 60 e 90 dias
- Identificação de unidades em risco de liquidez
- Gestão de inadimplência de royalties e seus impactos no caixa da franqueadora
- Sazonalidade do negócio (picos verão/inverno, datas comemorativas)
- Análise de break-even de caixa por unidade

DINÂMICA DE CAIXA — GELATO PREMIUM
- Recebimento: predominantemente à vista ou D+1 (cartões)
- Pagamento de fornecedores: 15 a 30 dias
- Folha de pagamento: mensal (dia 5 do mês seguinte)
- Royalties e fundo MKT: 8,5% + 1,5% = 10% da receita bruta, pagos mensalmente
- Aluguel: pagamento fixo mensal (prazo contratual)
- Sazonalidade: verão (out-mar) = pico de receita; inverno (jun-ago) = baixa

SINAIS DE ALERTA DE LIQUIDEZ
🚨 Crítico:
  - EBITDA < 0 (caixa operacional negativo)
  - Saldo de caixa < 1 folha de pagamento
  - Inadimplência de royalties > 60 dias

⚠️ Atenção:
  - EBITDA entre 0% e 5%
  - Tendência de queda de receita por 3 meses consecutivos
  - Aluguel > 12% da receita

FERRAMENTAS DE ANÁLISE
1. Demonstrativo de Fluxo de Caixa Indireto (EBITDA → Caixa)
2. Análise de Ciclo Financeiro (PMR + PME - PMP)
3. Projeção Rolling 90 dias
4. Stress Test: impacto de queda de 15% na receita no caixa

REGRAS INVIOLÁVEIS
{CEO_HARD_RULES}

METAS OPERACIONAIS
{OPERATIONAL_TARGETS}

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


class CashflowAgent(BaseAgent):
    MODEL = MODEL_AGENT

    async def _fetch_cashflow_data(self, months: int = 3) -> list[dict]:
        """
        Fetches the last N months of financial data per unit.
        Derives cash-flow proxies from EBITDA and balance sheet items.
        """
        query = """
            SELECT
                uf.unit_id,
                u.name              AS unit_name,
                u.city,
                u.format,
                uf.month,
                uf.gross_revenue,
                uf.net_revenue,
                uf.ebitda_operational,
                uf.ebitda_pct,
                uf.total_opex,
                uf.rent,
                uf.payroll,
                uf.royalties,
                uf.net_income,
                uf.net_margin_pct,
                -- Approximate free cash flow: EBITDA minus rent and payroll
                (uf.ebitda_operational - uf.rent - uf.payroll)
                                    AS approx_fcf
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE u.status = 'active'
            ORDER BY uf.month DESC, uf.ebitda_pct ASC
            LIMIT $1
        """
        return await self.db_fetch(query, months * 25)

    async def _fetch_royalties_cashflow(self, months: int = 3) -> list[dict]:
        """
        Fetches royalty payments per unit to identify delinquency
        and the cashflow impact on the franchisor side.
        """
        query = """
            SELECT
                uf.unit_id,
                u.name      AS unit_name,
                u.city,
                uf.month,
                uf.gross_revenue,
                uf.royalties                         AS royalties_paid,
                (uf.gross_revenue * 0.085)           AS royalties_expected,
                (uf.gross_revenue * 0.015)           AS mkt_fund_expected,
                (uf.gross_revenue * 0.10)            AS total_fees_expected,
                -- gap flags
                CASE
                    WHEN uf.royalties < (uf.gross_revenue * 0.085 * 0.95)
                    THEN 'UNDERPAYD'
                    ELSE 'OK'
                END                                  AS royalty_status
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE u.status = 'active'
            ORDER BY uf.month DESC, uf.royalties ASC
            LIMIT $1
        """
        return await self.db_fetch(query, months * 25)

    async def _fetch_network_cashflow_summary(self) -> list[dict]:
        """
        Aggregates cashflow at the network level per month.
        """
        query = """
            SELECT
                uf.month,
                COUNT(DISTINCT uf.unit_id)              AS units,
                SUM(uf.gross_revenue)                   AS total_gross_revenue,
                SUM(uf.net_revenue)                     AS total_net_revenue,
                SUM(uf.ebitda_operational)              AS total_ebitda,
                ROUND(
                    SUM(uf.ebitda_operational)::numeric /
                    NULLIF(SUM(uf.net_revenue), 0) * 100, 2
                )                                       AS network_ebitda_pct,
                SUM(uf.rent)                            AS total_rent,
                SUM(uf.payroll)                         AS total_payroll,
                SUM(uf.royalties)                       AS total_royalties_collected,
                SUM(uf.net_income)                      AS total_net_income
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE u.status = 'active'
            GROUP BY uf.month
            ORDER BY uf.month DESC
            LIMIT 6
        """
        return await self.db_fetch(query)

    def _build_cashflow_context(
        self,
        unit_data: list[dict],
        royalties_data: list[dict],
        network_summary: list[dict],
    ) -> str:
        """Formats cashflow data into a structured analysis context."""
        lines = ["=== ANÁLISE DE FLUXO DE CAIXA — DAVVERO GELATO ===\n"]

        # Network cashflow trend
        if network_summary:
            lines.append("--- CAIXA OPERACIONAL DA REDE (últimos 6 meses) ---")
            prev_ebitda = None
            for row in network_summary:
                ebitda = row.get("total_ebitda") or 0
                ebitda_pct = row.get("network_ebitda_pct") or 0
                trend = ""
                if prev_ebitda is not None:
                    if ebitda < prev_ebitda * 0.95:
                        trend = " 📉 QUEDA"
                    elif ebitda > prev_ebitda * 1.05:
                        trend = " 📈 CRESCIMENTO"
                    else:
                        trend = " ➡️ ESTÁVEL"
                prev_ebitda = ebitda

                alert = ""
                if ebitda_pct < 0:
                    alert = " 🚨 CAIXA NEGATIVO"
                elif ebitda_pct < 5:
                    alert = " 🔴 LIQUIDEZ CRÍTICA"
                elif ebitda_pct < 10:
                    alert = " ⚠️ ABAIXO DA META"

                lines.append(
                    f"  {row.get('month', 'N/A')} | "
                    f"EBITDA: R${ebitda:,.2f} ({ebitda_pct:.1f}%){alert}{trend} | "
                    f"Receita Bruta: R${row.get('total_gross_revenue', 0):,.2f} | "
                    f"Royalties Coletados: R${row.get('total_royalties_collected', 0):,.2f} | "
                    f"Folha Total: R${row.get('total_payroll', 0):,.2f} | "
                    f"Aluguel Total: R${row.get('total_rent', 0):,.2f}"
                )
            lines.append("")

        # Units with cashflow risk (lowest EBITDA first)
        if unit_data:
            by_unit: dict = {}
            for row in unit_data:
                uid = row.get("unit_id")
                by_unit.setdefault(uid, []).append(row)

            critical_units = []
            for uid, rows in by_unit.items():
                latest = rows[0]
                ebitda_pct = latest.get("ebitda_pct") or 0
                if ebitda_pct < 10:
                    critical_units.append((ebitda_pct, latest, rows))

            critical_units.sort(key=lambda x: x[0])

            lines.append("--- UNIDADES COM RISCO DE LIQUIDEZ (EBITDA < 10%) ---")
            if critical_units:
                for ebitda_pct, latest, rows in critical_units[:8]:
                    status = "🚨 CAIXA NEGATIVO" if ebitda_pct < 0 else (
                        "🔴 CRÍTICO" if ebitda_pct < 5 else "⚠️ ATENÇÃO"
                    )
                    trend_vals = [
                        f"{r.get('month', '?')[:7]}:{r.get('ebitda_pct', 0):.1f}%"
                        for r in rows[:3]
                    ]
                    fcf = latest.get("approx_fcf") or 0
                    lines.append(
                        f"  {status} {latest.get('unit_name', uid):<30} | "
                        f"EBITDA: {ebitda_pct:.1f}% | "
                        f"FCF Aprox: R${fcf:,.2f} | "
                        f"Tendência: {' → '.join(trend_vals)}"
                    )
            else:
                lines.append("  ✅ Nenhuma unidade em zona crítica de liquidez")
            lines.append("")

            # Full cashflow table for reference
            lines.append("--- FLUXO DE CAIXA POR UNIDADE (3 meses mais recentes) ---")
            shown_units = set()
            for row in unit_data[:60]:
                uid = row.get("unit_id")
                name = row.get("unit_name", uid)
                if uid not in shown_units:
                    shown_units.add(uid)
                    lines.append(f"  [{name}]")
                lines.append(
                    f"    {row.get('month', 'N/A')} | "
                    f"Rev: R${row.get('gross_revenue', 0):,.2f} | "
                    f"EBITDA: R${row.get('ebitda_operational', 0):,.2f} ({row.get('ebitda_pct', 0):.1f}%) | "
                    f"Aluguel: R${row.get('rent', 0):,.2f} | "
                    f"Folha: R${row.get('payroll', 0):,.2f}"
                )
            lines.append("")

        # Royalties cashflow
        if royalties_data:
            underpayd = [r for r in royalties_data if r.get("royalty_status") == "UNDERPAYD"]
            if underpayd:
                lines.append(f"--- ⚠️ ROYALTIES ABAIXO DO ESPERADO ({len(underpayd)} ocorrências) ---")
                for row in underpayd[:10]:
                    gap = (row.get("royalties_expected") or 0) - (row.get("royalties_paid") or 0)
                    lines.append(
                        f"  {row.get('unit_name', '?')} | Mês: {row.get('month', 'N/A')} | "
                        f"Pago: R${row.get('royalties_paid', 0):,.2f} | "
                        f"Esperado: R${row.get('royalties_expected', 0):,.2f} | "
                        f"Gap: R${gap:,.2f}"
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
        Fetches 3-month cashflow data, identifies liquidity risks and
        calls Claude for a structured 10-block cashflow analysis.
        """
        unit_data, royalties_data, network_summary = await asyncio.gather(
            self._fetch_cashflow_data(months=3),
            self._fetch_royalties_cashflow(months=3),
            self._fetch_network_cashflow_summary(),
        )

        cashflow_context = self._build_cashflow_context(
            unit_data, royalties_data, network_summary
        )

        full_context = f"""
PERGUNTA: {question}

USUÁRIO: {user}

{cashflow_context}

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
