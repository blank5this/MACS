"""Message routing for agent communication."""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import copy

from .agent import Message


class RoutePolicy(Enum):
    """Routing policy for message delivery."""

    DIRECT = "direct"  # Send directly to receiver
    BROADCAST = "broadcast"  # Send to all registered agents
    GROUP = "group"  # Send to agents in a specific group
    CONDITIONAL = "conditional"  # Use custom routing logic


@dataclass
class Route:
    """Represents a message route."""

    message_id: str
    source: str  # Original sender
    destination: str  # Intended receiver
    actual_route: List[str] = field(default_factory=list)  # Actual path taken
    hops: int = 0
    delivered: bool = False
    delivery_time: Optional[float] = None


class MessageRouter:
    """Routes messages between agents.

    The router maintains:
    - Agent registry: Maps agent names to their instances
    - Group mappings: Groups agents for group messaging
    - Route history: Track message delivery paths
    - Middleware: Optional message processing hooks
    """

    def __init__(self):
        self._agents: Dict[str, object] = {}  # name -> agent instance
        self._groups: Dict[str, List[str]] = {}  # group_name -> [agent_names]
        self._routes: Dict[str, Route] = {}  # message_id -> Route
        self._middleware: List[Callable] = []  # Message processing hooks
        self._fallback_handler: Optional[Callable] = None

    def register_agent(self, name: str, agent: object) -> None:
        """Register an agent with the router.

        Args:
            name: Agent's unique name.
            agent: Agent instance.
        """
        self._agents[name] = agent

    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent from the router.

        Args:
            name: Agent's name.

        Returns:
            True if agent was registered, False otherwise.
        """
        if name in self._agents:
            del self._agents[name]
            # Remove from all groups
            for group in self._groups.values():
                if name in group:
                    group.remove(name)
            return True
        return False

    def get_agent(self, name: str) -> Optional[object]:
        """Get an agent by name.

        Args:
            name: Agent's name.

        Returns:
            Agent instance or None if not found.
        """
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def create_group(self, name: str, members: Optional[List[str]] = None) -> None:
        """Create an agent group.

        Args:
            name: Group name.
            members: Initial group members.
        """
        self._groups[name] = members or []

    def add_to_group(self, group_name: str, agent_name: str) -> bool:
        """Add an agent to a group.

        Args:
            group_name: Name of the group.
            agent_name: Name of the agent to add.

        Returns:
            True if successful, False if agent not found.
        """
        if agent_name not in self._agents:
            return False
        if group_name not in self._groups:
            self._groups[group_name] = []
        if agent_name not in self._groups[group_name]:
            self._groups[group_name].append(agent_name)
        return True

    def remove_from_group(self, group_name: str, agent_name: str) -> bool:
        """Remove an agent from a group.

        Args:
            group_name: Name of the group.
            agent_name: Name of the agent to remove.

        Returns:
            True if agent was in group, False otherwise.
        """
        if group_name in self._groups and agent_name in self._groups[group_name]:
            self._groups[group_name].remove(agent_name)
            return True
        return False

    def get_group_members(self, group_name: str) -> List[str]:
        """Get members of a group.

        Args:
            group_name: Name of the group.

        Returns:
            List of agent names in the group.
        """
        return list(self._groups.get(group_name, []))

    def add_middleware(self, middleware: Callable[[Message], Optional[Message]]) -> None:
        """Add message processing middleware.

        Middleware is called before message delivery.
        If middleware returns None, message is dropped.

        Args:
            middleware: Callable that takes a message and returns optionally modified message.
        """
        self._middleware.append(middleware)

    def set_fallback_handler(self, handler: Callable[[Message], None]) -> None:
        """Set fallback handler for undeliverable messages.

        Args:
            handler: Callable that takes the undeliverable message.
        """
        self._fallback_handler = handler

    def route(self, message: Message) -> List[str]:
        """Route a message to its destination(s).

        Args:
            message: The message to route.

        Returns:
            List of agent names that received the message.
        """
        # Apply middleware
        processed_message = self._apply_middleware(message)
        if processed_message is None:
            return []  # Message was dropped

        recipients = self._resolve_recipients(processed_message)
        delivered_to = []

        for recipient in recipients:
            agent = self._agents.get(recipient)
            if agent:
                self._deliver_to_agent(processed_message, agent, recipient)
                delivered_to.append(recipient)

        # Track route
        route = Route(
            message_id=processed_message.id,
            source=processed_message.sender,
            destination=processed_message.receiver,
            actual_route=delivered_to,
            hops=len(delivered_to),
            delivered=len(delivered_to) > 0,
        )
        self._routes[processed_message.id] = route

        # Handle undeliverable
        if not delivered_to and self._fallback_handler:
            self._fallback_handler(processed_message)

        return delivered_to

    def _apply_middleware(self, message: Message) -> Optional[Message]:
        """Apply middleware chain to message."""
        result = message
        for mw in self._middleware:
            result = mw(copy.deepcopy(result))
            if result is None:
                return None
        return result

    def _resolve_recipients(self, message: Message) -> List[str]:
        """Resolve message recipients based on receiver field."""
        receiver = message.receiver

        if receiver == "*":
            # Broadcast to all
            return list(self._agents.keys())
        elif receiver.startswith("@"):
            # Group message
            group_name = receiver[1:]
            return self.get_group_members(group_name)
        else:
            # Direct message
            return [receiver] if receiver in self._agents else []

    def _deliver_to_agent(
        self, message: Message, agent: object, agent_name: str
    ) -> None:
        """Deliver message to a specific agent.

        This calls the agent's receive method if it exists.
        """
        if hasattr(agent, "receive"):
            agent.receive(message)

    def get_route_info(self, message_id: str) -> Optional[Route]:
        """Get routing information for a message.

        Args:
            message_id: The message ID.

        Returns:
            Route info or None if not found.
        """
        return self._routes.get(message_id)

    def clear_routes(self) -> None:
        """Clear route history."""
        self._routes.clear()
