"""AI Content Factory Agent — generates product copy, SEO keywords, and ad scripts."""

from __future__ import annotations

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)


def content_factory_node(state: AgentState) -> dict:
    """Generate marketing content: A+ page copy, SEO keywords, ad scripts."""

    task = _current_task_description(state)
    logger.info("content_factory_start", task=task)

    # Search knowledge base for product info
    product_info = _mock_product_search(task)

    llm = _get_llm()
    prompt = f"""你是一个顶级电商文案和广告创意专家。

任务：{task}

产品信息：
{_format_product(product_info)}

请生成以下内容：
1. **A+ 详情页文案**（含标题、卖点列表、品牌故事段落）
2. **SEO 关键词**（主关键词 3-5 个，长尾关键词 5-8 个）
3. **Facebook/Instagram 广告脚本**（含标题、正文、CTA，2-3 个版本）
4. **邮件营销文案**（欢迎邮件 + 弃购挽回邮件）

请用 Markdown 格式输出，每个部分用 ## 标题分隔。
"""

    content = _invoke_llm(llm, prompt)

    existing_results = state.get("tool_results", {})
    existing_results["content_factory"] = {"product": product_info, "generated": content}

    return {
        "tool_results": existing_results,
        "generated_content": content,
        "step_count": state.get("step_count", 0) + 1,
    }


def _mock_product_search(task: str) -> dict:
    return {
        "name": "有机棉T恤",
        "sku": "SKU-001",
        "materials": "100% GOTS 认证有机棉",
        "features": ["亲肤透气", "人体工学剪裁", "环保印染", "久洗不褪色"],
        "price": "$45.60",
        "colors": ["白色", "黑色", "灰色", "海军蓝"],
        "sizes": ["S", "M", "L", "XL", "XXL"],
        "target_audience": "25-40岁注重品质和环保的都市人群",
        "usp": "GOTS认证有机棉，48小时销量突破5000件",
    }


def _current_task_description(state: AgentState) -> str:
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)
    if index < len(subtasks):
        return subtasks[index].get("description", "")
    return state.get("task_description", "")


def _format_product(data: dict) -> str:
    lines = [
        f"产品名: {data['name']}",
        f"材质: {data['materials']}",
        f"卖点: {', '.join(data['features'])}",
        f"价格: {data['price']}",
        f"颜色: {', '.join(data['colors'])}",
        f"尺码: {', '.join(data['sizes'])}",
        f"目标人群: {data['target_audience']}",
        f"独特卖点: {data['usp']}",
    ]
    return "\n".join(lines)


def _get_llm():
    from src.llm import get_llm
    return get_llm()


def _invoke_llm(llm, prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        logger.warning("content_factory_llm_failed", exc_info=True)
        from src.llm.mock import MOCK_RESPONSES
        return MOCK_RESPONSES.get("content", "内容已生成。")
