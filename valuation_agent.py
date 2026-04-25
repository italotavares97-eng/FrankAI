"""
Valuation Agent — Frank AI OS (Davvero Gelato)
Specialist in franchise network valuation, EBITDA multiples,
investor ROI analysis, payback period and investment attractiveness.
"""

import asyncio
from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, CEO_HARD_RULES, BRAND


SYSTEM_PROMPT = f"""Você é o Especialista em Valuation e ROI do {BRAND}.

ESPECIALIDADE
Você calcula e interpreta o valor econômico da rede e de cada unidade individualmente,
analisando a atratividade do investimento em franquia e monitorando a entrega de retorno
prometida ao franqueado.

SEU DOMÍNIO
- Valuation da rede: múltiplos de EBITDA, DCF simplificado, comparáveis de mercado
- ROI do franqueado: retorno sobre o investimento inicial por unidade
- Payback period: tempo de recuperação do investimento
- EBITDA consolidado e por unidade
- Análise de investimento inicial vs retorno realizado
- Comparação com benchmarks de mercado para franquias food service
- Due diligence financeira para novas aberturas

PREMISSAS DE VALUATION — DAVVERO GELATO
- Múltiplo de EBITDA para food service premium: 5x a 8x
- Múltiplo alvo Davvero (crescimento + CMV diferenciado): 6x a 7x
- Taxa de desconto estimada: 18% a 22% ao ano (WACC Brasil food service)
- Perpetuidade: crescimento de 8% ao ano (inflação + expansão da rede)

MÉTRICAS DE INVESTIMENTO POR UNIDADE
- Investimento inicial: R$ (conforme tabela de franquia)
- Payback target: máximo 30 meses
- ROI mínimo em 24 meses: 1,5x (150% do investimento)
- EBITDA mínimo para boa performance: 10% da receita líquida

CÁLCULOS PADRÃO
Payback (meses) = Investimento Inicial / EBITDA Mensal
ROI 24m = (EBITDA Mensal × 24) / Investimento Inicial
Valuation Rede = EBITDA Anual × Múltiplo
EBITDA Anual = EBITDA Mensal Médio × 12

BENCHMARKS FOOD SERVICE BRASIL
- Múltiplo EBITDA fast-food/casual: 4x a 6x
- Múltiplo redes premium/diferenciadas: 6x a 9x
- Payback médio mercado: 24 a 36 meses
- ROI médio mercado: 1,2x a 1,8x em 24 meses

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


class ValuationAgent(BaseAgent):
    MODEL = MODEL_AGENT

    async def _fetch_network_ebitda(self) -> list[dict]:
        """
        Fetches the last 12 months of network EBITDA for valuation calculation.
        """
        query = """
            SELECT
                uf.month,
                COUNT(DISTINCT uf.unit_id)              AS active_units,
                SUM(uf.gross_revenue)                   AS total_gross_revenue,
                SUM(uf.net_revenue)                     AS total_net_revenue,
                SUM(uf.ebitda_operational)              AS total_ebitda,
                ROUND(
                    SUM(uf.ebitda_operational)::numeric /
                    NULLIF(SUM(uf.net_revenue), 0) * 100, 2
                )                                       AS ebitda_pct,
                SUM(uf.net_income)                      AS total_net_income,
                SUM(uf.royalties)                       AS total_royalties
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE u.status = 'active'
            GROUP BY uf.month
            ORDER BY uf.month DESC
            LIMIT 12
        """
        return await self.db_fetch(query)

    async def _fetch_unit_roi(self) -> list[dict]:
        """
        Fetches ROI data per unit, comparing cumulative EBITDA against
        the initial investment to calculate payback and ROI.
        """
        query = """
            SELECT
                u.id            AS unit_id,
                u.name          AS unit_name,
                u.city,
                u.format,
                u.opening_date,
                u.initial_investment,
                -- Average monthly EBITDA (last 6 months)
                AVG(uf.ebitda_operational)      AS avg_monthly_ebitda,
                AVG(uf.ebitda_pct)              AS avg_ebitda_pct,
                AVG(uf.gross_revenue)           AS avg_monthly_revenue,
                -- Payback in months: investment / avg monthly EBITDA
                CASE
                    WHEN AVG(uf.ebitda_operational) > 0
                    THEN ROUND(u.initial_investment / AVG(uf.ebitda_operational), 1)
                    ELSE NULL
                END                             AS payback_months,
                -- ROI in 24 months: (avg_ebitda × 24) / investment
                CASE
                    WHEN u.initial_investment > 0
                    THEN ROUND(
                        (AVG(uf.ebitda_operational) * 24) /
                        u.initial_investment, 2
                    )
                    ELSE NULL
                END                             AS roi_24m,
                -- Months since opening
                EXTRACT(
                    MONTH FROM AGE(CURRENT_DATE, u.opening_date)
                ) + EXTRACT(
                    YEAR FROM AGE(CURRENT_DATE, u.opening_date)
                ) * 12                          AS months_open,
                -- Cumulative EBITDA since opening (approximated by avg × months open)
                AVG(uf.ebitda_operational) *
                (EXTRACT(MONTH FROM AGE(CURRENT_DATE, u.opening_date)) +
                 EXTRACT(YEAR FROM AGE(CURRENT_DATE, u.opening_date)) * 12
                )                               AS cumulative_ebitda_approx
            FROM units u
            LEFT JOIN unit_financials uf ON uf.unit_id = u.id
            WHERE u.status = 'active'
              AND u.initial_investment > 0
            GROUP BY u.id, u.name, u.city, u.format, u.opening_date, u.initial_investment
            ORDER BY payback_months ASC NULLS LAST
        """
        return await self.db_fetch(query)

    async def _fetch_units_metadata(self) -> list[dict]:
        """Fetches unit metadata for context."""
        query = """
            SELECT id, code, name, city, format, status,
                   opening_date, initial_investment, monthly_rent
            FROM units
            WHERE status = 'active'
            ORDER BY opening_date
        """
        return await self.db_fetch(query)

    def _calculate_valuation(self, network_ebitda: list[dict]) -> dict:
        """
        Calculates the network valuation using EBITDA multiples.
        Returns a dict with valuation range and supporting metrics.
        """
        if not network_ebitda:
            return {}

        # Use trailing 12-month EBITDA
        ttm_ebitda = sum(r.get("total_ebitda") or 0 for r in network_ebitda[:12])
        avg_monthly = ttm_ebitda / min(len(network_ebitda), 12) if network_ebitda else 0
        annualized_ebitda = avg_monthly * 12

        # EBITDA multiples range
        multiple_low = 5.0
        multiple_mid = 6.5
        multiple_high = 8.0

        val_low = annualized_ebitda * multiple_low
        val_mid = annualized_ebitda * multiple_mid
        val_high = annualized_ebitda * multiple_high

        # Total network revenue
        total_revenue = sum(r.get("total_gross_revenue") or 0 for r in network_ebitda[:12])
        avg_ebitda_pct = (
            sum(r.get("ebitda_pct") or 0 for r in network_ebitda[:12]) /
            min(len(network_ebitda), 12)
            if network_ebitda else 0
        )

        return {
            "ttm_ebitda": ttm_ebitda,
            "annualized_ebitda": annualized_ebitda,
            "avg_monthly_ebitda": avg_monthly,
            "avg_ebitda_pct": avg_ebitda_pct,
            "total_ttm_revenue": total_revenue,
            "valuation_low": val_low,
            "valuation_mid": val_mid,
            "valuation_high": val_high,
            "multiple_low": multiple_low,
            "multiple_mid": multiple_mid,
            "multiple_high": multiple_high,
        }

    def _build_valuation_context(
        self,
        network_ebitda: list[dict],
        unit_roi: list[dict],
        units_meta: list[dict],
    ) -> str:
        """Formats valuation data into a structured analysis context."""
        lines = ["=== ANÁLISE DE VALUATION E ROI — DAVVERO GELATO ===\n"]

        # Network valuation
        valuation = self._calculate_valuation(network_ebitda)
        if valuation:
            lines.append("--- VALUATION DA REDE ---")
            lines.append(
                f"  EBITDA Acumulado 12M (TTM): R${valuation['ttm_ebitda']:,.2f}"
            )
            lines.append(
                f"  EBITDA Anualizado (run rate): R${valuation['annualized_ebitda']:,.2f}"
            )
            lines.append(
                f"  EBITDA% Médio: {valuation['avg_ebitda_pct']:.1f}%"
            )
            lines.append(
                f"  Receita Bruta 12M: R${valuation['total_ttm_revenue']:,.2f}"
            )
            lines.append("")
            lines.append("  FAIXA DE VALUATION (múltiplos EBITDA):")
            lines.append(
                f"    Conservador ({valuation['multiple_low']}x): "
                f"R${valuation['valuation_low']:,.2f}"
            )
            lines.append(
                f"    Base ({valuation['multiple_mid']}x): "
                f"R${valuation['valuation_mid']:,.2f}"
            )
            lines.append(
                f"    Otimista ({valuation['multiple_high']}x): "
                f"R${valuation['valuation_high']:,.2f}"
            )
            lines.append("")

        # Monthly EBITDA trend
        if network_ebitda:
            lines.append("--- EVOLUÇÃO EBITDA REDE (12 meses) ---")
            for row in network_ebitda[:12]:
                ebitda_flag = ""
                ebitda_pct = row.get("ebitda_pct") or 0
                if ebitda_pct < 10:
                    ebitda_flag = " ⚠️ ABAIXO META"
                lines.append(
                    f"  {row.get('month', 'N/A')} | "
                    f"EBITDA: R${row.get('total_ebitda', 0):,.2f} ({ebitda_pct:.1f}%){ebitda_flag} | "
                    f"Receita: R${row.get('total_gross_revenue', 0):,.2f} | "
                    f"Unidades: {row.get('active_units', 0)}"
                )
            lines.append("")

        # Per-unit ROI analysis
        if unit_roi:
            lines.append(f"--- ROI E PAYBACK POR UNIDADE ({len(unit_roi)} unidades) ---")
            lines.append("")

            alerts = []
            for row in unit_roi:
                payback = row.get("payback_months")
                roi_24m = row.get("roi_24m")
                investment = row.get("initial_investment") or 0
                avg_ebitda = row.get("avg_monthly_ebitda") or 0
                months_open = int(row.get("months_open") or 0)

                # Determine status
                payback_status = ""
                if payback is None or payback == 0:
                    payback_status = "🚨 EBITDA NEGATIVO"
                elif payback > 30:
                    payback_status = "🔴 ACIMA DO LIMITE (30m)"
                    alerts.append(row.get("unit_name", "?"))
                elif payback > 24:
                    payback_status = "⚠️ ATENÇÃO"
                else:
                    payback_status = "✅ DENTRO DO TARGET"

                roi_status = ""
                if roi_24m is not None:
                    if roi_24m < 1.0:
                        roi_status = " | ROI 24m: 🔴 < 1,0x"
                    elif roi_24m < 1.5:
                        roi_status = f" | ROI 24m: ⚠️ {roi_24m:.2f}x"
                    else:
                        roi_status = f" | ROI 24m: ✅ {roi_24m:.2f}x"

                payback_str = f"{payback:.1f}m" if payback else "N/A"
                lines.append(
                    f"  {row.get('unit_name', '?'):<30} | "
                    f"Investimento: R${investment:>12,.2f} | "
                    f"EBITDA Médio: R${avg_ebitda:>10,.2f}/mês | "
                    f"Payback: {payback_str:>6} {payback_status}{roi_status} | "
                    f"Aberta há: {months_open}m"
                )

            if alerts:
                lines.append(
                    f"\n  🚨 HARD RULE VIOLADA: {len(alerts)} unidade(s) com "
                    f"payback > 30 meses: {', '.join(alerts)}"
                )
            lines.append("")

        # Units metadata for reference
        if units_meta:
            lines.append(f"--- PORTFÓLIO: {len(units_meta)} UNIDADES ATIVAS ---")
            total_investment = sum(u.get("initial_investment") or 0 for u in units_meta)
            lines.append(f"  Investimento total da rede: R${total_investment:,.2f}")
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
        Fetches network financials, calculates valuation metrics and ROI,
        then calls Claude for a structured 10-block valuation analysis.
        """
        network_ebitda, unit_roi, units_meta = await asyncio.gather(
            self._fetch_network_ebitda(),
            self._fetch_unit_roi(),
            self._fetch_units_metadata(),
        )

        valuation_context = self._build_valuation_context(
            network_ebitda, unit_roi, units_meta
        )

        full_context = f"""
PERGUNTA: {question}

USUÁRIO: {user}

{valuation_context}

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
