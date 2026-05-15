"""Event bus for MACS monitoring — publish/subscribe for system events."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(Enum):
    """System events emitted throughout the agent lifecycle."""

    # Task lifecycle
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Agent lifecycle
    AGENT_STATE_CHANGED = "agent_state_changed"
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"

    # Message routing
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_DROPPED = "message_dropped"

    # Collaboration
    COLLABORATION_STARTED = "collaboration_started"
    COLLABORATION_COMPLETED = "collaboration_completed"
    COLLABORATION_PHASE = "collaboration_phase"

    # LLM
    LLM_CALL_STARTED = "llm_call_started"
    LLM_CALL_COMPLETED = "llm_call_completed"
    LLM_TOOL_USED = "llm_tool_used"

    # Self-correction
    CORRECTION_ATTEMPT_STARTED = "correction_attempt_started"
    CORRECTION_QUALITY_EVALUATED = "correction_quality_evaluated"
    CORRECTION_COMPLETED = "correction_completed"

    # Tools
    TOOL_INVOKED = "tool_invoked"
    TOOL_RESULT = "tool_result"

    # System
    ERROR = "error"
    WARNING = "warning"


logger = logging.getLogger(__name__)


@dataclass
class Event:
    """A single event in the system."""
    type: EventType
    source: str                           # Component that emitted the event
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


# Handler type: async or sync callable that accepts an Event
Handler = Callable[[Event], Any]


class EventBus:
    """Lightweight publish/subscribe event bus.

    Components call ``publish()`` to emit events; monitors and loggers
    call ``subscribe()`` to receive them.
    """

    def __init__(self):
        self._handlers: Dict[str, List[Handler]] = {}  # event_type → handlers
        self._wildcard: List[Handler] = []              # handlers for ALL events
        self._history: List[Event] = []
        self._max_history: int = 1000

    def subscribe(
        self,
        handler: Handler,
        event_type: Optional[EventType] = None,
    ) -> None:
        """Register a handler for an event type.

        Args:
            handler: Callable(Event) — sync or async.
            event_type: Event to listen for. Pass None to receive all events.
        """
        if event_type is None:
            self._wildcard.append(handler)
        else:
            key = event_type.value
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(handler)

    def unsubscribe(
        self,
        handler: Handler,
        event_type: Optional[EventType] = None,
    ) -> None:
        """Remove a handler."""
        if event_type is None:
            if handler in self._wildcard:
                self._wildcard.remove(handler)
        else:
            key = event_type.value
            if key in self._handlers and handler in self._handlers[key]:
                self._handlers[key].remove(handler)

    async def publish(self, event: Event) -> None:
        """Emit an event to all matching handlers."""
        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Collect handlers
        handlers = list(self._wildcard)
        handlers += self._handlers.get(event.type.value, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.warning(f"[EventBus] Handler error for {event.type.value}: {e}")

    def publish_sync(self, event: Event) -> None:
        """Fire-and-forget publish from sync contexts."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.publish(event))
            else:
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            pass  # No event loop available — silently skip

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Return recent events, optionally filtered by type."""
        history = self._history
        if event_type:
            history = [e for e in history if e.type == event_type]
        return history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()

    def __len__(self) -> int:
        return len(self._history)

    def __bool__(self) -> bool:
        """EventBus instances are always truthy, regardless of history length."""
        return True


# Global default event bus
_default_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Return the global default event bus."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


def reset_event_bus() -> None:
    global _default_bus
    _default_bus = None
