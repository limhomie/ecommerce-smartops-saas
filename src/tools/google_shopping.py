"""Google Shopping search tool — search competitor prices and products."""

from __future__ import annotations

from src.tools.base import BaseTool, ToolResult


class GoogleShoppingTool(BaseTool):
    name = "google_shopping"
    description = "搜索 Google Shopping 上的商品价格、竞品信息和市场趋势"

    async def execute(
        self,
        query: str = "",
        category: str = "",
        max_results: int = 10,
    ) -> ToolResult:
        # Mock implementation — in production, calls Google Shopping API
        mock_results = [
            {
                "title": f"竞品商品 {i} — {query or category}",
                "price": round(19.99 + i * 5.5, 2),
                "store": "Amazon / Walmart",
                "rating": round(3.5 + i * 0.3, 1),
                "reviews_count": 100 + i * 50,
                "url": f"https://shopping.google.com/product/{i}",
            }
            for i in range(min(max_results, 5))
        ]

        market_summary = {
            "avg_price": round(sum(r["price"] for r in mock_results) / len(mock_results), 2),
            "price_range": f"${mock_results[0]['price']} - ${mock_results[-1]['price']}",
            "avg_rating": round(sum(r["rating"] for r in mock_results) / len(mock_results), 1),
            "total_listings": len(mock_results),
        }

        return ToolResult(
            success=True,
            data={
                "query": query,
                "category": category,
                "market_summary": market_summary,
                "results": mock_results,
            },
            tool_name=self.name,
        )
