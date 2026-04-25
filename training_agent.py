"""
Training Agent — Análise de Necessidades de Treinamento e Desenvolvimento de Programas
Identifica gaps de treinamento com base em auditorias de qualidade e performance operacional.
"""

import json
import logging
from datetime import date, timedelta
from typing import Any

from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, ALERT_THRESHOLDS

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = f"""Você é o Especialista de Treinamento & Desenvolvimento da Davvero Gelato,
responsável por elevar a excelência operacional da rede via educação corporativa.

COMPETÊNCIAS CORE:
- Andragogia: aprendizado adulto, metodologias ativas, microlearning
- Treinamento operacional em franquias de foodservice premium
- Desenvolvimento de trilhas de aprendizado (onboarding, técnico, liderança)
- Análise de gaps: cruzamento de auditorias x performance x turnover
- Certificação e acompanhamento de competências

PADRÕES DA DAVVERO GELATO:
- Score mínimo de auditoria: {ALERT_THRESHOLDS.get('audit_score_min', 70)} pontos
- NPS mínimo aceitável: {ALERT_THRESHOLDS.get('nps_min', 55)}
- Unidades com score < 70 entram em plano de desenvolvimento imediato

ABORDAGEM:
1. Diagnóstico baseado em dados (auditoria + KPIs + turnover)
2. Mapeamento de gaps por dimensão (técnica, atendimento, gestão, produto)
3. Programa customizado por perfil e urgência
4. Métricas de eficácia do treinamento

Sempre responda no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO"""


