"""
HR Agent — Gestão de Pessoas, Equipes e Capital Humano
Dimensionamento de equipes, retenção, clima organizacional e políticas de RH para franquias de gelato.
"""

import json
import logging
from typing import Any

from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS, ALERT_THRESHOLDS

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = f"""Você é o Especialista de Recursos Humanos da Davvero Gelato,
responsável por garantir que cada unidade tenha a equipe certa, bem treinada e engajada.

ESPECIALIDADES:
- Dimensionamento de equipe para operações de gelato (formatos: quiosque, loja padrão, flagship)
- Recrutamento e seleção para o varejo alimentar premium
- Retenção e engajamento: clima organizacional, plano de carreira, reconhecimento
- Política de benefícios adaptada para franquias (sem poder de escala do franqueador)
- Gestão de jornada e escala operacional
- Folha de pagamento e encargos (leitura analítica, não execução)
- Compliance trabalhista em operações 7 dias/semana

BENCHMARKS DE EQUIPE DAVVERO:
- Quiosque (< 30m²): 2-3 colaboradores
- Loja Padrão (30-60m²): 4-6 colaboradores
- Flagship (> 60m²): 7-10 colaboradores
- Gerente: 1 por unidade (obrigatório certificado Davvero)
- Turnover tolerável: < 5% ao mês
- Horas de treinamento iniciais: mínimo 40h por colaborador

ALERTAS DE RH:
- Turnover > {ALERT_THRESHOLDS.get('turnover_monthly_pct', 5)}%/mês → plano de retenção imediato
- Equipe abaixo do mínimo por formato → risco operacional
- Gerente sem certificação → bloqueio de abertura / advertência formal

Formato de resposta:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO"""


# Team sizing benchmarks by format
TEAM_SIZING = {
    "quiosque": {"min": 2, "ideal": 3, "max": 4},
    "loja_padrao": {"min": 4, "ideal": 5, "max": 6},
    "flagship": {"min": 7, "ideal": 8, "max": 10},
    "default": {"min": 3, "ideal": 5, "max": 7},
}


