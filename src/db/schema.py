"""SQLite DDL statements for E-Commerce SmartOps Agent."""

from __future__ import annotations

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    username   TEXT NOT NULL UNIQUE,
    api_key    TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    title      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_TASK_HISTORY = """
CREATE TABLE IF NOT EXISTS task_history (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(id),
    session_id   TEXT NOT NULL REFERENCES sessions(id),
    question     TEXT NOT NULL,
    response_sum TEXT NOT NULL DEFAULT '',
    subtasks     TEXT NOT NULL DEFAULT '[]',
    elapsed_ms   INTEGER NOT NULL DEFAULT 0,
    cache_hit    INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

ALL_TABLES = [CREATE_USERS, CREATE_SESSIONS, CREATE_TASK_HISTORY]
