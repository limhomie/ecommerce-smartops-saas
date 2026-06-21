"""Sentiment Analyst Agent — analyzes social media sentiment and user reviews."""

from __future__ import annotations

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)


def sentiment_analyst_node(state: AgentState) -> dict:
    """Search social media and review platforms for sentiment signals."""

    task = _current_task_description(state)
    logger.info("sentiment_analyst_start", task=task)

    sentiment_data = _mock_sentiment_search()
    reviews = _mock_review_analysis()

    llm = _get_llm()
    prompt = f"""你是一个舆情分析专家。请分析以下数据：

任务：{task}

社交媒体舆情：
{_format_sentiment(sentiment_data)}

用户评价分析：
{_format_reviews(reviews)}

请给出：
1. 整体舆情概况（正面/负面/中性比例）
2. 主要负面话题和用户抱怨点
3. 建议的公关/改进策略
"""

    analysis = _invoke_llm(llm, prompt)

    existing_results = state.get("tool_results", {})
    existing_results["sentiment"] = sentiment_data
    existing_results["reviews"] = reviews

    # Generate sentiment charts
    from src.utils.chart_utils import sentiment_gauge, rating_distribution

    return {
        "tool_results": existing_results,
        "generated_content": analysis,
        "charts": [sentiment_gauge(), rating_distribution()],
        "step_count": state.get("step_count", 0) + 1,
    }


def _mock_sentiment_search() -> dict:
    return {
        "platforms": {
            "微博": {"mentions": 342, "sentiment": "中性偏负", "top_topics": ["物流速度", "面料质感"]},
            "小红书": {"mentions": 128, "sentiment": "正面偏正", "top_topics": ["穿搭分享", "开箱测评"]},
            "微信": {"mentions": 56, "sentiment": "中性", "top_topics": ["促销活动", "优惠券"]},
        },
        "negative_posts": [
            {"platform": "微博", "content": "买了两周了还没发货...", "engagement": 230},
            {"platform": "小红书", "content": "实物颜色和图片差距太大了", "engagement": 89},
            {"platform": "微博", "content": "客服回复太慢，一问三不知", "engagement": 156},
        ],
    }


def _mock_review_analysis() -> dict:
    return {
        "total_reviews": 1280,
        "avg_rating": 4.1,
        "rating_distribution": {"5星": "45%", "4星": "28%", "3星": "15%", "2星": "7%", "1星": "5%"},
        "top_complaints": [
            {"topic": "物流速度慢", "count": 45, "percentage": "35%"},
            {"topic": "色差问题", "count": 32, "percentage": "25%"},
            {"topic": "尺码不准", "count": 28, "percentage": "22%"},
            {"topic": "客服响应慢", "count": 23, "percentage": "18%"},
        ],
    }


def _current_task_description(state: AgentState) -> str:
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)
    if index < len(subtasks):
        return subtasks[index].get("description", "")
    return state.get("task_description", "")


def _format_sentiment(data: dict) -> str:
    lines = []
    for platform, info in data["platforms"].items():
        lines.append(f"  {platform}: {info['mentions']}条提及, 情绪: {info['sentiment']}, 话题: {', '.join(info['top_topics'])}")
    lines.append("\n负面帖子：")
    for post in data["negative_posts"]:
        lines.append(f"  [{post['platform']}] {post['content']} (互动: {post['engagement']})")
    return "\n".join(lines)


def _format_reviews(data: dict) -> str:
    lines = [
        f"总评价数: {data['total_reviews']}, 平均评分: {data['avg_rating']}",
        f"评分分布: {data['rating_distribution']}",
        "\n主要投诉:",
    ]
    for c in data["top_complaints"]:
        lines.append(f"  - {c['topic']}: {c['count']}条 ({c['percentage']})")
    return "\n".join(lines)


def _get_llm():
    from src.llm import get_llm
    return get_llm()


def _invoke_llm(llm, prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        logger.warning("sentiment_llm_failed", exc_info=True)
        return "舆情数据已拉取，等待后续节点汇总。"
