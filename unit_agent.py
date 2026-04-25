# =============================================================================
# UNIT_AGENT.PY — Frank AI OS · Davvero Gelato
# Agente de Análise de Saúde das Unidades
# =============================================================================

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from config import MODEL_AGENT, OPERATIONAL_TARGETS
from core.base_agent import BaseAgent

logger = logging.getLogger("frank.unit_agent")


class UnitAgent(BaseAgent):
    """
    Analista de Saúde das Unidades — Davvero Gelato.

    Responsabilidades:
    - Diagnóstico completo de saúde de cada unidade da rede
    - Monitoramento de KPIs diários e tendências
    - Cruzamento de dados financeiros, operacionais e de qualidade
    - Identificação de unidades em risco antes que virem crise
    - Alertas proativos para o COO

    Consultas ao banco:
    - units (status, formato, gestor)
    - unit_daily_kpis (7 e 30 dias)
    - quality_audits (última auditoria)
    - alerts (alertas ativos)
    """

    AGENT_NAME  = "Unit Agent"
    AGENT_ROLE  = "Analista de Saúde das Unidades"
    DIRECTOR    = "COO"
    MODEL       = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o ANALISTA DE SAÚDE DAS UNIDADES da Davvero Gelato.

MISSÃO:
Monitorar, diagnosticar e reportar a saúde operacional de cada unidade da rede.
Seu relatório é a base para decisões do COO e intervenções nas unidades.

O QUE VOCÊ ANALISA:
1. INDICADORES FINANCEIROS: CMV, ticket médio, receita, transações
2. PRODUTIVIDADE: R$/hora-trabalhada vs meta R$150/h
3. RUPTURAS: faltas de produto no ponto de venda (máx. 2/dia)
4. QUALIDADE: score da última auditoria (mínimo 80 pts)
5. CX: NPS, reclamações e elogios
6. STATUS GERAL: classificação verde/amarelo/laranja/vermelho

CRITÉRIOS DE STATUS DAS UNIDADES:
🟢 VERDE: todos KPIs dentro das metas
🟡 AMARELO: 1-2 KPIs em zona de alerta — monitoramento intensivo
🟠 LARANJA: 3+ KPIs em alerta — plano de ação obrigatório em 48h
🔴 VERMELHO: KPI em nível crítico OU auditoria < 70 — intervenção imediata

PARÂMETROS DE META:
• CMV target: 26,5% | alerta: 28% | crítico: 30%
• Ticket médio: R$35 (mín. R$30)
• Produtividade: R$150/hora (mín. R$120/h)
• Rupturas: máx. 2/dia (crítico: 5+/dia)
• NPS: 70 (alerta: 55 | crítico: 40)
• Auditoria: 80 pts (crítico: < 70)

ANÁLISE DE TENDÊNCIAS:
Compare sempre a performance dos últimos 7 dias com a média dos 30 dias anteriores.
Identifique tendências de alta ou queda antes que virem problemas sérios.

GESTÃO DE EQUIPE:
Avalie a consistência da equipe: rotatividade, presença de gestores, horas trabalhadas.
Unidades com baixa consistência de equipe tendem a ter CMV e NPS piores.

