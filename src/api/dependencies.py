"""FastAPI dependency injection utilities."""

from __future__ import annotations

from fastapi import Request

from src.agent.graph import get_agent_graph
from src.memory.manager import MemoryManager


def get_settings(request: Request):
    """Return application settings from app state."""
    return request.app.state.settings


def get_agent(request: Request):
    """Return the compiled agent graph."""
    return get_agent_graph()


def get_memory(request: Request):
    """Return the memory manager."""
    memory: MemoryManager | None = getattr(request.app.state, "memory_manager", None)
    if memory is None:
        memory = MemoryManager.create_default()
    return memory
