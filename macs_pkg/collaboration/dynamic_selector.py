"""Dynamic collaboration mode selector."""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from ..core.agent import BaseAgent, AgentRole
from .base import CollaborationMode, CollaborationConfig
from .hierarchical import HierarchicalMode
from .decentralized import DecentralizedMode
from .pipeline import PipelineMode, ParallelPipelineMode


@dataclass
class Task特征:
    """Task characteristics for mode selection."""
    complexity: str = "medium"  # low, medium, high
    independence: str = "dependent"  # independent, partial, dependent
    urgency: str = "normal"  # low, normal, high
    consensus_needed: bool = False
    requires_review: bool = True


class DynamicSelector:
    """Dynamically selects the best collaboration mode based on task characteristics.

    The selector analyzes task properties and selects the most appropriate
    collaboration mode from:
    - HierarchicalMode: Complex tasks needing decomposition
    - DecentralizedMode: Tasks requiring consensus
    - PipelineMode: Sequential processing tasks
    - ParallelPipelineMode: Parallel independent subtasks
    """

    # Mode selection rules based on task characteristics
    MODE_RULES = {
        # Task type -> preferred mode
        "decomposition": "hierarchical",
        "complex_planning": "hierarchical",
        "independent": "parallel_pipeline",
        "parallel_subtasks": "parallel_pipeline",
        "consensus": "decentralized",
        "negotiation": "decentralized",
        "verification": "hierarchical",
        "sequential": "pipeline",
        "etl": "pipeline",
        "general": "hierarchical",  # Default
    }

    def __init__(self):
        self._custom_rules: Dict[str, str] = {}
        self._mode_cache: Dict[str, CollaborationMode] = {}

    def register_rule(self, task_type: str, mode_name: str) -> None:
        """Register a custom selection rule.

        Args:
            task_type: Task type identifier.
            mode_name: Name of the collaboration mode to use.
        """
        self._custom_rules[task_type] = mode_name

    def select_mode(
        self,
        task: Any,
        available_agents: List[BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> CollaborationMode:
        """Select the best collaboration mode for a task.

        Args:
            task: The task to analyze.
            available_agents: List of available agents.
            context: Optional context for decision making.

        Returns:
            The selected collaboration mode instance.
        """
        # Extract task characteristics
        task_info = self._analyze_task(task)

        # Determine mode based on rules
        mode_name = self._determine_mode(task_info, context or {})

        # Create or retrieve mode instance
        return self._get_or_create_mode(mode_name)

    def _analyze_task(self, task: Any) -> Task特征:
        """Analyze task to extract characteristics.

        Args:
            task: Task object (dict, string, or custom type).

        Returns:
            Task characteristics.
        """
        features = Task特征()

        if isinstance(task, dict):
            # Extract from dict
            features.complexity = task.get("complexity", "medium")
            features.independence = task.get("independence", "dependent")
            features.urgency = task.get("urgency", "normal")
            features.consensus_needed = task.get("consensus_needed", False)
            features.requires_review = task.get("requires_review", True)
        elif isinstance(task, str):
            # Simple heuristic based on string length/content
            features.complexity = "high" if len(task) > 500 else "medium" if len(task) > 100 else "low"

        return features

    def _determine_mode(self, features: Task特征, context: Dict[str, Any]) -> str:
        """Determine which mode to use based on features.

        Args:
            features: Task characteristics.
            context: Additional context.

        Returns:
            Mode name.
        """
        # Check context for explicit mode override
        if "forced_mode" in context:
            return context["forced_mode"]

        # Apply selection rules based on characteristics
        if features.consensus_needed or features.independence == "independent":
            if features.complexity == "high":
                return "decentralized"
            return "parallel_pipeline"

        if features.independence == "independent":
            return "parallel_pipeline"

        if features.requires_review and features.complexity == "high":
            return "hierarchical"

        if features.complexity == "low":
            return "pipeline"

        return "hierarchical"  # Default

    def _get_or_create_mode(self, mode_name: str) -> CollaborationMode:
        """Get or create a mode instance.

        Args:
            mode_name: Name of the mode.

        Returns:
            Collaboration mode instance.
        """
        if mode_name not in self._mode_cache:
            mode_class = CollaborationRegistry.get(mode_name)
            if mode_class:
                self._mode_cache[mode_name] = mode_class()
            else:
                # Fallback to hierarchical
                self._mode_cache[mode_name] = HierarchicalMode()
        return self._mode_cache[mode_name]

    def get_available_modes(self) -> List[str]:
        """Get list of available collaboration modes."""
        return CollaborationRegistry.list_modes()


# Import registry to ensure modes are registered
from .base import CollaborationRegistry

# Register all modes
CollaborationRegistry.register("hierarchical", HierarchicalMode)
CollaborationRegistry.register("decentralized", DecentralizedMode)
CollaborationRegistry.register("pipeline", PipelineMode)
CollaborationRegistry.register("parallel_pipeline", ParallelPipelineMode)


class AdaptiveSelector(DynamicSelector):
    """Adaptive selector that learns from past executions.

    Tracks which modes work best for different task types
    and adjusts selection accordingly.
    """

    def __init__(self):
        super().__init__()
        self._performance_history: Dict[str, List[float]] = {}  # mode -> scores
        self._task_mode_mapping: Dict[str, str] = {}  # task_type -> best mode

    def record_performance(
        self,
        task_type: str,
        mode_name: str,
        score: float,
    ) -> None:
        """Record how well a mode performed for a task type.

        Args:
            task_type: Type of task.
            mode_name: Mode that was used.
            score: Performance score (0-1).
        """
        if mode_name not in self._performance_history:
            self._performance_history[mode_name] = []
        self._performance_history[mode_name].append(score)

        # Update best mode mapping
        current_best = self._task_mode_mapping.get(task_type)
        if current_best is None:
            self._task_mode_mapping[task_type] = mode_name
        else:
            current_avg = sum(self._performance_history.get(current_best, [])) / max(len(self._performance_history.get(current_best, [])), 1)
            new_avg = sum(self._performance_history[mode_name]) / len(self._performance_history[mode_name])
            if new_avg > current_avg:
                self._task_mode_mapping[task_type] = mode_name

    def get_best_mode(self, task_type: str) -> Optional[str]:
        """Get the best performing mode for a task type.

        Args:
            task_type: Type of task.

        Returns:
            Best mode name or None.
        """
        return self._task_mode_mapping.get(task_type)
