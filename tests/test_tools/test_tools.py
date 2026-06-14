"""Test the tool layer."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_google_shopping_tool(tool_registry):
    result = await tool_registry.execute("google_shopping", query="有机棉T恤")
    assert result.success
    assert "market_summary" in result.data


@pytest.mark.asyncio
async def test_meta_ads_tool(tool_registry):
    result = await tool_registry.execute(
        "meta_ads", action="generate", product_name="有机棉T恤"
    )
    assert result.success
    assert "ad_creative" in result.data


@pytest.mark.asyncio
async def test_shopify_tool(tool_registry):
    result = await tool_registry.execute("shopify_api", action="analytics")
    assert result.success
    assert "metrics" in result.data


@pytest.mark.asyncio
async def test_amazon_tool(tool_registry):
    result = await tool_registry.execute("amazon_api", action="inventory")
    assert result.success
    assert "inventory" in result.data


@pytest.mark.asyncio
async def test_erp_tool(tool_registry):
    result = await tool_registry.execute("erp_api", action="inventory")
    assert result.success


@pytest.mark.asyncio
async def test_logistics_tool(tool_registry):
    result = await tool_registry.execute(
        "logistics", action="track", tracking_number="YT202506130001"
    )
    assert result.success
    assert result.data["status"] == "运输中"


@pytest.mark.asyncio
async def test_automation_runner(tool_registry):
    result = await tool_registry.execute("automation_runner", script="daily_report")
    assert result.success


@pytest.mark.asyncio
async def test_tool_registry_list(tool_registry):
    tools = tool_registry.list_tools()
    assert len(tools) >= 7


@pytest.mark.asyncio
async def test_unknown_tool(tool_registry):
    result = await tool_registry.execute("nonexistent_tool")
    assert not result.success
    assert "not found" in result.error
