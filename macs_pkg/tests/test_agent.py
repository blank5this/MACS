"""Tests for Agent base classes."""

import pytest
import asyncio
from macs_pkg.core.agent import BaseAgent, AgentRole, Message, SimpleAgent, AgentState


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_agent_roles_exist(self):
        """Test that all expected roles exist."""
        assert AgentRole.PLANNER.value == "planner"
        assert AgentRole.EXECUTOR.value == "executor"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.TOOL.value == "tool"

    def test_agent_role_from_string(self):
        """Test creating role from string."""
        assert AgentRole("planner") == AgentRole.PLANNER


class TestMessage:
    """Tests for Message class."""

    def test_message_creation(self):
        """Test basic message creation."""
        msg = Message(
            sender="agent1",
            receiver="agent2",
            content="Hello",
            msg_type="text",
        )

        assert msg.sender == "agent1"
        assert msg.receiver == "agent2"
        assert msg.content == "Hello"
        assert msg.msg_type == "text"
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = Message(
            sender="agent1",
            receiver="agent2",
            content="Hello",
            msg_type="text",
        )

        d = msg.to_dict()
        assert d["sender"] == "agent1"
        assert d["receiver"] == "agent2"
        assert d["content"] == "Hello"
        assert "timestamp" in d


class TestSimpleAgent:
    """Tests for SimpleAgent implementation."""

    @pytest.mark.asyncio
    async def test_simple_agent_think(self):
        """Test simple agent think method."""
        agent = SimpleAgent("test", AgentRole.EXECUTOR)

        msg = Message(
            sender="user",
            receiver="test",
            content="Hello agent",
            msg_type="text",
        )

        response = await agent.think(msg)

        assert response.sender == "test"
        assert response.receiver == "user"
        assert "executor" in response.content.lower()
        assert response.msg_type == "result"

    @pytest.mark.asyncio
    async def test_simple_agent_act(self):
        """Test simple agent act method."""
        agent = SimpleAgent("test", AgentRole.EXECUTOR)

        msg = Message(
            sender="user",
            receiver="test",
            content="Hello",
            msg_type="text",
        )

        response = await agent.think(msg)
        actions = await agent.act(response)

        assert len(actions) == 1
        assert actions[0].sender == "test"
        assert actions[0].receiver == "user"

    @pytest.mark.asyncio
    async def test_agent_memory(self):
        """Test agent memory functionality."""
        agent = SimpleAgent("test", AgentRole.EXECUTOR)

        msg = Message(sender="user", receiver="test", content="Test", msg_type="text")

        response = await agent.think(msg)
        await agent.act(response)

        memory = agent.get_memory()
        assert len(memory) == 1

        agent.clear_memory()
        assert len(agent.get_memory()) == 0

    def test_agent_repr(self):
        """Test agent string representation."""
        agent = SimpleAgent("test_agent", AgentRole.PLANNER)
        assert "test_agent" in repr(agent)
        assert "planner" in repr(agent)


class TestAgentState:
    """Tests for AgentState enum."""

    def test_agent_states(self):
        """Test all agent states exist."""
        assert AgentState.IDLE.value == "idle"
        assert AgentState.THINKING.value == "thinking"
        assert AgentState.ACTING.value == "acting"
        assert AgentState.WAITING.value == "waiting"
        assert AgentState.DONE.value == "done"
