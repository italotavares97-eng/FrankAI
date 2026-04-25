# sectors/hr_training/main.py — Frank AI OS
from opep_director import OPEPDirector

class HRDirector:
    def __init__(self):
        self._director = OPEPDirector()

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
            "data": {"sector": "OPEP — RH & Treinamento", "analysis": response},
            "actions": [{"type": "task", "description": "Agendar treinamento — ver plano na análise"}] if "TREINAMENTO" in response.upper() else [],
            "director": "OPEP",
        }
