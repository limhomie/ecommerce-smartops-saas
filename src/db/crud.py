"""SQLite database with CRUD operations for users, sessions, and task history."""

from __future__ import annotations

import secrets
import sqlite3
import threading
from pathlib import Path
from typing import Any

from src.db.schema import ALL_TABLES
from src.observability.logger import get_logger

logger = get_logger(__name__)


def _generate_id() -> str:
    return secrets.token_hex(16)


def _generate_api_key() -> str:
    return "sk-" + secrets.token_hex(16)


class Database:
    """Thread-safe SQLite database for E-Commerce SmartOps Agent."""

    def __init__(self, path: str = "data/ecommerce.db") -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._connections: list[sqlite3.Connection] = []

    # ── Init ──

    def init(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            for ddl in ALL_TABLES:
                conn.execute(ddl)
            conn.commit()
        logger.info("db_initialized", path=str(self._path))

    # ── Users ──

    def create_user(self, username: str) -> dict[str, Any]:
        user_id = _generate_id()
        api_key = _generate_api_key()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (id, username, api_key) VALUES (?, ?, ?)",
                (user_id, username, api_key),
            )
            conn.commit()
        logger.info("user_created", username=username)
        return {"id": user_id, "username": username, "api_key": api_key}

    def get_user_by_api_key(self, key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, api_key, created_at FROM users WHERE api_key = ?",
                (key,),
            ).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, username, api_key, created_at FROM users ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Sessions ──

    def create_session(self, user_id: str, title: str = "") -> dict[str, Any]:
        session_id = _generate_id()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, user_id, title) VALUES (?, ?, ?)",
                (session_id, user_id, title),
            )
            conn.commit()
        return {"id": session_id, "user_id": user_id, "title": title}

    def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, user_id, title, created_at FROM sessions "
                "WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, user_id, title, created_at FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    # ── Task History ──

    def log_task(
        self,
        user_id: str,
        session_id: str,
        question: str,
        response_sum: str = "",
        subtasks: str = "[]",
        elapsed_ms: int = 0,
        cache_hit: bool = False,
    ) -> dict[str, Any]:
        task_id = _generate_id()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO task_history "
                "(id, user_id, session_id, question, response_sum, "
                "subtasks, elapsed_ms, cache_hit) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    user_id,
                    session_id,
                    question,
                    response_sum,
                    subtasks,
                    elapsed_ms,
                    1 if cache_hit else 0,
                ),
            )
            conn.commit()
        return {"id": task_id, "user_id": user_id, "session_id": session_id, "question": question}

    def list_tasks(
        self, user_id: str, session_id: str = ""
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM task_history WHERE user_id = ? AND session_id = ? "
                    "ORDER BY created_at DESC",
                    (user_id, session_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_history WHERE user_id = ? "
                    "ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
        return [dict(r) for r in rows]

    def get_user_stats(self, user_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total_tasks, "
                "COALESCE(AVG(elapsed_ms), 0) AS avg_elapsed_ms "
                "FROM task_history WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            session_row = conn.execute(
                "SELECT COUNT(*) AS total_sessions FROM sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return {
            "total_tasks": row["total_tasks"],
            "total_sessions": session_row["total_sessions"],
            "avg_elapsed_ms": round(row["avg_elapsed_ms"], 1),
        }

    def disable_user(self, user_id: str) -> bool:
        """Disable a user by removing their API key."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                return conn.total_changes > 0

    def get_system_stats(self) -> dict:
        """System-wide usage statistics."""
        with self._connect() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            task_count = conn.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
            avg_ms = conn.execute(
                "SELECT COALESCE(AVG(elapsed_ms), 0) FROM task_history"
            ).fetchone()[0]
            today = conn.execute(
                "SELECT COUNT(*) FROM task_history WHERE date(created_at) = date('now')"
            ).fetchone()[0]
        return {
            "total_users": user_count,
            "total_tasks": task_count,
            "avg_elapsed_ms": round(avg_ms, 1),
            "tasks_today": today,
        }

    # ── Internal ──

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        self._connections.append(conn)
        return conn

    def _close_all(self) -> None:
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
