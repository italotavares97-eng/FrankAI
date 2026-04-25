# sectors/legal/main.py — Frank AI OS
from legal_director import LegalDirector as _LegalDirector

class LegalDirector:
    def __init__(self):
        self._director = _LegalDirector()

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
            "data": {"sector": "Legal", "analysis": response},
            "actions": [{"type": "task", "description": "Revisar item jurídico — ver análise"}] if "ESCALAR" in response.upper() else [],
            "director": "Legal",
        }
