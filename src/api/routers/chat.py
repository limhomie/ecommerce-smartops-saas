"""Chat endpoint — SSE streaming conversation with the agent."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from src.observability.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/api/chat")
async def chat(request: Request):
    """SSE streaming chat. Accepts JSON body with 'message' and optional 'session_id'.

    Returns a Server-Sent Events stream of agent responses.
    """
    body = await request.json()
    user_message = body.get("message", "")
    session_id = body.get("session_id", str(uuid.uuid4()))
    user = getattr(request.state, "user", None)
    user_id = user["id"] if user else "default"

    async def event_stream():
        try:
            # Phase 1: Planning
            yield _sse("planning", {"status": "planning", "message": "正在分析您的需求..."})
            await asyncio.sleep(0.3)

            # Use the agent graph
            agent = request.app.state.agent_graph

            from langchain_core.messages import HumanMessage

            initial_state = {
                "messages": [HumanMessage(content=user_message)],
                "user_id": user_id,
                "session_id": session_id,
                "task_description": user_message,
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

            # Stream the final report
            report = final_state.get("final_report", "")
            action_items = final_state.get("action_items", [])

            if report:
                paragraphs = report.split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        yield _sse("content", {"content": para.strip()})
                        await asyncio.sleep(0.1)
            else:
                generated = final_state.get("generated_content", "")
                if generated:
                    yield _sse("content", {"content": generated})
                else:
                    yield _sse("content", {"content": "任务已完成，请查看报告。"})

            if action_items:
                yield _sse("action_items", {"items": action_items})

            yield _sse("done", {"status": "complete", "session_id": session_id})

        except Exception as exc:
            logger.exception("chat_error")
            yield _sse("error", {"error": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
