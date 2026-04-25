# =============================================================================
# COMPLIANCE_AGENT.PY — Frank AI OS · Legal Sector
# Agente de Compliance e Risco Regulatório
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT


class ComplianceAgent(BaseAgent):
    AGENT_NAME = "Compliance Agent"
    AGENT_ROLE = "Especialista em Compliance e Risco Regulatório"
    DIRECTOR   = "Legal"
    MODEL      = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de Compliance do Frank AI OS — Davvero Gelato.

MISSÃO:
Garantir que a rede Davvero opere em total conformidade legal,
regulatória e ética — prevenindo riscos antes que se tornem problemas.

ESPECIALIDADES:
• Lei de Franquias Brasileira (Lei 13.966/2019)
• Circular de Oferta de Franquia (COF) — requisitos e atualização anual
• ANVISA — boas práticas de fabricação e manipulação de alimentos
• Vigilância Sanitária — alvarás, licenças e vistorias
• LGPD — proteção de dados de clientes e franqueados
• Código de Defesa do Consumidor (CDC)
• Relações trabalhistas — CLT, pró-labore, funcionários de lojas

CHECKLIST DE COMPLIANCE:
✅ COF atualizada (obrigatório a cada ano ou mudança relevante)
✅ Contrato de Franquia dentro da lei 13.966/2019
✅ Alvará sanitário vigente em todas as unidades
✅ LGPD: política de privacidade e consentimento de dados
✅ Seguro obrigatório das lojas
✅ Registro de marca INPI vigente

ALERTAS CRÍTICOS:
• Alvará vencido → RISCO IMEDIATO de interdição
• COF desatualizada → RISCO de anulação do contrato de franquia
• Denúncia de consumidor → prazo de resposta 5 dias úteis
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        # Contratos próximos do vencimento
        expiring = await self.db_fetch("""
            SELECT name, email, contract_start, contract_end,
                   (contract_end - CURRENT_DATE) AS days_to_expiry,
                   status
            FROM franchisees
            WHERE contract_end IS NOT NULL
              AND contract_end <= CURRENT_DATE + INTERVAL '180 days'
              AND status = 'ativo'
            ORDER BY contract_end ASC
        """)

        # Unidades sem dados recentes (possível problema operacional/compliance)
        inactive_units = await self.db_fetch("""
            SELECT u.code, u.name, u.city, u.status,
                   MAX(dk.date) AS last_kpi_date,
                   (CURRENT_DATE - MAX(dk.date)) AS days_since_last_report
            FROM units u
            LEFT JOIN unit_daily_kpis dk ON dk.unit_id = u.id
            WHERE u.status = 'ativo'
            GROUP BY u.code, u.name, u.city, u.status
            HAVING MAX(dk.date) < CURRENT_DATE - INTERVAL '7 days'
                OR MAX(dk.date) IS NULL
            ORDER BY days_since_last_report DESC NULLS FIRST
            LIMIT 10
        """)

        kpi_str     = self.format_kpi_context(kpi_context)
        expiry_str  = self.format_db_data(expiring, "Contratos Expirando (≤180 dias)")
        inactive_str= self.format_db_data(inactive_units, "Unidades sem Reporte Recente")

        prompt = (
            f"{kpi_str}\n\n{expiry_str}\n{inactive_str}\n\n"
            f"Pergunta de {user}: {question}\n\n"
            "Avalie riscos de compliance, identifique não-conformidades e gere plano de ação."
        )
        return await self.call_claude(prompt)
