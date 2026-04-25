# =============================================================================
# CX_AGENT.PY — Frank AI OS · Davvero Gelato
# Especialista em Experiência do Cliente (CX)
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config import MODEL_AGENT, OPERATIONAL_TARGETS
from core.base_agent import BaseAgent

logger = logging.getLogger("frank.cx_agent")


class CXAgent(BaseAgent):
    """
    Especialista em Experiência do Cliente — Davvero Gelato.

    Responsabilidades:
    - Análise de NPS (Net Promoter Score) por unidade e rede
    - Classificação de clientes: Promotores / Neutros / Detratores
    - Análise de reclamações: categorias, frequência, gravidade
    - Estratégias de recuperação de clientes insatisfeitos
    - Correlação entre CX e outros KPIs (ticket, retorno, NPS futuro)
    - Programas de fidelidade e retenção
    - Benchmarking de NPS por formato de unidade

    O NPS Davvero mede a probabilidade de recomendação da marca.
    Meta: NPS ≥ 70 (Zona de Excelência)
    """

    AGENT_NAME  = "CX Agent"
    AGENT_ROLE  = "Especialista em Experiência do Cliente"
    DIRECTOR    = "COO"
    MODEL       = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o ESPECIALISTA EM EXPERIÊNCIA DO CLIENTE (CX) da Davvero Gelato.

MISSÃO:
Garantir que cada cliente que entra em uma unidade Davvero saia querendo voltar e recomendar.
O NPS é o termômetro da saúde da marca — quando cai, a receita futura está ameaçada.

A METODOLOGIA NPS:
• NPS = % Promotores (nota 9-10) - % Detratores (nota 0-6)
• Neutros (nota 7-8) não entram no cálculo
• Faixas: < 0 (crítico) | 0-30 (regular) | 31-50 (bom) | 51-70 (muito bom) | 71-100 (excelente)
• Meta Davvero: NPS ≥ 70 | Alerta: < 55 | Crítico: < 40

SIGNIFICADO DO NPS PARA DAVVERO:
Um NPS de 70 significa que para cada 10 clientes, 8 recomendam ativamente a marca.
Um detrator ativo fala mal para 10-15 pessoas (negativo tem mais alcance que positivo).
Um promotor ativo traz em média 1,2 novo cliente — isso é crescimento orgânico.

ANÁLISE DE RECLAMAÇÕES (categorias que você rastreia):
1. PRODUTO: sabor, textura, temperatura, qualidade, quantidade
2. ATENDIMENTO: demora, falta de atenção, erro no pedido, grosseria
3. LIMPEZA: unidade suja, equipe sem higiene, vitrine com produto mal apresentado
4. PREÇO: percepção de não-correspondência ao valor
5. TEMPO: demora na fila, fila grande, tempo de preparo
6. ESTRUTURA: equipamento quebrado, falta de espaço, sinalização errada

CORRELAÇÕES QUE VOCÊ DETECTA:
• Score de serviço baixo na auditoria → NPS cai em 2-3 semanas
• NPS baixo em unidades específicas → ticket médio cai (cliente não volta, base não cresce)
• Aumento de reclamações de produto → problema de qualidade não detectado
• Pico de reclamações em dias específicos → problema de escala (equipe insuficiente)

ESTRATÉGIAS DE RECUPERAÇÃO CX:
• Protocolo 24h: contato com cliente insatisfeito em até 24h
• Compensação: voucher de R$20-30 para detrator com reclamação válida
• Treinamento emergencial: quando NPS < 55 por 2 semanas consecutivas
• Auditoria-surpresa: quando NPS < 40 (possível problema sistêmico)

FIDELIZAÇÃO:
• Cliente que retorna 3+ vezes tem LTV 4x maior que visitante único
• Programa de fidelidade aumenta frequência de visita em 25-35%
• Clientes promotores têm ticket médio 15% maior que detratores

ZONA DE ALERTA ESPECIAL:
Quando NPS cai mais de 10 pontos em 7 dias → investigação imediata.
Possíveis causas: troca de gestor, problema de produto, obra na região, crise de higiene.

