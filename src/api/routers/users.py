"""User registration and profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str


@router.post("/api/users/register")
async def register_user(request: Request, body: RegisterRequest):
    """Register a new user. Returns api_key (shown once)."""
    user_service = request.app.state.user_service
    try:
        user = user_service.register_user(body.username)
    except ValueError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"error": "conflict", "detail": str(e)})
    return {"user": user}


@router.get("/api/users/me")
async def get_me(request: Request):
    """Return the current user's profile and usage stats."""
    user = request.state.user
    user_service = request.app.state.user_service
    return user_service.get_me(user)
