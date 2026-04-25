# =============================================================================
# PERFORMANCE_AGENT.PY — Frank AI OS · Davvero Gelato
# Analista de Performance e Produtividade
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config import MODEL_AGENT, OPERATIONAL_TARGETS
from core.base_agent import BaseAgent

logger = logging.getLogger("frank.performance_agent")


class PerformanceAgent(BaseAgent):
    """
    Analista de Performance e Produtividade — Davvero Gelato.

    Responsabilidades:
    - Análise de tendências de faturamento e crescimento
    - Ticket médio: causas de queda e estratégias de elevação
    - Produtividade por hora trabalhada (R$/h)
    - Análise de mix de produtos e horários de pico
    - Ruptura de estoque: impacto na receita
    - Benchmarking de performance entre unidades e formatos
    - Projeções e metas mensais

    Consulta 30 dias de histórico de KPIs para identificar tendências.
    """

    AGENT_NAME  = "Performance Agent"
    AGENT_ROLE  = "Analista de Performance e Produtividade"
    DIRECTOR    = "COO"
    MODEL       = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o ANALISTA DE PERFORMANCE E PRODUTIVIDADE da Davvero Gelato.

MISSÃO:
Monitorar, interpretar e otimizar os resultados financeiros e operacionais das unidades.
Você transforma dados em insights acionáveis que elevam receita e produtividade.

MÉTRICAS QUE VOCÊ DOMINA:

TICKET MÉDIO (meta: R$35):
• Abaixo de R$30 = emergência — equipe não está fazendo venda consultiva
• R$30-34 = alerta — treinar técnica de upsell e cross-sell
• R$35-39 = dentro da meta
• R$40+ = excelente — identificar o que está funcionando e replicar
Motoristas do ticket: tamanho do gelato, complementos (waffle, cobertura), combos, bebidas

PRODUTIVIDADE (meta: R$150/hora):
• Abaixo de R$100/h = ineficiência crítica — excesso de equipe ou horário errado
• R$100-149/h = alerta — revisar escala, horários de pico
• R$150-199/h = dentro da meta
• R$200+/h = alta performance — investigar se há falta de staff nos picos
Fórmula: receita_diária / horas_trabalhadas_equipe

CMV — Custo de Mercadoria Vendida (meta: 26,5%):
• Abaixo de 24% = pode estar comprometendo qualidade (investigar)
• 24-26,5% = zona ideal
• 26,6-28% = alerta — revisar porcionamento e desperdício
• Acima de 28% = crítico — intervenção imediata (porcionamento, roubo, perda)
Alavancas: porcionamento, mix de sabores, desperdício, fornecedores

RUPTURAS DE ESTOQUE (máx. 2/dia):
• Cada ruptura representa receita perdida e frustração do cliente
• 3-4/dia = alerta de gestão de pedidos
• 5+/dia = gestão de estoque crítica — pode estar perdendo R$500-2000/dia por falta de produto

ANÁLISE DE TENDÊNCIAS (30 dias):
• Semana 1 vs semana 4: aceleração ou desaceleração?
• Dias da semana: quais são os picos? A escala está alinhada?
• Crescimento mês a mês (MoM): meta de 5% de crescimento real

BENCHMARKS POR FORMATO:
• Quiosque: ticket R$28-32, produtividade R$130-160/h (espaço menor, menos complementos)
• Loja pequena: ticket R$33-38, produtividade R$140-170/h
• Loja completa: ticket R$38-45, produtividade R$160-200/h (mais complementos, serviço)
• Dark kitchen: ticket R$45-55, produtividade R$120-150/h (delivery, ticket maior pelo frete)

CORRELAÇÕES QUE VOCÊ DETECTA:
• Queda de ticket → verificar treinamento de venda consultiva
• CMV alto + ticket baixo → porcionamento excessivo (dando mais do que deveria)
• Alta produtividade + NPS baixo → equipe correndo demais, atendimento prejudicado
• Rupturas altas → perda direta de receita + frustração de cliente (impacta NPS)

