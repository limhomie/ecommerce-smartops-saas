"""Meta Ads (Facebook/Instagram) tool — real API with mock fallback.

Uses Facebook Graph API v19.0 + Marketing API.
Requires: access_token with ads_read permission, ad_account_id (act_xxx).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from src.tools.base import BaseTool, ToolResult
from src.observability.logger import get_logger

logger = get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


class MetaAdsTool(BaseTool):
    name = "meta_ads"
    description = "查询 Facebook/Instagram 广告投放效果，生成广告创意"

    def __init__(self, access_token: str = "", ad_account_id: str = ""):
        self.access_token = access_token
        self.ad_account_id = ad_account_id.replace("act_", "")
        self._enabled = bool(access_token and ad_account_id)

    async def _fetch(self, path: str, params: dict | None = None) -> dict | None:
        if not self._enabled:
            return None
        try:
            p = params or {}
            p["access_token"] = self.access_token
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{GRAPH_URL}/{path}", params=p)
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("meta_api_error", path=path, status=resp.status_code,
                               body=resp.text[:200])
                return None
        except Exception as e:
            logger.warning("meta_api_failed", path=path, error=str(e))
            return None

    async def execute(self, action: str = "insights", **kwargs) -> ToolResult:
        if action == "insights":
            return await self._get_insights(kwargs.get("date_range", "7_days"))
        elif action == "campaigns":
            return await self._get_campaigns()
        elif action == "generate":
            return await self._generate_ad(
                kwargs.get("product_name", ""),
                kwargs.get("target_audience", ""),
                kwargs.get("platform", "facebook"),
            )
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    async def _get_insights(self, date_range: str = "7_days") -> ToolResult:
        if self._enabled:
            since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d") \
                if date_range == "7_days" else \
                (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            until = datetime.now().strftime("%Y-%m-%d")
            path = f"act_{self.ad_account_id}/insights"
            params = {
                "time_range": f'{{"since":"{since}","until":"{until}"}}',
                "fields": "campaign_name,impressions,clicks,spend,ctr,cpc,actions,roas",
                "level": "campaign",
                "limit": 50,
            }
            data = await self._fetch(path, params)
            if data and "data" in data:
                campaigns = []
                for row in data["data"]:
                    conversions = 0
                    for a in row.get("actions", []):
                        if a.get("action_type") == "purchase":
                            conversions = int(a.get("value", 0))
                    campaigns.append({
                        "campaign": row.get("campaign_name", "?"),
                        "impressions": int(row.get("impressions", 0)),
                        "clicks": int(row.get("clicks", 0)),
                        "spend": float(row.get("spend", 0)),
                        "ctr": f"{float(row.get('ctr', 0)):.2f}%",
                        "cpc": f"${float(row.get('cpc', 0)):.2f}",
                        "conversions": conversions,
                        "roas": f"{float(row.get('roas', [{}])[0].get('value', 0)):.1f}x",
                    })
                return ToolResult(success=True, data={
                    "campaigns": campaigns, "source": "meta_ads_api",
                }, tool_name=self.name)

        # Mock fallback
        return ToolResult(success=True, data={
            "campaigns": [
                {"campaign": "夏季特惠", "impressions": 45230, "clicks": 1230,
                 "spend": 2500, "ctr": "2.72%", "cpc": "$0.35", "conversions": 89, "roas": "3.2x"},
                {"campaign": "新品首发", "impressions": 38200, "clicks": 980,
                 "spend": 1800, "ctr": "2.56%", "cpc": "$0.32", "conversions": 65, "roas": "2.8x"},
                {"campaign": "品牌种草", "impressions": 25600, "clicks": 720,
                 "spend": 1200, "ctr": "2.81%", "cpc": "$0.28", "conversions": 42, "roas": "2.1x"},
                {"campaign": "会员日", "impressions": 15400, "clicks": 450,
                 "spend": 800, "ctr": "2.92%", "cpc": "$0.31", "conversions": 28, "roas": "2.5x"},
                {"campaign": "清仓", "impressions": 8900, "clicks": 210,
                 "spend": 500, "ctr": "2.36%", "cpc": "$0.42", "conversions": 12, "roas": "1.6x"},
            ],
            "source": "mock",
        }, tool_name=self.name)

    async def _get_campaigns(self) -> ToolResult:
        if self._enabled:
            path = f"act_{self.ad_account_id}/campaigns"
            data = await self._fetch(path, {"fields": "id,name,status,objective,daily_budget"})
            if data and "data" in data:
                return ToolResult(success=True, data={
                    "campaigns": data["data"], "source": "meta_ads_api",
                }, tool_name=self.name)

        return ToolResult(success=True, data={
            "campaigns": [
                {"id": "C001", "name": "夏季特惠", "status": "ACTIVE", "objective": "CONVERSIONS"},
                {"id": "C002", "name": "新品首发", "status": "ACTIVE", "objective": "REACH"},
                {"id": "C003", "name": "品牌种草", "status": "PAUSED", "objective": "ENGAGEMENT"},
            ],
            "source": "mock",
        }, tool_name=self.name)

    async def _generate_ad(self, product_name: str, audience: str,
                           platform: str = "facebook") -> ToolResult:
        return ToolResult(success=True, data={
            "ad_creative": {
                "headline": f"🔥 {product_name or '爆款商品'} — 限时特惠",
                "primary_text": f"【{product_name or '品质之选'}】\n✓ 已售5000+件 | ⭐4.8分\n✓ 30天无忧退换 | 🚚全国包邮",
                "cta": "立即购买",
                "target": audience or "泛人群",
                "platform": platform.capitalize(),
            },
            "source": "mock",
        }, tool_name=self.name)


def create_meta_ads_tool() -> MetaAdsTool:
    from config.settings import Settings
    s = Settings()
    return MetaAdsTool(access_token=s.meta_ads_access_token,
                       ad_account_id=s.meta_ads_account_id)
