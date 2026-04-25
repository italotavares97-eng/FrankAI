# =============================================================================
# INTEGRATIONS/SOCIAL.PY — Frank AI OS
# Conector Meta Ads API + LinkedIn API
# =============================================================================

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

import httpx

from config import (
    META_ADS_TOKEN, META_ADS_ACCOUNT_ID,
    LINKEDIN_TOKEN, LINKEDIN_ORG_ID,
)

logger = logging.getLogger("frank.social")

META_GRAPH_URL   = "https://graph.facebook.com/v21.0"
LINKEDIN_API_URL = "https://api.linkedin.com/v2"


class SocialConnector:
    """
    Conector unificado para plataformas de mídia social.
    Suporta: Meta Ads (Facebook/Instagram), LinkedIn.
    """

    def __init__(self):
        self.meta_client = httpx.AsyncClient(
            base_url=META_GRAPH_URL,
            params={"access_token": META_ADS_TOKEN} if META_ADS_TOKEN else {},
            timeout=30,
        )
        self.linkedin_client = httpx.AsyncClient(
            base_url=LINKEDIN_API_URL,
            headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"} if LINKEDIN_TOKEN else {},
            timeout=30,
        )

    # =========================================================================
    # META ADS
    # =========================================================================

    async def get_campaign_insights(
        self,
        campaign_id: str,
        start: date,
        end: date,
        fields: Optional[List[str]] = None,
    ) -> Dict:
        """
        Busca métricas de uma campanha Meta Ads.

        Returns: {"spend": float, "impressions": int, "clicks": int, "ctr": float, "cpm": float, "cpc": float, "leads": int}
        """
        if not META_ADS_TOKEN:
            return self._mock_campaign_insights(campaign_id)

        default_fields = ["spend", "impressions", "clicks", "ctr", "cpm", "cpc", "leads", "reach"]
        fields = fields or default_fields

        try:
            resp = await self.meta_client.get(
                f"/{campaign_id}/insights",
                params={
                    "fields": ",".join(fields),
                    "time_range": {"since": start.isoformat(), "until": end.isoformat()},
                    "level": "campaign",
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", [{}])[0]
            return {
                "campaign_id":  campaign_id,
                "spend":        float(data.get("spend", 0)),
                "impressions":  int(data.get("impressions", 0)),
                "clicks":       int(data.get("clicks", 0)),
                "ctr":          float(data.get("ctr", 0)),
                "cpm":          float(data.get("cpm", 0)),
                "cpc":          float(data.get("cpc", 0)),
                "leads":        int(data.get("leads", 0)),
                "reach":        int(data.get("reach", 0)),
            }
        except Exception as e:
            logger.warning(f"Meta Ads insights error: {e}")
            return self._mock_campaign_insights(campaign_id)

    async def get_all_campaigns(self) -> List[Dict]:
        """Lista todas as campanhas ativas da conta."""
        if not META_ADS_TOKEN:
            return self._mock_campaigns()

        try:
            resp = await self.meta_client.get(
                f"/act_{META_ADS_ACCOUNT_ID}/campaigns",
                params={"fields": "id,name,status,objective,daily_budget,lifetime_budget"},
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            logger.warning(f"Meta campaigns error: {e}")
            return self._mock_campaigns()

    async def create_campaign(
        self,
        name: str,
        objective: str,
        daily_budget: float,
        status: str = "PAUSED",
    ) -> Dict:
        """
        Cria uma campanha Meta Ads.

        objective: LEAD_GENERATION | BRAND_AWARENESS | CONVERSIONS | TRAFFIC
        status: PAUSED | ACTIVE
        """
        if not META_ADS_TOKEN:
            logger.info(f"[MOCK] Criando campanha: {name} | {objective} | R${daily_budget}/dia")
            return {"id": "mock_campaign_123", "name": name, "status": "PAUSED", "mock": True}

        try:
            resp = await self.meta_client.post(
                f"/act_{META_ADS_ACCOUNT_ID}/campaigns",
                json={
                    "name": name,
                    "objective": objective,
                    "status": status,
                    "special_ad_categories": [],
                    "daily_budget": int(daily_budget * 100),  # centavos
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Create campaign error: {e}")
            return {"error": str(e)}

    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa uma campanha ativa."""
        if not META_ADS_TOKEN:
            logger.info(f"[MOCK] Pausando campanha {campaign_id}")
            return True
        try:
            resp = await self.meta_client.post(
                f"/{campaign_id}",
                json={"status": "PAUSED"},
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Pause campaign error: {e}")
            return False

    # =========================================================================
    # LINKEDIN
    # =========================================================================

    async def post_linkedin(self, text: str, media_url: Optional[str] = None) -> Dict:
        """
        Publica no LinkedIn da empresa.
        """
        if not LINKEDIN_TOKEN:
            logger.info(f"[MOCK] LinkedIn post: {text[:80]}...")
            return {"id": "mock_post_456", "mock": True}

        payload = {
            "author": f"urn:li:organization:{LINKEDIN_ORG_ID}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE" if not media_url else "IMAGE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        try:
            resp = await self.linkedin_client.post("/ugcPosts", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"LinkedIn post error: {e}")
            return {"error": str(e)}

    async def get_linkedin_analytics(self, post_id: str) -> Dict:
        """Busca métricas de um post no LinkedIn."""
        if not LINKEDIN_TOKEN:
            return self._mock_linkedin_analytics(post_id)
        try:
            resp = await self.linkedin_client.get(
                f"/socialActions/{post_id}",
                params={"projection": "(numLikes,numComments,numShares)"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"LinkedIn analytics error: {e}")
            return self._mock_linkedin_analytics(post_id)

    # =========================================================================
    # MOCK DATA
    # =========================================================================

    def _mock_campaign_insights(self, campaign_id: str) -> Dict:
        return {
            "campaign_id": campaign_id, "spend": 3500.0, "impressions": 125000,
            "clicks": 2800, "ctr": 2.24, "cpm": 28.0, "cpc": 1.25,
            "leads": 47, "reach": 98000, "source": "mock",
        }

    def _mock_campaigns(self) -> List[Dict]:
        return [
            {"id": "camp_001", "name": "Gelato Verão 2026", "status": "ACTIVE", "objective": "LEAD_GENERATION", "daily_budget": 15000},
            {"id": "camp_002", "name": "Franquia Davvero — Prospecção", "status": "ACTIVE", "objective": "LEAD_GENERATION", "daily_budget": 8000},
            {"id": "camp_003", "name": "Branding Premium", "status": "PAUSED", "objective": "BRAND_AWARENESS", "daily_budget": 5000},
        ]

    def _mock_linkedin_analytics(self, post_id: str) -> Dict:
        return {"post_id": post_id, "likes": 128, "comments": 23, "shares": 15, "source": "mock"}

    async def close(self):
        await self.meta_client.aclose()
        await self.linkedin_client.aclose()
