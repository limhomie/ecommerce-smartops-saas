"""Agent task management endpoints."""

from __future__ import annotations

import uuid
from typing import Any

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


@router.post("/api/agent/tasks")
async def create_task(request: Request, body: TaskRequest):
    """Submit an agent task for async processing."""
    task_id = str(uuid.uuid4())
    session_id = body.session_id or task_id

    _task_store[task_id] = {
        "id": task_id,
        "status": "processing",
        "task": body.task,
        "session_id": session_id,
    }

    try:
        agent = request.app.state.agent_graph
        from langchain_core.messages import HumanMessage

        initial_state = {
            "messages": [HumanMessage(content=body.task)],
            "user_id": "default",
            "session_id": session_id,
            "task_description": body.task,
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
        }

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 12}
        final_state = await agent.ainvoke(initial_state, config)

        _task_store[task_id] = {
            "id": task_id,
            "status": "completed",
            "task": body.task,
            "result": {
                "report": final_state.get("final_report", ""),
                "action_items": final_state.get("action_items", []),
                "subtasks": final_state.get("subtasks", []),
            },
        }
    except Exception as e:
        logger.error("task_error", error=str(e))
        _task_store[task_id]["status"] = "failed"
        _task_store[task_id]["error"] = str(e)

    return {"task_id": task_id, "status": _task_store[task_id]["status"]}


@router.get("/api/agent/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status and result."""
    task = _task_store.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task
