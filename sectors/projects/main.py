# sectors/projects/main.py — Frank AI OS
from frank_master import FrankMaster

class ProjectDirector:
    """Projetos estratégicos cross-funcionais → Frank Master decide."""

    def __init__(self):
        self._master = FrankMaster()

    def process(self, query: str) -> dict:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            self._master.frank_pipeline(question=query, user="CEO")
        )
        return {
            "data": {
                "sector": "Projetos Estratégicos",
                "director": result.get("routing", {}).get("director", "Frank"),
                "analysis": result.get("response", ""),
                "ceo_approved": result.get("ceo_validation", {}).get("approved", True),
            },
            "actions": [{"type": "task", "description": "Revisar projeto — ver análise completa"}],
            "director": "Frank",
        }
