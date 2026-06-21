"""Agent task management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.observability.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# In-memory task store (replace with DB in production)
_task_store: dict[str, dict] = {}


class TaskRequest(BaseModel):
    task: str
    session_id: str = ""


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None


def _classify_question(task: str) -> str:
    """Classify question complexity: simple | knowledge | complex."""
    t = task.strip().lower()
    # Simple greetings
    simple_patterns = ['你好', 'hello', 'hi', '谢谢', '再见', '你是谁', '你能做什么']
    for p in simple_patterns:
        if p in t:
            return 'simple'
    # Complex: analytics, content generation, multi-step
    complex_patterns = ['分析', '为什么下降', '生成', '广告脚本', '诊断', '周报', '综合',
                        '竞品', '转化率', '舆情', '报告']
    for p in complex_patterns:
        if p in t:
            return 'complex'
    # Everything else → RAG knowledge query
    return 'knowledge'


def _build_rag_answer_from_docs(question: str, docs: list[dict]) -> str:
    """Build a grounded answer by extracting relevant sentences from retrieved docs.
    Used in mock mode to simulate faithful RAG generation.
    """
    if not docs:
        return "抱歉，知识库中没有找到相关信息。"

    # Extract key sentences that overlap with question keywords
    q_words = set(question.replace('？','').replace('?','').replace('的','').replace('是',''))
    best_sentences: list[tuple[str, float]] = []

    for doc in docs[:5]:
        for sent in doc['content'].replace('\n', ' ').split('。'):
            sent = sent.strip()
            if len(sent) < 4:
                continue
            # Score: how many question chars appear in this sentence
            score = sum(1 for c in q_words if c in sent) / max(len(q_words), 1)
            score += (1 - doc.get('distance', 0)) * 0.5  # boost by relevance
            if score > 0.1:
                best_sentences.append((sent + '。', score))

    best_sentences.sort(key=lambda x: x[1], reverse=True)
    selected = best_sentences[:8]

    if not selected:
        return "抱歉，知识库中没有找到与您问题直接相关的信息。"

    # Format answer
    source_count = len(set(d.get('metadata', {}).get('collection', '?') for d in docs[:5]))
    lines = [f"根据知识库检索（{len(docs)}条相关记录，来自{source_count}个来源）：\n"]
    for sent, _ in selected:
        lines.append(f"• {sent}")
    return '\n'.join(lines)


@router.post("/api/agent/tasks")
async def create_task(request: Request):
    """Submit an agent task for async processing."""
    body_data = await request.json()
    task = body_data.get("task", "")
    task_id = str(uuid.uuid4())
    session_id = body_data.get("session_id") or task_id
    qclass = _classify_question(task)

    _task_store[task_id] = {
        "id": task_id,
        "status": "processing",
        "task": task,
        "session_id": session_id,
        "qclass": qclass,
    }

    try:
        from src.llm import get_llm
        llm = get_llm()

        # ── Simple: direct LLM answer ──
        if qclass == 'simple':
            resp = llm.invoke(f"简短回答用户问题，50字以内：{task}")
            text = resp.content if hasattr(resp, 'content') else str(resp)
            _task_store[task_id] = {
                "id": task_id, "status": "completed", "task": task,
                "result": {"report": text, "action_items": [], "subtasks": []},
            }

        # ── Knowledge: RAG search + relevance check + generation ──
        elif qclass == 'knowledge':
            from src.memory.manager import MemoryManager
            mm: MemoryManager = getattr(request.app.state, 'memory_manager', None)
            if mm is None:
                mm = MemoryManager.create_default()
            docs = mm.long_term.search_all(task, top_k=5)

            # Two-stage relevance check
            RELEVANCE_THRESHOLD = 0.75
            MIN_KEYWORD_OVERLAP = 3
            relevant_docs = [d for d in docs if d.get('distance', 9) <= RELEVANCE_THRESHOLD]

            # Check if ANY relevant doc has actual content overlap
            has_overlap = any(
                len(set(task) & set(d['content'])) >= MIN_KEYWORD_OVERLAP
                for d in relevant_docs
            )

            if not relevant_docs or not has_overlap:
                text = '抱歉，知识库中没有找到与您问题相关的信息。请尝试换个方式提问，或联系管理员补充相关资料。'
                _task_store[task_id] = {
                    "id": task_id, "status": "completed", "task": task,
                    "result": {"report": text, "action_items": [], "subtasks": [], "refused": True},
                }
            elif getattr(llm, 'provider_name', '') == 'mock':
                # Mock mode: construct answer directly from retrieved docs
                text = _build_rag_answer_from_docs(task, relevant_docs)
                _task_store[task_id] = {
                    "id": task_id, "status": "completed", "task": task,
                    "result": {"report": text, "action_items": [], "subtasks": [],
                               "refused": False, "sources": len(relevant_docs)},
                }
            else:
                context = '\n---\n'.join([
                    f"[来源{d.get('metadata',{}).get('collection','?')} | 相关度{1-d.get('distance',0):.0%}] {d['content'][:400]}"
                    for d in relevant_docs[:4]
                ])
                prompt = (
                    "你是电商客服助手。请严格基于以下知识库内容回答用户问题。\n\n"
                    "规则：\n"
                    "1. 只能使用知识库中的信息，不得编造\n"
                    "2. 如果知识库信息不足以完整回答，请明确指出缺失的部分\n"
                    "3. 回答要具体，引用知识库中的数据（如价格、电话、条款）\n"
                    "4. 如果知识库包含矛盾信息，指出矛盾并说明不同来源\n\n"
                    f"知识库：\n{context}\n\n"
                    f"用户问题：{task}\n\n"
                    "请用中文回答，条理清晰，有数据引用。"
                )
                resp = llm.invoke(prompt)
                text = resp.content if hasattr(resp, 'content') else str(resp)
                _task_store[task_id] = {
                    "id": task_id, "status": "completed", "task": task,
                    "result": {"report": text, "action_items": [], "subtasks": [],
                               "refused": False, "sources": len(relevant_docs)},
                }

        # ── Complex: full LangGraph agent pipeline ──
        else:
            agent = request.app.state.agent_graph
            from langchain_core.messages import HumanMessage

            user = getattr(request.state, "user", None)
            initial_state = {
                "messages": [HumanMessage(content=task)],
                "user_id": user["id"] if user else "default",
                "session_id": session_id,
                "task_description": task,
                "subtasks": [],
                "current_task_index": 0,
                "tool_results": {},
                "tool_calls": [],
                "retrieved_docs": [],
                "generated_content": "",
                "final_report": "",
                "action_items": [],
                "step_count": 0,
                "charts": [],
                "error": "",
                "next_agent": "",
                "cache_hit": False,
            }

            config = {"configurable": {"thread_id": session_id}, "recursion_limit": 12}
            final_state = await agent.ainvoke(initial_state, config)

            _task_store[task_id] = {
                "id": task_id,
                "status": "completed",
                "task": task,
                "result": {
                    "report": final_state.get("final_report", ""),
                    "action_items": final_state.get("action_items", []),
                    "subtasks": final_state.get("subtasks", []),
                },
            }
    except Exception as exc:
        logger.exception("task_error")
        _task_store[task_id]["status"] = "failed"
        _task_store[task_id]["error"] = str(exc)

    return {"task_id": task_id, "status": _task_store[task_id]["status"]}


@router.get("/api/agent/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status and result."""
    task = _task_store.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task
