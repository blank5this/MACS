"""Context management for shared state across agents."""

from typing import Any, Dict, Optional
from threading import RLock
from datetime import datetime
import copy


class ContextManager:
    """Manages shared and agent-specific context.

    The context manager provides:
    - Shared context: Accessible by all agents, for global state
    - Agent contexts: Isolated per-agent state
    - Context history: Track changes over time for debugging
    """

    def __init__(self):
        self._shared_context: Dict[str, Any] = {}
        self._agent_contexts: Dict[str, Dict[str, Any]] = {}
        self._history: list = []  # Track context changes
        self._lock = RLock()

    def update_shared(self, key: str, value: Any) -> None:
        """Update a shared context value.

        Args:
            key: Context key.
            value: Value to store.
        """
        with self._lock:
            old_value = self._shared_context.get(key)
            self._shared_context[key] = copy.deepcopy(value)
            self._history.append({
                "type": "shared",
                "action": "update",
                "key": key,
                "old_value": old_value,
                "new_value": value,
                "timestamp": datetime.now(),
            })

    def get_shared(self, key: str, default: Any = None) -> Any:
        """Get a shared context value.

        Args:
            key: Context key.
            default: Default value if key not found.

        Returns:
            The stored value or default.
        """
        with self._lock:
            return self._shared_context.get(key, default)

    def get_all_shared(self) -> Dict[str, Any]:
        """Get all shared context as a dictionary."""
        with self._lock:
            return copy.deepcopy(self._shared_context)

    def delete_shared(self, key: str) -> bool:
        """Delete a shared context key.

        Args:
            key: Context key to delete.

        Returns:
            True if key existed, False otherwise.
        """
        with self._lock:
            if key in self._shared_context:
                del self._shared_context[key]
                return True
            return False

    def update_agent(self, agent_id: str, key: str, value: Any) -> None:
        """Update an agent-specific context value.

        Args:
            agent_id: Agent identifier.
            key: Context key.
            value: Value to store.
        """
        with self._lock:
            if agent_id not in self._agent_contexts:
                self._agent_contexts[agent_id] = {}
            old_value = self._agent_contexts[agent_id].get(key)
            self._agent_contexts[agent_id][key] = copy.deepcopy(value)
            self._history.append({
                "type": "agent",
                "agent_id": agent_id,
                "action": "update",
                "key": key,
                "old_value": old_value,
                "new_value": value,
                "timestamp": datetime.now(),
            })

    def get_agent(self, agent_id: str, key: str, default: Any = None) -> Any:
        """Get an agent-specific context value.

        Args:
            agent_id: Agent identifier.
            key: Context key.
            default: Default value if key not found.

        Returns:
            The stored value or default.
        """
        with self._lock:
            if agent_id not in self._agent_contexts:
                return default
            return self._agent_contexts[agent_id].get(key, default)

    def get_all_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get all context for a specific agent."""
        with self._lock:
            if agent_id not in self._agent_contexts:
                return {}
            return copy.deepcopy(self._agent_contexts[agent_id])

    def delete_agent(self, agent_id: str) -> bool:
        """Delete all context for an agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            True if agent existed, False otherwise.
        """
        with self._lock:
            if agent_id in self._agent_contexts:
                del self._agent_contexts[agent_id]
                return True
            return False

    def get_history(self, limit: Optional[int] = None) -> list:
        """Get context change history.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of history entries, most recent first.
        """
        with self._lock:
            history = self._history[::-1]  # Reverse for most recent first
            if limit:
                return history[:limit]
            return history

    def clear_all(self) -> None:
        """Clear all shared and agent contexts."""
        with self._lock:
            self._shared_context.clear()
            self._agent_contexts.clear()
            self._history.append({
                "type": "system",
                "action": "clear_all",
                "timestamp": datetime.now(),
            })

    def __len__(self) -> int:
        """Total number of context entries."""
        with self._lock:
            return len(self._shared_context) + sum(
                len(ctx) for ctx in self._agent_contexts.values()
            )


class TaskContext:
    """Context for a specific task execution.

    Provides isolated context during task execution that can be
    merged back into the global context upon completion.
    """

    def __init__(self, task_id: str, parent: Optional[ContextManager] = None):
        self.task_id = task_id
        self._parent = parent
        self._task_data: Dict[str, Any] = {}
        self._created_at = datetime.now()

    def set(self, key: str, value: Any) -> None:
        """Set a task context value."""
        self._task_data[key] = copy.deepcopy(value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a task context value."""
        if key in self._task_data:
            return self._task_data[key]
        if self._parent:
            return self._parent.get_shared(key, default)
        return default

    def merge_to_parent(self) -> None:
        """Merge task context back to parent context manager."""
        if self._parent:
            for key, value in self._task_data.items():
                self._parent.update_shared(f"{self.task_id}.{key}", value)

    def to_dict(self) -> Dict[str, Any]:
        """Export task context as dictionary."""
        return {
            "task_id": self.task_id,
            "data": copy.deepcopy(self._task_data),
            "created_at": self._created_at.isoformat(),
        }
