"""Integration tests for MACS runtime."""

import pytest
import asyncio
from macs_pkg.runtime.engine import RuntimeEngine, create_runtime, RuntimeConfig
from macs_pkg.core.agent import AgentRole


class TestRuntimeEngine:
    """Tests for RuntimeEngine."""

    def test_engine_creation(self):
        """Test creating a runtime engine."""
        engine = RuntimeEngine()

        assert engine is not None
        assert len(engine.list_agents()) == 0

    def test_register_agent(self):
        """Test registering an agent."""
        from macs_pkg.core.agent import SimpleAgent

        engine = RuntimeEngine()
        agent = SimpleAgent("test", AgentRole.EXECUTOR)

        engine.register_agent(agent)

        assert len(engine.list_agents()) == 1
        assert engine.get_agent("test") == agent

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        from macs_pkg.core.agent import SimpleAgent

        engine = RuntimeEngine()
        agent = SimpleAgent("test", AgentRole.EXECUTOR)
        engine.register_agent(agent)

        result = engine.unregister_agent("test")

        assert result is True
        assert len(engine.list_agents()) == 0

    def test_create_and_register_agents(self):
        """Test creating multiple agents at once."""
        engine = RuntimeEngine()

        configs = [
            {"name": "planner", "role": "planner"},
            {"name": "executor", "role": "executor"},
        ]

        engine.create_and_register_agents(configs)

        assert len(engine.list_agents()) == 2
        assert engine.get_agent("planner") is not None
        assert engine.get_agent("executor") is not None

    def test_get_system_status(self):
        """Test getting system status."""
        from macs_pkg.core.agent import SimpleAgent

        engine = RuntimeEngine()
        agent = SimpleAgent("test", AgentRole.EXECUTOR)
        engine.register_agent(agent)

        status = engine.get_system_status()

        assert "agents" in status
        assert "test" in status["agents"]
        assert status["agents"]["test"]["role"] == "executor"

    @pytest.mark.asyncio
    async def test_execute_task(self):
        """Test executing a task."""
        from macs_pkg.core.agent import SimpleAgent

        engine = RuntimeEngine()
        agent = SimpleAgent("executor", AgentRole.EXECUTOR)
        engine.register_agent(agent)

        result = await engine.execute("test task")

        assert result is not None

    def test_execute_sync(self):
        """Test synchronous execution."""
        from macs_pkg.core.agent import SimpleAgent

        engine = RuntimeEngine()
        agent = SimpleAgent("executor", AgentRole.EXECUTOR)
        engine.register_agent(agent)

        result = engine.execute_sync("test task")

        assert result is not None

    def test_context_management(self):
        """Test shared context management."""
        engine = RuntimeEngine()

        engine.update_context("key1", "value1")

        assert engine.get_context("key1") == "value1"
        assert engine.get_context("nonexistent", "default") == "default"


class TestCreateRuntime:
    """Tests for create_runtime factory function."""

    def test_create_runtime_default(self):
        """Test creating runtime with defaults."""
        runtime = create_runtime()

        assert isinstance(runtime, RuntimeEngine)
        assert runtime.config.default_mode == "hierarchical"

    def test_create_runtime_with_agents(self):
        """Test creating runtime with agents."""
        runtime = create_runtime(
            agents=[
                {"name": "planner", "role": "planner"},
                {"name": "executor", "role": "executor"},
            ],
            mode="pipeline",
        )

        assert len(runtime.list_agents()) == 2
        assert runtime.config.default_mode == "pipeline"

    def test_create_runtime_with_options(self):
        """Test creating runtime with custom options."""
        runtime = create_runtime(
            log_level="DEBUG",
            max_iterations=5,
        )

        assert runtime.config.log_level == "DEBUG"
        assert runtime.config.max_iterations == 5


class TestRuntimeCollaborationModes:
    """Tests for runtime with different collaboration modes."""

    @pytest.mark.asyncio
    async def test_hierarchical_mode(self):
        """Test runtime with hierarchical mode."""
        runtime = create_runtime(
            agents=[
                {"name": "planner", "role": "planner"},
                {"name": "executor", "role": "executor"},
            ],
            mode="hierarchical",
        )

        result = await runtime.execute("complex task")

        assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_mode(self):
        """Test runtime with pipeline mode."""
        runtime = create_runtime(
            agents=[
                {"name": "processor1", "role": "executor"},
                {"name": "processor2", "role": "executor"},
            ],
            mode="pipeline",
        )

        result = await runtime.execute("data to process")

        assert result is not None

    def test_available_modes(self):
        """Test getting available collaboration modes."""
        runtime = RuntimeEngine()

        modes = runtime.get_available_modes()

        assert "hierarchical" in modes
        assert "pipeline" in modes
