"""Redis short-term conversation memory.

Stores recent conversation turns with TTL-based expiry.
"""

from __future__ import annotations

import json
import time
from typing import Any


class InMemoryBackend:
    """Fallback in-memory backend when Redis is unavailable."""

    def __init__(self, max_messages: int = 50):
        self._store: dict[str, list[dict]] = {}
        self.max_messages = max_messages

    async def get(self, key: str) -> list[dict]:
        return self._store.get(key, [])

    async def append(self, key: str, entry: dict) -> None:
        if key not in self._store:
            self._store[key] = []
        self._store[key].append(entry)
        if len(self._store[key]) > self.max_messages:
            self._store[key] = self._store[key][-self.max_messages:]

    async def clear(self, key: str) -> None:
        self._store.pop(key, None)


class RedisBackend:
    """Redis-backed conversation memory."""

    def __init__(self, redis_client: Any, tenant_id: str, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.tenant_id = tenant_id
        self.ttl = ttl_seconds

    def _make_key(self, session_id: str) -> str:
        return f"conv:{self.tenant_id}:{session_id}"

    async def get(self, session_id: str) -> list[dict]:
        key = self._make_key(session_id)
        data = await self.redis.get(key)
        if data is None:
            return []
        return json.loads(data)

    async def append(self, session_id: str, entry: dict) -> None:
        key = self._make_key(session_id)
        existing = await self.get(session_id)
        entry["ts"] = time.time()
        existing.append(entry)
        await self.redis.set(key, json.dumps(existing, ensure_ascii=False), ex=self.ttl)

    async def clear(self, session_id: str) -> None:
        key = self._make_key(session_id)
        await self.redis.delete(key)


class ShortTermMemory:
    """Manages short-term conversation context with Redis (or in-memory fallback)."""

    def __init__(self, backend: InMemoryBackend | RedisBackend, window_size: int = 5):
        self.backend = backend
        self.window_size = window_size

    async def get_context(self, session_id: str) -> list[dict]:
        history = await self.backend.get(session_id)
        return history[-self.window_size:] if history else []

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        await self.backend.append(session_id, {"role": role, "content": content})

    async def build_messages(self, session_id: str, system_prompt: str) -> list[dict]:
        """Build message list for LLM call: system + recent history."""
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        history = await self.get_context(session_id)
        for entry in history:
            messages.append({"role": entry["role"], "content": entry["content"]})
        return messages

    async def clear(self, session_id: str) -> None:
        await self.backend.clear(session_id)
