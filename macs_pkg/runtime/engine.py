"""Runtime engine - main entry point for MACS."""

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING
import asyncio
import time
from dataclasses import dataclass, field
from loguru import logger

from ..core.agent import BaseAgent, AgentRole, Message
from ..core.context import ContextManager, TaskContext
from ..core.router import MessageRouter
from ..core.aggregator import ResultAggregator, AggregationStrategy
from ..collaboration.base import CollaborationConfig, CollaborationRegistry
from ..collaboration.dynamic_selector import DynamicSelector, AdaptiveSelector
from ..collaboration.hierarchical import HierarchicalMode
from ..collaboration.decentralized import DecentralizedMode
from ..collaboration.pipeline import PipelineMode
from ..monitoring.event_bus import Event, EventType, get_event_bus

if TYPE_CHECKING:
    from ..memory.mempalace_client import MemoryConfig
    from ..memory.agent_memory import SharedMemory
    from ..llm.base import LLMProvider
    from ..visualization.tracer import ExecutionTracer


@dataclass
class RuntimeConfig:
    """Configuration for the runtime engine."""

    default_mode: str = "hierarchical"
    enable_dynamic_selection: bool = True
    max_iterations: int = 10
    timeout: Optional[float] = None
    stop_on_error: bool = True
    log_level: str = "INFO"
    enable_monitoring: bool = True
    enable_shared_memory: bool = True  # Enable shared memory via MemPalace
    enable_tracing: bool = False  # Enable ExecutionTracer for visualization

    # Collaboration settings
    collaboration: Dict[str, Any] = field(default_factory=lambda: {
        "hierarchical": {"max_iterations": 10},
        "decentralized": {"consensus_threshold": 0.5, "max_rounds": 5},
        "pipeline": {},
    })

    # Memory settings
    memory: Dict[str, Any] = field(default_factory=lambda: {
        "storage_path": "~/.macs/memory",
        "project_name": "macs_default",
    })


