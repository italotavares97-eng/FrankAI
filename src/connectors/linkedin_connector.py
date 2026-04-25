"""Frank AI OS — Conector LinkedIn API (prospecção B2B de franqueados)."""

import httpx
from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("linkedin_connector")

LINKEDIN_API_URL = "https://api.linkedin.com/v2"


class LinkedInConnector:
    """Integração com LinkedIn para prospecção de franqueados B2B."""

    def __init__(self):
        self.token = settings.linkedin_access_token
        self.org_id = settings.linkedin_organization_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
    async def get_organization_followers(self) -> Dict[str, Any]:
        """Busca seguidores e métricas da página da organização."""
        if settings.mock_external_apis:
            return {
                "followers_count": 4820,
                "followers_growth_30d": 312,
                "engagement_rate": 4.7,
                "impressions_30d": 98_000,
                "source": "mock",
            }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{LINKEDIN_API_URL}/organizationalEntityFollowerStatistics",
                headers=self._headers(),
                params={"q": "organizationalEntity", "organizationalEntity": f"urn:li:organization:{self.org_id}"},
            )
            resp.raise_for_status()
            return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
    async def get_post_analytics(self, days: int = 30) -> List[Dict]:
        """Busca performance dos posts recentes."""
        if settings.mock_external_apis:
            return [
                {
                    "post_id": "mock_post_001",
                    "text_preview": "Abra sua própria Davvero Gelato...",
                    "impressions": 12400,
                    "clicks": 342,
                    "engagement_rate": 5.2,
                    "leads_generated": 8,
                    "published_at": "2026-04-20",
                },
                {
                    "post_id": "mock_post_002",
                    "text_preview": "CMV médio de 23% na nossa rede...",
                    "impressions": 8700,
                    "clicks": 210,
                    "engagement_rate": 3.8,
                    "leads_generated": 4,
                    "published_at": "2026-04-15",
                },
            ]
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{LINKEDIN_API_URL}/organizationPageStatistics",
                headers=self._headers(),
                params={
                    "q": "organization",
                    "organization": f"urn:li:organization:{self.org_id}",
                    "timeIntervals.timeGranularityType": "DAY",
                    "timeIntervals.timeRange.start": str(int(__import__("time").time() - days * 86400) * 1000),
                },
            )
            resp.raise_for_status()
            return resp.json().get("elements", [])

    async def get_lead_gen_forms(self) -> List[Dict]:
        """Busca leads de formulários de captação B2B."""
        if settings.mock_external_apis:
            return [
                {
                    "form_id": "form_001",
                    "name": "Seja um Franqueado Davvero",
                    "leads_count": 23,
                    "leads_last_7d": 5,
                    "conversion_rate": 18.4,
                    "top_lead": {
                        "first_name": "Carlos",
                        "last_name": "M.",
                        "company": "Investimentos CM",
                        "submitted_at": "2026-04-23",
                        "capital_disponivel": "R$ 350.000",
                    },
                },
            ]
        return []

    async def get_pipeline_summary(self) -> Dict[str, Any]:
        """Sumário completo do pipeline LinkedIn B2B."""
        followers, posts, leads = await __import__("asyncio").gather(
            self.get_organization_followers(),
            self.get_post_analytics(),
            self.get_lead_gen_forms(),
            return_exceptions=True,
        )

        total_leads = sum(f.get("leads_count", 0) for f in (leads if isinstance(leads, list) else []))
        total_impressions = sum(p.get("impressions", 0) for p in (posts if isinstance(posts, list) else []))

        return {
            "followers": followers if not isinstance(followers, Exception) else {},
            "top_posts": posts if not isinstance(posts, list) else posts[:5],
            "lead_gen_forms": leads if not isinstance(leads, Exception) else [],
            "summary": {
                "total_leads_pipeline": total_leads,
                "impressions_30d": total_impressions,
                "source": "mock" if settings.mock_external_apis else "live",
            },
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
    async def publish_post(self, text: str, visibility: str = "PUBLIC") -> bool:
        """Publica post na página da organização."""
        if settings.mock_external_apis:
            logger.info("linkedin_post_mock", preview=text[:80])
            return True

        payload = {
            "author": f"urn:li:organization:{self.org_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{LINKEDIN_API_URL}/ugcPosts",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()

        logger.info("linkedin_post_published", preview=text[:50])
        return True


linkedin_connector = LinkedInConnector()
