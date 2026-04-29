"""Base classes for collaboration modes."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass

from ..core.agent import BaseAgent, AgentRole, Message


@dataclass
class CollaborationConfig:
    """Configuration for collaboration execution."""

    max_iterations: int = 10
    timeout: Optional[float] = None
    stop_on_error: bool = True
    enable_feedback: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CollaborationMode(ABC):
    """Abstract base class for collaboration modes.

    A collaboration mode defines how multiple agents work together
    to accomplish a task.
    """

    name: str = "base"
    description: str = "Base collaboration mode"

    def __init__(self, config: Optional[CollaborationConfig] = None):
        self.config = config or CollaborationConfig()

    @abstractmethod
    async def execute(
        self,
        task: Any,
        agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a collaborative task.

        Args:
            task: The task to execute.
            agents: Dictionary of available agents by name.
            context: Optional shared context.

        Returns:
            The result of the collaboration.
        """
        pass

    @abstractmethod
    def select_agents(
        self,
        task: Any,
        available_agents: List[BaseAgent],
    ) -> List[BaseAgent]:
        """Select appropriate agents for the task.

        Args:
            task: The task to execute.
            available_agents: List of available agents.

        Returns:
            List of selected agents.
        """
        pass

    def validate_agents(self, agents: List[BaseAgent]) -> bool:
        """Validate that the selected agents can collaborate.

        Args:
            agents: List of agents to validate.

        Returns:
            True if agents are valid for this mode.
        """
        return len(agents) > 0

    def get_required_roles(self) -> List[AgentRole]:
        """Get the roles required for this collaboration mode.

        Returns:
            List of required agent roles.
        """
        return []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"


class CollaborationRegistry:
    """Registry for collaboration modes.

    Allows dynamic registration and retrieval of collaboration modes.
    """

    _modes: Dict[str, Type[CollaborationMode]] = {}

    @classmethod
    def register(cls, name: str, mode_class: Type[CollaborationMode]) -> None:
        """Register a collaboration mode.

        Args:
            name: Mode identifier.
            mode_class: Mode class.
        """
        cls._modes[name] = mode_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[CollaborationMode]]:
        """Get a collaboration mode class.

        Args:
            name: Mode identifier.

        Returns:
            Mode class or None if not found.
        """
        return cls._modes.get(name)

    @classmethod
    def create(cls, name: str, config: Optional[CollaborationConfig] = None) -> Optional[CollaborationMode]:
        """Create a collaboration mode instance.

        Args:
            name: Mode identifier.
            config: Optional configuration.

        Returns:
            Collaboration mode instance or None.
        """
        mode_class = cls.get(name)
        if mode_class:
            return mode_class(config)
        return None

    @classmethod
    def list_modes(cls) -> List[str]:
        """List all registered mode names."""
        return list(cls._modes.keys())


# Register base mode
CollaborationRegistry.register("base", CollaborationMode)
