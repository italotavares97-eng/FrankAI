# sectors/deployment/main.py — Frank AI OS
from implantation_agent import ImplantationAgent

class DeploymentDirector:
    def __init__(self):
        self._agent = ImplantationAgent()

    def process(self, query: str) -> dict:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            self._agent.analyze(question=query, user="CEO")
        )
        return {
            "data": {"sector": "Implantação / Deployment", "analysis": response},
            "actions": [{"type": "task", "description": "Acompanhar cronograma de implantação"}] if "PRAZO" in response.upper() else [],
            "director": "OPEP",
        }
