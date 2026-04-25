# =============================================================================
# ROUTER.PY — Frank AI OS
# Roteador de perguntas para o diretor correto
# =============================================================================

from __future__ import annotations

import json
import logging
from typing import Dict, Optional

import anthropic

from config import ANTHROPIC_API_KEY, MODEL_FAST

logger = logging.getLogger("frank.router")

DIRECTOR_MAP = {
    "CFO":    "Finanças: DRE, CMV, fluxo de caixa, royalties, valuation, budget, impostos",
    "COO":    "Operações: lojas, qualidade, auditoria, performance, equipe, processos",
    "CMO":    "Marketing: campanhas, redes sociais, mídia paga, conteúdo, CRM, B2C",
    "CSO":    "Expansão: novos franqueados, leads B2B, novos mercados, ROI de unidades",
    "Supply": "Supply Chain: fornecedores, compras, estoque, insumos, pedidos",
    "OPEP":   "Operações de Expansão: implantação, treinamento, franquia operacional",
    "Legal":  "Jurídico: contratos, COF, compliance, regulatório",
    "BI":     "Dados: dashboards, KPIs, alertas, forecasts, análises",
    "Frank":  "Estratégia: questões cross-funcionais, visão CEO",
}

ROUTING_PROMPT = """Classifique a pergunta e retorne JSON com o diretor responsável.

Diretores disponíveis:
""" + "\n".join(f"- {k}: {v}" for k, v in DIRECTOR_MAP.items()) + """

Retorne APENAS JSON:
{
  "director": "<nome>",
  "confidence": <0.0-1.0>,
  "keywords": ["palavra1", "palavra2"],
  "reason": "justificativa em 1 frase"
}"""


class Router:
    """Roteador de perguntas usando LLM leve (Haiku)."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self._keyword_map = self._build_keyword_map()

    def _build_keyword_map(self) -> Dict[str, list]:
        """Mapa de palavras-chave para roteamento rápido sem LLM."""
        return {
            "CFO": [
                "cmv", "dre", "faturamento", "receita", "custo", "financeiro",
                "caixa", "fluxo", "royalt", "budget", "orçamento", "ebitda",
                "margem", "lucro", "valuation", "payback", "roi", "imposto",
            ],
            "COO": [
                "loja", "unidade", "operação", "qualidade", "auditoria", "vistoria",
                "equipe", "processo", "performance", "produtividade", "ticket",
                "cx", "cliente", "atendimento", "nps", "ruptura", "estoque",
            ],
            "CMO": [
                "marketing", "campanha", "anúncio", "post", "instagram", "facebook",
                "mídia", "conteúdo", "crm", "cliente", "b2c", "promoção",
                "influencer", "branding", "evento",
            ],
            "CSO": [
                "expansão", "franqueado", "nova loja", "lead", "prospecção",
                "mercado", "cidade", "inauguração", "contrato de franquia",
            ],
            "Supply": [
                "fornecedor", "compra", "pedido", "insumo", "matéria", "entrega",
                "supply", "estoque", "inventário", "preço", "cotação",
            ],
            "OPEP": [
                "implantação", "treinamento", "onboarding", "manual", "processo",
                "franquia operacional", "inaugurar", "abertura",
            ],
            "Legal": [
                "contrato", "jurídico", "legal", "compliance", "cof", "regulat",
                "lei", "multa", "rescisão", "renovação",
            ],
            "BI": [
                "dashboard", "kpi", "alerta", "forecast", "previsão", "relatório",
                "análise", "dados", "indicador", "meta", "gráfico",
            ],
        }

    def route_by_keywords(self, question: str) -> Optional[str]:
        """Tenta rotear apenas por palavras-chave (sem LLM)."""
        q = question.lower()
        scores = {dir_: 0 for dir_ in self._keyword_map}
        for dir_, keywords in self._keyword_map.items():
            for kw in keywords:
                if kw in q:
                    scores[dir_] += 1
        best = max(scores, key=scores.get)
        if scores[best] >= 2:
            return best
        return None

    async def route(self, question: str) -> Dict:
        """Roteia usando keyword match primeiro, depois LLM se necessário."""
        # Tenta keyword match rápido
        quick = self.route_by_keywords(question)
        if quick:
            return {
                "director": quick,
                "confidence": 0.8,
                "keywords": [],
                "method": "keywords",
            }

        # Usa LLM para casos ambíguos
        try:
            msg = await self.client.messages.create(
                model=MODEL_FAST,
                max_tokens=200,
                system=ROUTING_PROMPT,
                messages=[{"role": "user", "content": question}],
            )
            text = msg.content[0].text.strip()
            if "```" in text:
                text = text.split("```")[1].lstrip("json").strip()
            result = json.loads(text)
            result["method"] = "llm"
            return result
        except Exception as e:
            logger.warning(f"Router LLM fallback: {e}")
            return {
                "director": "Frank",
                "confidence": 0.4,
                "keywords": [],
                "method": "fallback",
            }

    def route_sync(self, question: str):
        """
        Versão síncrona do roteador — retorna instância do Director do setor correto.
        Usado pelo CEO CLI (main_cli.py).
        """
        from sectors.finance.main      import FinanceDirector
        from sectors.marketing.main    import MarketingDirector
        from sectors.operations.main   import OperationsDirector
        from sectors.legal.main        import LegalDirector
        from sectors.hr_training.main  import HRDirector
        from sectors.expansion.main    import ExpansionDirector
        from sectors.supply_chain.main import SupplyDirector
        from sectors.deployment.main   import DeploymentDirector
        from sectors.intelligence.main import IntelligenceDirector
        from sectors.projects.main     import ProjectDirector

        q = question.lower()

        if any(kw in q for kw in ["financ", "cmv", "dre", "faturamento", "receita", "custo", "caixa", "budget", "orçamento", "ebitda", "royalt", "margem", "lucro"]):
            return FinanceDirector()
        elif any(kw in q for kw in ["marketing", "campanha", "anúncio", "instagram", "redes sociais", "mídia", "b2c", "crm", "promoção"]):
            return MarketingDirector()
        elif any(kw in q for kw in ["loja", "operação", "operacional", "qualidade", "auditoria", "nps", "atendimento", "ticket", "performance", "produtividade"]):
            return OperationsDirector()
        elif any(kw in q for kw in ["contrato", "jurídico", "legal", "compliance", "cof", "lei", "multa"]):
            return LegalDirector()
        elif any(kw in q for kw in ["treinamento", "rh", "equipe", "pessoal", "onboarding", "hr"]):
            return HRDirector()
        elif any(kw in q for kw in ["expansão", "franquia", "nova loja", "lead b2b", "crescimento", "abertura"]):
            return ExpansionDirector()
        elif any(kw in q for kw in ["fornecedor", "estoque", "compra", "insumo", "supply", "ruptura", "pedido"]):
            return SupplyDirector()
        elif any(kw in q for kw in ["implantação", "obra", "inauguração", "abertura", "deploy"]):
            return DeploymentDirector()
        elif any(kw in q for kw in ["dados", "kpi", "insight", "dashboard", "alerta", "forecast", "previsão", "bi", "relatório"]):
            return IntelligenceDirector()
        elif any(kw in q for kw in ["projeto", "iniciativa", "estratégia", "cross"]):
            return ProjectDirector()
        else:
            return IntelligenceDirector()  # default: BI responde

    async def close(self):
        await self.client.close()
