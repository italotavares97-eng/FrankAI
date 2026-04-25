# =============================================================================
# PROCUREMENT_AGENT.PY — Frank AI OS · Supply Chain
# Agente de Compras e Gestão de Fornecedores
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT


class ProcurementAgent(BaseAgent):
    AGENT_NAME = "Procurement Agent"
    AGENT_ROLE = "Especialista em Compras e Fornecedores"
    DIRECTOR   = "Supply"
    MODEL      = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de Compras do Frank AI OS — Davvero Gelato.

MISSÃO:
Gerenciar fornecedores, negociar melhores condições e garantir que o
CMV da rede permaneça no target de 26,5%.

ESPECIALIDADES:
• Avaliação e homologação de fornecedores
• Negociação de preços, bonificações e prazos de pagamento
• Análise de impacto de preços no CMV
• Gestão de pedidos de compra e rastreamento de entregas
• Identificação de fornecedores backup para itens críticos
• Análise de custo-benefício (preço vs. qualidade vs. prazo)

CATEGORIAS PRINCIPAIS:
• Lácteos: leite integral, creme, manteiga (impacto alto no CMV)
• Frutas e polpas (fresh e congeladas)
• Embalagens: copos, colheres, tampas
• Insumos secos: açúcar, cacau, nuts, coberturas
• Higiene e limpeza

INDICADORES:
• Score fornecedor = (qualidade 40% + preço 30% + prazo 20% + atendimento 10%)
• Fornecedor estratégico: score ≥ 80 + is_strategic = true
• Alerta: lead_time > 5 dias ou score < 70
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        suppliers = await self.db_fetch("""
            SELECT name, category, score, quality_score, price_score,
                   delivery_score, payment_terms, lead_time_days,
                   status, is_strategic, is_backup
            FROM suppliers
            WHERE status = 'ativo'
            ORDER BY score DESC
            LIMIT 20
        """)

        recent_orders = await self.db_fetch("""
            SELECT s.name AS supplier, po.status, po.order_date,
                   po.expected_date, po.delivered_date,
                   po.total_value,
                   CASE WHEN po.delivered_date > po.expected_date THEN 'ATRASADO' ELSE 'OK' END AS delivery_status
            FROM purchase_orders po
            JOIN suppliers s ON s.id = po.supplier_id
            WHERE po.order_date >= NOW() - INTERVAL '30 days'
            ORDER BY po.order_date DESC
            LIMIT 15
        """)

        low_score = [s for s in suppliers if (s.get("score") or 0) < 70]

        kpi_str       = self.format_kpi_context(kpi_context)
        supplier_str  = self.format_db_data(suppliers, "Fornecedores Ativos")
        orders_str    = self.format_db_data(recent_orders, "Pedidos Últimos 30 Dias")
        alert_str     = ""
        if low_score:
            alert_str = f"\n⚠️ FORNECEDORES COM SCORE BAIXO: {[s['name'] for s in low_score]}"

        prompt = (
            f"{kpi_str}\n\n{supplier_str}\n{orders_str}{alert_str}\n\n"
            f"Pergunta de {user}: {question}"
        )
        return await self.call_claude(prompt)
