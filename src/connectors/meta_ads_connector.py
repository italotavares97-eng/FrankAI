"""Frank AI OS — Conector Meta Graph API (Facebook/Instagram Ads)."""

import httpx
from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("meta_connector")

META_GRAPH_URL = "https://graph.facebook.com/v20.0"


class MetaAdsConnector:

    def __init__(self):
        self.token = settings.meta_access_token
        self.ad_account_id = settings.meta_ad_account_id
        self.page_id = settings.meta_page_id

    def _params(self, extra: dict = {}) -> dict:
        return {"access_token": self.token, **extra}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
    async def get_campaigns_performance(self, date_preset: str = "last_7d") -> List[Dict]:
        if settings.mock_external_apis:
            return [
                {"campaign_id": "mock_001", "name": "Gelato Summer", "spend": 2400.0,
                 "impressions": 95000, "clicks": 3200, "conversions": 145, "roas": 3.2},
                {"campaign_id": "mock_002", "name": "Franqueado Lead Gen", "spend": 1800.0,
                 "impressions": 45000, "clicks": 980, "conversions": 28, "roas": 4.1},
            ]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{META_GRAPH_URL}/{self.ad_account_id}/campaigns",
                params=self._params({
                    "fields": "id,name,spend,impressions,clicks,actions",
                    "date_preset": date_preset,
                }),
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa campanha com ROAS abaixo do limite."""
        if settings.mock_external_apis:
            logger.info("meta_campaign_paused_mock", campaign_id=campaign_id)
            return True

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{META_GRAPH_URL}/{campaign_id}",
                params=self._params({"status": "PAUSED"}),
            )
            resp.raise_for_status()

        logger.info("meta_campaign_paused", campaign_id=campaign_id)
        return True

    async def get_page_comments(self, since_hours: int = 24) -> List[Dict]:
        """Busca comentários pendentes de resposta."""
        if settings.mock_external_apis:
            return [
                {"comment_id": "c001", "message": "Qual o sabor do dia?", "from": "Ana", "created_time": "2h atrás"},
                {"comment_id": "c002", "message": "Abrem domingo?", "from": "João", "created_time": "5h atrás"},
            ]
        return []

    async def reply_comment(self, comment_id: str, message: str) -> bool:
        """Responde automaticamente a um comentário."""
        if settings.mock_external_apis:
            logger.info("meta_comment_replied_mock", comment_id=comment_id, preview=message[:50])
            return True

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{META_GRAPH_URL}/{comment_id}/comments",
                params=self._params({"message": message}),
            )
            resp.raise_for_status()
        return True


meta_connector = MetaAdsConnector()
