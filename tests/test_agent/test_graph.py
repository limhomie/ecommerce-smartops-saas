"""Test the agent graph assembly and execution."""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage


def test_graph_compiles(agent_graph):
    """Verify the graph compiles without errors."""
    assert agent_graph is not None
    assert len(agent_graph.nodes) > 0


@pytest.mark.asyncio
async def test_graph_conversion_analysis(agent_graph):
    """Test the agent handles conversion rate analysis task."""
    initial_state = {
        "messages": [HumanMessage(content="帮我分析上周为什么转化率下降")],
        "user_id": "test_user",
        "session_id": "test_session_1",
        "task_description": "帮我分析上周为什么转化率下降",
        "subtasks": [],
        "current_task_index": 0,
        "tool_results": {},
        "tool_calls": [],
        "retrieved_docs": [],
        "generated_content": "",
        "final_report": "",
        "action_items": [],
        "step_count": 0,
        "error": "",
        "next_agent": "",
    }

    config = {"configurable": {"thread_id": "test_1"}, "recursion_limit": 12}
    result = await agent_graph.ainvoke(initial_state, config)

    assert result is not None
    assert "final_report" in result or "generated_content" in result


@pytest.mark.asyncio
async def test_graph_content_generation(agent_graph):
    """Test the agent handles content generation task."""
    initial_state = {
        "messages": [HumanMessage(content="为有机棉T恤生成Facebook广告脚本")],
        "user_id": "test_user",
        "session_id": "test_session_2",
        "task_description": "为有机棉T恤生成Facebook广告脚本",
        "subtasks": [],
        "current_task_index": 0,
        "tool_results": {},
        "tool_calls": [],
        "retrieved_docs": [],
        "generated_content": "",
        "final_report": "",
        "action_items": [],
        "step_count": 0,
        "error": "",
        "next_agent": "",
    }

    config = {"configurable": {"thread_id": "test_2"}, "recursion_limit": 12}
    result = await agent_graph.ainvoke(initial_state, config)

    assert result is not None


@pytest.mark.asyncio
async def test_graph_logistics_query(agent_graph):
    """Test the agent handles logistics tracking task."""
    initial_state = {
        "messages": [HumanMessage(content="查询包裹 YT202506130001 的物流状态")],
        "user_id": "test_user",
        "session_id": "test_session_3",
        "task_description": "查询包裹 YT202506130001 的物流状态",
        "subtasks": [],
        "current_task_index": 0,
        "tool_results": {},
        "tool_calls": [],
        "retrieved_docs": [],
        "generated_content": "",
        "final_report": "",
        "action_items": [],
        "step_count": 0,
        "error": "",
        "next_agent": "",
    }

    config = {"configurable": {"thread_id": "test_3"}, "recursion_limit": 12}
    result = await agent_graph.ainvoke(initial_state, config)

    assert result is not None
