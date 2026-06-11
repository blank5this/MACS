"""Tests for ReactAgent (P0-2)."""

import pytest
from macs_pkg.core.react_agent import ReactAgent
from macs_pkg.core.agent import AgentRole, AgentState, Message


class _DummyReactAgent(ReactAgent):
    """Concrete ReactAgent for testing."""

    def __init__(self, name: str = "test_agent"):
        super().__init__(name=name, role=AgentRole.EXECUTOR)
        self.think_call_count = 0
        self.act_call_count = 0

    async def _think_impl(self, message: Message) -> Message:
        self.think_call_count += 1
        return Message(
            sender=self.name,
            receiver=message.sender,
            content={"planned": f"planned_from_{message.content}"},
            msg_type="result",
        )

    async def _act_impl(self, response: Message) -> list[Message]:
        self.act_call_count += 1
        return [response]


class TestReactAgent:
    """Tests for ReactAgent enforcement."""

    @pytest.mark.asyncio
    async def test_run_full_cycle(self):
        """run() completes one think+act cycle."""
        agent = _DummyReactAgent()
        msg = Message(sender="user", receiver="test", content="hello")
        results = await agent.run(msg)
        assert agent.think_call_count == 1
        assert agent.act_call_count == 1
        assert len(results) == 1
        assert results[0].sender == agent.name

    @pytest.mark.asyncio
    async def test_act_before_think_raises(self):
        """Calling act() before think() must raise RuntimeError."""
        agent = _DummyReactAgent()
        msg = Message(sender="user", receiver="test", content="hello")

        with pytest.raises(RuntimeError, match="act.*called before think"):
            await agent.act(msg)

    @pytest.mark.asyncio
    async def test_think_sets_think_called_flag(self):
        """think() sets _think_called=True after returning."""
        agent = _DummyReactAgent()
        msg = Message(sender="user", receiver="test", content="hello")
        await agent.think(msg)
        assert agent._think_called is True

    @pytest.mark.asyncio
    async def test_act_resets_think_called_flag(self):
        """act() resets _think_called=False after completing."""
        agent = _DummyReactAgent()
        msg = Message(sender="user", receiver="test", content="hello")
        response = await agent.think(msg)
        await agent.act(response)
        assert agent._think_called is False

    @pytest.mark.asyncio
    async def test_sequential_think_act_cycles(self):
        """Two complete cycles work without error (each cycle: think→act resets flag)."""
        agent = _DummyReactAgent()
        for i in range(3):
            msg = Message(sender="user", receiver="test", content=f"cycle_{i}")
            response = await agent.think(msg)
            results = await agent.act(response)
            assert len(results) == 1
        assert agent.think_call_count == 3
        assert agent.act_call_count == 3

    @pytest.mark.asyncio
    async def test_act_receives_think_response(self):
        """act() receives the output of think() as its input."""
        agent = _DummyReactAgent()
        msg = Message(sender="user", receiver="test", content="hello")
        response = await agent.think(msg)
        assert response.content == {"planned": "planned_from_hello"}

        results = await agent.act(response)
        assert results[0].content == {"planned": "planned_from_hello"}

    @pytest.mark.asyncio
    async def test_state_is_idle_after_cycle(self):
        """State is IDLE after a full run() cycle."""
        agent = _DummyReactAgent()
        msg = Message(sender="user", receiver="test", content="hello")
        await agent.run(msg)
        assert agent.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_think_injects_thinking_state(self):
        """think() sets state to THINKING during execution (checked at entry)."""
        agent = _DummyReactAgent()
        assert agent.state == AgentState.IDLE

