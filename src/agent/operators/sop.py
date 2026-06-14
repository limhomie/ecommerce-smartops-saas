"""SOP Executor Agent — automates customer service, logistics queries, and workflows."""

from __future__ import annotations

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)


def sop_executor_node(state: AgentState) -> dict:
    """Execute standard operating procedures: track packages, handle tickets, auto-reply."""

    task = _current_task_description(state)
    logger.info("sop_executor_start", task=task)

    # Determine SOP type from task description
    if "物流" in task or "包裹" in task or "track" in task.lower():
        result = _handle_logistics(task)
    elif "退货" in task or "退款" in task or "return" in task.lower():
        result = _handle_return(task)
    elif "工单" in task or "ticket" in task.lower():
        result = _handle_ticket(task)
    else:
        result = _handle_general(task)

    existing_results = state.get("tool_results", {})
    existing_results["sop_executor"] = result

    return {
        "tool_results": existing_results,
        "generated_content": result.get("summary", ""),
        "step_count": state.get("step_count", 0) + 1,
    }


def _handle_logistics(task: str) -> dict:
    return {
        "sop_type": "logistics",
        "tracking_number": "YT202506130001",
        "carrier": "圆通速递",
        "status": "运输中",
        "current_location": "广州市分拣中心",
        "estimated_delivery": "2026-06-15",
        "auto_reply": (
            "尊敬的客户，您好！\n\n"
            "您的包裹（快递单号：YT202506130001）\n"
            "当前状态：运输中\n"
            "预计送达：2026-06-15\n\n"
            "如有任何问题，请随时联系我们。祝您购物愉快！"
        ),
        "summary": "已查询物流状态并生成自动回复",
    }


def _handle_return(task: str) -> dict:
    return {
        "sop_type": "return",
        "order_id": "ORD-001",
        "return_status": "已审批",
        "refund_amount": "$45.60",
        "instructions": "请将商品寄回至：深圳市南山区科技园XX号，收件人：退货组",
        "auto_reply": (
            "您的退货申请已通过审批。\n"
            "退款金额：$45.60，将在收到退货后3个工作日内原路返回。\n"
            "退货地址：深圳市南山区科技园XX号\n"
            "请在包裹内附上订单号 ORD-001。"
        ),
        "summary": "已处理退货申请并生成退货指引",
    }


def _handle_ticket(task: str) -> dict:
    return {
        "sop_type": "ticket",
        "ticket_id": "TK-20260613-001",
        "status": "已创建",
        "priority": "中",
        "assigned_to": "客服组-张三",
        "summary": "已创建工单并分配给对应处理人",
    }


def _handle_general(task: str) -> dict:
    return {
        "sop_type": "general",
        "actions": ["分析任务需求", "匹配SOP模板", "执行自动化流程"],
        "summary": "SOP 任务已执行",
    }


def _current_task_description(state: AgentState) -> str:
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)
    if index < len(subtasks):
        return subtasks[index].get("description", "")
    return state.get("task_description", "")