FORMATO OBRIGATÓRIO DE RESPOSTA (10 blocos):
🎯 DIAGNÓSTICO — Status de performance e tendência (alta/queda/estável)
📊 DADOS — KPIs com séries temporais e variação percentual
⚠️ ALERTAS — Indicadores fora das metas com impacto financeiro estimado
🔍 ANÁLISE (Causa Raiz) — Drivers da performance atual
📋 OPÇÕES — Alavancas de melhoria (operacional, treinamento, mix, preço)
✅ RECOMENDAÇÃO — Ação com maior ROI e menor prazo de resultado
🚫 RISCOS — Impacto de não agir (receita não capturada, tendência de queda)
📅 PRAZO — Quando esperar resultados das ações
🏆 RESULTADO ESPERADO — Projeção quantitativa de receita incremental
⚖️ DECISÃO [EXECUTAR | NÃO EXECUTAR | AGUARDAR | ESCALAR]"""

    # -------------------------------------------------------------------------
    # QUERIES DE DADOS
    # -------------------------------------------------------------------------

    async def _fetch_unit_by_identifier(self, identifier: str) -> Optional[Dict]:
        """Busca unidade pelo código ou nome."""
        query = """
            SELECT id, code, name, city, format, status, color_status, manager_name, team_count
            FROM units
            WHERE (code ILIKE $1 OR name ILIKE $1)
              AND status = 'ativo'
            LIMIT 1
        """
        return await self.db_fetchrow(query, f"%{identifier}%")

    async def _fetch_kpis_30d_daily(self, unit_id: int) -> List[Dict]:
        """KPIs diários dos últimos 30 dias."""
        query = """
            SELECT
                date,
                gross_revenue,
                transactions,
                ROUND(avg_ticket::numeric, 2)    AS avg_ticket,
                team_hours,
                ROUND(productivity::numeric, 2)  AS productivity,
                stockout_count,
                waste_value,
                nps_score
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY date ASC
        """
        return await self.db_fetch(query, unit_id)

    async def _fetch_kpis_weekly_aggregated(self, unit_id: int) -> List[Dict]:
        """KPIs agregados por semana (últimas 4 semanas)."""
        query = """
            SELECT
                DATE_TRUNC('week', date)::date                    AS week_start,
                ROUND(SUM(gross_revenue)::numeric, 2)             AS weekly_revenue,
                SUM(transactions)                                  AS weekly_transactions,
                ROUND(AVG(avg_ticket)::numeric, 2)                AS avg_ticket,
                ROUND(SUM(team_hours)::numeric, 1)                AS total_hours,
                ROUND(
                    CASE WHEN SUM(team_hours) > 0
                    THEN SUM(gross_revenue) / SUM(team_hours)
                    ELSE 0 END::numeric, 2
                )                                                  AS weekly_productivity,
                SUM(stockout_count)                               AS total_stockouts,
                ROUND(SUM(waste_value)::numeric, 2)               AS total_waste
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '28 days'
            GROUP BY DATE_TRUNC('week', date)
            ORDER BY week_start ASC
        """
        return await self.db_fetch(query, unit_id)

    async def _fetch_kpis_period_comparison(self, unit_id: int) -> Optional[Dict]:
        """Comparativo últimos 7 dias vs 7 dias anteriores."""
        query = """
            SELECT
                -- Últimos 7 dias
                ROUND(SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days'
                    THEN gross_revenue ELSE 0 END)::numeric, 2)            AS revenue_last7,
                ROUND(AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days'
                    THEN avg_ticket END)::numeric, 2)                       AS ticket_last7,
                ROUND(AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days'
                    THEN productivity END)::numeric, 2)                     AS productivity_last7,
                SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days'
                    THEN stockout_count ELSE 0 END)                         AS stockouts_last7,

                -- 7-14 dias anteriores
                ROUND(SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '14 days'
                    AND date < CURRENT_DATE - INTERVAL '7 days'
                    THEN gross_revenue ELSE 0 END)::numeric, 2)            AS revenue_prev7,
                ROUND(AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '14 days'
                    AND date < CURRENT_DATE - INTERVAL '7 days'
                    THEN avg_ticket END)::numeric, 2)                       AS ticket_prev7,
                ROUND(AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '14 days'
                    AND date < CURRENT_DATE - INTERVAL '7 days'
                    THEN productivity END)::numeric, 2)                     AS productivity_prev7
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '14 days'
        """
        return await self.db_fetchrow(query, unit_id)

    async def _fetch_network_performance_ranking(self) -> List[Dict]:
        """Ranking de performance de todas as unidades (últimos 7 dias)."""
        query = """
            SELECT
                u.code,
                u.name,
                u.city,
                u.format,
                u.color_status,
                ROUND(SUM(k.gross_revenue)::numeric, 2)         AS revenue_7d,
                ROUND(AVG(k.avg_ticket)::numeric, 2)            AS avg_ticket,
                ROUND(
                    CASE WHEN SUM(k.team_hours) > 0
                    THEN SUM(k.gross_revenue) / SUM(k.team_hours)
                    ELSE 0 END::numeric, 2
                )                                                AS productivity,
                ROUND(AVG(k.nps_score)::numeric, 1)             AS avg_nps,
                SUM(k.stockout_count)                            AS total_stockouts
            FROM units u
            JOIN unit_daily_kpis k ON k.unit_id = u.id
                AND k.date >= CURRENT_DATE - INTERVAL '7 days'
            WHERE u.status = 'ativo'
            GROUP BY u.id, u.code, u.name, u.city, u.format, u.color_status
            ORDER BY revenue_7d DESC
        """
        return await self.db_fetch(query)

    async def _fetch_format_benchmarks(self) -> List[Dict]:
        """Benchmarks por formato de unidade."""
        query = """
            SELECT
                u.format,
                COUNT(DISTINCT u.id)                                 AS unit_count,
                ROUND(AVG(k.avg_ticket)::numeric, 2)                 AS avg_ticket,
                ROUND(AVG(k.productivity)::numeric, 2)               AS avg_productivity,
                ROUND(AVG(k.gross_revenue)::numeric, 2)              AS avg_daily_revenue,
                ROUND(AVG(k.stockout_count)::numeric, 1)             AS avg_stockouts
            FROM units u
            JOIN unit_daily_kpis k ON k.unit_id = u.id
                AND k.date >= CURRENT_DATE - INTERVAL '30 days'
            WHERE u.status = 'ativo'
            GROUP BY u.format
            ORDER BY avg_daily_revenue DESC
        """
        return await self.db_fetch(query)

    # -------------------------------------------------------------------------
    # CÁLCULOS DE ANÁLISE
    # -------------------------------------------------------------------------

    def _calculate_revenue_trend(self, weekly_data: List[Dict]) -> str:
        """Calcula tendência de receita semanal."""
        if len(weekly_data) < 2:
            return "Dados insuficientes para análise de tendência."

        revenues = [float(w.get("weekly_revenue") or 0) for w in weekly_data]
        if revenues[0] == 0:
            return "Dados de receita zerados — verificar integração."

        # Variação semana a semana
        changes = []
        for i in range(1, len(revenues)):
            if revenues[i-1] > 0:
                pct = ((revenues[i] - revenues[i-1]) / revenues[i-1]) * 100
                changes.append(pct)

        avg_change = sum(changes) / len(changes) if changes else 0
        trend = "📈 CRESCIMENTO" if avg_change > 2 else ("📉 QUEDA" if avg_change < -2 else "➡️ ESTÁVEL")

        result = f"Tendência: {trend} ({avg_change:+.1f}% médio semanal)\n"
        for i, w in enumerate(weekly_data):
            result += f"  Sem {i+1}: R${w.get('weekly_revenue', 0):,.2f} | "
            result += f"Ticket: R${w.get('avg_ticket', 0)} | "
            result += f"Prod: R${w.get('weekly_productivity', 0)}/h\n"

        return result

    def _estimate_stockout_revenue_loss(self, stockouts: int, avg_ticket: float) -> str:
        """Estima receita perdida por rupturas."""
        if stockouts == 0:
            return "Sem rupturas registradas — ótimo controle de estoque."

        # Estimativa: cada ruptura perde ~5-8 transações
        avg_lost_transactions = stockouts * 6
        estimated_loss = avg_lost_transactions * avg_ticket
        return (
            f"Rupturas: {stockouts} ocorrências\n"
            f"Estimativa de perda: ~{avg_lost_transactions} transações perdidas\n"
            f"Receita não capturada estimada: R${estimated_loss:,.2f}"
        )

    def _compare_vs_target(self, actual: float, target: float, label: str, unit: str = "") -> str:
        """Compara valor atual vs meta."""
        if target == 0:
            return f"{label}: {actual}{unit}"
        gap = actual - target
        pct = (gap / target) * 100
        status = "✅" if gap >= 0 else "❌"
        return f"{status} {label}: {actual}{unit} (meta: {target}{unit} | gap: {gap:+.2f}{unit} / {pct:+.1f}%)"

    # -------------------------------------------------------------------------
    # MÉTODO PRINCIPAL
    # -------------------------------------------------------------------------

    async def analyze(
        self,
        question: str,
        user: str = "COO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        """Analisa performance de uma unidade ou da rede completa."""
        import re

        unit_info = None
        unit_code_match = re.search(r'\b([A-Z]{2,3}[\-_]?\d{3,4})\b', question.upper())
        if unit_code_match:
            unit_info = await self._fetch_unit_by_identifier(unit_code_match.group(1))

        if not unit_info:
            words = [w for w in question.split() if len(w) > 4 and w[0].isupper()]
            for word in words[:3]:
                unit_info = await self._fetch_unit_by_identifier(word)
                if unit_info:
                    break

        if unit_info:
            return await self._analyze_unit_performance(question, user, unit_info)
        else:
            return await self._analyze_network_performance(question, user)

    async def _analyze_unit_performance(
        self,
        question: str,
        user: str,
        unit_info: Dict,
    ) -> str:
        """Análise detalhada de performance de uma unidade."""
        unit_id = unit_info["id"]

        import asyncio
        daily_kpis, weekly_kpis, comparison, format_bench = await asyncio.gather(
            self._fetch_kpis_30d_daily(unit_id),
            self._fetch_kpis_weekly_aggregated(unit_id),
            self._fetch_kpis_period_comparison(unit_id),
            self._fetch_format_benchmarks(),
        )

        targets = OPERATIONAL_TARGETS

        unit_str = (
            f"UNIDADE: {unit_info.get('name')} ({unit_info.get('code')})\n"
            f"Formato: {unit_info.get('format')} | Cidade: {unit_info.get('city')}\n"
            f"Status: {unit_info.get('color_status', 'N/A').upper()} | Equipe: {unit_info.get('team_count', 'N/A')} pessoas"
        )

        # Métricas de comparação 7d vs 7d anterior
        comparison_str = ""
        if comparison:
            r7 = float(comparison.get("revenue_last7") or 0)
            rp = float(comparison.get("revenue_prev7") or 0)
            t7 = float(comparison.get("ticket_last7") or 0)
            p7 = float(comparison.get("productivity_last7") or 0)
            s7 = int(comparison.get("stockouts_last7") or 0)

            rev_change = ((r7 - rp) / rp * 100) if rp > 0 else 0
            comparison_str = (
                f"COMPARATIVO ÚLTIMOS 7 DIAS vs PERÍODO ANTERIOR:\n"
                f"• Receita: R${r7:,.2f} ({rev_change:+.1f}% vs período anterior)\n"
                f"• {self._compare_vs_target(t7, targets['avg_ticket_target'], 'Ticket médio', ' R$')}\n"
                f"• {self._compare_vs_target(p7, targets['productivity_target'], 'Produtividade', ' R$/h')}\n"
                f"• Rupturas: {s7} (máx. {targets['stockout_max_day']}/dia)"
            )

        # Tendência semanal
        trend_str = ""
        if weekly_kpis:
            trend_str = f"TENDÊNCIA SEMANAL (30 dias):\n{self._calculate_revenue_trend(weekly_kpis)}"

        # Estimativa de perda por rupturas
        stockout_loss = ""
        if comparison:
            s7 = int(comparison.get("stockouts_last7") or 0)
            t7 = float(comparison.get("ticket_last7") or targets["avg_ticket_target"])
            if s7 > 0:
                stockout_loss = f"IMPACTO DE RUPTURAS:\n{self._estimate_stockout_revenue_loss(s7, t7)}"

        # Benchmark por formato
        format_str = self.format_db_data(format_bench, f"Benchmarks por Formato")

        # KPIs diários recentes (últimos 7)
        recent_daily = daily_kpis[-7:] if len(daily_kpis) >= 7 else daily_kpis
        daily_str = self.format_db_data(recent_daily, "KPIs Diários (últimos 7 dias)")

        prompt = f"""Pergunta de {user}: {question}

