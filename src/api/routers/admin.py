"""Admin endpoints for user management and system stats."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _is_admin(request: Request) -> bool:
    """Check if the current request has admin privileges."""
    user = getattr(request.state, "user", None)
    if not user:
        return False
    settings = request.app.state.settings
    api_key = request.headers.get(settings.api_key_header, "")
    return api_key in settings.admin_api_keys


def _require_admin(request: Request):
    if not _is_admin(request):
        return {"error": "admin only"}, 403
    return None


@router.get("/api/admin/users")
async def list_users(request: Request):
    """List all users (admin only)."""
    err = _require_admin(request)
    if err:
        return err
    db = request.app.state.db
    return {"users": db.list_users()}


@router.post("/api/admin/users/{user_id}/disable")
async def disable_user(request: Request, user_id: str):
    """Disable a user by ID (admin only)."""
    err = _require_admin(request)
    if err:
        return err
    db = request.app.state.db
    ok = db.disable_user(user_id)
    return {"disabled": ok, "user_id": user_id}


@router.get("/api/admin/stats")
async def system_stats(request: Request):
    """System-wide usage statistics (admin only)."""
    err = _require_admin(request)
    if err:
        return err
    db = request.app.state.db
    return {"stats": db.get_system_stats()}


@router.get("/api/admin/sync/status")
async def sync_status():
    import json
    from pathlib import Path
    reg = Path("data/doc_registry.json")
    entries = len(json.loads(reg.read_text(encoding="utf-8"))) if reg.exists() else 0
    return {"entries": entries}


import threading
_sync_results: dict[str, dict] = {}

@router.post("/api/admin/sync")
async def trigger_sync():
    import uuid
    job_id = str(uuid.uuid4())
    _sync_results[job_id] = {"status": "running", "result": None}

    def _run():
        from config.settings import Settings
        from src.memory.long_term import LongTermMemory
        from src.memory.sync import DocumentSync
        from src.memory.vector_store import VectorStore
        s = Settings()
        store = VectorStore(s)
        ltm = LongTermMemory(store)
        syncer = DocumentSync(ltm)
        result = syncer.sync_directory("data/documents/products", "products")
        _sync_results[job_id] = {"status": "done", "result": result}

    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job_id, "status": "running"}


@router.get("/api/admin/sync/status/{job_id}")
async def sync_job_status(job_id: str):
    job = _sync_results.get(job_id)
    if not job:
        return {"status": "not_found"}
    return job
