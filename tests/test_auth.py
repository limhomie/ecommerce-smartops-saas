"""Tests for src.auth — API Key auth, user registration, rate limiting."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.auth.middleware import AuthMiddleware
from src.auth.rate_limit import RateLimiter
from src.auth.user_service import UserService
from src.db import Database


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "test_auth.db")
        database = Database(path)
        database.init()
        yield database
        database._close_all()


@pytest.fixture
def user_service(db):
    return UserService(db)


@pytest.fixture
def client(db, user_service):
    app = FastAPI()
    app.add_middleware(AuthMiddleware, db=db, user_service=user_service)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/protected")
    async def protected(request: Request):
        return {"user": request.state.user["username"]}

    app.state.db = db
    return TestClient(app)


class TestAuthMiddleware:
    def test_no_key_returns_401(self, client):
        resp = client.get("/api/protected")
        assert resp.status_code == 401
        assert "unauthorized" in resp.json()["error"]

    def test_bad_key_returns_401(self, client):
        resp = client.get("/api/protected", headers={"X-API-Key": "sk-badkey"})
        assert resp.status_code == 401

    def test_valid_key_returns_200(self, client, db):
        user = db.create_user("testuser")
        resp = client.get("/api/protected", headers={"X-API-Key": user["api_key"]})
        assert resp.status_code == 200
        assert resp.json()["user"] == "testuser"

    def test_health_bypasses_auth(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestUserService:
    def test_register_user(self, user_service):
        user = user_service.register_user("alice")
        assert user["username"] == "alice"
        assert user["api_key"].startswith("sk-")

    def test_register_invalid_username_short(self, user_service):
        with pytest.raises(ValueError, match="3-32"):
            user_service.register_user("ab")

    def test_register_invalid_username_chars(self, user_service):
        with pytest.raises(ValueError):
            user_service.register_user("hello world!")

    def test_register_chinese_username(self, user_service):
        user = user_service.register_user("张三运营")
        assert user["username"] == "张三运营"

    def test_duplicate_username(self, user_service):
        user_service.register_user("bob")
        with pytest.raises(ValueError, match="taken"):
            user_service.register_user("bob")

    def test_get_me(self, user_service, db):
        user = user_service.register_user("charlie")
        sess = db.create_session(user["id"])
        db.log_task(user["id"], sess["id"], "Q")
        profile = user_service.get_me(user)
        assert profile["username"] == "charlie"
        assert profile["stats"]["total_tasks"] == 1


class TestRateLimiter:
    def test_allows_up_to_max(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert rl.check("user1") is True

    def test_blocks_after_max(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert rl.check("user2") is True
        assert rl.check("user2") is False

    def test_separate_users(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        assert rl.check("a") is True
        assert rl.check("a") is True
        assert rl.check("a") is False
        assert rl.check("b") is True  # different user

    def test_reset(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.check("c")
        rl.check("c")
        assert rl.check("c") is False
        rl.reset("c")
        assert rl.check("c") is True
