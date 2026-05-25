"""Tests for collaboration modes."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from macs_pkg.core.agent import BaseAgent, AgentRole, Message
from macs_pkg.collaboration.hierarchical import HierarchicalMode
from macs_pkg.collaboration.pipeline import PipelineMode
from macs_pkg.collaboration.decentralized import DecentralizedMode


# ─────────────────────────────────────────────────────────────────────────────
# Mock Agent Class (reuses conftest.MockAgent logic)
# ─────────────────────────────────────────────────────────────────────────────

class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, name: str, responses: list = None, role: AgentRole = AgentRole.EXECUTOR):
        super().__init__(name, role)
        self.responses = responses or []
        self.call_count = 0

    async def think(self, message: Message) -> Message:
        return Message(
            sender=self.name,
            content={"status": "thinking", "thought": f"{self.name} is thinking"},
            msg_type="thought",
        )

    async def act(self, response: Message) -> list:
        self.call_count += 1
        idx = min(self.call_count - 1, len(self.responses) - 1)
        response_text = self.responses[idx] if self.responses else f"Response from {self.name}"
        if isinstance(response_text, dict):
            return [Message(sender=self.name, content=response_text, msg_type="action")]
        return [Message(sender=self.name, content={"result": response_text}, msg_type="action")]


# ─────────────────────────────────────────────────────────────────────────────
# Test HierarchicalMode
# ─────────────────────────────────────────────────────────────────────────────

class TestHierarchicalMode:
    """Tests for HierarchicalMode."""

    @pytest.fixture
    def planner(self):
        return MockAgent("planner", role=AgentRole.PLANNER, responses=[
            {"subtask": "Step 1: Analyze the task"},
            {"subtask": "Step 2: Plan execution"},
        ])

    @pytest.fixture
    def executor(self):
        return MockAgent("executor", role=AgentRole.EXECUTOR, responses=[
            {"result": "Executor completed step 1"},
        ])

    @pytest.fixture
    def reviewer(self):
        return MockAgent("reviewer", role=AgentRole.REVIEWER, responses=[
            {"action": "review_complete", "status": "approved", "feedback": "Looks good"},
        ])

    @pytest.fixture
    def mode(self, planner, executor, reviewer):
        mode = HierarchicalMode()
        mode._leader = planner
        mode._executors = [executor]
        mode._reviewer = reviewer
        return mode

    @pytest.mark.asyncio
    async def test_init(self, mode, planner, executor, reviewer):
        """Test mode initializes with correct agents."""
        assert mode._leader is planner
        assert mode._executors == [executor]
        assert mode._reviewer is reviewer

    @pytest.mark.asyncio
    async def test_execute_single_task(self, mode):
        """Test executing a single task through hierarchical mode."""
        task = Message(
            sender="user",
            content={"type": "test", "description": "Test task"},
            msg_type="task",
        )
        exec_agent = MockAgent("exec1")
        result = await mode.execute(task, {"exec1": exec_agent})
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_empty_agents(self, mode):
        """Test executing with empty agents dict (uses pre-set leader/executors)."""
        task = Message(
            sender="user",
            content={"type": "test"},
            msg_type="task",
        )
        result = await mode.execute(task, {})
        assert result is not None

    @pytest.mark.parametrize("num_executors,expected_results", [
        (1, 1),
        (3, 3),
    ])
    @pytest.mark.asyncio
    async def test_multiple_executors(self, num_executors, expected_results, mock_agent):
        """Test hierarchical mode with multiple executors."""
        planner = mock_agent("planner", AgentRole.PLANNER, responses=[
            {"subtask": "Analyze"},
            {"subtask": "Plan"},
        ])

        executors = [
            mock_agent(f"executor{i}", AgentRole.EXECUTOR, responses=[{"result": f"Result {i}"}])
            for i in range(num_executors)
        ]

        reviewer = mock_agent("reviewer", AgentRole.REVIEWER, responses=[
            {"action": "review_complete", "status": "approved"}
        ])

        mode = HierarchicalMode()
        mode._leader = planner
        mode._executors = executors
        mode._reviewer = reviewer

        task = Message(sender="user", content={"description": "Test task"}, msg_type="task")
        result = await mode.execute(task, {a.name: a for a in executors})

        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# Test PipelineMode
# ─────────────────────────────────────────────────────────────────────────────

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
        mode = PipelineMode()
        mode._chain = agents
        return mode

    @pytest.mark.asyncio
    async def test_init(self, mode, agents):
        """Test mode initializes with correct chain."""
        assert mode._chain == agents

    @pytest.mark.asyncio
    async def test_execute_pipeline(self, mode):
        """Test pipeline execution through multiple agents."""
        task = Message(
            sender="user",
            content="input data",
            msg_type="task",
        )
        result = await mode.execute(task, {a.name: a for a in mode._chain})
        assert result is not None

    @pytest.mark.asyncio
    async def test_single_agent_pipeline(self):
        """Test pipeline with single agent."""
        agent = MockAgent("solo", responses=["Solo result"])
        mode = PipelineMode()
        mode._chain = [agent]

        task = Message(sender="user", content="data", msg_type="task")
        result = await mode.execute(task, {"solo": agent})
        assert result is not None

    @pytest.mark.parametrize("num_agents,expected_stage", [
        (2, 2),
        (3, 3),
        (5, 5),
    ])
    @pytest.mark.asyncio
    async def test_pipeline_with_multiple_agents(self, num_agents, expected_stage, mock_agent):
        """Test pipeline stages with varying number of agents."""
        agents = [
            mock_agent(f"stage{i}", responses=[f"Stage {i} output"])
            for i in range(num_agents)
        ]

        mode = PipelineMode()
        mode._chain = agents

        task = Message(sender="user", content="input", msg_type="task")
        result = await mode.execute(task, {a.name: a for a in agents})

        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# Test DecentralizedMode
# ─────────────────────────────────────────────────────────────────────────────

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
        mode = DecentralizedMode()
        mode._agents = agents
        return mode

    @pytest.mark.asyncio
    async def test_init(self, mode, agents):
        """Test mode initializes with correct peers."""
        assert mode._agents == agents
        assert len(mode._agents) == 3

    @pytest.mark.asyncio
    async def test_execute_decentralized(self, mode):
        """Test decentralized execution with consensus."""
        task = Message(
            sender="user",
            content="Consensus decision needed",
            msg_type="task",
        )
        result = await mode.execute(task, {a.name: a for a in mode._agents})
        assert result is not None

    @pytest.mark.asyncio
    async def test_insufficient_agents(self, mode):
        """Test with only one agent (no true consensus possible)."""
        task = Message(sender="user", content="task", msg_type="task")
        mode._peers = []
        result = await mode.execute(task, {"solo": MockAgent("solo")})
        assert result is not None

    @pytest.mark.parametrize("num_agents", [2, 3, 4, 5])
    @pytest.mark.asyncio
    async def test_different_agent_counts(self, num_agents, mock_agent):
        """Test decentralized mode with varying agent counts."""
        agents = [
            mock_agent(f"node{i}", responses=[f"Proposal {i}"])
            for i in range(num_agents)
        ]

        mode = DecentralizedMode()
        mode._agents = agents

        task = Message(sender="user", content="Decision needed", msg_type="task")
        result = await mode.execute(task, {a.name: a for a in agents})

        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# Test AgentInteraction
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentInteraction:
    """Test agent-to-agent communication."""

    @pytest.mark.asyncio
    async def test_message_passing(self):
        """Test basic message passing between agents."""
        sender = MockAgent("sender")
        receiver = MockAgent("receiver", responses=["ACK"])

        msg = Message(sender="sender", content="data", msg_type="message")
        thought = await receiver.think(msg)

        assert thought.sender == "receiver"
        assert thought.content["status"] == "thinking"

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel execution of multiple agents."""
        agents = [MockAgent(f"agent{i}") for i in range(5)]

        task = Message(sender="user", content="parallel task", msg_type="task")

        results = await asyncio.gather(*[
            agent.think(task) for agent in agents
        ])

        assert len(results) == 5
        assert all(r.sender.startswith("agent") for r in results)

    @pytest.mark.parametrize("num_agents", [2, 3, 5, 10])
    @pytest.mark.asyncio
    async def test_parallel_scaled(self, num_agents):
        """Test parallel execution scales correctly."""
        agents = [MockAgent(f"parallel_agent{i}") for i in range(num_agents)]

        task = Message(sender="user", content="scaled parallel task", msg_type="task")

        results = await asyncio.gather(*[
            agent.think(task) for agent in agents
        ])

        assert len(results) == num_agents
        assert all(isinstance(r, Message) for r in results)