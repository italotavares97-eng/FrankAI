"""
Contract Agent — Gestão do Ciclo de Vida dos Contratos de Franquia
COF, renovações, aditivos e monitoramento de vencimentos.
"""

import json
import logging
from datetime import date, timedelta
from typing import Any

from core.base_agent import BaseAgent
from config import MODEL_AGENT

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Você é o Especialista em Contratos de Franquia da Davvero Gelato,
com profundo conhecimento da Lei 13.966/2019 e do mercado de franquias brasileiro.

ESPECIALIDADES:
1. COF (Circular de Oferta de Franquia)
   - Requisitos obrigatórios do Art. 2º da Lei 13.966/2019
   - Prazo de entrega: mínimo 10 dias antes da assinatura
   - Conteúdo: histórico, balanços, litigiosidade, taxas, território, etc.
   - Atualização anual obrigatória

2. CONTRATOS DE FRANQUIA
   - Prazo de vigência (padrão Davvero: 5 anos, renovável)
   - Royalties (% sobre faturamento bruto)
   - Fundo de marketing (% sobre faturamento bruto)
   - Território e exclusividade
   - Obrigações do franqueado e franqueador
   - Cláusulas de rescisão e transferência

3. RENOVAÇÕES E ADITIVOS
   - Checklist de pré-renovação (12 meses antes)
   - Atualização de taxas e condições
   - Adaptações regulatórias

4. MONITORAMENTO
   - Alertas de vencimento (12, 6, 3 meses)
   - Contratos em risco (inadimplência, litígio)
   - Score de saúde contratual por franqueado

REQUISITOS COF (Lei 13.966/2019 — Art. 2º):
- I: histórico e experiência do franqueador
- II: balanços e demonstrações financeiras (últimos 2 anos)
- III: indicação de pendências judiciais
- IV: descrição detalhada da franquia
- V: perfil do franqueado ideal
- VI: requisitos de infraestrutura e localização
- VII: informações sobre treinamento
- VIII: layout e design (se obrigatório)
- IX: lista de fornecedores exclusivos
- X: território e exclusividade
- XI: remuneração e taxas
- XII: sublicença de propriedade intelectual
- XIII: obrigações pós-contrato
- XIV: modelo do contrato

Formato de resposta:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO"""


class ContractAgent(BaseAgent):
    """
    Manages franchise contract lifecycle: COF review, expiry monitoring,
    renewal process, and contract health scoring.
    """

    # Alert thresholds in days
    CRITICAL_THRESHOLD_DAYS = 90
    WARNING_THRESHOLD_DAYS = 180
    WATCH_THRESHOLD_DAYS = 365

    def __init__(self):
        super().__init__(
            agent_name="ContractAgent",
            model=MODEL_AGENT,
            system_prompt=SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        """
        Identify expiring contracts (< 6 months) and generate contract analysis.
        """
        logger.info(f"[ContractAgent] analyze called | query={query[:80]!r}")

        active_contracts = await self._fetch_active_contracts()
        expiring_critical = await self._fetch_expiring_contracts(self.CRITICAL_THRESHOLD_DAYS)
        expiring_warning = await self._fetch_expiring_contracts(self.WARNING_THRESHOLD_DAYS)
        expired = await self._fetch_expired_contracts()
        royalty_analysis = await self._fetch_royalty_analysis()

        prompt = f"""
CONSULTA CONTRATUAL: {query}

=== CONTRATOS ATIVOS — VISÃO GERAL ===
{active_contracts}

=== CONTRATOS CRÍTICOS (< 90 DIAS PARA VENCIMENTO) ===
{expiring_critical}

=== CONTRATOS DE ATENÇÃO (< 180 DIAS PARA VENCIMENTO) ===
{expiring_warning}

=== CONTRATOS VENCIDOS / IRREGULARES ===
{expired}

=== ANÁLISE DE ROYALTIES ===
{royalty_analysis}

Com base nesses dados, forneça:
1. Status consolidado do portfólio de contratos
2. Priorização de ações por urgência:
   - Crítico (< 90 dias): ação imediata de renovação
   - Atenção (90-180 dias): iniciar processo de renovação
   - Monitoramento (180-365 dias): comunicar franqueado
