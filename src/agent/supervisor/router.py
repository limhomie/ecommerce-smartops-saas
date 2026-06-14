"""Supervisor Router — determines which sub-agent to invoke next."""

from __future__ import annotations

from src.agent.state import AgentState
from src.observability.logger import get_logger

logger = get_logger(__name__)

# Maps agent type names to LangGraph node names
AGENT_ROUTE_MAP: dict[str, str] = {
    "conversion_analyst": "conversion_analyst",
    "competitor_analyst": "competitor_analyst",
    "sentiment_analyst": "sentiment_analyst",
    "content_factory": "content_factory",
    "sop_executor": "sop_executor",
    "report_generator": "report_generator",
}


def get_next_agent(state: AgentState) -> str:
    """Return the node name for the next sub-agent to execute."""
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)

    if index >= len(subtasks):
        return "END"

    current = subtasks[index]
    agent_type = current.get("agent", "report_generator")
    next_node = AGENT_ROUTE_MAP.get(agent_type, "report_generator")

    logger.info("routing", index=index, agent=agent_type, node=next_node)
    return next_node


def advance_task(state: AgentState) -> AgentState:
    """Increment the task index after a sub-agent completes."""
    index = state.get("current_task_index", 0)
    return {"current_task_index": index + 1}


def should_continue(state: AgentState) -> str:
    """Determine if there are more subtasks to process."""
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)

    if state.get("error"):
        return "END"

    if index >= len(subtasks):
        return "END"

    return get_next_agent(state)