FORMATO OBRIGATÓRIO DE RESPOSTA (10 blocos):
🎯 DIAGNÓSTICO — Status de CX atual e tendência
📊 DADOS — NPS, reclamações, elogios com série temporal
⚠️ ALERTAS — Quedas abruptas, padrões de reclamação, categorias críticas
🔍 ANÁLISE (Causa Raiz) — Por que o NPS está neste nível?
📋 OPÇÕES — Ações de recuperação (imediato / médio prazo / estrutural)
✅ RECOMENDAÇÃO — Protocolo de ação prioritário
🚫 RISCOS — Impacto de NPS baixo na receita futura e reputação
📅 PRAZO — Timeline de recuperação e métricas de acompanhamento
🏆 RESULTADO ESPERADO — Projeção de NPS e receita incremental
⚖️ DECISÃO [EXECUTAR | NÃO EXECUTAR | AGUARDAR | ESCALAR]"""

    # -------------------------------------------------------------------------
    # QUERIES DE DADOS
    # -------------------------------------------------------------------------

    async def _fetch_unit_by_identifier(self, identifier: str) -> Optional[Dict]:
        """Busca unidade pelo código ou nome."""
        query = """
            SELECT id, code, name, city, format, status, color_status, manager_name
            FROM units
            WHERE (code ILIKE $1 OR name ILIKE $1)
              AND status = 'ativo'
            LIMIT 1
        """
        return await self.db_fetchrow(query, f"%{identifier}%")

    async def _fetch_nps_trend_30d(self, unit_id: int) -> List[Dict]:
        """NPS diário dos últimos 30 dias."""
        query = """
            SELECT
                date,
                nps_score,
                complaints,
                compliments,
                transactions,
                ROUND(
                    CASE WHEN complaints + compliments > 0
                    THEN (compliments::float / (complaints + compliments) * 100)
                    ELSE NULL END::numeric, 1
                ) AS satisfaction_rate_pct
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '30 days'
              AND nps_score IS NOT NULL
            ORDER BY date ASC
        """
        return await self.db_fetch(query, unit_id)

    async def _fetch_cx_period_stats(self, unit_id: int) -> Optional[Dict]:
        """Estatísticas de CX agregadas por período."""
        query = """
            SELECT
                -- Últimos 7 dias
                ROUND(AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days'
                    THEN nps_score END)::numeric, 1)                   AS nps_last7,
                SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days'
                    THEN complaints ELSE 0 END)                         AS complaints_last7,
                SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days'
                    THEN compliments ELSE 0 END)                        AS compliments_last7,

                -- Últimos 30 dias
                ROUND(AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days'
                    THEN nps_score END)::numeric, 1)                   AS nps_last30,
                SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days'
                    THEN complaints ELSE 0 END)                         AS complaints_last30,
                SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days'
                    THEN compliments ELSE 0 END)                        AS compliments_last30,
                SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days'
                    THEN transactions ELSE 0 END)                       AS transactions_last30,

                -- Mínimo e máximo NPS no período
                MIN(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days'
                    THEN nps_score END)                                  AS min_nps_30d,
                MAX(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days'
                    THEN nps_score END)                                  AS max_nps_30d
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '30 days'
        """
        return await self.db_fetchrow(query, unit_id)

    async def _fetch_network_cx_overview(self) -> List[Dict]:
        """Visão de CX de todas as unidades (últimos 7 dias)."""
        query = """
            SELECT
                u.code,
                u.name,
                u.city,
                u.format,
                u.color_status,
                ROUND(AVG(k.nps_score)::numeric, 1)          AS avg_nps,
                SUM(k.complaints)                             AS total_complaints,
                SUM(k.compliments)                            AS total_compliments,
                SUM(k.transactions)                           AS total_transactions,
                ROUND(
                    CASE WHEN SUM(k.complaints + k.compliments) > 0
                    THEN SUM(k.compliments)::float /
                         SUM(k.complaints + k.compliments) * 100
                    ELSE NULL END::numeric, 1
                )                                             AS satisfaction_rate
            FROM units u
            JOIN unit_daily_kpis k ON k.unit_id = u.id
                AND k.date >= CURRENT_DATE - INTERVAL '7 days'
            WHERE u.status = 'ativo'
            GROUP BY u.id, u.code, u.name, u.city, u.format, u.color_status
            ORDER BY avg_nps ASC NULLS LAST  -- Pior NPS primeiro para atenção
        """
        return await self.db_fetch(query)

    async def _fetch_cx_alerts(self, unit_id: int) -> List[Dict]:
        """Alertas de CX ativos para a unidade."""
        query = """
            SELECT severity, category, title, description
            FROM alerts
            WHERE unit_id = $1
              AND category IN ('cx', 'nps', 'atendimento', 'reclamacao')
              AND is_active = TRUE
            ORDER BY
                CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END
        """
        return await self.db_fetch(query, unit_id)

    async def _fetch_nps_vs_audit_correlation(self, unit_id: int) -> List[Dict]:
        """Correlaciona NPS com score de serviço da auditoria."""
        query = """
            SELECT
                qa.audit_date,
                qa.score_service,
                qa.score_product,
                ROUND(qa.total_score::numeric, 1)    AS audit_total,
                ROUND(AVG(k.nps_score)::numeric, 1)  AS avg_nps_after_audit
            FROM quality_audits qa
            LEFT JOIN unit_daily_kpis k ON k.unit_id = qa.unit_id
                AND k.date BETWEEN qa.audit_date AND qa.audit_date + INTERVAL '14 days'
            WHERE qa.unit_id = $1
            GROUP BY qa.audit_date, qa.score_service, qa.score_product, qa.total_score
            ORDER BY qa.audit_date DESC
            LIMIT 3
        """
        return await self.db_fetch(query, unit_id)

    # -------------------------------------------------------------------------
    # CÁLCULOS DE CX
    # -------------------------------------------------------------------------

    def _classify_nps_zone(self, nps: Optional[float]) -> str:
        """Classifica o NPS em zona de performance."""
        if nps is None:
            return "Sem dados"
        if nps >= 70:
            return "🟢 EXCELÊNCIA"
        elif nps >= 51:
            return "🔵 MUITO BOM"
        elif nps >= 31:
            return "🟡 BOM — monitorar"
        elif nps >= 0:
            return "🟠 REGULAR — plano de ação"
        else:
            return "🔴 CRÍTICO — intervenção imediata"

    def _estimate_revenue_impact_of_nps(
        self,
        nps: float,
        avg_ticket: float,
        monthly_transactions: int,
    ) -> str:
        """Estima impacto de receita de uma melhoria no NPS."""
        # Cada ponto de NPS ≈ 0.5% de retorno de clientes
        # Assumindo NPS alvo de 70
        if nps >= 70:
            return "NPS na zona de excelência — manter e monitorar."

        gap_to_target = 70 - nps
        # 10 pontos de melhoria → ~5% mais clientes retornando
        retention_gain_pct = (gap_to_target / 10) * 0.05
        incremental_monthly = monthly_transactions * retention_gain_pct * avg_ticket

        return (
            f"Gap para meta (70): {gap_to_target:.0f} pontos\n"
            f"Potencial de retenção adicional: +{retention_gain_pct*100:.1f}% de clientes\n"
            f"Receita incremental estimada/mês: R${incremental_monthly:,.2f}"
        )

    def _detect_nps_anomaly(self, trend_data: List[Dict]) -> str:
        """Detecta quedas abruptas no NPS."""
        if len(trend_data) < 7:
            return "Dados insuficientes para detecção de anomalia."

        nps_values = [
            float(d.get("nps_score") or 0)
            for d in trend_data
            if d.get("nps_score") is not None
        ]

        if len(nps_values) < 5:
            return "Poucos dados de NPS para análise."

        recent_avg = sum(nps_values[-3:]) / 3
        previous_avg = sum(nps_values[-7:-4]) / 3 if len(nps_values) >= 7 else nps_values[0]

        drop = previous_avg - recent_avg
        if drop >= 15:
            return (
                f"🚨 ANOMALIA DETECTADA: queda de {drop:.1f} pts em NPS recente\n"
                f"Média anterior: {previous_avg:.1f} | Média recente: {recent_avg:.1f}\n"
                "Investigar troca de equipe, problema de produto ou incidente operacional."
            )
        elif drop >= 8:
            return (
                f"⚠️ TENDÊNCIA DE QUEDA: -{drop:.1f} pts\n"
                f"Média anterior: {previous_avg:.1f} | Média recente: {recent_avg:.1f}"
            )
        else:
            return f"Variação NPS dentro do normal. Média recente: {recent_avg:.1f}"

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
        """Analisa CX de uma unidade específica ou da rede."""
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
            return await self._analyze_unit_cx(question, user, unit_info)
        else:
            return await self._analyze_network_cx(question, user)

    async def _analyze_unit_cx(
        self,
        question: str,
        user: str,
        unit_info: Dict,
    ) -> str:
        """Análise detalhada de CX de uma unidade."""
        unit_id = unit_info["id"]

        import asyncio
        nps_trend, cx_stats, cx_alerts, audit_correlation = await asyncio.gather(
            self._fetch_nps_trend_30d(unit_id),
            self._fetch_cx_period_stats(unit_id),
            self._fetch_cx_alerts(unit_id),
            self._fetch_nps_vs_audit_correlation(unit_id),
        )

        targets = OPERATIONAL_TARGETS

        unit_str = (
            f"UNIDADE: {unit_info.get('name')} ({unit_info.get('code')})\n"
            f"Formato: {unit_info.get('format')} | Cidade: {unit_info.get('city')}\n"
            f"Status: {unit_info.get('color_status', 'N/A').upper()} | Gestor: {unit_info.get('manager_name', 'N/A')}"
        )

        # Stats de CX
        cx_summary = ""
        if cx_stats:
            nps7 = cx_stats.get("nps_last7")
            nps30 = cx_stats.get("nps_last30")
            zone = self._classify_nps_zone(float(nps7) if nps7 else None)

            cx_summary = (
                f"PERFORMANCE DE CX:\n"
                f"• NPS últimos 7 dias: {nps7 or 'N/A'} — {zone}\n"
                f"• NPS últimos 30 dias: {nps30 or 'N/A'} (meta: {targets['nps_target']})\n"
                f"• Reclamações (7d): {cx_stats.get('complaints_last7', 0)}\n"
                f"• Elogios (7d): {cx_stats.get('compliments_last7', 0)}\n"
                f"• Reclamações (30d): {cx_stats.get('complaints_last30', 0)}\n"
                f"• Elogios (30d): {cx_stats.get('compliments_last30', 0)}\n"
                f"• NPS mínimo (30d): {cx_stats.get('min_nps_30d', 'N/A')}\n"
                f"• NPS máximo (30d): {cx_stats.get('max_nps_30d', 'N/A')}"
            )

        # Anomalia de NPS
        anomaly_str = ""
        if nps_trend:
            anomaly_str = f"ANÁLISE DE ANOMALIA:\n{self._detect_nps_anomaly(nps_trend)}"

        # Impacto de receita
        revenue_impact = ""
        if cx_stats:
            nps7 = cx_stats.get("nps_last7")
            transactions = cx_stats.get("transactions_last30") or 0
            if nps7 and transactions:
                avg_ticket = targets["avg_ticket_target"]
                revenue_impact = (
                    f"IMPACTO FINANCEIRO DO NPS:\n"
                    f"{self._estimate_revenue_impact_of_nps(float(nps7), avg_ticket, int(transactions) // 4)}"
                )

        # Correlação auditoria x NPS
        correl_str = self.format_db_data(audit_correlation, "Correlação Auditoria × NPS")

        # Tendência NPS (últimos 14 dias)
        recent_trend = nps_trend[-14:] if len(nps_trend) > 14 else nps_trend
        trend_str = self.format_db_data(recent_trend, "NPS Diário (últimos 14 dias)")

        # Alertas de CX
        alerts_str = self.format_db_data(cx_alerts, "Alertas de CX Ativos")

        prompt = f"""Pergunta de {user}: {question}