3. Roteiro de renovação por franqueado (etapas, prazos, documentos)
4. Riscos contratuais identificados
5. Checklist de atualização do COF se necessário

Responda no formato estruturado completo:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""
        response = await self.call_claude(user_message=prompt)
        logger.info("[ContractAgent] analyze completed")
        return response

    # ------------------------------------------------------------------
    # COF review
    # ------------------------------------------------------------------

    async def cof_review(self) -> str:
        """Assess the current COF against Lei 13.966/2019 requirements."""
        contracts_overview = await self._fetch_active_contracts()

        prompt = f"""
REVISÃO DA COF (CIRCULAR DE OFERTA DE FRANQUIA) — DAVVERO GELATO

REQUISITOS OBRIGATÓRIOS — LEI 13.966/2019 (Art. 2º):
I.   Histórico e experiência do franqueador (mínimo 2 anos)
II.  Balanços e DRE dos últimos 2 exercícios
III. Pendências judiciais do franqueador, seus diretores e gestores
IV.  Descrição detalhada da franquia
V.   Perfil do franqueado ideal
VI.  Requisitos de ponto comercial e infraestrutura
VII. Informações completas sobre treinamento inicial e continuado
VIII. Layout e design (se padronizados)
IX.  Lista completa de fornecedores exclusivos ou indicados
X.   Território e critérios de exclusividade
XI.  Remuneração ao franqueador (taxas, royalties, fundo de marketing)
XII. Sublicenciamento de propriedade intelectual
XIII. Situação do franqueado pós-contrato (não-concorrência, etc.)
XIV. Modelo do contrato de franquia e eventuais aditivos

PRAZO LEGAL: COF deve ser entregue ao candidato com no mínimo 10 dias
              de antecedência à assinatura do contrato ou pagamento.

ATUALIZAÇÃO: Obrigatória anualmente (Art. 2º, §2º).

CONTRATOS ATIVOS NA REDE:
{contracts_overview}

Realize uma análise de conformidade da COF incluindo:
1. Checklist de todos os 14 requisitos do Art. 2º
2. Pontos de atenção e lacunas mais comuns
3. Recomendações de atualização para o exercício atual
4. Riscos de nulidade contratual por COF inadequada
5. Modelo de cronograma de atualização anual

Responda no formato estruturado.
"""
        return await self.call_claude(user_message=prompt)

    async def renewal_package(self, franchisee_id: int) -> str:
        """Generate a complete renewal package for a specific franchisee."""
        franchisee = await self.db_fetchrow(
            "SELECT * FROM franchisees WHERE id = $1", franchisee_id
        )
        if not franchisee:
            return f"Franqueado ID {franchisee_id} não encontrado."

        units = await self.db_fetch(
            """
            SELECT u.code, u.name, u.city, u.format, u.status,
                   u.opening_date, u.color_status
            FROM units u
            JOIN franchisees f ON f.id = $1
            WHERE u.status NOT IN ('encerrada', 'transferida')
            LIMIT 10
            """,
            franchisee_id,
        )
        units_text = self.format_db_data(units, title="Unidades do Franqueado")

        contract_end = franchisee.get("contract_end")
        days_to_expiry = (contract_end - date.today()).days if contract_end else None

        prompt = f"""
PACOTE DE RENOVAÇÃO — FRANQUEADO: {franchisee.get('name')}
Email: {franchisee.get('email')}
Contrato: {franchisee.get('contract_start')} → {franchisee.get('contract_end')}
Royalty atual: {franchisee.get('royalty_pct')}%
Status: {franchisee.get('status')}
Dias para vencimento: {days_to_expiry}

{units_text}

Gere o Pacote de Renovação completo:
1. Carta de renovação formal (texto pronto)
2. Checklist de documentos necessários para renovação
3. Proposta de novas condições (taxas, prazo, território)
4. Cronograma do processo de renovação (marcos e responsáveis)
5. Cláusulas de atualização recomendadas
6. Roteiro da reunião de renovação com o franqueado
7. Aviso: validar com advogado (OAB) antes de enviar

Urgência: {'CRÍTICA — menos de 90 dias!' if days_to_expiry and days_to_expiry < 90 else 'Normal'}

Formato estruturado completo.
"""
        return await self.call_claude(user_message=prompt)

    async def contract_health_score(self, franchisee_id: int) -> dict[str, Any]:
        """Calculate a contract health score (0-100) for a franchisee."""
        franchisee = await self.db_fetchrow(
            "SELECT * FROM franchisees WHERE id = $1", franchisee_id
        )
        if not franchisee:
            return {"error": f"Franqueado {franchisee_id} não encontrado"}

        contract_end = franchisee.get("contract_end")
        today = date.today()
        days_to_expiry = (contract_end - today).days if contract_end else 0

        score = 100
        issues = []

        # Deduct for expiry proximity
        if days_to_expiry < 0:
            score -= 40
            issues.append("Contrato vencido")
        elif days_to_expiry < 90:
            score -= 30
            issues.append(f"Contrato vence em {days_to_expiry} dias (crítico)")
        elif days_to_expiry < 180:
            score -= 15
            issues.append(f"Contrato vence em {days_to_expiry} dias (atenção)")
        elif days_to_expiry < 365:
            score -= 5
            issues.append(f"Contrato vence em {days_to_expiry} dias (monitoramento)")

        # Check franchisee status
        if franchisee.get("status") != "ativo":
            score -= 20
            issues.append(f"Status irregular: {franchisee.get('status')}")

        # Check royalty rate (flag if zero or null)
        if not franchisee.get("royalty_pct"):
            score -= 10
            issues.append("Royalty não configurado")

        return {
            "franchisee_id": franchisee_id,
            "franchisee_name": franchisee.get("name"),
            "contract_health_score": max(0, score),
            "days_to_expiry": days_to_expiry,
            "issues": issues,
            "classification": (
                "saudável" if score >= 80
                else "atenção" if score >= 60
                else "crítico"
            ),
        }

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _fetch_active_contracts(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT f.name, f.email, f.status,
                   f.contract_start, f.contract_end,
                   f.royalty_pct,
                   (f.contract_end - CURRENT_DATE) AS days_to_expiry
            FROM franchisees f
            WHERE f.status IN ('ativo', 'em_renovacao', 'inadimplente')
            ORDER BY f.contract_end ASC
            """
        )
        return self.format_db_data(rows, title="Contratos Ativos")

    async def _fetch_expiring_contracts(self, within_days: int) -> str:
        rows = await self.db_fetch(
            """
            SELECT f.name, f.email, f.status,
                   f.contract_start, f.contract_end,
                   f.royalty_pct,
                   (f.contract_end - CURRENT_DATE) AS days_to_expiry
            FROM franchisees f
            WHERE f.status = 'ativo'
              AND f.contract_end BETWEEN CURRENT_DATE AND CURRENT_DATE + ($1 || ' days')::INTERVAL
            ORDER BY f.contract_end ASC
            """,
            str(within_days),
        )
        return self.format_db_data(
            rows, title=f"Contratos Expirando em até {within_days} dias"
        )

    async def _fetch_expired_contracts(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT f.name, f.email, f.status,
                   f.contract_end,
                   (CURRENT_DATE - f.contract_end) AS days_overdue
            FROM franchisees f
            WHERE f.contract_end < CURRENT_DATE
              AND f.status != 'encerrado'
            ORDER BY days_overdue DESC
            """
        )
        return self.format_db_data(rows, title="Contratos Vencidos / Irregulares")

    async def _fetch_royalty_analysis(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT f.name,
                   f.royalty_pct,
                   ROUND(AVG(uf.net_revenue)::numeric, 2) AS avg_monthly_revenue,
                   ROUND(AVG(uf.net_revenue * f.royalty_pct / 100)::numeric, 2) AS avg_monthly_royalty
            FROM franchisees f
            JOIN units u ON TRUE  -- simplified join; adjust if franchisee_id exists in units
            JOIN unit_financials uf ON uf.unit_id = u.id
            WHERE f.status = 'ativo'
            GROUP BY f.id, f.name, f.royalty_pct
            ORDER BY avg_monthly_royalty DESC
            LIMIT 20
            """
        )
        return self.format_db_data(rows, title="Análise de Royalties por Franqueado")
