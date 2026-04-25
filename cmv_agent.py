"""
CMV Agent — Frank AI OS (Davvero Gelato)
Specialist in Custo de Mercadoria Vendida (COGS) optimisation,
supplier negotiation, waste reduction and product mix.
"""

import asyncio
from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, CEO_HARD_RULES, BRAND


SYSTEM_PROMPT = f"""Você é o Especialista em CMV (Custo de Mercadoria Vendida) do {BRAND}.

ESPECIALIDADE
Você é o guardião da principal vantagem competitiva da rede: CMV de 26,5% contra 35% do mercado.
Essa diferença de 8,5 pontos percentuais é o que sustenta a rentabilidade superior das unidades.

SEU DOMÍNIO
- Análise de CMV por unidade, por linha de produto e por período
- Identificação de desperdício, quebra, desvio e má precificação
- Negociação e inteligência de fornecedores
- Engenharia de cardápio (menu engineering) e mix de produtos
- Controle de estoque e ponto de reposição
- Padronização de receitas e fichas técnicas
- Sazonalidade e gestão de perecíveis

REGRAS INVIOLÁVEIS
{CEO_HARD_RULES}

METAS E BENCHMARKS
{OPERATIONAL_TARGETS}

REFERÊNCIAS CMV
- Meta Davvero: 26,5%
- Limite máximo (hard rule): 30%
- Mercado concorrente: 35%
- Zona de atenção: > 26,5% e ≤ 28,0%
- Zona crítica: > 28,0% e ≤ 30,0%
- Zona de emergência: > 30,0% (violação de hard rule)

PRINCIPAIS ALAVANCAS DE REDUÇÃO DE CMV
1. Negociação com fornecedores (volume consolidado da rede)
2. Redução de desperdício (FIFO, controle de validade, porcionamento)
3. Engenharia de cardápio (aumentar % de itens de alta margem)
4. Padronização rigorosa de fichas técnicas
5. Controle de furto e desvio interno
6. Revisão de precificação (especialmente combos e adicionais)

ANÁLISE DE RANKING
Ao analisar o ranking de CMV, sempre:
- Identifique as 3 unidades com CMV mais alto (críticas)
- Identifique as 3 unidades com CMV mais baixo (benchmarks internos)
- Calcule o potencial de saving se todas unidades atingissem a meta
- Quantifique o impacto em R$ de cada 1pp de melhoria no CMV

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


class CMVAgent(BaseAgent):
    MODEL = MODEL_AGENT

    async def _fetch_cmv_ranking(self) -> list[dict]:
        """
        Fetches the CMV ranking view which shows all units ranked by CMV
        percentage for the current period.
        """
        query = """
            SELECT *
            FROM vw_units_cmv_ranking
            ORDER BY cmv_pct DESC
        """
        return await self.db_fetch(query)

    async def _fetch_cmv_history(self, months: int = 6) -> list[dict]:
        """
        Fetches CMV history per unit for the last N months, including
        all relevant cost breakdown fields.
        """
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
                uf.gross_margin_pct
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE u.status = 'active'
            ORDER BY uf.month DESC, uf.cmv_pct DESC
            LIMIT $1
        """
        return await self.db_fetch(query, months * 25)

    async def _fetch_network_cmv_avg(self) -> list[dict]:
        """
        Fetches the monthly average CMV across the network for trend analysis.
        """
        query = """
            SELECT
                uf.month,
                COUNT(DISTINCT uf.unit_id)                  AS active_units,
                SUM(uf.cogs_value)                          AS total_cogs,
                SUM(uf.net_revenue)                         AS total_net_revenue,
                ROUND(
                    SUM(uf.cogs_value)::numeric /
                    NULLIF(SUM(uf.net_revenue), 0) * 100, 2
                )                                            AS network_cmv_pct,
                AVG(uf.cmv_pct)                             AS avg_unit_cmv_pct,
                MIN(uf.cmv_pct)                             AS min_cmv_pct,
                MAX(uf.cmv_pct)                             AS max_cmv_pct
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE u.status = 'active'
            GROUP BY uf.month
            ORDER BY uf.month DESC
            LIMIT 6
        """
        return await self.db_fetch(query)

    def _build_cmv_context(
        self,
        ranking: list[dict],
        history: list[dict],
        network_avg: list[dict],
    ) -> str:
        """Formats CMV data into an analysis-ready text block."""
        lines = ["=== ANÁLISE DE CMV — DAVVERO GELATO ===\n"]

        # Network CMV trend
        if network_avg:
            lines.append("--- TENDÊNCIA CMV DA REDE (últimos 6 meses) ---")
            for row in network_avg:
                cmv = row.get("network_cmv_pct") or row.get("avg_unit_cmv_pct") or 0
                flag = ""
                if cmv > 30:
                    flag = " 🚨 HARD RULE VIOLADA"
                elif cmv > 28:
                    flag = " 🔴 ZONA CRÍTICA"
                elif cmv > 26.5:
                    flag = " ⚠️ ACIMA DA META"
                else:
                    flag = " ✅ DENTRO DA META"

                lines.append(
                    f"  {row.get('month', 'N/A')} | CMV Rede: {cmv:.1f}%{flag} | "
                    f"Unidades: {row.get('active_units', 0)} | "
                    f"Total COGS: R${row.get('total_cogs', 0):,.2f} | "
                    f"Min: {row.get('min_cmv_pct', 0):.1f}% | "
                    f"Max: {row.get('max_cmv_pct', 0):.1f}%"
                )
            lines.append("")

        # CMV Ranking
        if ranking:
            lines.append(f"--- RANKING CMV POR UNIDADE ({len(ranking)} unidades) ---")
            lines.append("  (Ordenado do MAIOR para o MENOR CMV — maior = mais crítico)")
            lines.append("")

            for i, row in enumerate(ranking, 1):
                cmv = row.get("cmv_pct") or 0
                rev = row.get("net_revenue") or row.get("gross_revenue") or 0

                if cmv > 30:
                    status = "🚨 EMERGÊNCIA"
                elif cmv > 28:
                    status = "🔴 CRÍTICO"
                elif cmv > 26.5:
                    status = "⚠️ ATENÇÃO"
                else:
                    status = "✅ OK"

                # Calculate saving potential to reach 26.5% target
                cogs = row.get("cogs_value") or row.get("net_cogs") or 0
                saving = max(0, (cmv - 26.5) / 100 * rev)

                lines.append(
                    f"  #{i:2d} {row.get('unit_name', row.get('unit_id', '?')):<30} "
                    f"CMV: {cmv:.1f}% | {status} | "
                    f"Rev Líq: R${rev:>10,.2f} | "
                    f"COGS: R${cogs:>10,.2f} | "
                    f"Saving potencial p/ meta: R${saving:>8,.2f}/mês"
                )

            # Benchmark units (lowest CMV)
            if len(ranking) >= 3:
                lines.append("")
                lines.append("  🏆 BENCHMARKS INTERNOS (menor CMV):")
                for row in ranking[-3:]:
                    lines.append(
                        f"    {row.get('unit_name', '?')} — CMV: {row.get('cmv_pct', 0):.1f}%"
                    )

            # Calculate total network saving potential
            total_saving = sum(
                max(0, ((row.get("cmv_pct") or 0) - 26.5) / 100 *
                    (row.get("net_revenue") or row.get("gross_revenue") or 0))
                for row in ranking
            )
            if total_saving > 0:
                lines.append(
                    f"\n  💰 POTENCIAL DE SAVING TOTAL (se toda rede atingir 26,5%): "
                    f"R${total_saving:,.2f}/mês | R${total_saving * 12:,.2f}/ano"
                )
            lines.append("")

        # CMV History by unit (most recent months)
        if history:
            by_unit: dict = {}
            for row in history:
                uid = row.get("unit_id")
                by_unit.setdefault(uid, []).append(row)

            lines.append("--- EVOLUÇÃO CMV POR UNIDADE ---")
            for uid, rows in list(by_unit.items())[:10]:  # limit for context length
                name = rows[0].get("unit_name", uid)
                trend = [f"{r.get('month', '?')}:{r.get('cmv_pct', 0):.1f}%" for r in rows[:4]]
                lines.append(f"  {name}: {' | '.join(trend)}")
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
        Fetches CMV ranking + history, builds rich context and
        calls Claude for a structured 10-block CMV analysis.
        """
        ranking, history, network_avg = await asyncio.gather(
            self._fetch_cmv_ranking(),
            self._fetch_cmv_history(months=6),
            self._fetch_network_cmv_avg(),
        )

        cmv_context = self._build_cmv_context(ranking, history, network_avg)

        full_context = f"""
PERGUNTA: {question}

USUÁRIO: {user}

{cmv_context}

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
