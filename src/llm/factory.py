"""LLM provider factory — creates and configures LLM backends.

Supports: mock, openai, anthropic, deepseek
"""

from __future__ import annotations

from typing import Any, Protocol

from config.settings import Settings


class LLMProvider(Protocol):
    """Protocol that all LLM providers must satisfy."""

    model: str
    provider_name: str

    def invoke(self, prompt: str, **kwargs: Any) -> Any: ...
    async def ainvoke(self, prompt: str, **kwargs: Any) -> Any: ...
    def stream(self, prompt: str, **kwargs: Any) -> Any: ...


def create_llm_from_settings(settings: Settings) -> LLMProvider:
    """Factory: return the right LLM provider based on settings.llm_provider."""
    provider = settings.llm_provider.lower()

    if provider == "mock":
        from src.llm.mock import MockProvider

        return MockProvider(model="mock")

    if provider in ("openai", "deepseek"):
        from langchain_openai import ChatOpenAI

        base_url = settings.llm_base_url if provider == "deepseek" else None
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=base_url,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            max_retries=settings.llm_max_retries,
            timeout=settings.llm_timeout_seconds,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            max_retries=settings.llm_max_retries,
            timeout=settings.llm_timeout_seconds,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
