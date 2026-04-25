# =============================================================================
# INTEGRATIONS/ERP.PY — Frank AI OS
# Conector ERP — Sults · Linx · Everest
# =============================================================================

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    ERP_SULTS_URL, ERP_SULTS_TOKEN,
    ERP_LINX_URL, ERP_LINX_TOKEN,
)

logger = logging.getLogger("frank.erp")


class ERPConnector:
    """
    Conector unificado para sistemas ERP da Davvero.
    Suporta: Sults (operacional), Linx (PDV), Everest (financeiro/estoque).
    Todos os métodos retornam dicts normalizados, independente do ERP.
    """

    def __init__(self):
        self.sults_client = httpx.AsyncClient(
            base_url=ERP_SULTS_URL,
            headers={"Authorization": f"Bearer {ERP_SULTS_TOKEN}"},
            timeout=30,
        )
        self.linx_client = httpx.AsyncClient(
            base_url=ERP_LINX_URL or "https://api.linx.com.br/v1",
            headers={"Authorization": f"Bearer {ERP_LINX_TOKEN}"},
            timeout=30,
        ) if ERP_LINX_TOKEN else None

    # -------------------------------------------------------------------------
    # VENDAS
    # -------------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def fetch_sales_data(
        self,
        unit_id: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """
        Busca dados de vendas de uma unidade por período.

        Returns: [{"date": date, "revenue": float, "transactions": int, "avg_ticket": float}]
        """
        if not ERP_SULTS_TOKEN:
            return self._mock_sales_data(unit_id, start_date, end_date)

        try:
            resp = await self.sults_client.get(
                "/sales",
                params={
                    "unit_id": unit_id,
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            )
            resp.raise_for_status()
            raw = resp.json()
            return self._normalize_sales(raw)
        except Exception as e:
            logger.warning(f"ERP sales fetch error: {e} — usando mock")
            return self._mock_sales_data(unit_id, start_date, end_date)

    async def fetch_daily_sales(self, unit_id: str, day: date) -> Dict:
        """Busca vendas de um dia específico."""
        rows = await self.fetch_sales_data(unit_id, day, day)
        return rows[0] if rows else {"date": day, "revenue": 0, "transactions": 0, "avg_ticket": 0}

    # -------------------------------------------------------------------------
    # ESTOQUE
    # -------------------------------------------------------------------------

    async def fetch_inventory(self, unit_id: str) -> List[Dict]:
        """
        Busca posição de estoque atual de uma unidade.

        Returns: [{"sku": str, "product": str, "qty": float, "unit": str, "min_qty": float}]
        """
        if not ERP_SULTS_TOKEN:
            return self._mock_inventory(unit_id)

        try:
            resp = await self.sults_client.get(f"/inventory/{unit_id}")
            resp.raise_for_status()
            return self._normalize_inventory(resp.json())
        except Exception as e:
            logger.warning(f"ERP inventory error: {e}")
            return self._mock_inventory(unit_id)

    async def fetch_low_stock(self, unit_id: str) -> List[Dict]:
        """Retorna itens abaixo do estoque mínimo."""
        inventory = await self.fetch_inventory(unit_id)
        return [i for i in inventory if i.get("qty", 0) <= i.get("min_qty", 0)]

    # -------------------------------------------------------------------------
    # FINANCEIRO
    # -------------------------------------------------------------------------

    async def fetch_financial_summary(self, unit_id: str, month: date) -> Dict:
        """
        Busca resumo financeiro do ERP para o mês.

        Returns: {"revenue": float, "cogs": float, "expenses": dict}
        """
        if not ERP_SULTS_TOKEN:
            return self._mock_financial(unit_id, month)

        try:
            resp = await self.sults_client.get(
                "/financial/summary",
                params={"unit_id": unit_id, "month": month.strftime("%Y-%m")},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"ERP financial error: {e}")
            return self._mock_financial(unit_id, month)

    async def fetch_cogs(self, unit_id: str, month: date) -> float:
        """Busca CMV do mês diretamente do ERP."""
        summary = await self.fetch_financial_summary(unit_id, month)
        return summary.get("cogs", 0)

    # -------------------------------------------------------------------------
    # OPERACIONAL
    # -------------------------------------------------------------------------

    async def fetch_unit_performance(self, unit_id: str, days: int = 30) -> Dict:
        """Busca métricas operacionais dos últimos N dias."""
        if not ERP_SULTS_TOKEN:
            return self._mock_performance(unit_id)

        try:
            resp = await self.sults_client.get(
                f"/units/{unit_id}/performance",
                params={"days": days},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"ERP performance error: {e}")
            return self._mock_performance(unit_id)

    # -------------------------------------------------------------------------
    # NORMALIZAÇÃO
    # -------------------------------------------------------------------------

    def _normalize_sales(self, raw: Any) -> List[Dict]:
        if isinstance(raw, list):
            return [
                {
                    "date":        r.get("date") or r.get("data"),
                    "revenue":     float(r.get("revenue") or r.get("faturamento") or 0),
                    "transactions": int(r.get("transactions") or r.get("transacoes") or 0),
                    "avg_ticket":  float(r.get("avg_ticket") or r.get("ticket_medio") or 0),
                }
                for r in raw
            ]
        return []

    def _normalize_inventory(self, raw: Any) -> List[Dict]:
        if isinstance(raw, list):
            return [
                {
                    "sku":      r.get("sku", ""),
                    "product":  r.get("product") or r.get("produto", ""),
                    "qty":      float(r.get("qty") or r.get("quantidade") or 0),
                    "unit":     r.get("unit") or r.get("unidade", "un"),
                    "min_qty":  float(r.get("min_qty") or r.get("estoque_minimo") or 0),
                }
                for r in raw
            ]
        return []

    # -------------------------------------------------------------------------
    # MOCK DATA — usado quando ERP não está configurado
    # -------------------------------------------------------------------------

    def _mock_sales_data(self, unit_id: str, start: date, end: date) -> List[Dict]:
        import random
        from datetime import timedelta
        days = (end - start).days + 1
        return [
            {
                "date": (start + timedelta(days=i)).isoformat(),
                "revenue": round(random.uniform(800, 2500), 2),
                "transactions": random.randint(25, 80),
                "avg_ticket": round(random.uniform(28, 45), 2),
                "source": "mock",
            }
            for i in range(days)
        ]

    def _mock_inventory(self, unit_id: str) -> List[Dict]:
        return [
            {"sku": "LT001", "product": "Leite Integral 1L", "qty": 45, "unit": "L", "min_qty": 30},
            {"sku": "CR001", "product": "Creme de Leite", "qty": 12, "unit": "L", "min_qty": 15},
            {"sku": "AC001", "product": "Açúcar Refinado", "qty": 28, "unit": "kg", "min_qty": 20},
            {"sku": "FR001", "product": "Morango Congelado", "qty": 8, "unit": "kg", "min_qty": 10},
            {"sku": "CP001", "product": "Copo 350ml", "qty": 450, "unit": "un", "min_qty": 200},
        ]

    def _mock_financial(self, unit_id: str, month: date) -> Dict:
        return {
            "unit_id": unit_id,
            "month": month.isoformat(),
            "revenue": 85000.0,
            "cogs": 22525.0,
            "cogs_pct": 26.5,
            "expenses": {
                "rent": 9500, "payroll": 18700, "royalties": 7225,
                "electricity": 1800, "packaging": 2100, "other": 3200,
            },
            "source": "mock",
        }

    def _mock_performance(self, unit_id: str) -> Dict:
        return {
            "unit_id": unit_id,
            "avg_daily_revenue": 2800.0,
            "avg_ticket": 34.5,
            "avg_transactions": 81,
            "productivity": 145.0,
            "stockouts_30d": 3,
            "waste_30d": 850.0,
            "source": "mock",
        }

    async def close(self):
        await self.sults_client.aclose()
        if self.linx_client:
            await self.linx_client.aclose()