FORMATO OBRIGATÓRIO DE RESPOSTA (10 blocos):
🎯 DIAGNÓSTICO — Status geral e classificação de cor
📊 DADOS — KPIs quantitativos com comparativo de período
⚠️ ALERTAS — Indicadores fora das metas (ordenados por severidade)
🔍 ANÁLISE (Causa Raiz) — Por que está assim? Correlações entre indicadores
📋 OPÇÕES — 2-3 caminhos possíveis de ação
✅ RECOMENDAÇÃO — Ação prioritária com responsável e prazo
🚫 RISCOS — O que pode piorar se não agirmos
📅 PRAZO — Timeline de implementação e check-ins
🏆 RESULTADO ESPERADO — Projeção quantitativa após ação
⚖️ DECISÃO [EXECUTAR | NÃO EXECUTAR | AGUARDAR | ESCALAR]"""

    # -------------------------------------------------------------------------
    # QUERIES DE DADOS
    # -------------------------------------------------------------------------

    async def _fetch_unit_info(self, unit_identifier: str) -> Optional[Dict]:
        """Busca informações básicas da unidade pelo código ou nome."""
        # Tenta por código primeiro, depois por nome
        query = """
            SELECT
                id, code, name, city, format, status,
                color_status, manager_name, team_count
            FROM units
            WHERE (code ILIKE $1 OR name ILIKE $1)
              AND status = 'ativo'
            LIMIT 1
        """
        return await self.db_fetchrow(query, f"%{unit_identifier}%")

    async def _fetch_unit_kpis_7d(self, unit_id: int) -> List[Dict]:
        """KPIs diários dos últimos 7 dias."""
        query = """
            SELECT
                date,
                gross_revenue,
                transactions,
                ROUND(avg_ticket::numeric, 2) AS avg_ticket,
                team_hours,
                ROUND(productivity::numeric, 2) AS productivity,
                stockout_count,
                waste_value,
                nps_score,
                complaints,
                compliments
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY date DESC
        """
        return await self.db_fetch(query, unit_id)

    async def _fetch_unit_kpis_30d_avg(self, unit_id: int) -> Optional[Dict]:
        """Médias dos últimos 30 dias para comparativo."""
        query = """
            SELECT
                ROUND(AVG(gross_revenue)::numeric, 2)   AS avg_revenue_30d,
                ROUND(AVG(transactions)::numeric, 1)     AS avg_transactions_30d,
                ROUND(AVG(avg_ticket)::numeric, 2)       AS avg_ticket_30d,
                ROUND(AVG(productivity)::numeric, 2)     AS avg_productivity_30d,
                ROUND(AVG(stockout_count)::numeric, 1)   AS avg_stockouts_30d,
                ROUND(AVG(waste_value)::numeric, 2)      AS avg_waste_30d,
                ROUND(AVG(nps_score)::numeric, 1)        AS avg_nps_30d,
                ROUND(AVG(complaints)::numeric, 1)       AS avg_complaints_30d,
                SUM(gross_revenue)                       AS total_revenue_30d,
                SUM(transactions)                        AS total_transactions_30d
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '30 days'
        """
        return await self.db_fetchrow(query, unit_id)

    async def _fetch_last_audit(self, unit_id: int) -> Optional[Dict]:
        """Última auditoria de qualidade da unidade."""
        query = """
            SELECT
                audit_date,
                score_visual,
                score_product,
                score_portioning,
                score_service,
                score_hygiene,
                score_operations,
                ROUND(total_score::numeric, 1) AS total_score,
                classification,
                non_conformities,
                action_plan
            FROM quality_audits
            WHERE unit_id = $1
            ORDER BY audit_date DESC
            LIMIT 1
        """
        return await self.db_fetchrow(query, unit_id)

    async def _fetch_active_alerts(self, unit_id: int) -> List[Dict]:
        """Alertas ativos da unidade."""
        query = """
            SELECT
                severity,
                category,
                title,
                description
            FROM alerts
            WHERE unit_id = $1
              AND is_active = TRUE
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'high'     THEN 2
                    WHEN 'medium'   THEN 3
                    WHEN 'low'      THEN 4
                    ELSE 5
                END
        """
        return await self.db_fetch(query, unit_id)

    async def _fetch_all_units_summary(self) -> List[Dict]:
        """Resumo de todas as unidades ativas com KPIs recentes."""
        query = """
            SELECT
                u.code,
                u.name,
                u.city,
                u.format,
                u.color_status,
                u.manager_name,
                ROUND(AVG(k.avg_ticket)::numeric, 2)    AS avg_ticket_7d,
                ROUND(AVG(k.productivity)::numeric, 2)  AS productivity_7d,
                ROUND(AVG(k.nps_score)::numeric, 1)     AS nps_7d,
                ROUND(AVG(k.stockout_count)::numeric, 1) AS stockouts_7d,
                SUM(k.gross_revenue)                     AS revenue_7d
            FROM units u
            LEFT JOIN unit_daily_kpis k ON k.unit_id = u.id
                AND k.date >= CURRENT_DATE - INTERVAL '7 days'
            WHERE u.status = 'ativo'
            GROUP BY u.id, u.code, u.name, u.city, u.format, u.color_status, u.manager_name
            ORDER BY u.color_status DESC, revenue_7d DESC NULLS LAST
        """
        return await self.db_fetch(query)

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
        """
        Analisa saúde de uma unidade específica ou da rede completa.
        Extrai o identificador da unidade da pergunta, se presente.
        """
        # Detecta se a pergunta é sobre uma unidade específica ou a rede
        unit_info = None
        unit_id = None

        # Tenta identificar unidade por código (ex: DV001, SP003) ou nome
        import re
        unit_code_match = re.search(r'\b([A-Z]{2,3}[\-_]?\d{3,4})\b', question.upper())
        if unit_code_match:
            code = unit_code_match.group(1)
            unit_info = await self._fetch_unit_info(code)

        # Se não achou por código, tenta por palavras-chave no nome
        if not unit_info:
            # Extrai possível nome de cidade ou unidade da pergunta
            words = [w for w in question.split() if len(w) > 4 and w[0].isupper()]
            for word in words[:3]:
                unit_info = await self._fetch_unit_info(word)
                if unit_info:
                    break

        # Busca dados conforme o escopo detectado
        if unit_info:
            unit_id = unit_info["id"]
            return await self._analyze_single_unit(question, user, unit_info)
        else:
            return await self._analyze_network(question, user)

    async def _analyze_single_unit(
        self,
        question: str,
        user: str,
        unit_info: Dict,
    ) -> str:
        """Análise detalhada de uma unidade específica."""
        unit_id = unit_info["id"]

        # Busca todos os dados em paralelo
        import asyncio
        kpis_7d, kpis_30d, last_audit, alerts = await asyncio.gather(
            self._fetch_unit_kpis_7d(unit_id),
            self._fetch_unit_kpis_30d_avg(unit_id),
            self._fetch_last_audit(unit_id),
            self._fetch_active_alerts(unit_id),
        )

        # Formata os dados para o prompt
        targets = OPERATIONAL_TARGETS

        unit_str = f"""
