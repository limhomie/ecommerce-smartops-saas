"""Conditional edge routing for the LangGraph agent.

Determines which node to visit next based on the agent state.
"""

from __future__ import annotations

from src.agent.state import AgentState
from src.agent.supervisor.router import AGENT_ROUTE_MAP


def route_next_agent(state: AgentState) -> str:
    """After each sub-agent completes, route to the next one or end."""
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0)

    if state.get("error"):
        return "report_generator"

    if index >= len(subtasks):
        return "report_generator"

    current = subtasks[index]
    agent_type = current.get("agent", "report_generator")
    return AGENT_ROUTE_MAP.get(agent_type, "report_generator")


def route_after_planner(state: AgentState) -> str:
    """After planner, route to the first sub-agent."""
    subtasks = state.get("subtasks", [])
    if not subtasks:
        return "report_generator"

    first = subtasks[0]
    agent_type = first.get("agent", "report_generator")
    return AGENT_ROUTE_MAP.get(agent_type, "report_generator")


def route_after_analyst(state: AgentState) -> str:
    """After an analyst completes, check if we should continue or generate report."""
    subtasks = state.get("subtasks", [])
    index = state.get("current_task_index", 0) + 1  # Next task

    if index >= len(subtasks):
        return "report_generator"

    next_task = subtasks[index]
    agent_type = next_task.get("agent", "report_generator")
    return AGENT_ROUTE_MAP.get(agent_type, "report_generator")
