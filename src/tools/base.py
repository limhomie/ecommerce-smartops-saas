"""Tool base class and registry for the agent tool layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = ""
    tool_name: str = ""


class BaseTool(ABC):
    """All tools inherit from this base."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        ...

    def to_langchain_tool(self) -> dict:
        """Export as a dict that can be used with LangChain tool interfaces."""
        return {
            "name": self.name,
            "description": self.description,
            "func": self.execute,
        }


class ToolRegistry:
    """Registry for all available tools. Supports lookup by name."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=name)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


def create_default_registry() -> ToolRegistry:
    """Create a registry with all available tools registered."""
    registry = ToolRegistry()

    from src.tools.google_shopping import GoogleShoppingTool
    from src.tools.meta_ads import MetaAdsTool
    from src.tools.shopify_api import ShopifyTool
    from src.tools.amazon_api import AmazonTool
    from src.tools.erp_api import ERPTool
    from src.tools.logistics import LogisticsTool
    from src.tools.runner import AutomationRunner

    from src.tools.google_ads_api import GoogleAdsTool

    registry.register(GoogleShoppingTool())
    registry.register(MetaAdsTool())
    registry.register(ShopifyTool())
    registry.register(AmazonTool())
    registry.register(GoogleAdsTool())
    registry.register(ERPTool())
    registry.register(LogisticsTool())
    registry.register(AutomationRunner())

    return registry
