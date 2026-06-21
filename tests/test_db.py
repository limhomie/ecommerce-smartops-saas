"""Tests for src.db — SQLite database layer."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

import pytest

from src.db import Database


@pytest.fixture
def db():
    """Fresh database in a temp file for each test."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "test.db")
        database = Database(path)
        database.init()
        yield database
        # Force-close all connections so Windows can clean up WAL files
        database._close_all()


class TestInit:
    def test_init_creates_tables(self, db):
        conn = db._connect()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [r["name"] for r in tables]
        assert "users" in names
        assert "sessions" in names
        assert "task_history" in names


class TestUsers:
    def test_create_user(self, db):
        user = db.create_user("alice")
        assert user["username"] == "alice"
        assert user["api_key"].startswith("sk-")
        assert len(user["api_key"]) == 35  # "sk-" + 32 hex

    def test_get_user_by_api_key(self, db):
        user = db.create_user("bob")
        found = db.get_user_by_api_key(user["api_key"])
        assert found is not None
        assert found["username"] == "bob"

    def test_get_user_bad_key_returns_none(self, db):
        assert db.get_user_by_api_key("sk-deadbeef") is None

    def test_duplicate_username_raises(self, db):
        db.create_user("eve")
        with pytest.raises(Exception):
            db.create_user("eve")

    def test_list_users(self, db):
        db.create_user("u1")
        db.create_user("u2")
        users = db.list_users()
        assert len(users) == 2


class TestSessions:
    def test_create_session(self, db):
        user = db.create_user("s1")
        sess = db.create_session(user["id"], "My Session")
        assert sess["title"] == "My Session"
        assert sess["user_id"] == user["id"]
        assert len(sess["id"]) == 32

    def test_list_sessions_filtered_by_user(self, db):
        u1 = db.create_user("u1")
        u2 = db.create_user("u2")
        db.create_session(u1["id"], "U1 Session")
        db.create_session(u2["id"], "U2 Session")
        assert len(db.list_sessions(u1["id"])) == 1
        assert len(db.list_sessions(u2["id"])) == 1

    def test_get_session(self, db):
        user = db.create_user("s2")
        sess = db.create_session(user["id"], "Find Me")
        found = db.get_session(sess["id"])
        assert found is not None
        assert found["title"] == "Find Me"

    def test_get_session_missing(self, db):
        assert db.get_session("nonexistent") is None


class TestTaskHistory:
    def test_log_task(self, db):
        user = db.create_user("t1")
        sess = db.create_session(user["id"])
        task = db.log_task(user["id"], sess["id"], "What is conversion rate?",
                           response_sum="Analysis result", elapsed_ms=1500)
        assert task["question"] == "What is conversion rate?"
        assert len(task["id"]) == 32

    def test_list_tasks(self, db):
        user = db.create_user("t2")
        sess = db.create_session(user["id"])
        db.log_task(user["id"], sess["id"], "Q1")
        db.log_task(user["id"], sess["id"], "Q2")
        tasks = db.list_tasks(user["id"], sess["id"])
        assert len(tasks) == 2

    def test_list_tasks_user_isolation(self, db):
        u1 = db.create_user("iso1")
        u2 = db.create_user("iso2")
        s1 = db.create_session(u1["id"])
        s2 = db.create_session(u2["id"])
        db.log_task(u1["id"], s1["id"], "ISO1")
        db.log_task(u2["id"], s2["id"], "ISO2")
        assert len(db.list_tasks(u1["id"])) == 1
        assert len(db.list_tasks(u2["id"])) == 1

    def test_cache_hit_flag(self, db):
        user = db.create_user("t3")
        sess = db.create_session(user["id"])
        db.log_task(user["id"], sess["id"], "Q", cache_hit=True)
        tasks = db.list_tasks(user["id"], sess["id"])
        assert tasks[0]["cache_hit"] == 1

    def test_get_user_stats(self, db):
        user = db.create_user("t4")
        sess = db.create_session(user["id"])
        db.log_task(user["id"], sess["id"], "Q1", elapsed_ms=500)
        db.log_task(user["id"], sess["id"], "Q2", elapsed_ms=1500)
        stats = db.get_user_stats(user["id"])
        assert stats["total_tasks"] == 2
        assert stats["total_sessions"] == 1
        assert stats["avg_elapsed_ms"] == 1000.0


class TestConcurrency:
    def test_concurrent_writes(self, db):
        user = db.create_user("concurrent")
        sess = db.create_session(user["id"])
        errors: list[Exception] = []

        def writer(n: int):
            try:
                db.log_task(user["id"], sess["id"], f"Q{n}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        tasks = db.list_tasks(user["id"], sess["id"])
        assert len(tasks) == 5
