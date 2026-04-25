# =============================================================================
# SUPPLY_DIRECTOR.PY — Frank AI OS · Supply Chain Sector
# Diretor de Supply Chain
# =============================================================================

from __future__ import annotations
from typing import Dict, Optional
from core.base_agent import BaseAgent
from config import MODEL_MASTER


class SupplyDirector(BaseAgent):
    AGENT_NAME = "Supply Director"
    AGENT_ROLE = "Diretor de Supply Chain"
    DIRECTOR   = "Supply"
    MODEL      = MODEL_MASTER

    SYSTEM_PROMPT = """Você é o Diretor de Supply Chain do Frank AI OS — Davvero Gelato.

MISSÃO:
Garantir a cadeia de suprimentos da rede: fornecedores estratégicos,
estoque adequado, CMV controlado e zero ruptura nas lojas.

RESPONSABILIDADES:
• Gestão de fornecedores (leite, creme, frutas, embalagens, insumos)
• Controle de CMV via negociação e fichas técnicas
• Prevenção de rupturas (stockout) nas lojas
• Pedidos de compra e rastreamento de entregas
• Avaliação de fornecedores (qualidade, preço, prazo, confiabilidade)
• Negociação de bonificações e melhores condições

KPIs CHAVE:
• CMV meta: 26,5% (vantagem competitiva central)
• Cobertura de estoque: mínimo 15 dias
• Lead time máximo fornecedor: 5 dias
• Ruptura máxima: 2 itens/dia/loja
• Score mínimo fornecedor estratégico: 80/100
"""

    def __init__(self):
        super().__init__()
        from procurement_agent import ProcurementAgent
        from inventory_agent   import InventoryAgent
        self.procurement = ProcurementAgent()
        self.inventory   = InventoryAgent()

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        q = question.lower()
        agent = None

        if any(kw in q for kw in ["estoque", "ruptura", "falta", "inventário", "reposição"]):
            agent = self.inventory
        elif any(kw in q for kw in ["fornecedor", "compra", "pedido", "cotação", "negociação", "cmv"]):
            agent = self.procurement
        else:
            agent = self.procurement  # default

        agent.db_pool      = self.db_pool
        agent.redis_client = self.redis_client
        return await agent.analyze(question, user, kpi_context, extra_context)
