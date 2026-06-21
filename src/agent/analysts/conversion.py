"""Conversion Analyst Agent — analyzes sales data, traffic, and conversion funnels."""

from __future__ import annotations

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)


def conversion_analyst_node(state: AgentState) -> dict:
    """Analyze conversion rate and related metrics.

    Calls Shopify API for analytics data, then uses LLM to interpret results.
    """
    llm = _get_llm()
    task = _current_task_description(state)

    logger.info("conversion_analyst_start", task=task)

    # Simulate tool call to Shopify API
    tool_data = _mock_shopify_analytics()

    # Build prompt with data
    prompt = f"""你是一个电商数据分析专家。请分析以下数据：

任务：{task}

数据：
- 时间范围：{tool_data['date_range']}
- 转化率：{tool_data['metrics']['conversion_rate']}（前值：{tool_data['metrics']['previous_conversion_rate']}，变化：{tool_data['metrics']['change']}）
- 总访客：{tool_data['metrics']['total_visitors']}
- 总订单：{tool_data['metrics']['total_orders']}
- 客单价：{tool_data['metrics']['average_order_value']}
- 跳出率：{tool_data['metrics']['bounce_rate']}
- 购物车放弃率：{tool_data['metrics']['cart_abandonment']}

热销产品：
{_format_products(tool_data['top_products'])}

请给出：
1. 关键指标诊断
2. 可能的原因分析
3. 针对性建议
"""

    analysis = _invoke_llm(llm, prompt)

    # Store results
    existing_results = state.get("tool_results", {})
    existing_results["shopify_analytics"] = tool_data

    # Generate charts
    from src.utils.chart_utils import conversion_trend_chart, conversion_funnel, traffic_source_pie

    charts = [
        conversion_trend_chart(),
        conversion_funnel(),
        traffic_source_pie(),
    ]

    return {
        "tool_results": existing_results,
        "generated_content": analysis,
        "charts": charts,
        "step_count": state.get("step_count", 0) + 1,
    }


def _mock_shopify_analytics() -> dict:
    return {
        "date_range": "2026-06-06 ~ 2026-06-12",
        "metrics": {
            "conversion_rate": "2.1%",
            "previous_conversion_rate": "3.4%",
            "change": "-38%",
            "total_visitors": 25430,
            "total_orders": 534,
            "average_order_value": "$45.60",
            "bounce_rate": "61%",
            "cart_abandonment": "72%",
        },
        "top_products": [
            {"name": "有机棉T恤", "sales": 120, "revenue": "$5,472"},
            {"name": "环保帆布袋", "sales": 89, "revenue": "$2,136"},
            {"name": "竹纤维毛巾", "sales": 67, "revenue": "$1,005"},
        ],
    }


def _current_task_description(state: AgentState) -> str:
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)
    if index < len(subtasks):
        return subtasks[index].get("description", "")
    return state.get("task_description", "")


def _format_products(products: list[dict]) -> str:
    return "\n".join(
        f"  - {p['name']}: 销量 {p['sales']}, 收入 {p['revenue']}"
        for p in products
    )


def _get_llm():
    from src.llm import get_llm
    return get_llm()


def _invoke_llm(llm, prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        logger.warning("conversion_llm_failed", exc_info=True)
        return "数据已拉取，等待后续节点分析。"
