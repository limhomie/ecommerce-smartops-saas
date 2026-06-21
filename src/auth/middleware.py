"""FastAPI middleware for API Key authentication."""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.logger import get_logger

logger = get_logger(__name__)

_AUTH_WHITELIST = {"/api/health", "/api/users/register", "/docs", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header against the users table."""

    def __init__(self, app, db: Any, user_service: Any) -> None:
        super().__init__(app)
        self._db = db
        self._user_service = user_service

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Whitelisted paths skip auth
        path = request.url.path.rstrip("/")
        if path in _AUTH_WHITELIST or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "detail": "Missing X-API-Key header"},
            )

        user = self._db.get_user_by_api_key(api_key)
        if user is None:
            logger.warning("auth_invalid_key")
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "detail": "Invalid API Key"},
            )

        request.state.user = user
        return await call_next(request)
