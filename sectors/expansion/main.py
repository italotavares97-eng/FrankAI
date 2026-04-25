# sectors/expansion/main.py — Frank AI OS
from cso_director import CSODirector

class ExpansionDirector:
    def __init__(self):
        self._director = CSODirector()

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
            "data": {"sector": "CSO — Expansão", "analysis": response},
            "actions": [{"type": "task", "description": "Avaliar lead de expansão — ver análise ROI"}] if "EXECUTAR" in response.upper() else [],
            "director": "CSO",
        }
