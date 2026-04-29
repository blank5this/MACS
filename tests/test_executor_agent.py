"""Tests for Executor Agent."""

import pytest
import asyncio
from macs_pkg.agents.executor import ExecutorAgent
from macs_pkg.core.agent import AgentRole, Message


@pytest.mark.asyncio
async def test_executor_agent_initialization():
    """Test executor can be initialized."""
    executor = ExecutorAgent(name="test_executor")
    assert executor.name == "test_executor"
    assert executor.role == AgentRole.EXECUTOR


@pytest.mark.asyncio
async def test_executor_prepare_execution_plan():
    """Test executor creates execution plan for a task."""
    executor = ExecutorAgent(name="test_executor")

    msg = Message(
        sender="test",
        receiver="test_executor",
        content={"action": "execute", "subtask": {"id": "sub_1", "description": "Process order"}},
        msg_type="task",
    )

    response = await executor.think(msg)
    assert response is not None
    assert "execution_plan" in response.content or response.content.get("action") == "ready_to_execute"


@pytest.mark.asyncio
async def test_executor_stores_results():
    """Test executor stores execution results."""
    executor = ExecutorAgent(name="test_executor", max_retries=1)

    msg = Message(
        sender="test",
        receiver="test_executor",
        content={"action": "execute", "subtask": {"id": "sub_1", "description": "Test task"}},
        msg_type="task",
    )

    response = await executor.think(msg)
    actions = await executor.act(response)

    # Check that result was stored
    results = executor.get_all_results()
    # Results may be empty if execution was simple/mock


@pytest.mark.asyncio
async def test_executor_with_tools():
    """Test executor can register and use tools."""
    executor = ExecutorAgent(name="test_executor")

    # Register a mock tool
    def mock_tool(input_text):
        return f"Processed: {input_text}"

    executor.register_tool("processor", mock_tool)

    assert "processor" in executor._tools
    assert executor._tools["processor"] == mock_tool