UNIDADE: {unit_info.get('name')} | Código: {unit_info.get('code')}
Cidade: {unit_info.get('city')} | Formato: {unit_info.get('format')}
Status: {unit_info.get('color_status', 'N/A').upper()} | Gestor: {unit_info.get('manager_name', 'N/A')}
Equipe: {unit_info.get('team_count', 'N/A')} pessoas"""

        kpi_7d_str = self.format_db_data(kpis_7d, "KPIs Últimos 7 Dias")

        kpi_30d_str = ""
        if kpis_30d:
            kpi_30d_str = f"""
MÉDIAS 30 DIAS (comparativo):
• Receita média/dia: R${kpis_30d.get('avg_revenue_30d', 'N/A')}
• Ticket médio: R${kpis_30d.get('avg_ticket_30d', 'N/A')} (meta: R${targets['avg_ticket_target']})
• Produtividade: R${kpis_30d.get('avg_productivity_30d', 'N/A')}/h (meta: R${targets['productivity_target']}/h)
• NPS médio: {kpis_30d.get('avg_nps_30d', 'N/A')} (meta: {targets['nps_target']})
• Rupturas médias: {kpis_30d.get('avg_stockouts_30d', 'N/A')}/dia (máx: {targets['stockout_max_day']})
• Desperdício médio: R${kpis_30d.get('avg_waste_30d', 'N/A')}
• Receita total 30d: R${kpis_30d.get('total_revenue_30d', 'N/A')}"""

        audit_str = ""
        if last_audit:
            audit_str = f"""
ÚLTIMA AUDITORIA ({last_audit.get('audit_date', 'N/A')}):
• Score Total: {last_audit.get('total_score', 'N/A')}/100 (mínimo: {targets['audit_score_min']})
• Classificação: {last_audit.get('classification', 'N/A')}
• Visual: {last_audit.get('score_visual', 'N/A')}/20
• Produto: {last_audit.get('score_product', 'N/A')}/25
• Porcionamento: {last_audit.get('score_portioning', 'N/A')}/15
• Serviço: {last_audit.get('score_service', 'N/A')}/20
• Higiene: {last_audit.get('score_hygiene', 'N/A')}/10
• Operações: {last_audit.get('score_operations', 'N/A')}/10
• Não-conformidades: {last_audit.get('non_conformities', 'Nenhuma registrada')}"""
        else:
            audit_str = "\nÚLTIMA AUDITORIA: Nenhuma auditoria registrada."

        alerts_str = self.format_db_data(alerts, "Alertas Ativos")

        prompt = f"""Pergunta de {user}: {question}

DADOS COMPLETOS DA UNIDADE:
{unit_str}

{kpi_7d_str}

{kpi_30d_str}

{audit_str}

{alerts_str}

METAS DE REFERÊNCIA:
• CMV: ≤ {targets['cmv_target_pct']}% (alerta: {targets['cmv_alert_pct']}% | crítico: {targets['cmv_critical_pct']}%)
• Ticket: ≥ R${targets['avg_ticket_target']} | Produtividade: ≥ R${targets['productivity_target']}/h
• NPS: ≥ {targets['nps_target']} | Auditoria: ≥ {targets['audit_score_min']} pts | Rupturas: ≤ {targets['stockout_max_day']}/dia

Analise a saúde completa desta unidade e forneça diagnóstico nos 10 blocos obrigatórios.
Classifique o status (VERDE/AMARELO/LARANJA/VERMELHO) com justificativa quantitativa."""

        return await self.call_claude(prompt)

    async def _analyze_network(self, question: str, user: str) -> str:
        """Análise consolidada de todas as unidades da rede."""
        units_summary = await self._fetch_all_units_summary()

        # Contadores de status
        status_counts = {"verde": 0, "amarelo": 0, "laranja": 0, "vermelho": 0}
        for u in units_summary:
            s = (u.get("color_status") or "amarelo").lower()
            if s in status_counts:
                status_counts[s] += 1

        network_overview = f"""
RESUMO DA REDE:
• Total ativas: {len(units_summary)}
• Verde: {status_counts['verde']} | Amarelo: {status_counts['amarelo']} | Laranja: {status_counts['laranja']} | Vermelho: {status_counts['vermelho']}"""

        units_str = self.format_db_data(units_summary, "Todas as Unidades Ativas (7 dias)")

        prompt = f"""Pergunta de {user}: {question}

{network_overview}

{units_str}

METAS DE REFERÊNCIA:
• Ticket: ≥ R${OPERATIONAL_TARGETS['avg_ticket_target']}
• Produtividade: ≥ R${OPERATIONAL_TARGETS['productivity_target']}/h
• NPS: ≥ {OPERATIONAL_TARGETS['nps_target']}
• Rupturas: ≤ {OPERATIONAL_TARGETS['stockout_max_day']}/dia

Analise o panorama completo da rede nos 10 blocos obrigatórios.
Destaque as unidades mais críticas e as que estão servindo de benchmark."""

        return await self.call_claude(prompt)
