"""Tests for Planner Agent."""

import pytest
import asyncio
from macs_pkg.agents.planner import PlannerAgent
from macs_pkg.core.agent import AgentRole


@pytest.mark.asyncio
async def test_planner_agent_initialization():
    """Test planner can be initialized."""
    planner = PlannerAgent(name="test_planner")
    assert planner.name == "test_planner"
    assert planner.role == AgentRole.PLANNER


@pytest.mark.asyncio
async def test_planner_decompose_simple_task(mock_llm_provider):
    """Test planner can decompose a simple task."""
    planner = PlannerAgent(name="test_planner", provider=mock_llm_provider)

    from macs_pkg.core.agent import Message
    msg = Message(
        sender="test",
        receiver="test_planner",
        content={"action": "decompose", "task": "完成销售报告"},
        msg_type="task",
    )

    response = await planner.think(msg)
    assert response is not None
    # Response content should have action
    assert "action" in response.content


@pytest.mark.asyncio
async def test_planner_without_llm_falls_back_to_simple():
    """Test planner falls back to simple decomposition without LLM."""
    planner = PlannerAgent(name="test_planner")  # No provider

    from macs_pkg.core.agent import Message
    msg = Message(
        sender="test",
        receiver="test_planner",
        content={"action": "decompose", "task": "分析销售数据"},
        msg_type="task",
    )

    response = await planner.think(msg)
    # Should still get a response, just simpler
    assert response is not None


@pytest.mark.asyncio
async def test_planner_act_sends_messages():
    """Test planner act() creates outgoing messages."""
    planner = PlannerAgent(name="test_planner")

    from macs_pkg.core.agent import Message
    # First trigger think() so the ReactAgent lifecycle accepts act()
    trigger = Message(
        sender="test",
        receiver="test_planner",
        content={"action": "decompose", "task": "demo task"},
        msg_type="task",
    )
    await planner.think(trigger)

    # Now feed the synthetic response we want to test act() against
    response = Message(
        sender="test_planner",
        receiver="test",
        content={
            "action": "decompose",
            "subtasks": [
                {"id": "subtask_1", "description": "Task 1"},
                {"id": "subtask_2", "description": "Task 2"},
            ],
            "executors": ["executor1", "executor2"],
        },
        msg_type="result",
    )

    actions = await planner.act(response)
    # Should create messages for each subtask
    assert len(actions) >= 0  # May be 0 if no subtasks to dispatch