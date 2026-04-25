# =============================================================================
# INVENTORY_AGENT.PY — Frank AI OS · Supply Chain
# Agente de Gestão de Estoque
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT, OPERATIONAL_TARGETS


class InventoryAgent(BaseAgent):
    AGENT_NAME = "Inventory Agent"
    AGENT_ROLE = "Especialista em Estoque e Prevenção de Rupturas"
    DIRECTOR   = "Supply"
    MODEL      = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de Estoque do Frank AI OS — Davvero Gelato.

MISSÃO:
Garantir que todas as lojas tenham os insumos necessários,
evitando rupturas (stockouts) e desperdícios.

ESPECIALIDADES:
• Monitoramento de estoque mínimo por loja
• Alertas de reposição automática (trigger: qty ≤ min_qty)
• Análise de giro de estoque e sazonalidade
• Controle de FIFO e prazo de validade
• Cálculo de reorder point (ROP = demanda diária × lead time + estoque segurança)
• Gestão de desperdício — impacto direto no CMV

FÓRMULAS CHAVE:
• Cobertura = estoque_atual / consumo_diário_médio (meta: ≥ 15 dias)
• Ponto de pedido = consumo_diário × lead_time_fornecedor + estoque_segurança
• Desperdício aceitável: < 2% do CMV

AÇÕES AUTOMÁTICAS:
• Qty ≤ min_qty → gerar alerta de reposição
• Qty ≤ 0 → CRÍTICO, bloquear abertura do turno
• Desperdício semanal > R$500 → investigação obrigatória
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        # Estoque geral da rede
        low_stock = await self.db_fetch("""
            SELECT u.code AS loja, u.name AS nome_loja,
                   i.product_name, i.sku, i.current_qty, i.min_qty,
                   i.unit,
                   CASE WHEN i.current_qty <= 0 THEN 'CRÍTICO — ZERADO'
                        WHEN i.current_qty <= i.min_qty THEN 'ALERTA — ABAIXO MÍNIMO'
                        ELSE 'OK'
                   END AS status
            FROM inventory i
            JOIN units u ON u.id = i.unit_id
            WHERE i.current_qty <= i.min_qty * 1.2  -- 20% acima do mínimo para antecipar
            ORDER BY i.current_qty ASC
            LIMIT 30
        """)

        waste_data = await self.db_fetch("""
            SELECT u.code, u.name,
                   SUM(dk.waste_value)  AS waste_30d,
                   SUM(dk.stockout_count) AS stockouts_30d,
                   ROUND(AVG(dk.waste_value),2) AS avg_daily_waste
            FROM unit_daily_kpis dk
            JOIN units u ON u.id = dk.unit_id
            WHERE dk.date >= NOW() - INTERVAL '30 days'
            GROUP BY u.code, u.name
            HAVING SUM(dk.waste_value) > 0 OR SUM(dk.stockout_count) > 0
            ORDER BY waste_30d DESC
            LIMIT 15
        """)

        kpi_str   = self.format_kpi_context(kpi_context)
        stock_str = self.format_db_data(low_stock, "Itens com Estoque Baixo ou Crítico")
        waste_str = self.format_db_data(waste_data, "Desperdício e Rupturas (30 dias)")

        cover_days = OPERATIONAL_TARGETS.get("inventory_cover_days", 15)
        prompt = (
            f"{kpi_str}\n\n{stock_str}\n{waste_str}\n\n"
            f"Meta de cobertura de estoque: {cover_days} dias\n"
            f"Ruptura máxima permitida: {OPERATIONAL_TARGETS.get('stockout_max_day', 2)}/dia\n\n"
            f"Pergunta de {user}: {question}"
        )
        return await self.call_claude(prompt)
