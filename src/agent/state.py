"""AgentState — the shared state that flows through the LangGraph.

Every node reads from and writes to this TypedDict.
"""

from __future__ import annotations

from operator import add as _add
from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


def add_charts(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer: merge chart lists from multiple nodes."""
    return left + right


class AgentState(TypedDict):
    # ── Core conversation ──
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str

    # ── Task planning ──
    task_description: str
    subtasks: list[dict]
    current_task_index: int

    # ── Tool execution ──
    tool_results: dict[str, Any]
    tool_calls: list[dict]

    # ── RAG results ──
    retrieved_docs: list[dict]
    generated_content: str

    # ── Charts (merged across nodes) ──
    charts: Annotated[list[dict], add_charts]

    # ── Final output ──
    final_report: str
    action_items: list[str]

    # ── Control ──
    step_count: int
    error: str
    next_agent: str
    cache_hit: bool
