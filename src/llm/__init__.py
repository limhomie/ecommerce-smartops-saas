"""LLM provider module — global singleton for agent nodes.

Usage:
    from src.llm import set_llm, get_llm

    # Once at startup:
    provider = create_llm_from_settings(settings)
    set_llm(provider)

    # In any agent node:
    llm = get_llm()
    response = llm.invoke(prompt)
"""

from __future__ import annotations

from typing import Any

_llm_instance: Any = None


def set_llm(provider: Any) -> None:
    """Set the global LLM provider instance."""
    global _llm_instance
    _llm_instance = provider


def get_llm() -> Any:
    """Get the global LLM provider instance (falls back to Mock)."""
    global _llm_instance
    if _llm_instance is None:
        from src.llm.mock import MockProvider
        _llm_instance = MockProvider()
    return _llm_instance
