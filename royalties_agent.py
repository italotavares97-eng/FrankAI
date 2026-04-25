"""
Royalties Agent — Frank AI OS (Davvero Gelato)
Specialist in franchise fee management: royalties (8.5%) and marketing fund (1.5%),
delinquency tracking, collection strategy and fee compliance.
"""

import asyncio
from datetime import date
from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, CEO_HARD_RULES, BRAND


SYSTEM_PROMPT = f"""Você é o Especialista em Royalties e Taxas de Franquia do {BRAND}.

ESPECIALIDADE
Gestão, monitoramento e cobrança das receitas de royalties e fundo de marketing.
Você protege a receita da franqueadora e garante a conformidade dos franqueados.

ESTRUTURA DE TAXAS — DAVVERO GELATO
- Royalties: 8,5% da receita bruta mensal
- Fundo de Marketing: 1,5% da receita bruta mensal
- TOTAL de taxas: 10,0% da receita bruta mensal
- Prazo de pagamento: até o 10º dia útil do mês subsequente
- Base de cálculo: receita bruta declarada (com auditoria cruzada via sistema PDV)

REGRAS DE ADIMPLÊNCIA
✅ Adimplente: pagamento até o vencimento
⚠️ Em atraso leve: 1 a 30 dias de atraso
🔴 Em atraso crítico: 31 a 60 dias de atraso
🚨 Inadimplente: > 60 dias de atraso (acionamento jurídico obrigatório)

IMPACTO DA INADIMPLÊNCIA NA FRANQUEADORA
- Perda direta de receita recorrente
- Impacto no fundo de marketing (reduz investimento para toda a rede)
- Sinalização de dificuldade financeira da unidade (warning sign)
- Risco de rescisão contratual e fechamento da unidade

ESTRATÉGIAS DE COBRANÇA
1. Preventivo: alerta 5 dias antes do vencimento (automático)
2. Leve: contato imediato no dia seguinte ao vencimento
3. Moderado: negociação de parcelamento (máx 3x, com juros)
4. Grave: notificação formal + visita presencial do consultor de campo
5. Crítico: notificação extrajudicial + suspensão de suporte
6. Máximo: rescisão contratual por inadimplência

ANÁLISE DE ROYALTIES
- Valide se o royalty pago é coerente com a receita declarada
- Detecte sub-declaração de faturamento (royalty% < 8,5% pode indicar fraude)
- Monitore tendência: queda de royalties = queda de faturamento ou sub-declaração
- Compare por formato de unidade (quiosque vs loja vs drive-thru)

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

# Royalty and marketing fund rates
ROYALTY_RATE = 0.085
MKT_FUND_RATE = 0.015
TOTAL_FEES_RATE = ROYALTY_RATE + MKT_FUND_RATE


class RoyaltiesAgent(BaseAgent):
    MODEL = MODEL_AGENT

    async def _fetch_royalties_by_unit(self, months: int = 6) -> list[dict]:
        """
        Fetches royalty payments per unit for the last N months,
        cross-referencing against expected amounts based on gross revenue.
        """
        query = """
            SELECT
                uf.unit_id,
                u.name                      AS unit_name,
                u.city,
                u.format,
                f.name                      AS franchisee_name,
                f.royalty_pct               AS contracted_royalty_pct,
                uf.month,
                uf.gross_revenue,
                uf.net_revenue,
                uf.royalties                AS royalties_paid,
                -- Expected based on standard rate
                ROUND(uf.gross_revenue * 0.085, 2)   AS royalties_expected_std,
                -- Expected based on contracted rate (if different)
                ROUND(uf.gross_revenue * COALESCE(f.royalty_pct / 100.0, 0.085), 2)
                                            AS royalties_expected_contracted,
                -- Marketing fund expected
                ROUND(uf.gross_revenue * 0.015, 2)   AS mkt_fund_expected,
                -- Total fees expected
                ROUND(uf.gross_revenue * 0.10, 2)    AS total_fees_expected,
                -- Effective royalty rate paid
                CASE
                    WHEN uf.gross_revenue > 0
                    THEN ROUND(uf.royalties / uf.gross_revenue * 100, 2)
                    ELSE 0
                END                         AS effective_royalty_pct,
                -- Payment gap (positive = underpaid)
                ROUND(
                    (uf.gross_revenue * 0.085) - uf.royalties, 2
                )                           AS royalty_gap,
                -- Status classification
                CASE
                    WHEN uf.royalties >= (uf.gross_revenue * 0.085 * 0.98)
                    THEN 'OK'
                    WHEN uf.royalties >= (uf.gross_revenue * 0.085 * 0.90)
                    THEN 'DIVERGENCIA_LEVE'
                    WHEN uf.royalties >= (uf.gross_revenue * 0.085 * 0.75)
                    THEN 'DIVERGENCIA_CRITICA'
                    ELSE 'INADIMPLENTE'
                END                         AS payment_status
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            JOIN franchisees f ON f.id = u.franchisee_id
            WHERE u.status = 'active'
            ORDER BY uf.month DESC, uf.royalties ASC
            LIMIT $1
        """
        return await self.db_fetch(query, months * 25)

    async def _fetch_royalties_summary(self) -> list[dict]:
        """
        Monthly network-level royalty collection summary.
        """
        query = """
            SELECT
                uf.month,
                COUNT(DISTINCT uf.unit_id)          AS paying_units,
                SUM(uf.gross_revenue)                AS total_gross_revenue,
                SUM(uf.royalties)                    AS total_royalties_collected,
                ROUND(SUM(uf.gross_revenue) * 0.085, 2)
                                                     AS total_royalties_expected,
                ROUND(SUM(uf.gross_revenue) * 0.015, 2)
                                                     AS total_mkt_fund_expected,
                ROUND(SUM(uf.gross_revenue) * 0.10, 2)
                                                     AS total_fees_expected,
                -- Collection rate
                CASE
                    WHEN SUM(uf.gross_revenue) * 0.085 > 0
                    THEN ROUND(
                        SUM(uf.royalties) /
                        (SUM(uf.gross_revenue) * 0.085) * 100, 1
                    )
                    ELSE 0
                END                                  AS collection_rate_pct,
                -- Total gap
                ROUND(
                    SUM(uf.gross_revenue) * 0.085 - SUM(uf.royalties), 2
                )                                    AS total_royalty_gap
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE u.status = 'active'
            GROUP BY uf.month
            ORDER BY uf.month DESC
            LIMIT 6
        """
        return await self.db_fetch(query)

    async def _fetch_franchisees(self) -> list[dict]:
        """Fetches franchisee data for contextual cross-reference."""
        query = """
            SELECT f.id, f.name, f.royalty_pct,
                   COUNT(u.id) AS unit_count
            FROM franchisees f
            LEFT JOIN units u ON u.franchisee_id = f.id AND u.status = 'active'
            GROUP BY f.id, f.name, f.royalty_pct
            ORDER BY unit_count DESC
        """
        return await self.db_fetch(query)

    def _build_royalties_context(
        self,
        unit_royalties: list[dict],
        summary: list[dict],
        franchisees: list[dict],
    ) -> str:
        """Formats royalties data into a structured analysis context."""
        lines = ["=== ANÁLISE DE ROYALTIES E FUNDO DE MARKETING ===\n"]
        lines.append(f"  Taxa de Royalties Padrão: {ROYALTY_RATE*100:.1f}% da receita bruta")
        lines.append(f"  Fundo de Marketing: {MKT_FUND_RATE*100:.1f}% da receita bruta")
        lines.append(f"  Total de Taxas: {TOTAL_FEES_RATE*100:.1f}% da receita bruta\n")

        # Network collection summary
        if summary:
            lines.append("--- ARRECADAÇÃO DE ROYALTIES — REDE (últimos 6 meses) ---")
            total_gap_6m = 0
            for row in summary:
                collection_rate = row.get("collection_rate_pct") or 0
                gap = row.get("total_royalty_gap") or 0
                total_gap_6m += gap

                if collection_rate >= 98:
                    rate_flag = " ✅"
                elif collection_rate >= 90:
                    rate_flag = " ⚠️ ATENÇÃO"
                else:
                    rate_flag = " 🚨 CRÍTICO"

                lines.append(
                    f"  {row.get('month', 'N/A')} | "
                    f"Arrecadado: R${row.get('total_royalties_collected', 0):,.2f} | "
                    f"Esperado: R${row.get('total_royalties_expected', 0):,.2f} | "
                    f"Gap: R${gap:,.2f} | "
                    f"Taxa Coleta: {collection_rate:.1f}%{rate_flag} | "
                    f"Unidades: {row.get('paying_units', 0)}"
                )

            if total_gap_6m > 0:
                lines.append(
                    f"\n  💰 GAP TOTAL 6 MESES: R${total_gap_6m:,.2f} em royalties não coletados"
                )
            lines.append("")

        # Per-unit royalty analysis
        if unit_royalties:
            # Group by unit, take latest month
            by_unit: dict = {}
            for row in unit_royalties:
                uid = row.get("unit_id")
                by_unit.setdefault(uid, []).append(row)

            # Separate by status
            inadimplentes = []
            criticos = []
            atencao = []
            ok = []

            for uid, rows in by_unit.items():
                latest = rows[0]
                status = latest.get("payment_status", "OK")
                if status == "INADIMPLENTE":
                    inadimplentes.append(latest)
                elif status == "DIVERGENCIA_CRITICA":
                    criticos.append(latest)
                elif status == "DIVERGENCIA_LEVE":
                    atencao.append(latest)
                else:
                    ok.append(latest)

            # Critical section: defaulters
            if inadimplentes:
                lines.append(f"🚨 INADIMPLENTES ({len(inadimplentes)} unidades) — AÇÃO IMEDIATA")
                total_inadimplencia = sum(r.get("royalty_gap") or 0 for r in inadimplentes)
                for row in inadimplentes:
                    eff_rate = row.get("effective_royalty_pct") or 0
                    lines.append(
                        f"  ❌ {row.get('unit_name', '?'):<30} | "
                        f"{row.get('month', 'N/A')} | "
                        f"Pago: R${row.get('royalties_paid', 0):,.2f} | "
                        f"Esperado: R${row.get('royalties_expected_std', 0):,.2f} | "
                        f"Gap: R${row.get('royalty_gap', 0):,.2f} | "
                        f"Taxa efetiva: {eff_rate:.1f}% (meta: 8,5%)"
                    )
                lines.append(
                    f"  → Total em inadimplência: R${total_inadimplencia:,.2f}"
                )
                lines.append("")

            # Critical divergence
            if criticos:
                lines.append(f"🔴 DIVERGÊNCIA CRÍTICA ({len(criticos)} unidades)")
                for row in criticos:
                    eff_rate = row.get("effective_royalty_pct") or 0
                    lines.append(
                        f"  ⚠️ {row.get('unit_name', '?'):<30} | "
                        f"{row.get('month', 'N/A')} | "
                        f"Pago: R${row.get('royalties_paid', 0):,.2f} | "
                        f"Esperado: R${row.get('royalties_expected_std', 0):,.2f} | "
                        f"Gap: R${row.get('royalty_gap', 0):,.2f} | "
                        f"Taxa efetiva: {eff_rate:.1f}%"
                    )
                lines.append("")

            # Attention
            if atencao:
                lines.append(f"⚠️ DIVERGÊNCIA LEVE ({len(atencao)} unidades)")
                for row in atencao:
                    lines.append(
                        f"  {row.get('unit_name', '?'):<30} | "
                        f"Gap: R${row.get('royalty_gap', 0):,.2f} | "
                        f"Taxa efetiva: {row.get('effective_royalty_pct', 0):.1f}%"
                    )
                lines.append("")

            lines.append(
                f"✅ Unidades adimplentes: {len(ok)} | "
                f"⚠️ Atenção: {len(atencao)} | "
                f"🔴 Crítico: {len(criticos)} | "
                f"🚨 Inadimplentes: {len(inadimplentes)}"
            )
            lines.append("")

            # Sub-declaration detection (royalty rate significantly below 8.5%)
            sub_decl = [
                r for r in [by_unit[uid][0] for uid in by_unit]
                if (r.get("effective_royalty_pct") or 0) < 7.5
                and (r.get("royalties_paid") or 0) > 0
            ]
            if sub_decl:
                lines.append(
                    f"🔍 ALERTA: {len(sub_decl)} unidade(s) com taxa efetiva < 7,5% — "
                    f"possível sub-declaração de faturamento:"
                )
                for row in sub_decl:
                    lines.append(
                        f"  {row.get('unit_name', '?')} — "
                        f"Taxa efetiva: {row.get('effective_royalty_pct', 0):.1f}%"
                    )
                lines.append("")

        # Franchisees overview
        if franchisees:
            lines.append(f"--- FRANQUEADOS ({len(franchisees)}) ---")
            for f in franchisees:
                lines.append(
                    f"  {f.get('name', '?'):<35} | "
                    f"Royalty contratual: {f.get('royalty_pct', 8.5):.1f}% | "
                    f"Unidades ativas: {f.get('unit_count', 0)}"
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
        Fetches royalty payment data, identifies defaulters and anomalies,
        then calls Claude for a structured 10-block royalties analysis.
        """
        unit_royalties, summary, franchisees = await asyncio.gather(
            self._fetch_royalties_by_unit(months=6),
            self._fetch_royalties_summary(),
            self._fetch_franchisees(),
        )

        royalties_context = self._build_royalties_context(
            unit_royalties, summary, franchisees
        )

        full_context = f"""
PERGUNTA: {question}

USUÁRIO: {user}

DATA DE REFERÊNCIA: {date.today().strftime('%d/%m/%Y')}

{royalties_context}

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
