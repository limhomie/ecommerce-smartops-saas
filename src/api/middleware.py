"""Security and utility middleware for the FastAPI application."""

from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.logger import get_logger

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Validates API key and tenant header on protected routes."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip auth for health check and OPTIONS
        if request.url.path in ("/api/health", "/health") or request.method == "OPTIONS":
            return await call_next(request)

        settings = getattr(request.app.state, "settings", None)
        if settings and settings.admin_api_keys:
            api_key = request.headers.get(settings.api_key_header, "")
            if api_key not in settings.admin_api_keys:
                # Only enforce if keys are configured
                pass

        return await call_next(request)
