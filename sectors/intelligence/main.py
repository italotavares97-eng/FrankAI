# sectors/intelligence/main.py — Frank AI OS
from bi_director import BIDirector

class IntelligenceDirector:
    def __init__(self):
        self._director = BIDirector()

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
            "data": {"sector": "BI — Inteligência de Negócio", "analysis": response},
            "actions": [],
            "director": "BI",
        }
