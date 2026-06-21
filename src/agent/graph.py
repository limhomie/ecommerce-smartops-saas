"""LangGraph agent assembly — builds the state machine for E-Commerce SmartOps.

Graph topology (Supervisor pattern with query cache):

    START -> check_cache -> [hit] -> END
                         -> [miss] -> planner -> [sub-agent loop]
                                  -> report_generator -> write_cache -> END

Sub-agents:
    - conversion_analyst: analyze sales/conversion data
    - competitor_analyst: search competitor prices & trends
    - sentiment_analyst: analyze social media sentiment
    - content_factory: generate product copy, SEO, ad scripts
    - sop_executor: handle logistics, returns, tickets

After each sub-agent, the router checks if more subtasks remain.
Once all subtasks are done, the report_generator synthesizes the final output.
The query cache (check_cache / write_cache) skips the entire pipeline on repeat questions.
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
from src.agent.cache import get_agent_cache
from src.observability.logger import get_logger

logger = get_logger(__name__)

# ── Conversation store with semantic retrieval + auto-summarization ──
#    Session-level dict: session_id → [{role, content, embedding?, summarized?}, ...]
_conv_store: dict[str, list[dict]] = {}
_CONV_WINDOW = 3      # last N turns always included (time window)
_SEMANTIC_TOP_K = 3   # up to K semantically-similar turns (regardless of distance)
_MAX_RAW_TURNS = 6    # beyond this, oldest turns get auto-summarized

# Shared embedding function (lazy, reused across callers)
_shared_embedding_fn = None


def _get_shared_embedding_fn():
    """Lazy-load BGE embedding model, shared with cache semantic stage."""
    global _shared_embedding_fn
    if _shared_embedding_fn is not None:
        return _shared_embedding_fn
    try:
        import sentence_transformers
        from config.settings import Settings
        s = Settings()
        for local_only in (True, False):
            try:
                _shared_embedding_fn = sentence_transformers.SentenceTransformer(
                    s.embedding_model, device=s.embedding_device,
                    local_files_only=local_only,
                )
                break
            except Exception:
                if not local_only:
                    raise
        _shared_embedding_fn.encode(["warmup"], show_progress_bar=False)
        logger.info("conv_embedding_ready", model=s.embedding_model)
    except Exception as e:
        logger.warning("conv_embedding_unavailable", error=str(e))
        _shared_embedding_fn = None
    return _shared_embedding_fn


def _embed(text: str) -> list[float] | None:
    fn = _get_shared_embedding_fn()
    if fn is None:
        return None
    try:
        return fn.encode([text], show_progress_bar=False)[0].tolist()
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _format_history(history: list[dict], current_question: str = "") -> str:
    """Build formatted context from history entries.

    Strategy:
      1. Always include the last _CONV_WINDOW turns (time proximity).
      2. If current_question is provided, do a semantic search across ALL
         past user messages and include up to _SEMANTIC_TOP_K distant but
         semantically-related turns (deduplicated with time window).
      3. Old turns beyond _MAX_RAW_TURNS are shown as one-line summaries.
    """
    if not history:
        return ""

    # Mark which indices to include
    selected: set[int] = set()

    # (1) Time window — always include last N
    for i in range(max(0, len(history) - _CONV_WINDOW), len(history)):
        selected.add(i)

    # (2) Semantic search — find distant but related turns
    if current_question:
        q_emb = _embed(current_question)
        if q_emb is not None:
            scored = []
            for i, entry in enumerate(history):
                if entry.get("role") != "user":
                    continue
                emb = entry.get("embedding")
                if emb is None:
                    continue
                sim = _cosine(q_emb, emb)
                if sim >= 0.85 and i not in selected:  # threshold + dedup
                    scored.append((i, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            for i, _ in scored[:_SEMANTIC_TOP_K]:
                selected.add(i)
                logger.info("conv_semantic_hit", turn=i, similarity=round(scored[0][1], 3))

    # (3) Build lines — summaries for old, raw for recent
    lines = []
    for i in sorted(selected):
        entry = history[i]
        role = "用户" if entry["role"] == "user" else "助手"
        if entry.get("summarized"):
            lines.append(f"[{role} 摘要]: {entry['content']}")
        else:
            text = entry["content"][:250]
            lines.append(f"[{role}]: {text}")

    return "\n".join(lines)


def _maybe_summarize_old_turns(session_id: str, llm) -> None:
    """Summarize oldest turns if session exceeds _MAX_RAW_TURNS."""
    turns = _conv_store.get(session_id, [])
    if len(turns) <= _MAX_RAW_TURNS:
        return

    # Find the oldest non-summarized turn
    for entry in turns:
        if not entry.get("summarized"):
            _summarize_one(entry, llm)
            break  # one per invocation to spread cost


def _log_task_to_db(
    user_id: str, session_id: str, question: str, state: dict
) -> None:
    """Write a task_history record via the db module (best-effort)."""
    from src.db import Database

    db = Database()
    db.init()
    subtasks = state.get("subtasks", [])
    import json

    db.log_task(
        user_id=user_id or "default",
        session_id=session_id,
        question=question,
        response_sum=state.get("final_report", "")[:300],
        subtasks=json.dumps(subtasks, ensure_ascii=False),
        elapsed_ms=0,
        cache_hit=bool(state.get("cache_hit")),
    )


def _summarize_one(entry: dict, llm) -> None:
    try:
        prompt = (
            "将以下内容压缩为一句中文摘要（20字以内，只保留关键信息）：\n"
            f"{entry['content'][:500]}"
        )
        resp = llm.invoke(prompt)
        summary = resp.content if hasattr(resp, "content") else str(resp)
        entry["content"] = summary.strip()[:80]
        entry["summarized"] = True
        logger.info("conv_summarized", preview=entry["content"][:60])
    except Exception:
        logger.exception("conv_summarize_failed")


def planner_node(state: AgentState) -> dict:
    """Entry node: decompose the user's task into subtasks.

    Injects conversation history with:
      - Time window (last 3 turns)
      - Semantic retrieval (distant but related turns via BGE)
      - Auto-summarization (old turns compressed)
    """
    from src.llm import get_llm

    task = state.get("task_description", "")
    session_id = state.get("session_id", "default")
    llm = get_llm()

    # Auto-summarize if conversation is too long
    _maybe_summarize_old_turns(session_id, llm)

    # Build context: time window + semantic retrieval
    all_turns = _conv_store.get(session_id, [])
    context = _format_history(all_turns, current_question=task)

    result = plan_task(state, llm, extra_context=context)
    logger.info("planner_done", subtasks=len(result.get("subtasks", [])),
                history_turns=len(all_turns), context_chars=len(context))

    # Remember the user's question (with embedding)
    if task:
        _conv_store.setdefault(session_id, []).append({
            "role": "user", "content": task, "embedding": _embed(task),
            "summarized": False,
        })

    return result


def advance_and_route(state: AgentState) -> dict:
    """Advance task index after a sub-agent completes (used when not going to report)."""
    return {"current_task_index": state.get("current_task_index", 0) + 1}


def check_cache_node(state: AgentState) -> dict:
    """Check if this question has a cached response. If so, populate final fields."""
    messages = state.get("messages", [])
    if not messages:
        return {"cache_hit": False}

    question = _extract_question(messages[-1])
    user_id = state.get("user_id", "")

    cache = get_agent_cache()
    cached = cache.get(question, user_id=user_id)
    if cached:
        logger.info("agent_cache_hit", question_preview=question[:80])
        return {
            "cache_hit": True,
            "final_report": cached.get("final_report", ""),
            "charts": cached.get("charts", []),
            "action_items": cached.get("action_items", []),
            "generated_content": cached.get("generated_content", ""),
        }
    return {"cache_hit": False}


def write_cache_node(state: AgentState) -> dict:
    """Store the final result in the query cache (skip if was a cache hit)."""
    if state.get("cache_hit"):
        return {}

    messages = state.get("messages", [])
    if not messages:
        return {}

    question = _extract_question(messages[-1])
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "default")

    cache = get_agent_cache()
    cache.set(question, {
        "final_report": state.get("final_report", ""),
        "charts": state.get("charts", []),
        "action_items": state.get("action_items", []),
        "generated_content": state.get("generated_content", ""),
    }, user_id=user_id)

    # Persist to task_history (if db is available)
    try:
        _log_task_to_db(
            user_id=user_id, session_id=session_id, question=question,
            state=state,
        )
    except Exception:
        logger.exception("task_history_write_failed")

    # Remember assistant response for future conversation context
    report = state.get("final_report", "")
    if report:
        _conv_store.setdefault(session_id, []).append({
            "role": "assistant", "content": report[:400], "embedding": None,
            "summarized": False,
        })

    return {}


def route_after_cache_check(state: AgentState) -> str:
    """Route to END if cache hit, otherwise proceed to planner."""
    return END if state.get("cache_hit") else "planner"


def _extract_question(msg) -> str:
    """Extract question text from a LangChain message object."""
    if hasattr(msg, "content"):
        return msg.content if isinstance(msg.content, str) else str(msg.content)
    return str(msg)


def build_graph(max_steps: int = 10) -> StateGraph:
    """Build and compile the E-Commerce SmartOps agent graph.

    Args:
        max_steps: Maximum number of graph steps (LangGraph recursion_limit).

    Returns a compiled StateGraph ready for invocation.
    """
    workflow = StateGraph(AgentState)

    # ── Add nodes ──
    workflow.add_node("check_cache", check_cache_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("conversion_analyst", conversion_analyst_node)
    workflow.add_node("competitor_analyst", competitor_analyst_node)
    workflow.add_node("sentiment_analyst", sentiment_analyst_node)
    workflow.add_node("content_factory", content_factory_node)
    workflow.add_node("sop_executor", sop_executor_node)
    workflow.add_node("report_generator", report_generator_node)
    workflow.add_node("write_cache", write_cache_node)
    workflow.add_node("advance", advance_and_route)

    # ── Edges ──
    workflow.set_entry_point("check_cache")

    # Check cache: hit → END, miss → planner
    workflow.add_conditional_edges(
        "check_cache",
        route_after_cache_check,
        {"planner": "planner", END: END},
    )

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

    # Report generator -> write cache -> END
    workflow.add_edge("report_generator", "write_cache")
    workflow.add_edge("write_cache", END)

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
