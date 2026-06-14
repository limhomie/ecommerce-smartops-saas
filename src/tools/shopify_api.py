"""Shopify API tool — real API with mock fallback.

Supports: orders, products, analytics, inventory.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from src.tools.base import BaseTool, ToolResult
from src.observability.logger import get_logger

logger = get_logger(__name__)


class ShopifyTool(BaseTool):
    name = "shopify_api"
    description = "查询 Shopify 店铺的订单、产品、客户和转化数据"

    def __init__(self, store_url: str = "", api_key: str = "", api_password: str = "",
                 access_token: str = ""):
        self.store_url = store_url.rstrip("/")
        self.api_key = api_key
        self.api_password = api_password
        self.access_token = access_token
        self._enabled = bool(store_url and (access_token or (api_key and api_password)))

    def _headers(self) -> dict:
        if self.access_token:
            return {"X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json"}
        return {"Content-Type": "application/json"}

    def _url(self, path: str, api_version: str = "2024-01") -> str:
        return f"{self.store_url}/admin/api/{api_version}/{path}"

    async def _fetch(self, path: str, params: dict | None = None) -> dict | None:
        if not self._enabled:
            return None
        try:
            url = self._url(path)
            auth = None
            if self.api_key and self.api_password:
                auth = (self.api_key, self.api_password)
            async with httpx.AsyncClient(timeout=15, auth=auth) as client:
                resp = await client.get(url, headers=self._headers(), params=params)
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("shopify_api_error", path=path, status=resp.status_code)
                return None
        except Exception as e:
            logger.warning("shopify_api_failed", path=path, error=str(e))
            return None

    async def execute(self, action: str = "analytics", date_range: str = "7_days",
                      **kwargs) -> ToolResult:
        if action == "analytics":
            return await self._get_analytics(date_range)
        elif action == "products":
            return await self._get_products()
        elif action == "orders":
            return await self._get_orders(date_range, kwargs.get("status"))
        elif action == "inventory":
            return await self._get_inventory()
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    # ── Real API calls with mock fallback ──

    async def _get_orders(self, date_range: str, status: str | None = None) -> ToolResult:
        if self._enabled:
            params = {"status": "any", "limit": 250}
            if date_range == "7_days":
                params["created_at_min"] = (datetime.now() - timedelta(days=7)).isoformat()
            elif date_range == "30_days":
                params["created_at_min"] = (datetime.now() - timedelta(days=30)).isoformat()
            data = await self._fetch("orders.json", params)
            if data and "orders" in data:
                orders = data["orders"]
                total = sum(float(o.get("total_price", 0)) for o in orders)
                return ToolResult(success=True, data={
                    "orders": [{"id": o["id"], "total": o["total_price"],
                                "status": o.get("fulfillment_status", "unfulfilled"),
                                "date": o["created_at"][:10]}
                               for o in orders[:50]],
                    "summary": {"total_orders": len(orders), "total_revenue": f"${total:,.2f}"},
                    "source": "shopify_api",
                }, tool_name=self.name)

        # Mock fallback
        return ToolResult(success=True, data={
            "orders": [{"id": f"ORD-{i:03d}", "status": s, "total": f"${p:.2f}", "date": "2026-06-10"}
                       for i, (s, p) in enumerate([("delivered",45.6),("shipped",69.6),("processing",24.0)])],
            "summary": {"total_orders": 534, "total_revenue": "$24,350.40"},
            "source": "mock",
        }, tool_name=self.name)

    async def _get_products(self) -> ToolResult:
        if self._enabled:
            data = await self._fetch("products.json", {"limit": 50})
            if data and "products" in data:
                products = []
                for p in data["products"]:
                    inv = sum(v.get("inventory_quantity", 0) for v in
                              (p.get("variants", [{}])))
                    products.append({"id": p["id"], "title": p["title"],
                                     "price": p.get("variants",[{}])[0].get("price","?"),
                                     "inventory": inv})
                return ToolResult(success=True, data={"products": products, "source": "shopify_api"},
                                  tool_name=self.name)

        # Mock
        return ToolResult(success=True, data={
            "products": [{"id": "P001", "title": "有机棉T恤", "price": "$45.60", "inventory": 230},
                         {"id": "P002", "title": "环保帆布袋", "price": "$24.00", "inventory": 150},
                         {"id": "P003", "title": "竹纤维毛巾", "price": "$15.00", "inventory": 400}],
            "source": "mock",
        }, tool_name=self.name)

    async def _get_analytics(self, date_range: str) -> ToolResult:
        if self._enabled:
            orders_data = await self._get_orders(date_range)
            products_data = await self._get_products()
            if orders_data.success and products_data.success:
                orders = orders_data.data
                products = products_data.data
                return ToolResult(success=True, data={
                    "date_range": date_range,
                    "metrics": {
                        "total_orders": orders["summary"]["total_orders"],
                        "total_revenue": orders["summary"]["total_revenue"] if isinstance(orders["summary"], dict) else "$0",
                        "product_count": len(products.get("products", [])),
                    },
                    "source": "shopify_api",
                }, tool_name=self.name)

        # Mock
        return ToolResult(success=True, data={
            "date_range": date_range,
            "metrics": {"conversion_rate": "2.1%", "total_visitors": 25430,
                        "total_orders": 534, "average_order_value": "$45.60",
                        "bounce_rate": "61%", "cart_abandonment": "72%"},
            "top_products": [{"name": "有机棉T恤", "sales": 120, "revenue": "$5,472"}],
            "source": "mock",
        }, tool_name=self.name)

    async def _get_inventory(self) -> ToolResult:
        return await self._get_products()


def create_shopify_tool() -> ShopifyTool:
    """Factory: create Shopify tool from settings."""
    from config.settings import Settings
    s = Settings()
    return ShopifyTool(
        store_url=s.shopify_store_url,
        api_key=s.shopify_api_key,
        api_password=s.shopify_api_password,
        access_token=s.shopify_access_token,
    )
