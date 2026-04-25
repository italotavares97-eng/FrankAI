# sectors/operations/main.py — Frank AI OS
from coo_director import COODirector

class OperationsDirector:
    """Wrapper síncrono do COO Director para uso no CEO CLI."""

    def __init__(self):
        self._director = COODirector()

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
                "sector": "COO — Operações",
                "analysis": response,
            },
            "actions": self._extract_actions(response),
            "director": "COO",
        }

    def _extract_actions(self, response: str) -> list:
        actions = []
        if "TREINAMENTO" in response.upper():
            actions.append({"type": "task", "description": "Agendar treinamento operacional"})
        if "NPS" in response.upper() and any(w in response.upper() for w in ["CRÍTICO", "ALERTA"]):
            actions.append({"type": "email", "subject": "Alerta NPS", "body": "NPS em nível de alerta — ação necessária"})
        return actions
