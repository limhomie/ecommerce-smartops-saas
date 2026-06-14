"""LangGraph agent assembly — builds the state machine for E-Commerce SmartOps.

Graph topology (Supervisor pattern):

    START -> planner -> [sub-agent loop] -> report_generator -> END

Sub-agents:
    - conversion_analyst: analyze sales/conversion data
    - competitor_analyst: search competitor prices & trends
    - sentiment_analyst: analyze social media sentiment
    - content_factory: generate product copy, SEO, ad scripts
    - sop_executor: handle logistics, returns, tickets

After each sub-agent, the router checks if more subtasks remain.
Once all subtasks are done, the report_generator synthesizes the final output.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.agent.state import AgentState
from src.agent.supervisor.planner import plan_task
from src.agent.analysts.conversion import conversion_analyst_node
from src.agent.analysts.competitor import competitor_analyst_node
from src.agent.analysts.sentiment import sentiment_analyst_node
from src.agent.operators.content import content_factory_node
from src.agent.operators.sop import sop_executor_node
from src.agent.operators.report import report_generator_node
from src.agent.edges.routing import route_after_analyst, route_after_planner
from src.observability.logger import get_logger

logger = get_logger(__name__)


def planner_node(state: AgentState) -> dict:
    """Entry node: decompose the user's task into subtasks."""
    from src.llm import get_llm

    llm = get_llm()
    result = plan_task(state, llm)
    logger.info("planner_done", subtasks=len(result.get("subtasks", [])))
    return result


def advance_and_route(state: AgentState) -> dict:
    """Advance task index after a sub-agent completes (used when not going to report)."""
    return {"current_task_index": state.get("current_task_index", 0) + 1}


def build_graph(max_steps: int = 10) -> StateGraph:
    """Build and compile the E-Commerce SmartOps agent graph.

    Args:
        max_steps: Maximum number of graph steps (LangGraph recursion_limit).

    Returns a compiled StateGraph ready for invocation.
    """
    workflow = StateGraph(AgentState)

    # ── Add nodes ──
    workflow.add_node("planner", planner_node)
    workflow.add_node("conversion_analyst", conversion_analyst_node)
    workflow.add_node("competitor_analyst", competitor_analyst_node)
    workflow.add_node("sentiment_analyst", sentiment_analyst_node)
    workflow.add_node("content_factory", content_factory_node)
    workflow.add_node("sop_executor", sop_executor_node)
    workflow.add_node("report_generator", report_generator_node)
    workflow.add_node("advance", advance_and_route)

    # ── Edges ──
    workflow.set_entry_point("planner")

    # Planner -> first sub-agent (or report_generator if no tasks)
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "conversion_analyst": "conversion_analyst",
            "competitor_analyst": "competitor_analyst",
            "sentiment_analyst": "sentiment_analyst",
            "content_factory": "content_factory",
            "sop_executor": "sop_executor",
            "report_generator": "report_generator",
        },
    )

    # After each analyst/operator -> advance -> route to next or report
    for node_name in [
        "conversion_analyst",
        "competitor_analyst",
        "sentiment_analyst",
        "content_factory",
        "sop_executor",
    ]:
        workflow.add_edge(node_name, "advance")
    workflow.add_conditional_edges(
        "advance",
        route_after_analyst,
        {
            "conversion_analyst": "conversion_analyst",
            "competitor_analyst": "competitor_analyst",
            "sentiment_analyst": "sentiment_analyst",
            "content_factory": "content_factory",
            "sop_executor": "sop_executor",
            "report_generator": "report_generator",
        },
    )

    # Report generator -> END
    workflow.add_edge("report_generator", END)

    # ── Compile with checkpointing ──
    checkpointer = MemorySaver()
    compiled = workflow.compile(checkpointer=checkpointer)

    logger.info("agent_graph_compiled", nodes=list(workflow.nodes.keys()))

    return compiled


# Module-level graph instance (lazy init)
_agent_graph = None


def get_agent_graph() -> StateGraph:
    """Return the singleton agent graph instance."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_graph()
    return _agent_graph