class RuntimeEngine:
    """Main runtime engine for MACS.

    The engine orchestrates:
    - Agent registration and management
    - Context management across agents
    - Message routing
    - Collaboration mode selection and execution
    - Result aggregation
    - Shared memory management (via MemPalace)
    - Execution tracing (via ExecutionTracer)
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        memory_config: Optional["MemoryConfig"] = None,
    ):
        self.config = config or RuntimeConfig()
        self._agents: Dict[str, BaseAgent] = {}
        self._context = ContextManager()
        self._router = MessageRouter()
        self._selector: DynamicSelector = (
            AdaptiveSelector() if self.config.enable_dynamic_selection
            else DynamicSelector()
        )
        self._aggregator = ResultAggregator(
            strategy=AggregationStrategy.ALL_COMPLETE,
            timeout=self.config.timeout,
        )
        self._running = False
        self._task_history: List[Dict[str, Any]] = []
        self._shared_memory: Optional["SharedMemory"] = None

        # Initialize tracing if enabled
        self._tracer: Optional["ExecutionTracer"] = None
        if self.config.enable_tracing:
            from ..visualization.tracer import ExecutionTracer
            self._tracer = ExecutionTracer(task_id="init")
            logger.info("Execution tracing enabled")

        # Setup logging
        logger.remove()
        logger.add(lambda msg: print(msg, end=""), level=self.config.log_level)

        # Initialize shared memory if enabled
        if self.config.enable_shared_memory:
            self._init_shared_memory(memory_config)

    def _init_shared_memory(self, memory_config: Optional["MemoryConfig"]) -> None:
        """Initialize shared memory via MemPalace."""
        if self._shared_memory is not None:
            return

        try:
            from ..memory.mempalace_client import MemPalaceClient, MemoryConfig
            from ..memory.agent_memory import SharedMemory

            config = memory_config or MemoryConfig(
                storage_path=self.config.memory.get("storage_path", "~/.macs/memory"),
            )
            client = MemPalaceClient(config)
            self._shared_memory = SharedMemory(
                client=client,
                project_name=self.config.memory.get("project_name", "macs_default"),
            )
            logger.info("Shared memory initialized")
        except ImportError:
            logger.warning(
                "MemPalace not available. Shared memory disabled. "
                "Install with: pip install mempalace"
            )
            self._shared_memory = None
        except Exception as e:
            logger.error(f"Failed to initialize shared memory: {e}")
            self._shared_memory = None

    async def init_shared_memory_async(self) -> None:
        """Async initialization of shared memory."""
        if self._shared_memory:
            await self._shared_memory.initialize()
            # Also initialize agent memories
            await BaseAgent.init_shared_memory()

    # ==================== Agent Management ====================

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the runtime.

        Args:
            agent: Agent instance to register.
        """
        if agent.name in self._agents:
            logger.warning(f"Agent {agent.name} already registered, replacing")

        self._agents[agent.name] = agent
        self._router.register_agent(agent.name, agent)
        logger.info(f"Registered agent: {agent.name} (role: {agent.role.value})")

    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent.

        Args:
            name: Agent name.

        Returns:
            True if agent was registered, False otherwise.
        """
        if name in self._agents:
            del self._agents[name]
            self._router.unregister_agent(name)
            logger.info(f"Unregistered agent: {name}")
            return True
        return False

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def create_and_register_agents(
        self,
        agent_configs: List[Dict[str, Any]],
        provider: Optional["LLMProvider"] = None,
    ) -> None:
        """Create and register multiple agents.

        Args:
            agent_configs: List of agent configurations.
                Each dict should have: 'name', 'role', and optionally 'model'.
            provider: Optional LLM provider to use for all agents.
        """
        for config in agent_configs:
            name = config["name"]
            role_str = config["role"]
            model = config.get("model", "gpt-4")
            enable_llm = config.get("enable_llm", provider is not None)

            # Map role string to enum
            try:
                role = AgentRole(role_str)
            except ValueError:
                logger.error(f"Invalid role {role_str} for agent {name}")
                continue

            # Create agent based on role
            if role == AgentRole.PLANNER:
                from ..agents.planner import PlannerAgent
                agent = PlannerAgent(
                    name=name,
                    model=model,
                    provider=provider if enable_llm else None,
                    enable_llm=enable_llm,
                )
            elif role == AgentRole.EXECUTOR:
                from ..agents.executor import ExecutorAgent
                agent = ExecutorAgent(
                    name=name,
                    model=model,
                    provider=provider if enable_llm else None,
                    enable_llm=enable_llm,
                )
            elif role == AgentRole.REVIEWER:
                from ..agents.reviewer import ReviewerAgent
                agent = ReviewerAgent(
                    name=name,
                    model=model,
                    provider=provider if enable_llm else None,
                    enable_llm=enable_llm,
                )
            elif role == AgentRole.TOOL:
                from ..agents.tool_agent import create_tool_agent_with_defaults
                agent = create_tool_agent_with_defaults(name=name)
            else:
                from ..core.agent import SimpleAgent
                agent = SimpleAgent(name=name, role=role, model=model)

            self.register_agent(agent)

    def set_llm_provider(self, provider: "LLMProvider") -> None:
        """Set LLM provider for all registered agents.

        Args:
            provider: LLM provider instance.
        """
        for agent in self._agents.values():
            if hasattr(agent, "set_provider"):
                agent.set_provider(provider)
        logger.info(f"Set LLM provider for {len(self._agents)} agents")

    # ==================== Execution ====================

    async def execute(
        self,
        task: Any,
        mode: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a task using the multi-agent system.

        Args:
            task: Task to execute (dict, string, or custom type).
            mode: Collaboration mode ('hierarchical', 'decentralized', 'pipeline').
                  If None, uses dynamic selection.
            context: Optional execution context.

        Returns:
            Execution result.
        """
        # Initialize shared memory if not already done
        if self.config.enable_shared_memory and self._shared_memory:
            await self.init_shared_memory_async()

        task_id = f"task_{len(self._task_history)}"
        logger.info(f"Starting task {task_id}")

        # Publish task-started event
        _bus = get_event_bus()
        await _bus.publish(Event(
            type=EventType.TASK_STARTED,
            source="runtime",
            data={"task_id": task_id},
        ))
        _task_start = time.monotonic()

        # Trace task received
        if self._tracer:
            task_desc = task.get("description", str(task)) if isinstance(task, dict) else str(task)
            for agent_name in self._agents:
                self._tracer.trace_task_received(agent_name, task_id, task_desc)

        # Create task context
        task_context = TaskContext(task_id, self._context)

        # Determine collaboration mode
        if mode:
            collaboration_mode = CollaborationRegistry.create(
                mode,
                CollaborationConfig(max_iterations=self.config.max_iterations),
            )
        else:
            collaboration_mode = self._selector.select_mode(
                task,
                list(self._agents.values()),
                context,
            )

        if collaboration_mode is None:
            # Fallback to hierarchical
            collaboration_mode = HierarchicalMode(
                CollaborationConfig(max_iterations=self.config.max_iterations)
            )

        logger.info(f"Using collaboration mode: {collaboration_mode.name}")

        # Execute collaboration
        try:
            result = await collaboration_mode.execute(
                task,
                self._agents,
                context,
            )

            # Merge task context
            task_context.set("result", result)
            task_context.merge_to_parent()

            # Record in history
            _duration = time.monotonic() - _task_start
            self._task_history.append({
                "task_id": task_id,
                "task": task,
                "mode": collaboration_mode.name,
                "result": result,
                "status": "completed",
                "duration_s": _duration,
            })

            # Trace task completed
            if self._tracer:
                for agent_name in self._agents:
                    self._tracer.trace_task_completed(agent_name, task_id, success=True)

            # Record collaboration in shared memory
            if self._shared_memory:
                try:
                    await self._shared_memory.add_collaboration_record(
                        task_id=task_id,
                        agents=list(self._agents.keys()),
                        mode=collaboration_mode.name,
                        result=str(result)[:500],  # Truncate for storage
                    )
                except Exception as e:
                    logger.warning(f"Failed to record collaboration in shared memory: {e}")

            await _bus.publish(Event(
                type=EventType.TASK_COMPLETED,
                source="runtime",
                data={"task_id": task_id, "mode": collaboration_mode.name, "duration_s": _duration},
            ))

            logger.info(f"Task {task_id} completed in {_duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")

            # Trace error
            if self._tracer:
                for agent_name in self._agents:
                    self._tracer.trace_error(agent_name, str(e), {"task_id": task_id})

            self._task_history.append({
                "task_id": task_id,
                "task": task,
                "mode": collaboration_mode.name,
                "error": str(e),
                "status": "failed",
            })
            await _bus.publish(Event(
                type=EventType.TASK_FAILED,
                source="runtime",
                data={"task_id": task_id, "mode": collaboration_mode.name, "error": str(e)},
            ))
            if self.config.stop_on_error:
                raise
            return {"error": str(e)}

    def execute_sync(
        self,
        task: Any,
        mode: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Synchronous wrapper for execute.

        Args:
            task: Task to execute.
            mode: Collaboration mode.
            context: Optional context.

        Returns:
            Execution result.
        """
        return asyncio.run(self.execute(task, mode, context))

    # ==================== Collaboration Mode Management ====================

    def set_collaboration_mode(self, mode: str) -> None:
        """Set the default collaboration mode.

        Args:
            mode: Mode name ('hierarchical', 'decentralized', 'pipeline').
        """
        self.config.default_mode = mode

    def get_available_modes(self) -> List[str]:
        """Get list of available collaboration modes."""
        return self._selector.get_available_modes()

    # ==================== Context Management ====================

    def update_context(self, key: str, value: Any) -> None:
        """Update shared context.

        Args:
            key: Context key.
            value: Value to store.
        """
        self._context.update_shared(key, value)

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get shared context value.

        Args:
            key: Context key.
            default: Default value if not found.

        Returns:
            Context value or default.
        """
        return self._context.get_shared(key, default)

    # ==================== Shared Memory Management ====================

    def get_shared_memory(self) -> Optional["SharedMemory"]:
        """Get the shared memory instance.

        Returns:
            SharedMemory instance or None if not enabled.
        """
        return self._shared_memory

    async def search_shared_memory(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search shared memory.

        Args:
            query: Search query.
            category: Optional category filter.
            limit: Maximum results.

        Returns:
            List of matching shared memories.
        """
        if self._shared_memory:
            return await self._shared_memory.search_shared(
                query=query,
                category=category,
                limit=limit,
            )
        return []

    async def store_shared_decision(
        self,
        decision: str,
        made_by: str,
        rationale: Optional[str] = None,
    ) -> Optional[str]:
        """Store a team decision in shared memory.

        Args:
            decision: Decision made.
            made_by: Agent that made the decision.
            rationale: Optional reasoning.

        Returns:
            Memory ID.
        """
        if self._shared_memory:
            return await self._shared_memory.store_decision(
                decision=decision,
                made_by=made_by,
                rationale=rationale,
            )
        return None

    async def store_shared_knowledge(
        self,
        fact: str,
        source: Optional[str] = None,
    ) -> Optional[str]:
        """Store team knowledge in shared memory.

        Args:
            fact: Knowledge fact.
            source: Optional source.

        Returns:
            Memory ID.
        """
        if self._shared_memory:
            return await self._shared_memory.store_knowledge(
                fact=fact,
                source=source,
            )
        return None

    # ==================== Tracer Access ====================

    def get_tracer(self) -> Optional["ExecutionTracer"]:
        """Get the execution tracer.

        Returns:
            ExecutionTracer instance or None if tracing is disabled.
        """
        return self._tracer

    def enable_tracing(self, task_id: str = "task_0") -> None:
        """Enable execution tracing.

        Args:
            task_id: Initial task ID for tracing.
        """
        if self._tracer is None:
            from ..visualization.tracer import ExecutionTracer
            self._tracer = ExecutionTracer(task_id=task_id)
            logger.info("Execution tracing enabled")

    def disable_tracing(self) -> None:
        """Disable execution tracing."""
        self._tracer = None
        logger.info("Execution tracing disabled")

    # ==================== Utilities ====================

    def get_task_history(self) -> List[Dict[str, Any]]:
        """Get task execution history."""
        return self._task_history.copy()

    def clear_task_history(self) -> None:
        """Clear task execution history."""
        self._task_history.clear()

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information.

        Returns:
            Dictionary with system status.
        """
        return {
            "running": self._running,
            "agents": {
                name: {
                    "role": agent.role.value,
                    "state": agent.state.value,
                    "memory_size": len(agent.memory),
                }
                for name, agent in self._agents.items()
            },
            "context_size": len(self._context),
            "tasks_completed": len([t for t in self._task_history if t.get("status") == "completed"]),
            "tasks_failed": len([t for t in self._task_history if t.get("status") == "failed"]),
        }

    def reset(self) -> None:
        """Reset the runtime to initial state."""
        for agent in self._agents.values():
            agent.clear_memory()
        self._context.clear_all()
        self._router.clear_routes()
        self._task_history.clear()
        logger.info("Runtime reset")


# Factory function for quick setup
def create_runtime(
    agents: Optional[List[Dict[str, Any]]] = None,
    mode: str = "hierarchical",
    **kwargs,
) -> RuntimeEngine:
    """Create and configure a runtime engine.

    Args:
        agents: List of agent configurations.
        mode: Default collaboration mode.
        **kwargs: Additional runtime config options.

    Returns:
        Configured RuntimeEngine instance.
    """
    config = RuntimeConfig(default_mode=mode, **kwargs)
    runtime = RuntimeEngine(config)

    if agents:
        runtime.create_and_register_agents(agents)

    return runtime
