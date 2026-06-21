"""Mock LLM provider for development and demo without API keys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MockResponse:
    content: str
    model: str = "mock"
    usage: dict | None = None


MOCK_RESPONSES: dict[str, str] = {
    "planning": (
        "好的，我来分析这个任务。\n\n"
        "## 任务拆解\n"
        "1. **数据采集** — 从 Shopify/ERP 拉取转化率、流量、客单价等关键指标\n"
        "2. **竞品分析** — 通过 Google Shopping 搜索同品类竞品价格和促销活动\n"
        "3. **舆情分析** — 搜索社交媒体和评论区，了解用户反馈和差评原因\n"
        "4. **综合报告** — 汇总所有数据，生成分析报告和行动建议\n\n"
        "我将按照以上步骤逐一执行。"
    ),
    "analysis": (
        "## 分析结果\n\n"
        "### 数据概览\n"
        "- 上周转化率：2.1%（前周 3.4%，下降 38%）\n"
        "- 流量变化：+5%（流量小幅上升）\n"
        "- 客单价：$45.60（持平）\n\n"
        "### 关键发现\n"
        "1. 竞品 A 上周降价 15%，抢走了价格敏感用户\n"
        "2. 产品页面跳出率从 42% 升至 61%\n"
        "3. 社交媒体出现 3 条关于物流慢的负面评价\n\n"
        "### 行动建议\n"
        "1. 针对竞品 A 的热销品，调整定价策略或推出限时优惠\n"
        "2. 优化产品页加载速度和 A+ 内容\n"
        "3. 联系物流团队改善配送时效，同步更新物流政策页"
    ),
    "content": (
        "## AI 内容生成\n\n"
        "### A+ 详情页文案\n"
        "**标题**: 让每一次穿着都成为享受\n\n"
        "产品卖点：\n"
        "- 采用 100% 有机棉，亲肤透气\n"
        "- 人体工学剪裁，活动自如\n"
        "- 环保印染工艺，久洗不褪色\n\n"
        "### SEO 关键词\n"
        "- 主关键词：有机棉T恤、环保服装、舒适休闲装\n"
        "- 长尾关键词：2025夏季男士有机棉短袖、透气不闷汗T恤推荐\n\n"
        "### Facebook 广告脚本\n"
        "**标题**: 穿上它，才知道什么叫「会呼吸的面料」\n"
        "**正文**: 100%有机棉，48小时销量突破5000件。限时8折，立即抢购👉 [链接]"
    ),
    "sop": (
        "## SOP 自动执行\n\n"
        "### 工单处理\n"
        "- 查询物流单号：YT202506130001\n"
        "- 物流状态：运输中，预计 2026-06-15 送达\n"
        "- 已生成自动回复：\n\n"
        "尊敬的客户，您的包裹目前正在运输中，预计6月15日送达。"
        "如有任何问题，请随时联系我们。祝您购物愉快！"
    ),
    "report": (
        "## 综合运营报告\n\n"
        "### 本周关键指标\n"
        "| 指标 | 数值 | 环比 |\n"
        "|------|------|------|\n"
        "| 转化率 | 2.1% | -38% |\n"
        "| 客单价 | $45.60 | 持平 |\n"
        "| 退货率 | 5.2% | +1.1% |\n\n"
        "### 风险预警\n"
        "- 竞品价格战加剧，建议启动限时促销\n"
        "- 产品页体验下滑，需优化加载速度和内容\n\n"
        "## 4. 行动建议\n"
        "1. 启动「夏日特惠」促销活动（目标：转化率恢复至 3%+）\n"
        "2. 优化 TOP 10 产品的 A+ 详情页\n"
        "3. 跟进物流 SLA，将平均配送时效从 5天 压缩至 3天"
    ),
    "default": (
        "我是电商智能运营助手，可以帮您：\n"
        "- 分析销售数据和转化率\n"
        "- 生成产品文案和广告脚本\n"
        "- 查询竞品信息和市场趋势\n"
        "- 自动处理客服工单\n\n"
        "请告诉我您需要什么帮助？"
    ),
}

CATEGORY_KEYWORDS = {
    "planning": ["分析", "为什么", "下降", "拆解", "计划", "策略", "怎么做", "如何提升"],
    "analysis": ["数据", "转化", "竞品", "趋势", "报表", "指标"],
    "content": ["文案", "广告", "SEO", "关键词", "脚本", "详情页", "描述", "素材"],
    "sop": ["物流", "工单", "包裹", "退货", "客服", "查询", "订单"],
    "report": ["报告", "汇总", "总结", "周报", "月报"],
}


class MockProvider:
    """Mock LLM provider that returns pre-written responses based on keyword matching."""

    def __init__(self, model: str = "mock"):
        self.model = model
        self.provider_name = "mock"

    def _classify(self, prompt: str) -> str:
        """Simple keyword-based classification to pick the right mock response."""
        scores: dict[str, int] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            scores[category] = sum(1 for kw in keywords if kw in prompt)
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] == 0:
            return "default"
        return best

    def invoke(self, prompt: str, **kwargs: Any) -> MockResponse:
        category = self._classify(prompt)
        return MockResponse(content=MOCK_RESPONSES.get(category, MOCK_RESPONSES["default"]))

    async def ainvoke(self, prompt: str, **kwargs: Any) -> MockResponse:
        return self.invoke(prompt, **kwargs)

    def stream(self, prompt: str, **kwargs: Any):
        category = self._classify(prompt)
        text = MOCK_RESPONSES.get(category, MOCK_RESPONSES["default"])
        for paragraph in text.split("\n\n"):
            if paragraph.strip():
                yield paragraph.strip()
