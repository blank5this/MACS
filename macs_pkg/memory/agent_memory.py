"""Agent memory integration for MACS.

This module provides memory management for individual agents and
shared memory across agents in the collaboration system.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
import asyncio

if TYPE_CHECKING:
    from ..core.agent import BaseAgent, Message
    from .mempalace_client import MemPalaceClient, MemoryConfig


@dataclass
class MemoryEntry:
    """A single memory entry with metadata."""

    id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    memory_type: str = "interaction"  # interaction, decision, result, error
    related_agent: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "memory_type": self.memory_type,
            "related_agent": self.related_agent,
            "task_id": self.task_id,
            "metadata": self.metadata,
        }


@dataclass
class AgentMemoryConfig:
    """Configuration for agent memory."""

    # Memory behavior
    enabled: bool = True
    auto_save: bool = True
    max_short_term: int = 100  # Max items in short-term memory

    # Retrieval settings
    retrieve_on_think: bool = True  # Retrieve relevant memories before thinking
    retrieve_limit: int = 5  # Number of memories to retrieve
    similarity_threshold: float = 0.6

    # Categorization
    store_interactions: bool = True
    store_decisions: bool = True
    store_results: bool = True
    store_errors: bool = True


class AgentMemory:
    """Long-term memory manager for a single agent.

    AgentMemory provides:
    - Short-term memory: Current conversation/context
    - Long-term memory: Persisted memories via MemPalace
    - Semantic retrieval: Search relevant memories
    - Automatic categorization: Interactions, decisions, results, errors
    """

    def __init__(
        self,
        agent_name: str,
        agent_role: str,
        client: "MemPalaceClient",
        config: Optional[AgentMemoryConfig] = None,
    ):
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.client = client
        self.config = config or AgentMemoryConfig()

        # Short-term memory (in-memory, not persisted)
        self._short_term: List[MemoryEntry] = []

        # Wing/room structure for this agent
        self._wing = f"agent_{agent_name}"
        self._role_room = f"role_{agent_role}"

        # Cache of recent retrievals
        self._retrieval_cache: Dict[str, List[MemoryEntry]] = {}
        self._cache_ttl = 60  # seconds

    async def initialize(self) -> None:
        """Initialize the agent's memory."""
        await self.client.initialize()

        # Create wing for this agent
        # (In MemPalace, wings are created automatically on first add)

        logger.debug(f"Initialized memory for agent {self.agent_name}")

    async def remember(
        self,
        content: str,
        memory_type: str = "interaction",
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a memory.

        Args:
            content: Content to remember.
            memory_type: Type of memory (interaction, decision, result, error).
            task_id: Associated task ID.
            metadata: Additional metadata.

        Returns:
            Memory ID if successful.
        """
        if not self.config.enabled:
            return None

        memory_id = f"{self.agent_name}_{datetime.now().timestamp()}"

        # Add to short-term memory
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            related_agent=self.agent_name,
            task_id=task_id,
            metadata=metadata or {},
        )
        self._short_term.append(entry)

        # Trim short-term if too long
        if len(self._short_term) > self.config.max_short_term:
            self._short_term = self._short_term[-self.config.max_short_term:]

        # Persist to MemPalace if enabled
        if self.config.auto_save:
            room = f"{self._role_room}_{memory_type}"
            result = await self.client.add_memory(
                content=content,
                wing=self._wing,
                room=room,
                drawer=memory_id,
                metadata={
                    "memory_type": memory_type,
                    "agent_role": self.agent_role,
                    "task_id": task_id,
                    **(metadata or {}),
                },
            )
            return result

        return memory_id

    async def recall(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryEntry]:
        """Recall relevant memories based on a query.

        Args:
            query: Search query.
            memory_type: Optional filter by memory type.
            limit: Maximum number of results.

        Returns:
            List of relevant memory entries.
        """
        if not self.config.enabled or not self.client.is_available():
            return []

        # Build room filter
        room = None
        if memory_type:
            room = f"{self._role_room}_{memory_type}"

        # Search MemPalace
        results = await self.client.search(
            query=query,
            wing=self._wing,
            room=room,
            limit=limit,
        )

        # Convert to MemoryEntry objects
        entries = []
        for item in results:
            entry = MemoryEntry(
                id=item.get("drawer", item.get("id", "")),
                content=item.get("content", ""),
                memory_type=item.get("metadata", {}).get("memory_type", "interaction"),
                task_id=item.get("metadata", {}).get("task_id"),
                metadata=item.get("metadata", {}),
            )
            entries.append(entry)

        # Cache results
        self._retrieval_cache[query] = entries

        return entries

    async def recall_context(
        self,
        task_id: str,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Recall memories related to a specific task.

        Args:
            task_id: Task identifier.
            limit: Maximum number of results.

        Returns:
            List of memory entries for the task.
        """
        return await self.recall(
            query=f"task:{task_id}",
            limit=limit,
        )

    async def remember_interaction(
        self,
        message_content: str,
        sender: str,
        receiver: str,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember an interaction with another agent.

        Args:
            message_content: Content of the interaction.
            sender: Sender agent name.
            receiver: Receiver agent name.
            task_id: Associated task ID.

        Returns:
            Memory ID.
        """
        content = f"[{sender} -> {receiver}]: {message_content}"
        return await self.remember(
            content=content,
            memory_type="interaction",
            task_id=task_id,
            metadata={
                "sender": sender,
                "receiver": receiver,
            },
        )

    async def remember_decision(
        self,
        decision: str,
        rationale: str,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember a decision made by the agent.

        Args:
            decision: The decision made.
            rationale: Reasoning behind the decision.
            task_id: Associated task ID.

        Returns:
            Memory ID.
        """
        content = f"Decision: {decision}\nRationale: {rationale}"
        return await self.remember(
            content=content,
            memory_type="decision",
            task_id=task_id,
            metadata={"rationale": rationale},
        )

    async def remember_result(
        self,
        action: str,
        result: Any,
        success: bool,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember a result from an action.

        Args:
            action: Action that produced the result.
            result: Result content.
            success: Whether the action was successful.
            task_id: Associated task ID.

        Returns:
            Memory ID.
        """
        content = f"Action: {action}\nResult: {result}\nSuccess: {success}"
        return await self.remember(
            content=content,
            memory_type="result",
            task_id=task_id,
            metadata={"action": action, "success": success},
        )

    async def remember_error(
        self,
        error: str,
        context: str,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember an error encountered.

        Args:
            error: Error message.
            context: Context where error occurred.
            task_id: Associated task ID.

        Returns:
            Memory ID.
        """
        content = f"Error: {error}\nContext: {context}"
        return await self.remember(
            content=content,
            memory_type="error",
            task_id=task_id,
            metadata={"context": context},
        )

    def get_short_term(self, limit: int = 10) -> List[MemoryEntry]:
        """Get recent short-term memories.

        Args:
            limit: Maximum number to return.

        Returns:
            List of recent memories.
        """
        return self._short_term[-limit:]

    async def get_all_memories(self, limit: int = 100) -> List[MemoryEntry]:
        """Get all memories for this agent.

        Args:
            limit: Maximum number to return.

        Returns:
            List of all memory entries.
        """
        results = await self.client.get_memories(
            wing=self._wing,
            limit=limit,
        )

        entries = []
        for item in results:
            entry = MemoryEntry(
                id=item.get("drawer", ""),
                content=item.get("content", ""),
                memory_type=item.get("metadata", {}).get("memory_type", "interaction"),
                task_id=item.get("metadata", {}).get("task_id"),
                metadata=item.get("metadata", {}),
            )
            entries.append(entry)

        return entries

    async def clear(self) -> None:
        """Clear all memories for this agent."""
        count = await self.client.clear_wing(self._wing)
        self._short_term.clear()
        self._retrieval_cache.clear()
        logger.info(f"Cleared {count} memories for agent {self.agent_name}")

    def get_wing(self) -> str:
        """Get the wing name for this agent."""
        return self._wing


class SharedMemory:
    """Shared memory across multiple agents.

    SharedMemory provides:
    - Shared knowledge accessible by all agents
    - Collaboration history
    - Team-wide decisions and context
    """

    def __init__(
        self,
        client: "MemPalaceClient",
        project_name: str = "macs_shared",
    ):
        self.client = client
        self.project_name = project_name
        self._shared_wing = f"shared_{project_name}"
        self._rooms = {
            "decisions": "shared_decisions",
            "context": "shared_context",
            "knowledge": "shared_knowledge",
            "history": "shared_history",
        }

    async def initialize(self) -> None:
        """Initialize shared memory."""
        await self.client.initialize()
        logger.debug(f"Initialized shared memory for project {self.project_name}")

    async def store_shared(
        self,
        content: str,
        category: str = "knowledge",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a shared memory.

        Args:
            content: Content to store.
            category: Category (decisions, context, knowledge, history).
            metadata: Additional metadata.

        Returns:
            Memory ID.
        """
        room = self._rooms.get(category, "shared_knowledge")

        return await self.client.add_memory(
            content=content,
            wing=self._shared_wing,
            room=room,
            metadata=metadata or {},
        )

    async def search_shared(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search shared memories.

        Args:
            query: Search query.
            category: Optional category filter.
            limit: Maximum results.

        Returns:
            List of matching shared memories.
        """
        room = self._rooms.get(category) if category else None

        return await self.client.search(
            query=query,
            wing=self._shared_wing,
            room=room,
            limit=limit,
        )

    async def store_decision(
        self,
        decision: str,
        made_by: str,
        rationale: Optional[str] = None,
    ) -> Optional[str]:
        """Store a team decision.

        Args:
            decision: Decision made.
            made_by: Agent that made the decision.
            rationale: Optional reasoning.

        Returns:
            Memory ID.
        """
        content = f"Decision by {made_by}: {decision}"
        if rationale:
            content += f"\nRationale: {rationale}"

        return await self.store_shared(
            content=content,
            category="decisions",
            metadata={
                "made_by": made_by,
                "rationale": rationale,
            },
        )

    async def store_context(
        self,
        key: str,
        value: Any,
        updated_by: Optional[str] = None,
    ) -> Optional[str]:
        """Store shared context.

        Args:
            key: Context key.
            value: Context value.
            updated_by: Agent that updated.

        Returns:
            Memory ID.
        """
        content = f"{key}: {value}"
        return await self.store_shared(
            content=content,
            category="context",
            metadata={
                "key": key,
                "updated_by": updated_by,
            },
        )

    async def get_shared_context(self, key: str) -> Optional[str]:
        """Get a specific shared context value.

        Args:
            key: Context key.

        Returns:
            Context value or None.
        """
        results = await self.search_shared(
            query=f"context: {key}",
            category="context",
            limit=1,
        )

        if results:
            content = results[0].get("content", "")
            # Extract value after ": "
            if ": " in content:
                return content.split(": ", 1)[1]
        return None

    async def store_knowledge(
        self,
        fact: str,
        source: Optional[str] = None,
    ) -> Optional[str]:
        """Store a piece of team knowledge.

        Args:
            fact: Knowledge fact.
            source: Optional source of the knowledge.

        Returns:
            Memory ID.
        """
        return await self.store_shared(
            content=fact,
            category="knowledge",
            metadata={"source": source},
        )

    async def add_collaboration_record(
        self,
        task_id: str,
        agents: List[str],
        mode: str,
        result: str,
    ) -> Optional[str]:
        """Record a collaboration session.

        Args:
            task_id: Task identifier.
            agents: Agents involved.
            mode: Collaboration mode used.
            result: Result of collaboration.

        Returns:
            Memory ID.
        """
        content = f"Collaboration on {task_id}: {agents} used {mode} mode"
        content += f"\nResult: {result}"

        return await self.store_shared(
            content=content,
            category="history",
            metadata={
                "task_id": task_id,
                "agents": agents,
                "mode": mode,
            },
        )

    async def search_history(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search collaboration history.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of matching history entries.
        """
        return await self.search_shared(
            query=query,
            category="history",
            limit=limit,
        )
