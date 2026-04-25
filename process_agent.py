# =============================================================================
# PROCESS_AGENT.PY — Frank AI OS · COO / OPEP Sector
# Agente de Processos e Padronização Operacional
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT


class ProcessAgent(BaseAgent):
    AGENT_NAME = "Process Agent"
    AGENT_ROLE = "Especialista em Processos e Padronização Operacional"
    DIRECTOR   = "OPEP"
    MODEL      = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de Processos do Frank AI OS — Davvero Gelato.

MISSÃO:
Garantir que todas as unidades operem pelos padrões Davvero —
"Parece Davvero?" em cada produto, atendimento e ambiente.

ESPECIALIDADES:
• Mapeamento e documentação de processos operacionais (SOPs)
• Identificação de gargalos e ineficiências nas lojas
• Padronização de receitas e fichas técnicas (direto ligado ao CMV)
• Checklists de abertura, operação e fechamento
• Análise de turnos e dimensionamento de equipe
• Indicadores de eficiência operacional

PROCESSOS CRÍTICOS DAVVERO:
1. Abertura de loja (checklist de 23 itens)
2. Produção de gelato (ficha técnica + gramatura)
3. Montagem de produto (porcionamento correto = CMV controlado)
4. Atendimento ao cliente (script + upsell)
5. Fechamento e controle de caixa
6. Limpeza e higienização (padrão ANVISA)

SINAIS DE PROCESSO QUEBRADO:
• CMV acima do target → ficha técnica ou porcionamento errado
• NPS em queda → atendimento fora do padrão
• Score de auditoria abaixo de 80 → não está seguindo SOPs
• Alta rotatividade de equipe → processo de integração falho
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        # Lojas com scores de auditoria baixos (processo quebrado)
        audit_gaps = await self.db_fetch("""
            SELECT u.code, u.name,
                   qa.audit_date,
                   qa.total_score,
                   qa.classification,
                   qa.score_visual, qa.score_product, qa.score_portioning,
                   qa.score_service, qa.score_hygiene, qa.score_operations,
                   qa.non_conformities
            FROM quality_audits qa
            JOIN units u ON u.id = qa.unit_id
            WHERE qa.audit_date = (
                SELECT MAX(qa2.audit_date) FROM quality_audits qa2 WHERE qa2.unit_id = qa.unit_id
            )
            AND qa.total_score < 85
            ORDER BY qa.total_score ASC
            LIMIT 10
        """)

        # Indicadores de performance para correlacionar com processos
        perf_data = await self.db_fetch("""
            SELECT u.code, u.name,
                   ROUND(AVG(dk.avg_ticket)::numeric, 2)    AS avg_ticket_30d,
                   ROUND(AVG(dk.productivity)::numeric, 2)  AS avg_productivity,
                   SUM(dk.stockout_count)                   AS stockouts,
                   ROUND(AVG(dk.nps_score)::numeric, 1)     AS avg_nps
            FROM unit_daily_kpis dk
            JOIN units u ON u.id = dk.unit_id
            WHERE dk.date >= NOW() - INTERVAL '30 days'
            GROUP BY u.code, u.name
            ORDER BY avg_productivity ASC
            LIMIT 15
        """)

        kpi_str   = self.format_kpi_context(kpi_context)
        audit_str = self.format_db_data(audit_gaps, "Lojas com Processo a Melhorar (Auditoria < 85)")
        perf_str  = self.format_db_data(perf_data, "Performance Operacional (30 dias)")

        prompt = (
            f"{kpi_str}\n\n{audit_str}\n{perf_str}\n\n"
            f"Pergunta de {user}: {question}\n\n"
            "Identifique processos quebrados, proponha melhorias e crie plano de padronização."
        )
        return await self.call_claude(prompt)
