# sectors/marketing/main.py — Frank AI OS
from cmo_director import CMODirector

class MarketingDirector:
    """Wrapper síncrono do CMO Director para uso no CEO CLI."""

    def __init__(self):
        self._director = CMODirector()

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
                "sector": "CMO — Marketing",
                "analysis": response,
            },
            "actions": self._extract_actions(response),
            "director": "CMO",
        }

    def _extract_actions(self, response: str) -> list:
        actions = []
        if "CAMPANHA" in response.upper() and "EXECUTAR" in response.upper():
            actions.append({"type": "task", "description": "Criar campanha Meta Ads — ver briefing na análise"})
        return actions
