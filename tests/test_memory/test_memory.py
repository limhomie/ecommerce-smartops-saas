"""Tests for the memory layer."""

from __future__ import annotations

import pytest
from src.memory.short_term import InMemoryBackend, ShortTermMemory


@pytest.mark.asyncio
async def test_short_term_memory():
    backend = InMemoryBackend(max_messages=10)
    memory = ShortTermMemory(backend, window_size=3)

    await memory.add_message("session_1", "user", "你好")
    await memory.add_message("session_1", "assistant", "你好！有什么可以帮您？")
    await memory.add_message("session_1", "user", "帮我查询物流")

    context = await memory.get_context("session_1")
    assert len(context) == 3
    assert context[0]["role"] == "user"


@pytest.mark.asyncio
async def test_short_term_window():
    backend = InMemoryBackend(max_messages=10)
    memory = ShortTermMemory(backend, window_size=2)

    for i in range(5):
        await memory.add_message("s1", "user", f"msg {i}")

    context = await memory.get_context("s1")
    assert len(context) == 2


@pytest.mark.asyncio
async def test_build_messages():
    backend = InMemoryBackend(max_messages=10)
    memory = ShortTermMemory(backend, window_size=5)

    await memory.add_message("s1", "user", "测试问题")

    messages = await memory.build_messages("s1", "你是一个助手")
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "测试问题"
