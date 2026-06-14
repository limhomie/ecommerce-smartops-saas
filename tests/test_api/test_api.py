"""Tests for the FastAPI endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from config.settings import Settings


@pytest.fixture
def test_app():
    settings = Settings(environment="dev", llm_provider="mock", debug=False)
    return create_app(settings)


@pytest.mark.asyncio
async def test_health_endpoint(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_endpoint(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"message": "帮我分析转化率下降的原因", "session_id": "test"},
            timeout=30,
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_agent_task(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent/tasks",
            json={"task": "生成运营周报"},
            timeout=30,
        )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data


@pytest.mark.asyncio
async def test_knowledge_search(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/search",
            json={"query": "物流政策", "collection": "enterprise_wiki"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_knowledge_stats(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/knowledge/stats")
    assert response.status_code == 200
