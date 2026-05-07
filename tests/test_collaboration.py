"""Tests for collaboration modes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from macs_pkg.core.agent import BaseAgent, AgentRole, Message
from macs_pkg.collaboration.hierarchical import HierarchicalMode
from macs_pkg.collaboration.pipeline import PipelineMode
from macs_pkg.collaboration.decentralized import DecentralizedMode


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, name: str, responses: list = None):
        super().__init__(name, AgentRole.EXECUTOR)
        self.responses = responses or []
        self.call_count = 0

    async def think(self, message: Message) -> Message:
        return Message(
            sender=self.name,
            content={"status": "thinking", "thought": f"{self.name} is thinking"},
            type="thought",
        )

    async def act(self, response: Message) -> list:
        self.call_count += 1
        idx = min(self.call_count - 1, len(self.responses) - 1)
        response_text = self.responses[idx] if self.responses else f"Response from {self.name}"
        return [
            Message(
                sender=self.name,
                content={"result": response_text},
                type="action",
            )
        ]


class TestHierarchicalMode:
    """Tests for HierarchicalMode."""

    @pytest.fixture
    def planner(self):
        return MockAgent("planner", responses=[
            {"subtask": "Step 1: Analyze the task"},
            {"subtask": "Step 2: Plan execution"},
        ])

    @pytest.fixture
    def executor(self):
        return MockAgent("executor", responses=[
            {"result": "Executor completed step 1"},
        ])

    @pytest.fixture
    def reviewer(self):
        return MockAgent("reviewer", responses=[
            {"status": "approved", "feedback": "Looks good"},
        ])

    @pytest.fixture
    def mode(self, planner, executor, reviewer):
        return HierarchicalMode(
            leader=planner,
            executors=[executor],
            reviewer=reviewer,
        )

    @pytest.mark.asyncio
    async def test_init(self, mode, planner, executor, reviewer):
        assert mode._leader is planner
        assert mode._executors == [executor]
        assert mode._reviewer is reviewer

    @pytest.mark.asyncio
    async def test_execute_single_task(self, mode):
        task = Message(
            sender="user",
            content={"type": "test", "description": "Test task"},
            type="task",
        )

        with patch.object(mode, '_execute_with_hierarchy', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = Message(
                sender="system",
                content={"result": "success"},
                type="result",
            )
            result = await mode.execute(task, [MockAgent("exec1")])

        assert result.sender == "system"

    @pytest.mark.asyncio
    async def test_execute_empty_agents(self, mode):
        task = Message(
            sender="user",
            content={"type": "test"},
            type="task",
        )

        with pytest.raises(ValueError, match="At least one agent"):
            await mode.execute(task, [])


class TestPipelineMode:
    """Tests for PipelineMode."""

    @pytest.fixture
    def agents(self):
        return [
            MockAgent("agent1", responses=["Processed by agent1"]),
            MockAgent("agent2", responses=["Processed by agent2"]),
            MockAgent("agent3", responses=["Final result"]),
        ]

    @pytest.fixture
    def mode(self, agents):
        return PipelineMode(agents=agents)

    @pytest.mark.asyncio
    async def test_init(self, mode, agents):
        assert mode._agents == agents

    @pytest.mark.asyncio
    async def test_execute_pipeline(self, mode):
        task = Message(
            sender="user",
            content="input data",
            type="task",
        )

        result = await mode.execute(task, mode._agents)

        assert result.sender == "agent3"
        assert "Final result" in result.content.get("result", "")

    @pytest.mark.asyncio
    async def test_single_agent_pipeline(self):
        agent = MockAgent("solo", responses=["Solo result"])
        mode = PipelineMode(agents=[agent])

        task = Message(sender="user", content="data", type="task")
        result = await mode.execute(task, [agent])

        assert result.sender == "solo"


class TestDecentralizedMode:
    """Tests for DecentralizedMode."""

    @pytest.fixture
    def agents(self):
        return [
            MockAgent("node1", responses=["Node1 opinion"]),
            MockAgent("node2", responses=["Node2 opinion"]),
            MockAgent("node3", responses=["Node3 opinion"]),
        ]

    @pytest.fixture
    def mode(self, agents):
        return DecentralizedMode(agents=agents)

    @pytest.mark.asyncio
    async def test_init(self, mode, agents):
        assert mode._agents == agents
        assert len(mode._agents) == 3

    @pytest.mark.asyncio
    async def test_execute_decentralized(self, mode):
        task = Message(
            sender="user",
            content="Consensus decision needed",
            type="task",
        )

        with patch.object(mode, '_reach_consensus', new_callable=AsyncMock) as mock_consensus:
            mock_consensus.return_value = Message(
                sender="system",
                content={"consensus": "reached"},
                type="result",
            )
            result = await mode.execute(task, mode._agents)

        assert result.sender == "system"

    @pytest.mark.asyncio
    async def test_insufficient_agents(self, mode):
        task = Message(sender="user", content="task", type="task")

        with pytest.raises(ValueError, match="At least 2 agents"):
            await mode.execute(task, [MockAgent("solo")])


class TestAgentInteraction:
    """Test agent-to-agent communication."""

    @pytest.mark.asyncio
    async def test_message_passing(self):
        sender = MockAgent("sender")
        receiver = MockAgent("receiver", responses=["ACK"])

        msg = Message(sender="sender", content="data", type="message")
        thought = await receiver.think(msg)

        assert thought.sender == "receiver"
        assert thought.content["status"] == "thinking"

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        agents = [MockAgent(f"agent{i}") for i in range(5)]

        task = Message(sender="user", content="parallel task", type="task")

        # Execute in parallel
        results = await asyncio.gather(*[
            agent.think(task) for agent in agents
        ])

        assert len(results) == 5
        assert all(r.sender.startswith("agent") for r in results)
