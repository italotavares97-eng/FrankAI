"""Frank AI OS — Conector ERP Sults (dados reais de vendas e estoque)."""

import httpx
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("sults_connector")


class SultsConnector:
    """Busca dados reais de vendas, CMV e estoque do ERP Sults."""

    def __init__(self):
        self.base_url = settings.sults_api_url
        self.headers = {
            "Authorization": f"Bearer {settings.sults_api_key}",
            "X-Tenant": settings.sults_tenant_id,
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
    async def get_sales_by_unit(
        self,
        unit_id: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Busca vendas reais de uma unidade no período."""
        if settings.mock_external_apis:
            import random
            random.seed(hash(unit_id + start_date) % 1000)
            return {
                "unit_id": unit_id,
                "period": f"{start_date} to {end_date}",
                "revenue": round(random.uniform(45_000, 120_000), 2),
                "transactions": random.randint(300, 900),
                "avg_ticket": round(random.uniform(25, 85), 2),
                "top_products": [
                    {"name": "Gelato Pistache 300g", "qty": random.randint(80, 250), "revenue": random.uniform(5000, 18000)},
                    {"name": "Gelato Morango 300g", "qty": random.randint(70, 200), "revenue": random.uniform(4000, 15000)},
                ],
                "source": "mock",
            }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/v1/sales",
                headers=self.headers,
                params={
                    "unit_id": unit_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_all_units_sales(self, period_days: int = 1) -> List[Dict]:
        """Busca vendas de TODAS as unidades em paralelo."""
        import asyncio
        today = date.today()
        start = (today - timedelta(days=period_days)).isoformat()
        end = today.isoformat()

        tasks = [
            self.get_sales_by_unit(uid, start, end)
            for uid in settings.network_units
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for uid, result in zip(settings.network_units, results):
            if isinstance(result, Exception):
                logger.error("sults_unit_error", unit=uid, error=str(result))
            else:
                output.append(result)
        return output

    async def get_inventory(self, unit_id: str) -> Dict:
        """Busca estoque atual de uma unidade."""
        if settings.mock_external_apis:
            import random
            random.seed(hash(unit_id + "inv") % 1000)
            return {
                "unit_id": unit_id,
                "items": [
                    {"sku": "LAT-001", "name": "Leite integral", "qty_kg": round(random.uniform(5, 40), 1), "reorder_point": 10},
                    {"sku": "FRU-002", "name": "Morango congelado", "qty_kg": round(random.uniform(3, 20), 1), "reorder_point": 8},
                    {"sku": "EMB-003", "name": "Pote 300g", "qty_un": random.randint(100, 800), "reorder_point": 200},
                ],
                "source": "mock",
            }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.base_url}/v1/inventory/{unit_id}", headers=self.headers)
            resp.raise_for_status()
            return resp.json()


sults_connector = SultsConnector()
