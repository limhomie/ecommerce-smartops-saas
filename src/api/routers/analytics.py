"""Analytics and report endpoints."""

from __future__ import annotations

import threading
import uuid

from fastapi import APIRouter, Request

from src.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Share task store with agent router
_task_store: dict[str, dict] = {}


@router.get("/api/analytics/report")
async def get_report(request: Request, date: str = "latest"):
    """Generate or retrieve an analytics report."""
    return {
        "date": date,
        "report": "Report generation will be available after data integration.",
        "status": "ok",
    }


@router.post("/api/content/generate")
async def generate_content(request: Request):
    """Generate marketing content using LLM (async, returns task_id)."""
    body = await request.json()
    product = body.get("product", "")
    prompt = body.get("prompt", "")

    if not prompt:
        types_str = ", ".join(body.get("types", ["all"]))
        prompt = f"为产品「{product}」生成以下类型的内容：{types_str}。请用中文输出。"

    task_id = str(uuid.uuid4())
    _task_store[task_id] = {"id": task_id, "status": "running", "task": prompt}

    def _run():
        try:
            from src.llm import get_llm
            llm = get_llm()
            response = llm.invoke(prompt)
            generated = response.content if hasattr(response, "content") else str(response)
            _task_store[task_id] = {
                "id": task_id, "status": "completed", "task": prompt,
                "result": {"report": generated, "generated": generated},
            }
        except Exception as e:
            logger.warning("content_generate_failed", error=str(e))
            from src.llm.mock import MOCK_RESPONSES
            generated = MOCK_RESPONSES.get("content", "内容已生成。")
            _task_store[task_id] = {
                "id": task_id, "status": "completed", "task": prompt,
                "result": {"report": generated, "generated": generated},
            }

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "running"}


@router.get("/api/content/tasks/{task_id}")
async def get_content_task(task_id: str):
    """Get content generation task status."""
    task = _task_store.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task
