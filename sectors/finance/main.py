# sectors/finance/main.py — Frank AI OS
from cfo_director import CFODirector

class FinanceDirector:
    """Wrapper síncrono do CFO Director para uso no CEO CLI."""

    def __init__(self):
        self._director = CFODirector()

    def process(self, query: str) -> dict:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            self._director.analyze(question=query, user="CEO")
        )
        return {
            "data": {
                "sector": "CFO — Financeiro",
                "analysis": response,
            },
            "actions": self._extract_actions(response),
            "director": "CFO",
        }

    def _extract_actions(self, response: str) -> list:
        actions = []
        if "EXECUTAR" in response.upper():
            actions.append({"type": "task", "description": f"Ação CFO aprovada — ver análise completa"})
        if "CMV" in response.upper() and "CRÍTICO" in response.upper():
            actions.append({"type": "whatsapp", "message": "⚠️ Alerta CMV Crítico — Frank AI OS"})
        return actions
