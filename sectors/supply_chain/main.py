# sectors/supply_chain/main.py — Frank AI OS
from supply_director import SupplyDirector as _SupplyDirector

class SupplyDirector:
    def __init__(self):
        self._director = _SupplyDirector()

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
        actions = []
        if "REPOR" in response.upper() or "PEDIDO" in response.upper():
            actions.append({"type": "email", "subject": "Pedido urgente — Supply", "body": "Reposição necessária — ver análise Frank AI OS"})
        return {
            "data": {"sector": "Supply Chain", "analysis": response},
            "actions": actions,
            "director": "Supply",
        }
