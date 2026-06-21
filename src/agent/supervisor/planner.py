"""Supervisor Planner — decomposes fuzzy instructions into subtasks.

Given "为什么上周转化率下降了?",
the planner breaks it into:
  1. 拉取转化率相关数据
  2. 搜索竞品价格变化
  3. 搜索社交媒体舆情
  4. 生成分析报告
"""

from __future__ import annotations

import json

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是一个电商运营专家的任务规划器。给定用户的模糊指令，你需要将其拆解为3-4个核心子任务（不要超过4个，确保效率）。

可用的 Agent 类型：
- conversion_analyst: 分析转化率、销售数据、流量数据
- competitor_analyst: 搜索竞品价格、促销活动、市场趋势
- sentiment_analyst: 分析社交媒体舆情、用户评价、差评原因
- content_factory: 生成产品文案、SEO关键词、广告脚本
- sop_executor: 处理客服工单、物流查询、自动化流程
- report_generator: 汇总分析结果，生成报告和行动建议

请以 JSON 格式返回子任务列表（最多4个）：
[{"step": 1, "agent": "agent_type", "description": "任务描述", "tool_hint": "建议使用的工具"}]

只返回 JSON 数组，不要其他内容。"""

# Fallback planning for mock mode (doesn't depend on LLM)
FALLBACK_PLANS: dict[str, list[dict]] = {
    "转化率": [
        {"step": 1, "agent": "conversion_analyst", "description": "拉取上周转化率、流量、客单价数据", "tool_hint": "shopify_api"},
        {"step": 2, "agent": "competitor_analyst", "description": "搜索竞品价格和促销活动变化", "tool_hint": "google_shopping"},
        {"step": 3, "agent": "sentiment_analyst", "description": "搜索社交媒体和相关渠道的差评", "tool_hint": "sentiment_search"},
        {"step": 4, "agent": "report_generator", "description": "汇总数据生成分析报告和行动建议", "tool_hint": "report"},
    ],
    "广告": [
        {"step": 1, "agent": "content_factory", "description": "检索产品素材并生成广告脚本", "tool_hint": "meta_ads"},
        {"step": 2, "agent": "content_factory", "description": "生成配套的SEO关键词和详情页文案", "tool_hint": "content_factory"},
    ],
    "物流": [
        {"step": 1, "agent": "sop_executor", "description": "查询物流状态", "tool_hint": "logistics"},
        {"step": 2, "agent": "sop_executor", "description": "生成客户回复", "tool_hint": "logistics"},
    ],
    "竞品": [
        {"step": 1, "agent": "competitor_analyst", "description": "搜索竞品价格和产品信息", "tool_hint": "google_shopping"},
        {"step": 2, "agent": "competitor_analyst", "description": "对比分析竞品与本品的优劣势", "tool_hint": "amazon_api"},
        {"step": 3, "agent": "report_generator", "description": "生成竞品分析报告", "tool_hint": "report"},
    ],
    "报告": [
        {"step": 1, "agent": "conversion_analyst", "description": "拉取本周销售和转化数据", "tool_hint": "shopify_api"},
        {"step": 2, "agent": "report_generator", "description": "生成综合运营报告", "tool_hint": "report"},
    ],
    "default": [
        {"step": 1, "agent": "conversion_analyst", "description": "拉取核心运营数据", "tool_hint": "shopify_api"},
        {"step": 2, "agent": "report_generator", "description": "基于数据生成分析", "tool_hint": "report"},
    ],
}


def plan_task(state: AgentState, llm=None, extra_context: str = "") -> dict:
    """Decompose the user's task description into subtasks.

    Uses LLM if available, otherwise falls back to keyword matching.

    Args:
        extra_context: Optional conversation history to inject into the prompt,
                       so the planner understands follow-up questions.
    """
    task = state.get("task_description", "")
    if not task:
        # Extract from last user message
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                task = msg.content
                break

    logger.info("planning_task", task=task[:100])

    # Try LLM-based planning
    if llm and hasattr(llm, "invoke"):
        try:
            prompt = SYSTEM_PROMPT
            if extra_context:
                prompt += (
                    "\n\n## 对话历史（用于理解当前问题的上下文）\n"
                    f"{extra_context}\n"
                    "如果当前问题是对上文的理解或跟进（如'那竞品呢？''再详细一点'），"
                    "请结合历史对话推断用户意图，拆解为正确的子任务。\n"
                )
            prompt += f"\n\n用户指令：{task}"
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            # Robust JSON extraction: find the first '[' and last ']'
            content = content.strip()
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end > start:
                content = content[start:end + 1]
            subtasks = json.loads(content)
            logger.info("llm_planning_success", steps=len(subtasks))
            return {"subtasks": subtasks, "current_task_index": 0, "task_description": task}
        except Exception:
            logger.warning("llm_planning_failed", exc_info=True)

    # Fallback: keyword matching
    for keyword, plan in FALLBACK_PLANS.items():
        if keyword in task:
            return {"subtasks": plan, "current_task_index": 0, "task_description": task}

    return {
        "subtasks": FALLBACK_PLANS["default"],
        "current_task_index": 0,
        "task_description": task,
    }
