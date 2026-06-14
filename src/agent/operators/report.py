"""Report Generator Agent — synthesizes all analysis results into a structured report."""

from __future__ import annotations

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)


def report_generator_node(state: AgentState) -> dict:
    """Synthesize all collected data and analyses into a final report with action items."""

    task = state.get("task_description", "")
    tool_results = state.get("tool_results", {})
    subtasks = state.get("subtasks", [])

    logger.info("report_generator_start", results_count=len(tool_results))

    # Collect outputs from previous agents
    previous_content = state.get("generated_content", "")

    llm = _get_llm()
    prompt = f"""你是一个电商运营总监，请基于以下所有分析结果，生成一份综合报告。

原始任务：{task}

执行的子任务：
{_format_subtasks(subtasks)}

收集的数据源：{', '.join(tool_results.keys())}

前面的分析结果：
{previous_content[:2000] if previous_content else "（无前置分析）"}

请生成以下结构的报告（Markdown 格式）：

## 1. 执行摘要
（3-5句话概括核心发现）

## 2. 数据分析
（关键指标和趋势）

## 3. 问题诊断
（根因分析）

## 4. 行动建议
（具体可执行的改进方案，每项标注优先级 🔴高 🟡中 🟢低）

## 5. 跟进计划
（时间线和负责人建议）
"""

    report = _invoke_llm(llm, prompt)

    # Extract action items
    action_items = _extract_action_items(report)

    return {
        "final_report": report,
        "action_items": action_items,
        "generated_content": report,
        "step_count": state.get("step_count", 0) + 1,
    }


def _format_subtasks(subtasks: list[dict]) -> str:
    if not subtasks:
        return "（无）"
    return "\n".join(
        f"  {s['step']}. [{s.get('agent', 'N/A')}] {s.get('description', '')}"
        for s in subtasks
    )


def _extract_action_items(report: str) -> list[str]:
    """Simple extraction of action items from report."""
    items = []
    in_actions = False
    for line in report.split("\n"):
        if "行动建议" in line or "改进方案" in line:
            in_actions = True
            continue
        if in_actions and line.startswith("##"):
            break
        if in_actions and line.strip().startswith(("- ", "* ", "1.", "2.", "3.")):
            items.append(line.strip().lstrip("- *").strip())
    return items if items else ["查看完整报告获取行动建议"]


def _get_llm():
    from src.llm import get_llm
    return get_llm()


def _invoke_llm(llm, prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        from src.llm.mock import MOCK_RESPONSES
        return MOCK_RESPONSES.get("report", "报告已生成。")
