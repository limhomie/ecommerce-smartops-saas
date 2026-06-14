"""Competitor Analyst Agent — searches competitor prices, promotions, and market trends."""

from __future__ import annotations

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)


def competitor_analyst_node(state: AgentState) -> dict:
    """Analyze competitor landscape using Google Shopping and marketplace data."""

    task = _current_task_description(state)
    logger.info("competitor_analyst_start", task=task)

    # Simulate multi-source data collection
    google_data = _mock_google_shopping()
    amazon_data = _mock_amazon_competitor()

    llm = _get_llm()
    prompt = f"""你是一个竞品分析专家。请分析以下数据：

任务：{task}

Google Shopping 搜索结果：
{_format_shopping(google_data)}

亚马逊竞品对比：
{_format_amazon(amazon_data)}

请给出：
1. 竞品价格策略分析
2. 市场定位对比
3. 我们的应对策略建议
"""

    analysis = _invoke_llm(llm, prompt)

    existing_results = state.get("tool_results", {})
    existing_results["google_shopping"] = google_data
    existing_results["amazon_competitor"] = amazon_data

    # Generate competitor price chart
    from src.utils.chart_utils import competitor_price_chart

    return {
        "tool_results": existing_results,
        "generated_content": analysis,
        "charts": [competitor_price_chart()],
        "step_count": state.get("step_count", 0) + 1,
    }


def _mock_google_shopping() -> dict:
    return {
        "query": "有机棉T恤",
        "market_summary": {
            "avg_price": "$29.50",
            "price_range": "$19.99 - $45.60",
            "avg_rating": 4.2,
            "total_listings": 45,
        },
        "results": [
            {"title": "竞品A — 基础款有机棉T恤", "price": 19.99, "store": "Amazon", "rating": 4.0},
            {"title": "竞品B — 高端有机棉T恤", "price": 34.99, "store": "Walmart", "rating": 4.5},
            {"title": "竞品C — 环保有机棉T恤", "price": 29.99, "store": "Target", "rating": 4.3},
        ],
    }


def _mock_amazon_competitor() -> dict:
    return {
        "competitors": [
            {"name": "Competitor A", "price": "$29.99", "rating": 4.2, "reviews": 1200},
            {"name": "Competitor B", "price": "$34.99", "rating": 4.5, "reviews": 890},
        ],
        "your_position": {"price": "$45.60", "rating": 4.6, "reviews": 950},
        "analysis": "你的价格比市场均价高 55%，但评分最高",
    }


def _current_task_description(state: AgentState) -> str:
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)
    if index < len(subtasks):
        return subtasks[index].get("description", "")
    return state.get("task_description", "")


def _format_shopping(data: dict) -> str:
    lines = [f"市场均价: {data['market_summary']['avg_price']}"]
    for r in data["results"]:
        lines.append(f"  - {r['title']}: ${r['price']}, 评分 {r['rating']}")
    return "\n".join(lines)


def _format_amazon(data: dict) -> str:
    lines = [f"我方价格: {data['your_position']['price']}, 评分: {data['your_position']['rating']}"]
    for c in data["competitors"]:
        lines.append(f"  - {c['name']}: {c['price']}, 评分 {c['rating']}, 评论 {c['reviews']}")
    if "analysis" in data:
        lines.append(f"\n{data['analysis']}")
    return "\n".join(lines)


def _get_llm():
    from src.llm import get_llm
    return get_llm()


def _invoke_llm(llm, prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        return "竞品数据已拉取，等待后续节点汇总分析。"
