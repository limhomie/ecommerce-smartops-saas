"""Google Ads API tool — real API with mock fallback.

Uses Google Ads API v16 (REST).
Requires: developer_token, client_id, client_secret, refresh_token, customer_id.
Setup: https://developers.google.com/google-ads/api/docs/first-call/overview
"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from src.tools.base import BaseTool, ToolResult
from src.observability.logger import get_logger

logger = get_logger(__name__)

API_URL = "https://googleads.googleapis.com/v16"
OAUTH_URL = "https://www.googleapis.com/oauth2/v4/token"


class GoogleAdsTool(BaseTool):
    name = "google_ads_api"
    description = "查询 Google Ads 广告账户的投放效果和关键词数据"

    def __init__(self, developer_token: str = "", client_id: str = "",
                 client_secret: str = "", refresh_token: str = "",
                 customer_id: str = "", login_customer_id: str = ""):
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.customer_id = customer_id.replace("-", "")
        self.login_customer_id = login_customer_id.replace("-", "")
        self._access_token = ""
        self._enabled = bool(developer_token and client_id and client_secret
                            and refresh_token and customer_id)

    async def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(OAUTH_URL, data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                })
                if resp.status_code == 200:
                    self._access_token = resp.json()["access_token"]
                    return self._access_token
        except Exception as e:
            logger.warning("google_ads_auth_failed", error=str(e))
        return ""

    async def _fetch(self, path: str, query: str, params: dict | None = None) -> dict | None:
        if not self._enabled:
            return None
        token = await self._get_access_token()
        if not token:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "developer-token": self.developer_token,
            }
            if self.login_customer_id:
                headers["login-customer-id"] = self.login_customer_id
            url = f"{API_URL}/customers/{self.customer_id}/{path}"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, headers=headers, json={"query": query})
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("google_ads_error", status=resp.status_code,
                               body=resp.text[:200])
                return None
        except Exception as e:
            logger.warning("google_ads_failed", error=str(e))
            return None

    async def execute(self, action: str = "performance", **kwargs) -> ToolResult:
        if action == "performance":
            return await self._get_performance(
                kwargs.get("date_range", "7_days"))
        elif action == "campaigns":
            return await self._get_campaigns()
        elif action == "keywords":
            return await self._get_keywords()
        elif action == "search_terms":
            return await self._get_search_terms()
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    async def _get_performance(self, date_range: str = "7_days") -> ToolResult:
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d") \
            if date_range == "7_days" else \
            (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")

        query = f"""
            SELECT
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.ctr,
                metrics.average_cpc,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{since}' AND '{until}'
            ORDER BY metrics.impressions DESC
            LIMIT 20
        """

        if self._enabled:
            data = await self._fetch("googleAds:search", query)
            if data and "results" in data:
                campaigns = []
                for row in data["results"]:
                    c = row["campaign"]
                    m = row["metrics"]
                    campaigns.append({
                        "campaign": c["name"],
                        "impressions": int(m.get("impressions", 0)),
                        "clicks": int(m.get("clicks", 0)),
                        "cost": round(int(m.get("costMicros", 0)) / 1_000_000, 2),
                        "ctr": f"{float(m.get('ctr', 0)):.2f}%",
                        "cpc": f"${float(m.get('averageCpc', 0)) / 1_000_000:.2f}",
                        "conversions": float(m.get("conversions", 0)),
                        "conversion_value": float(m.get("conversionsValue", 0)),
                    })
                return ToolResult(success=True, data={
                    "campaigns": campaigns, "source": "google_ads_api",
                }, tool_name=self.name)

        # Mock
        return ToolResult(success=True, data={
            "campaigns": [
                {"campaign": "搜索-品牌词", "impressions": 32400, "clicks": 2180,
                 "cost": 1962.00, "ctr": "6.73%", "cpc": "$0.90",
                 "conversions": 128, "conversion_value": 5836.80},
                {"campaign": "购物-有机棉", "impressions": 18600, "clicks": 1240,
                 "cost": 1488.00, "ctr": "6.67%", "cpc": "$1.20",
                 "conversions": 89, "conversion_value": 4058.40},
                {"campaign": "展示-再营销", "impressions": 89200, "clicks": 980,
                 "cost": 588.00, "ctr": "1.10%", "cpc": "$0.60",
                 "conversions": 45, "conversion_value": 2052.00},
                {"campaign": "搜索-DSA", "impressions": 5200, "clicks": 380,
                 "cost": 456.00, "ctr": "7.31%", "cpc": "$1.20",
                 "conversions": 28, "conversion_value": 1276.80},
            ],
            "source": "mock",
        }, tool_name=self.name)

    async def _get_campaigns(self) -> ToolResult:
        query = "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type FROM campaign LIMIT 20"
        if self._enabled:
            data = await self._fetch("googleAds:search", query)
            if data and "results" in data:
                return ToolResult(success=True, data={
                    "campaigns": [r["campaign"] for r in data["results"]],
                    "source": "google_ads_api",
                }, tool_name=self.name)

        return ToolResult(success=True, data={
            "campaigns": [
                {"id": "G001", "name": "搜索-品牌词", "status": "ENABLED", "type": "SEARCH"},
                {"id": "G002", "name": "购物-有机棉", "status": "ENABLED", "type": "SHOPPING"},
                {"id": "G003", "name": "展示-再营销", "status": "PAUSED", "type": "DISPLAY"},
            ],
            "source": "mock",
        }, tool_name=self.name)

    async def _get_keywords(self) -> ToolResult:
        query = """
            SELECT keyword_view.text, metrics.impressions, metrics.clicks, metrics.cost_micros
            FROM keyword_view
            WHERE metrics.impressions > 100
            ORDER BY metrics.impressions DESC LIMIT 10
        """
        if self._enabled:
            data = await self._fetch("googleAds:search", query)
            if data and "results" in data:
                return ToolResult(success=True, data={
                    "keywords": data["results"], "source": "google_ads_api",
                }, tool_name=self.name)

        return ToolResult(success=True, data={
            "keywords": [
                {"text": "有机棉T恤", "impressions": 5400, "clicks": 380, "cost": 342.00},
                {"text": "纯棉短袖 女", "impressions": 3200, "clicks": 210, "cost": 189.00},
                {"text": "环保内衣品牌", "impressions": 1800, "clicks": 145, "cost": 130.50},
            ],
            "source": "mock",
        }, tool_name=self.name)

    async def _get_search_terms(self) -> ToolResult:
        return await self._get_keywords()


def create_google_ads_tool() -> GoogleAdsTool:
    from config.settings import Settings
    s = Settings()
    return GoogleAdsTool(
        developer_token=s.google_ads_developer_token,
        client_id=s.google_ads_client_id,
        client_secret=s.google_ads_client_secret,
        refresh_token=s.google_ads_refresh_token,
        customer_id=s.google_ads_customer_id,
        login_customer_id=s.google_ads_login_customer_id,
    )
