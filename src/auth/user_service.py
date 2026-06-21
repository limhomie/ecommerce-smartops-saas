"""User registration and profile service."""

from __future__ import annotations

import re
from typing import Any

from src.observability.logger import get_logger

logger = get_logger(__name__)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_一-鿿]{3,32}$")


class UserService:
    """Handles user registration and profile queries."""

    def __init__(self, db: Any) -> None:
        self._db = db

    def register_user(self, username: str) -> dict[str, Any]:
        """Register a new user. Returns user dict with api_key (shown once)."""
        username = username.strip()
        if not _USERNAME_RE.match(username):
            raise ValueError(
                "Username must be 3-32 characters, alphanumeric/underscore/Chinese only"
            )

        existing = self._get_user_by_username(username)
        if existing is not None:
            raise ValueError("Username already taken")

        user = self._db.create_user(username)
        logger.info("user_registered", username=username)
        return user

    def get_me(self, user: dict[str, Any]) -> dict[str, Any]:
        """Return user profile with usage stats."""
        stats = self._db.get_user_stats(user["id"])
        return {
            "id": user["id"],
            "username": user["username"],
            "created_at": user.get("created_at", ""),
            "stats": stats,
        }

    def _get_user_by_username(self, username: str) -> dict[str, Any] | None:
        users = self._db.list_users()
        for u in users:
            if u["username"] == username:
                return u
        return None
