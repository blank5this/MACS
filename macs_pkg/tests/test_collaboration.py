"""Tests for collaboration modes."""

import pytest
import asyncio
from macs_pkg.core.agent import BaseAgent, AgentRole, Message, SimpleAgent
from macs_pkg.collaboration.base import CollaborationConfig, CollaborationRegistry, CollaborationMode
from macs_pkg.collaboration.hierarchical import HierarchicalMode
from macs_pkg.collaboration.pipeline import PipelineMode
from macs_pkg.collaboration.dynamic_selector import DynamicSelector


class TestCollaborationRegistry:
    """Tests for CollaborationRegistry."""

    def test_register_and_get(self):
        """Test registering and retrieving modes."""
        class CustomMode(CollaborationMode):
            name = "custom"

            async def execute(self, task, agents, context=None):
                return "custom_result"

            def select_agents(self, task, available_agents):
                return []

        CollaborationRegistry.register("custom", CustomMode)

        retrieved = CollaborationRegistry.get("custom")
        assert retrieved == CustomMode

    def test_create_mode(self):
        """Test creating mode instance."""
        CollaborationRegistry.register("test_mode", HierarchicalMode)

        mode = CollaborationRegistry.create("test_mode")
        assert isinstance(mode, HierarchicalMode)

    def test_list_modes(self):
        """Test listing registered modes."""
        modes = CollaborationRegistry.list_modes()
        assert "hierarchical" in modes
        assert "pipeline" in modes


class TestHierarchicalMode:
    """Tests for HierarchicalMode."""

    @pytest.mark.asyncio
    async def test_select_agents(self):
        """Test agent selection for hierarchical mode."""
        mode = HierarchicalMode()

        agents = [
            SimpleAgent("planner", AgentRole.PLANNER),
            SimpleAgent("executor1", AgentRole.EXECUTOR),
            SimpleAgent("executor2", AgentRole.EXECUTOR),
            SimpleAgent("reviewer", AgentRole.REVIEWER),
        ]

        selected = mode.select_agents("test_task", agents)

        assert len(selected) == 4
        assert mode._leader is not None
        assert len(mode._executors) == 2
        assert mode._reviewer is not None

    @pytest.mark.asyncio
    async def test_execute_hierarchical(self):
        """Test hierarchical execution."""
        mode = HierarchicalMode(CollaborationConfig(max_iterations=3))

        agents = {
            "planner": SimpleAgent("planner", AgentRole.PLANNER),
            "executor1": SimpleAgent("executor1", AgentRole.EXECUTOR),
            "executor2": SimpleAgent("executor2", AgentRole.EXECUTOR),
        }

        # Give executors to planner's executors list
        mode._leader = agents["planner"]
        mode._executors = [agents["executor1"], agents["executor2"]]

        task = {
            "type": "complex_task",
            "description": "A complex task that needs decomposition",
        }

        result = await mode.execute(task, agents)

        # Result should be produced (actual content depends on implementation)
        assert result is not None


class TestPipelineMode:
    """Tests for PipelineMode."""

    def test_select_agents_pipeline(self):
        """Test agent selection for pipeline mode."""
        mode = PipelineMode()

        agents = [
            SimpleAgent("tool", AgentRole.TOOL),
            SimpleAgent("executor", AgentRole.EXECUTOR),
            SimpleAgent("reviewer", AgentRole.REVIEWER),
        ]

        selected = mode.select_agents("test_task", agents)

        # Should be ordered by role priority
        assert len(selected) == 3
        assert selected[0].role == AgentRole.TOOL
        assert selected[-1].role == AgentRole.REVIEWER

    @pytest.mark.asyncio
    async def test_execute_pipeline(self):
        """Test pipeline execution."""
        mode = PipelineMode()

        agents = {
            "tool": SimpleAgent("tool", AgentRole.TOOL),
            "executor": SimpleAgent("executor", AgentRole.EXECUTOR),
        }

        # Set custom order
        mode._chain = [agents["tool"], agents["executor"]]

        task = "Process this data"

        result = await mode.execute(task, agents)

        # Result should flow through the pipeline
        assert result is not None


class TestDynamicSelector:
    """Tests for DynamicSelector."""

    def test_selector_initialization(self):
        """Test selector initialization."""
        selector = DynamicSelector()
        modes = selector.get_available_modes()

        assert "hierarchical" in modes
        assert "pipeline" in modes

    def test_register_custom_rule(self):
        """Test registering custom selection rule."""
        selector = DynamicSelector()
        selector.register_rule("my_task", "pipeline")

        # The custom rule should be used when available
        # (actual behavior depends on task analysis)
        assert "my_task" in selector._custom_rules

    def test_select_mode_hierarchical(self):
        """Test selecting hierarchical mode for complex tasks."""
        selector = DynamicSelector()

        agents = [
            SimpleAgent("planner", AgentRole.PLANNER),
            SimpleAgent("executor", AgentRole.EXECUTOR),
        ]

        task = {
            "complexity": "high",
            "requires_review": True,
        }

        mode = selector.select_mode(task, agents)

        assert isinstance(mode, HierarchicalMode)

    def test_select_mode_pipeline(self):
        """Test selecting pipeline mode for sequential tasks."""
        selector = DynamicSelector()

        agents = [
            SimpleAgent("executor1", AgentRole.EXECUTOR),
            SimpleAgent("executor2", AgentRole.EXECUTOR),
        ]

        task = {
            "complexity": "low",
            "independence": "dependent",
        }

        mode = selector.select_mode(task, agents)

        assert isinstance(mode, PipelineMode)
