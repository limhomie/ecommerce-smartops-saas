"""Conversation session management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: str = ""


@router.get("/api/sessions")
async def list_sessions(request: Request):
    """List all sessions for the current user."""
    user = request.state.user
    db = request.app.state.db
    return {"sessions": db.list_sessions(user["id"])}


@router.post("/api/sessions")
async def create_session(request: Request, body: CreateSessionRequest):
    """Create a new conversation session."""
    user = request.state.user
    db = request.app.state.db
    session = db.create_session(user["id"], body.title)
    return {"session": session}


@router.get("/api/sessions/{session_id}/tasks")
async def get_session_tasks(request: Request, session_id: str):
    """Get task history for a session."""
    user = request.state.user
    db = request.app.state.db
    tasks = db.list_tasks(user["id"], session_id)
    return {"tasks": tasks}
