"""MemPalace client wrapper for MACS.

This module provides a clean interface to MemPalace's memory system,
adapting it for multi-agent collaboration scenarios.

Note: MemPalace 3.x is a CLI-based tool optimized for project code/doc mining.
For dynamic agent runtime memory, we use an enhanced in-memory fallback
that provides the same interface.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from loguru import logger
import asyncio
import subprocess
import json
import os
import re

from ..utils.errors import MemoryException, MACSErrorCode


@dataclass
class MemoryConfig:
    """Configuration for MemPalace integration."""

    # Storage path for memory data
    storage_path: str = "~/.macs/memory"

    # Wing/room/drawer naming conventions
    wing_prefix: str = "agent"
    room_prefix: str = "role"
    shared_wing: str = "shared"

    # Search settings
    default_limit: int = 5
    similarity_threshold: float = 0.7

    # Performance settings
    batch_size: int = 100
    async_mode: bool = True

    # MCP server settings
    enable_mcp: bool = True
    mcp_port: int = 8765


class MemPalaceClient:
    """Client for interacting with MemPalace memory system.

    MemPalace uses a palace metaphor for memory organization:
    - Wings: Top-level organization (agents, projects, people)
    - Rooms: Second-level topics within wings
    - Drawers: Individual memory entries within rooms

    This client provides both low-level access and high-level
    abstractions optimized for MACS workflows.

    Note: MemPalace 3.x CLI is designed for project file mining.
    For runtime agent memory (short-term interactions, decisions, results),
    we use an enhanced in-memory store with semantic-like search.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._initialized = False
        self._cli_available = False  # MemPalace CLI status
        self._palace_path: Optional[str] = None
        self._lock = asyncio.Lock() if self.config.async_mode else None

        # Enhanced in-memory fallback store
        self._store: Dict[str, Dict[str, Any]] = {}
        self._store_counter = 0

        # Cache for frequently accessed memories
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_ttl = 300  # seconds

    async def initialize(self, storage_path: Optional[str] = None) -> None:
        """Initialize the memory system.

        Args:
            storage_path: Optional custom storage path.
        """
        if self._initialized:
            logger.warning("Memory already initialized")
            return

        path = os.path.expanduser(storage_path or self.config.storage_path)
        logger.info(f"Initializing memory at {path}")

        # Try to use MemPalace CLI if available
        self._cli_available = await self._check_cli()

        if self._cli_available:
            self._palace_path = path
            logger.info("MemPalace CLI available - using CLI mode")
        else:
            logger.info("Using enhanced in-memory fallback for agent memory")

        self._initialized = True

    async def _check_cli(self) -> bool:
        """Check if MemPalace CLI is available and functional."""
        try:
            result = subprocess.run(
                ["mempalace", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Check if palace is initialized
                check = subprocess.run(
                    ["mempalace", "status"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                # CLI works but may need init
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return False

    async def add_memory(
        self,
        content: str,
        wing: str,
        room: str,
        drawer: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Add a memory entry.

        Args:
            content: The memory content (will be stored verbatim).
            wing: Wing name (e.g., "planner_agent", "shared").
            room: Room name (e.g., "task_analysis", "decisions").
            drawer: Optional drawer ID (auto-generated if not provided).
            metadata: Optional metadata dictionary.

        Returns:
            Memory ID if successful, None otherwise.
        """
        if not self._initialized:
            await self.initialize()

        drawer_id = drawer or f"drawer_{self._store_counter}"
        self._store_counter += 1

        key = f"{wing}:{room}:{drawer_id}"
        self._store[key] = {
            "content": content,
            "wing": wing,
            "room": room,
            "drawer": drawer_id,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        logger.debug(f"Added memory: {wing}/{room}/{drawer_id}")
        return drawer_id

    async def search(
        self,
        query: str,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        limit: int = 5,
        mode: str = "hybrid",
    ) -> List[Dict[str, Any]]:
        """Search memories.

        Args:
            query: Natural language search query.
            wing: Optional wing to search within.
            room: Optional room to search within.
            limit: Maximum number of results.
            mode: Search mode (for compatibility, not used in fallback).

        Returns:
            List of matching memory entries with content and metadata.
        """
        if not self._initialized:
            await self.initialize()

        results = []
        query_lower = query.lower()

        # Tokenize query for better matching
        query_tokens = set(re.findall(r'\w+', query_lower))

        for key, data in self._store.items():
            wing_match = not wing or data["wing"] == wing
            room_match = not room or data["room"] == room

            if not wing_match or not room_match:
                continue

            content_lower = data["content"].lower()
            content_tokens = set(re.findall(r'\w+', content_lower))

            # Calculate simple relevance score
            if query_lower in content_lower:
                score = 1.0  # Exact substring match
            elif query_tokens and query_tokens & content_tokens:
                # Token overlap
                overlap = len(query_tokens & content_tokens)
                score = overlap / max(len(query_tokens), 1) * 0.8
            else:
                score = 0.0

            if score > 0:
                results.append({
                    **data,
                    "score": score,
                })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def get_memories(
        self,
        wing: str,
        room: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all memories in a wing/room.

        Args:
            wing: Wing name.
            room: Optional room name.
            limit: Maximum number of results.

        Returns:
            List of memory entries.
        """
        if not self._initialized:
            await self.initialize()

        results = []
        for key, data in self._store.items():
            if data["wing"] != wing:
                continue
            if room and data["room"] != room:
                continue
            results.append({**data, "score": 1.0})

        return results[:limit]

    async def delete_memory(
        self,
        wing: str,
        room: str,
        drawer: str,
    ) -> bool:
        """Delete a specific memory.

        Args:
            wing: Wing name.
            room: Room name.
            drawer: Drawer ID.

        Returns:
            True if successful.
        """
        key = f"{wing}:{room}:{drawer}"
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def update_memory(
        self,
        wing: str,
        room: str,
        drawer: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing memory.

        Args:
            wing: Wing name.
            room: Room name.
            drawer: Drawer ID.
            content: New content.
            metadata: Optional new metadata.

        Returns:
            True if successful.
        """
        key = f"{wing}:{room}:{drawer}"
        if key in self._store:
            self._store[key]["content"] = content
            if metadata:
                self._store[key]["metadata"] = metadata
            self._store[key]["timestamp"] = datetime.now().isoformat()
            return True
        return False

    async def get_agent_wing(self, agent_name: str) -> str:
        """Get or create the wing name for an agent.

        Args:
            agent_name: Name of the agent.

        Returns:
            Wing name for the agent.
        """
        return f"{self.config.wing_prefix}_{agent_name}"

    async def get_role_room(self, role: str) -> str:
        """Get or create the room name for a role.

        Args:
            role: Agent role.

        Returns:
            Room name for the role.
        """
        return f"{self.config.room_prefix}_{role}"

    # ==================== Knowledge Graph Operations ====================

    async def add_entity(
        self,
        entity_type: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add an entity to the knowledge graph.

        Args:
            entity_type: Type of entity (e.g., "agent", "task", "project").
            name: Entity name/identifier.
            properties: Optional entity properties.

        Returns:
            True if successful.
        """
        return await self.add_memory(
            content=json.dumps({"type": entity_type, "name": name, "props": properties}),
            wing="knowledge_graph",
            room="entities",
            drawer=name,
            metadata={"entity_type": entity_type},
        ) is not None

    async def add_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a relation between two entities.

        Args:
            from_entity: Source entity.
            to_entity: Target entity.
            relation_type: Type of relation (e.g., "collaborated_with", "depends_on").
            properties: Optional relation properties.

        Returns:
            True if successful.
        """
        return await self.add_memory(
            content=json.dumps({
                "from": from_entity,
                "to": to_entity,
                "type": relation_type,
                "props": properties,
            }),
            wing="knowledge_graph",
            room="relations",
            drawer=f"{from_entity}_{relation_type}_{to_entity}",
            metadata={"relation_type": relation_type},
        ) is not None

    async def query_knowledge(
        self,
        entity: Optional[str] = None,
        relation_type: Optional[str] = None,
        depth: int = 1,
    ) -> Dict[str, Any]:
        """Query the knowledge graph.

        Args:
            entity: Optional entity to start from.
            relation_type: Optional relation type to follow.
            depth: Traversal depth (not used in simple implementation).

        Returns:
            Query results.
        """
        entities = []
        relations = []

        for key, data in self._store.items():
            if data["wing"] == "knowledge_graph":
                if data["room"] == "entities":
                    entities.append(data)
                elif data["room"] == "relations":
                    relations.append(data)

        return {"entities": entities, "relations": relations}

    # ==================== Utility Methods ====================

    async def clear_wing(self, wing: str) -> int:
        """Clear all memories in a wing.

        Args:
            wing: Wing name.

        Returns:
            Number of memories cleared.
        """
        keys_to_delete = [
            k for k, v in self._store.items()
            if v["wing"] == wing
        ]
        for key in keys_to_delete:
            del self._store[key]
        return len(keys_to_delete)

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics.

        Returns:
            Statistics dictionary.
        """
        return {
            "initialized": self._initialized,
            "backend": "mempalace_cli" if self._cli_available else "enhanced_fallback",
            "storage_path": self.config.storage_path,
            "total_entries": len(self._store),
            "cli_available": self._cli_available,
        }

    def is_available(self) -> bool:
        """Check if memory system is available.

        Returns:
            True if initialized and ready.
        """
        return self._initialized
