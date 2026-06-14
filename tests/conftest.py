"""Pytest fixtures for all tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def settings():
    from config.settings import Settings

    return Settings()


@pytest.fixture
def mock_llm():
    from src.llm.mock import MockProvider

    return MockProvider()


@pytest.fixture
def tool_registry():
    from src.tools.base import create_default_registry

    return create_default_registry()


@pytest.fixture
def memory_manager():
    from src.memory.manager import MemoryManager

    return MemoryManager.create_default()


@pytest.fixture
def agent_graph():
    from src.agent.graph import build_graph

    return build_graph()