class TrainingAgent(BaseAgent):
    """
    Analisa gaps de treinamento cruzando auditorias de qualidade com KPIs operacionais.
    Desenvolve programas de capacitação customizados por unidade e perfil.
    """

    AUDIT_SCORE_MIN = ALERT_THRESHOLDS.get("audit_score_min", 70)
    NPS_MIN = ALERT_THRESHOLDS.get("nps_min", 55)

    def __init__(self):
        super().__init__(
            agent_name="TrainingAgent",
            model=MODEL_AGENT,
            system_prompt=SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        """
        Fetch low-scoring audits and performance gaps, then ask Claude to
        produce a training plan.
        """
        logger.info(f"[TrainingAgent] analyze called | query={query[:80]!r}")

        audit_data = await self._fetch_low_audit_scores()
        nps_data = await self._fetch_low_nps_units()
        recent_audits = await self._fetch_recent_audits()
        training_gaps = await self._identify_training_gaps()

        prompt = f"""
CONSULTA DE TREINAMENTO: {query}

=== UNIDADES COM AUDITORIA ABAIXO DE {self.AUDIT_SCORE_MIN} PONTOS ===
{audit_data}

=== UNIDADES COM NPS ABAIXO DE {self.NPS_MIN} ===
{nps_data}

=== AUDITORIAS RECENTES (ÚLTIMOS 90 DIAS) ===
{recent_audits}

=== GAPS IDENTIFICADOS POR DIMENSÃO ===
{training_gaps}

Com base nesses dados, elabore um plano de treinamento estruturado incluindo:
1. Priorização das unidades que precisam de intervenção imediata
2. Mapeamento dos gaps por dimensão (técnica, atendimento, gestão, produto, higiene)
3. Programa de capacitação com metodologia, carga horária e formato
4. KPIs de acompanhamento da eficácia do treinamento
5. Cronograma de implementação

Responda no formato completo:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""
        response = await self.call_claude(user_message=prompt)
        logger.info("[TrainingAgent] analyze completed")
        return response

    # ------------------------------------------------------------------
    # Specific training program builders
    # ------------------------------------------------------------------

    async def build_onboarding_program(self, unit_code: str) -> str:
        """Generate a full onboarding training program for a new franchisee/manager."""
        unit = await self.db_fetchrow(
            "SELECT * FROM units WHERE code = $1", unit_code
        )
        if not unit:
            return f"Unidade {unit_code} não encontrada."

        prompt = f"""
Unidade: {unit.get('name')} ({unit_code}) — Cidade: {unit.get('city')}
Formato: {unit.get('format')} | Manager: {unit.get('manager_name')}

Crie um programa completo de ONBOARDING para esta unidade com:
- Trilha de 30 dias para franqueado novo
- Trilha de 14 dias para colaborador de loja
- Módulos: produto/gelato artesanal, atendimento premium, operações/SOP, gestão financeira básica
- Avaliações de competência por módulo
- Checklist de certificação antes da abertura

Responda no formato estruturado completo.
"""
        return await self.call_claude(user_message=prompt)

    async def analyze_unit_training_need(self, unit_id: int) -> str:
        """Deep-dive training needs analysis for a specific unit."""
        audit = await self.db_fetchrow(
            """
            SELECT qa.total_score, qa.classification, qa.audit_date,
                   u.name, u.code, u.manager_name
            FROM quality_audits qa
            JOIN units u ON u.id = qa.unit_id
            WHERE qa.unit_id = $1
            ORDER BY qa.audit_date DESC
            LIMIT 1
            """,
            unit_id,
        )
        kpis = await self.db_fetchrow(
            """
            SELECT AVG(nps_score) as avg_nps,
                   AVG(avg_ticket) as avg_ticket,
                   SUM(transactions) as total_transactions
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '30 days'
            """,
            unit_id,
        )

        context = f"Auditoria: {json.dumps(dict(audit or {}), default=str)}\nKPIs 30d: {json.dumps(dict(kpis or {}), default=str)}"
        return await self.analyze(
            f"Análise detalhada de necessidade de treinamento para unidade ID={unit_id}",
            context={"raw": context},
        )

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _fetch_low_audit_scores(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT u.code, u.name, u.city,
                   qa.total_score, qa.classification, qa.audit_date
            FROM quality_audits qa
            JOIN units u ON u.id = qa.unit_id
            WHERE qa.total_score < $1
              AND qa.audit_date >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY qa.total_score ASC
            """,
            self.AUDIT_SCORE_MIN,
        )
        return self.format_db_data(rows, title=f"Auditorias Abaixo de {self.AUDIT_SCORE_MIN} pts")

    async def _fetch_low_nps_units(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT u.code, u.name, u.city,
                   ROUND(AVG(dk.nps_score)::numeric, 1) AS avg_nps_30d,
                   COUNT(dk.date) AS days_measured
            FROM unit_daily_kpis dk
            JOIN units u ON u.id = dk.unit_id
            WHERE dk.date >= CURRENT_DATE - INTERVAL '30 days'
              AND dk.nps_score IS NOT NULL
            GROUP BY u.id, u.code, u.name, u.city
            HAVING AVG(dk.nps_score) < $1
            ORDER BY avg_nps_30d ASC
            """,
            self.NPS_MIN,
        )
        return self.format_db_data(rows, title=f"Unidades com NPS < {self.NPS_MIN}")

    async def _fetch_recent_audits(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT u.code, u.name,
                   qa.total_score, qa.classification, qa.audit_date
            FROM quality_audits qa
            JOIN units u ON u.id = qa.unit_id
            WHERE qa.audit_date >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY qa.audit_date DESC, qa.total_score ASC
            LIMIT 20
            """
        )
        return self.format_db_data(rows, title="Auditorias Recentes (90 dias)")

    async def _identify_training_gaps(self) -> str:
        """Cross-reference audit scores with NPS and revenue to identify gap dimensions."""
        rows = await self.db_fetch(
            """
            SELECT
                u.code, u.name, u.city,
                COALESCE(qa.total_score, 0)                        AS audit_score,
                COALESCE(qa.classification, 'sem_auditoria')       AS classification,
                ROUND(AVG(dk.nps_score)::numeric, 1)               AS avg_nps,
                ROUND(AVG(dk.avg_ticket)::numeric, 2)              AS avg_ticket,
                COALESCE(uf.cmv_pct, 0)                            AS cmv_pct,
                COALESCE(uf.ebitda_pct, 0)                         AS ebitda_pct
            FROM units u
            LEFT JOIN (
                SELECT DISTINCT ON (unit_id) unit_id, total_score, classification, audit_date
                FROM quality_audits
                ORDER BY unit_id, audit_date DESC
            ) qa ON qa.unit_id = u.id
            LEFT JOIN unit_daily_kpis dk
                   ON dk.unit_id = u.id
                  AND dk.date >= CURRENT_DATE - INTERVAL '30 days'
            LEFT JOIN (
                SELECT DISTINCT ON (unit_id) unit_id, cmv_pct, ebitda_pct
                FROM unit_financials
                ORDER BY unit_id, id DESC
            ) uf ON uf.unit_id = u.id
            WHERE u.status = 'ativa'
            GROUP BY u.id, u.code, u.name, u.city,
                     qa.total_score, qa.classification,
                     uf.cmv_pct, uf.ebitda_pct
            ORDER BY audit_score ASC NULLS FIRST
            """
        )
        return self.format_db_data(rows, title="Gap Matrix: Auditoria x NPS x Financeiro")