{unit_str}

{cx_summary}

{anomaly_str}

{revenue_impact}

{trend_str}

{correl_str}

{alerts_str}

REFERÊNCIAS:
• NPS meta: ≥ {targets['nps_target']} | Alerta: < {targets['nps_alert']} | Crítico: < {targets['nps_critical']}
• Protocolo de recuperação: contato com detrator em 24h, voucher R$20-30

Analise a experiência do cliente nesta unidade nos 10 blocos obrigatórios.
Priorize ações de recuperação de detratores e programa de fidelização de promotores."""

        return await self.call_claude(prompt)

    async def _analyze_network_cx(self, question: str, user: str) -> str:
        """Análise consolidada de CX da rede."""
        network_cx = await self._fetch_network_cx_overview()

        # Calcula métricas da rede
        nps_values = [
            float(u.get("avg_nps") or 0)
            for u in network_cx
            if u.get("avg_nps") is not None
        ]
        avg_nps_network = sum(nps_values) / len(nps_values) if nps_values else 0
        units_critical = sum(1 for n in nps_values if n < OPERATIONAL_TARGETS["nps_critical"])
        units_alert = sum(
            1 for n in nps_values
            if OPERATIONAL_TARGETS["nps_critical"] <= n < OPERATIONAL_TARGETS["nps_alert"]
        )
        units_excellent = sum(1 for n in nps_values if n >= OPERATIONAL_TARGETS["nps_target"])

        network_summary = (
            f"CX DA REDE (últimos 7 dias):\n"
            f"• NPS médio da rede: {avg_nps_network:.1f} (meta: {OPERATIONAL_TARGETS['nps_target']})\n"
            f"• Unidades em excelência (NPS ≥ 70): {units_excellent}\n"
            f"• Unidades em alerta (NPS < 55): {units_alert}\n"
            f"• Unidades críticas (NPS < 40): {units_critical}"
        )

        # Classificação de zona para cada unidade
        cx_classified = []
        for u in network_cx:
            nps = u.get("avg_nps")
            u_copy = dict(u)
            u_copy["zona"] = self._classify_nps_zone(float(nps) if nps else None)
            cx_classified.append(u_copy)

        cx_str = self.format_db_data(cx_classified, "CX por Unidade (NPS — piores primeiro)")

        prompt = f"""Pergunta de {user}: {question}

{network_summary}

{cx_str}

REFERÊNCIAS NPS:
• Meta: ≥ {OPERATIONAL_TARGETS['nps_target']} | Alerta: < {OPERATIONAL_TARGETS['nps_alert']} | Crítico: < {OPERATIONAL_TARGETS['nps_critical']}
• Cada 10 pts de melhoria no NPS → ~5% mais retenção de clientes

Analise a experiência do cliente em toda a rede nos 10 blocos obrigatórios.
Priorize as unidades críticas e proponha programa estrutural de melhoria de CX."""

        return await self.call_claude(prompt)