class HRAgent(BaseAgent):
    """
    Gerencia capital humano da rede Davvero Gelato.
    Cruza dados de equipe, turnover, performance e auditoria para análises de RH.
    """

    def __init__(self):
        super().__init__(
            agent_name="HRAgent",
            model=MODEL_AGENT,
            system_prompt=SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        """
        Fetch team data and performance metrics across all units,
        then produce HR recommendations.
        """
        logger.info(f"[HRAgent] analyze called | query={query[:80]!r}")

        team_data = await self._fetch_team_overview()
        understaffed = await self._identify_understaffed_units()
        high_performers = await self._fetch_top_performing_units()
        hr_alerts = await self._fetch_hr_alerts()

        prompt = f"""
CONSULTA DE RH: {query}

=== VISÃO GERAL DE EQUIPES ===
{team_data}

=== UNIDADES COM EQUIPE ABAIXO DO MÍNIMO ===
{understaffed}

=== UNIDADES TOP PERFORMANCE (REFERÊNCIA) ===
{high_performers}

=== ALERTAS DE RH ATIVOS ===
{hr_alerts}

=== BENCHMARKS DE DIMENSIONAMENTO ===
{json.dumps(TEAM_SIZING, ensure_ascii=False, indent=2)}

Com base nesses dados, forneça análise completa de RH incluindo:
1. Diagnóstico do capital humano da rede
2. Unidades em risco por subdimensionamento
3. Análise de retenção e engajamento
4. Plano de ação para unidades críticas
5. Recomendações de recrutamento por perfil
6. Políticas de reconhecimento e carreira

Responda no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""
        response = await self.call_claude(user_message=prompt)
        logger.info("[HRAgent] analyze completed")
        return response

    # ------------------------------------------------------------------
    # Specific HR methods
    # ------------------------------------------------------------------

    async def team_sizing_analysis(self, unit_id: int) -> str:
        """Analyze whether a unit is correctly staffed for its format and volume."""
        unit = await self.db_fetchrow(
            "SELECT * FROM units WHERE id = $1", unit_id
        )
        if not unit:
            return f"Unidade ID {unit_id} não encontrada."

        fmt = (unit.get("format") or "default").lower().replace(" ", "_")
        benchmark = TEAM_SIZING.get(fmt, TEAM_SIZING["default"])
        current_team = unit.get("team_count", 0)

        kpis = await self.db_fetchrow(
            """
            SELECT AVG(transactions) AS avg_daily_transactions,
                   AVG(gross_revenue) AS avg_daily_revenue
            FROM unit_daily_kpis
            WHERE unit_id = $1
              AND date >= CURRENT_DATE - INTERVAL '30 days'
            """,
            unit_id,
        )

        status = "adequado"
        if current_team < benchmark["min"]:
            status = "SUBDIMENSIONADO"
        elif current_team > benchmark["max"]:
            status = "superdimensionado"

        prompt = f"""
ANÁLISE DE DIMENSIONAMENTO — {unit.get('name')} ({unit.get('code')})
Formato: {unit.get('format')} | Cidade: {unit.get('city')}
Equipe atual: {current_team} colaboradores
Benchmark para o formato: mín {benchmark['min']}, ideal {benchmark['ideal']}, máx {benchmark['max']}
Status: {status}

KPIs Operacionais (30 dias):
- Transações médias/dia: {round(float(kpis.get('avg_daily_transactions') or 0), 1)}
- Receita média/dia: R$ {round(float(kpis.get('avg_daily_revenue') or 0), 2)}

Forneça recomendação detalhada de dimensionamento incluindo:
1. Escala de turnos sugerida (manhã/tarde/noite)
2. Perfis a contratar (se subdimensionado)
3. Custo estimado de folha com o time ideal
4. Plano de transição para o dimensionamento correto

Formato estruturado obrigatório.
"""
        return await self.call_claude(user_message=prompt)

    async def retention_plan(self, unit_code: str) -> str:
        """Generate a retention plan for a unit with high turnover risk."""
        unit = await self.db_fetchrow(
            "SELECT * FROM units WHERE code = $1", unit_code
        )
        if not unit:
            return f"Unidade {unit_code} não encontrada."

        prompt = f"""
PLANO DE RETENÇÃO — {unit.get('name')} ({unit_code})
Formato: {unit.get('format')} | Equipe: {unit.get('team_count')} colaboradores
Manager: {unit.get('manager_name')}

Crie um Plano de Retenção de 90 dias com:
1. Diagnóstico de causas-raiz do turnover em franquias de gelato
2. Ações de curto prazo (primeiros 30 dias): escuta ativa, ajustes imediatos
3. Ações de médio prazo (31-60 dias): benefícios, reconhecimento, carreira
4. Ações de longo prazo (61-90 dias): cultura, liderança, desenvolvimento
5. KPIs de acompanhamento (turnover mensal, NPS interno, absenteísmo)
6. Custo estimado do plano vs. custo de substituição de colaborador

Formato estruturado obrigatório.
"""
        return await self.call_claude(user_message=prompt)

    async def recruitment_brief(self, role: str, unit_code: str) -> str:
        """Generate a recruitment brief for a specific role and unit."""
        unit = await self.db_fetchrow(
            "SELECT * FROM units WHERE code = $1", unit_code
        )
        prompt = f"""
BRIEF DE RECRUTAMENTO
Cargo: {role}
Unidade: {unit.get('name', unit_code) if unit else unit_code}
Cidade: {unit.get('city', 'não informada') if unit else 'não informada'}
Formato: {unit.get('format', 'padrão') if unit else 'padrão'}

Crie um brief completo de recrutamento incluindo:
1. Descrição do cargo e responsabilidades
2. Requisitos obrigatórios e desejáveis
3. Perfil comportamental ideal (DISC / competências)
4. Faixa salarial de mercado (referência interior SP/Brasil)
5. Canais de recrutamento recomendados
6. Roteiro de entrevista com perguntas situacionais
7. Processo de integração dos primeiros 30 dias

Formato estruturado obrigatório.
"""
        return await self.call_claude(user_message=prompt)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _fetch_team_overview(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT u.code, u.name, u.city, u.format,
                   u.team_count, u.manager_name, u.color_status,
                   ROUND(AVG(dk.nps_score)::numeric, 1) AS avg_nps_30d
            FROM units u
            LEFT JOIN unit_daily_kpis dk
                   ON dk.unit_id = u.id
                  AND dk.date >= CURRENT_DATE - INTERVAL '30 days'
            WHERE u.status = 'ativa'
            GROUP BY u.id, u.code, u.name, u.city,
                     u.format, u.team_count, u.manager_name, u.color_status
            ORDER BY u.team_count ASC
            """
        )
        return self.format_db_data(rows, title="Visão Geral de Equipes")

    async def _identify_understaffed_units(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT u.code, u.name, u.city, u.format,
                   u.team_count,
                   CASE u.format
                       WHEN 'quiosque'    THEN 2
                       WHEN 'flagship'   THEN 7
                       ELSE 4
                   END AS team_min_required
            FROM units u
            WHERE u.status = 'ativa'
              AND u.team_count < CASE u.format
                                     WHEN 'quiosque'  THEN 2
                                     WHEN 'flagship'  THEN 7
                                     ELSE 4
                                 END
            ORDER BY u.team_count ASC
            """
        )
        return self.format_db_data(rows, title="Unidades Subdimensionadas")

    async def _fetch_top_performing_units(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT u.code, u.name, u.city, u.format,
                   u.team_count, u.manager_name,
                   ROUND(AVG(dk.nps_score)::numeric, 1)    AS avg_nps,
                   ROUND(AVG(dk.gross_revenue)::numeric, 2) AS avg_daily_revenue
            FROM units u
            JOIN unit_daily_kpis dk ON dk.unit_id = u.id
                AND dk.date >= CURRENT_DATE - INTERVAL '30 days'
            WHERE u.status = 'ativa'
            GROUP BY u.id, u.code, u.name, u.city,
                     u.format, u.team_count, u.manager_name
            ORDER BY avg_nps DESC NULLS LAST
            LIMIT 5
            """
        )
        return self.format_db_data(rows, title="Top 5 Unidades por NPS (referência)")

    async def _fetch_hr_alerts(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT a.severity, a.title, a.description,
                   a.metric_value, a.threshold_value,
                   u.code AS unit_code, u.name AS unit_name
            FROM alerts a
            JOIN units u ON u.id = a.unit_id
            WHERE a.is_active = TRUE
              AND a.category = 'hr'
            ORDER BY a.severity DESC, a.id DESC
            LIMIT 20
            """
        )
        return self.format_db_data(rows, title="Alertas de RH Ativos")