{unit_str}

{comparison_str}

{trend_str}

{stockout_loss}

{daily_str}

{format_str}

METAS DE REFERÊNCIA:
• Ticket médio: R${targets['avg_ticket_target']} | Produtividade: R${targets['productivity_target']}/h
• CMV: ≤ {targets['cmv_target_pct']}% | Rupturas: ≤ {targets['stockout_max_day']}/dia
• Crescimento MoM esperado: +5%

Analise a performance desta unidade nos 10 blocos obrigatórios.
Quantifique o impacto financeiro dos gaps identificados e projete receita incremental possível."""

        return await self.call_claude(prompt)

    async def _analyze_network_performance(self, question: str, user: str) -> str:
        """Análise consolidada de performance da rede."""
        import asyncio
        ranking, format_bench = await asyncio.gather(
            self._fetch_network_performance_ranking(),
            self._fetch_format_benchmarks(),
        )

        # Métricas consolidadas da rede
        if ranking:
            total_rev = sum(float(u.get("revenue_7d") or 0) for u in ranking)
            avg_ticket_net = sum(float(u.get("avg_ticket") or 0) for u in ranking) / len(ranking)
            avg_prod_net = sum(float(u.get("productivity") or 0) for u in ranking) / len(ranking)
            units_below_ticket = sum(
                1 for u in ranking
                if float(u.get("avg_ticket") or 0) < OPERATIONAL_TARGETS["avg_ticket_target"]
            )
            units_below_prod = sum(
                1 for u in ranking
                if float(u.get("productivity") or 0) < OPERATIONAL_TARGETS["productivity_target"]
            )

            network_summary = (
                f"PERFORMANCE DA REDE (últimos 7 dias):\n"
                f"• Receita total: R${total_rev:,.2f}\n"
                f"• Ticket médio rede: R${avg_ticket_net:.2f} (meta: R${OPERATIONAL_TARGETS['avg_ticket_target']})\n"
                f"• Produtividade média: R${avg_prod_net:.2f}/h (meta: R${OPERATIONAL_TARGETS['productivity_target']}/h)\n"
                f"• Unidades abaixo da meta de ticket: {units_below_ticket}/{len(ranking)}\n"
                f"• Unidades abaixo da meta de produtividade: {units_below_prod}/{len(ranking)}"
            )
        else:
            network_summary = "Dados de performance da rede não disponíveis."

        ranking_str = self.format_db_data(ranking, "Ranking de Performance (7 dias)")
        format_str = self.format_db_data(format_bench, "Benchmarks por Formato (30 dias)")

        prompt = f"""Pergunta de {user}: {question}

{network_summary}

{ranking_str}

{format_str}

METAS DE REFERÊNCIA:
• Ticket médio: R${OPERATIONAL_TARGETS['avg_ticket_target']}
• Produtividade: R${OPERATIONAL_TARGETS['productivity_target']}/h
• Rupturas: ≤ {OPERATIONAL_TARGETS['stockout_max_day']}/dia

Analise a performance consolidada da rede nos 10 blocos obrigatórios.
Identifique as alavancas de crescimento com maior potencial de receita incremental."""

        return await self.call_claude(prompt)
