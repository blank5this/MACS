"""Session memory — short-term conversation context per user session.

Stores conversation history per session_id, retrieves for context,
and automatically expires old sessions.

Usage::

    from macs_pkg.utils.session_memory import SessionMemory

    memory = SessionMemory(ttl_seconds=3600)  # 1 hour TTL

    await memory.add("user123", "Hello", "assistant", "Hi, how can I help?")
    history = await memory.get("user123")
    await memory.clear("user123")
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str          # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionMemory:
    """In-memory session storage with TTL auto-expiry.

    Each session has:
    - Conversation history (list of ConversationTurn)
    - Last access timestamp (for TTL)
    - Session metadata (user info, preferences, etc.)
    """

    def __init__(
        self,
        ttl_seconds: float = 3600.0,
        max_turns_per_session: int = 50,
        max_sessions: int = 1000,
    ):
        """Initialize session memory.

        Args:
            ttl_seconds: Time-to-live for sessions (seconds of inactivity).
            max_turns_per_session: Maximum conversation turns to keep per session.
            max_sessions: Maximum number of concurrent sessions before LRU eviction.
        """
        self._sessions: Dict[str, List[ConversationTurn]] = {}
        self._session_meta: Dict[str, Dict[str, Any]] = {}
        self._last_access: Dict[str, float] = {}
        self._ttl = ttl_seconds
        self._max_turns = max_turns_per_session
        self._max_sessions = max_sessions

    def _now(self) -> float:
        return time.time()

    def _is_expired(self, session_id: str) -> bool:
        """Check if session has expired due to inactivity."""
        if session_id not in self._last_access:
            return True
        return self._now() - self._last_access[session_id] > self._ttl

    def _evict_expired(self) -> None:
        """Remove expired sessions."""
        expired = [
            sid for sid in self._sessions
            if self._is_expired(sid)
        ]
        for sid in expired:
            del self._sessions[sid]
            del self._last_access[sid]
            self._session_meta.pop(sid, None)

    def _evict_lru_if_needed(self) -> None:
        """Evict least recently used session if at capacity."""
        if len(self._sessions) >= self._max_sessions:
            # Find LRU session
            lru_sid = min(self._last_access, key=self._last_access.get)
            del self._sessions[lru_sid]
            del self._last_access[lru_sid]
            self._session_meta.pop(lru_sid, None)

    # ─── Public API ────────────────────────────────────────────────────────

    async def add(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a turn to a session's conversation history.

        Args:
            session_id: Unique session identifier.
            role: "user" or "assistant".
            content: Message content.
            metadata: Optional metadata (intent, tool used, etc.).
        """
        self._evict_expired()
        self._evict_lru_if_needed()

        if session_id not in self._sessions:
            self._sessions[session_id] = []
            self._session_meta[session_id] = {}

        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self._sessions[session_id].append(turn)

        # Trim if over max turns (keep most recent)
        if len(self._sessions[session_id]) > self._max_turns:
            self._sessions[session_id] = self._sessions[session_id][-self._max_turns:]

        self._last_access[session_id] = self._now()

    async def get(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """Get conversation history for a session.

        Args:
            session_id: Session to retrieve.
            limit: Maximum number of recent turns to return.

        Returns:
            List of ConversationTurn, newest last.
        """
        if self._is_expired(session_id):
            return []

        self._last_access[session_id] = self._now()
        history = self._sessions.get(session_id, [])

        if limit:
            return history[-limit:]
        return history.copy()

    async def get_last_user_message(self, session_id: str) -> Optional[str]:
        """Get the most recent user message.

        Args:
            session_id: Session to search.

        Returns:
            Content of last user message, or None.
        """
        history = await self.get(session_id)
        for turn in reversed(history):
            if turn.role == "user":
                return turn.content
        return None

    async def set_metadata(self, session_id: str, **kwargs: Any) -> None:
        """Set metadata for a session.

        Args:
            session_id: Session to update.
            **kwargs: Metadata key-value pairs.
        """
        if session_id not in self._session_meta:
            self._session_meta[session_id] = {}
        self._session_meta[session_id].update(kwargs)
        self._last_access[session_id] = self._now()

    async def get_metadata(self, session_id: str) -> Dict[str, Any]:
        """Get metadata for a session.

        Args:
            session_id: Session to retrieve.

        Returns:
            Metadata dict (empty if session not found).
        """
        if self._is_expired(session_id):
            return {}
        return self._session_meta.get(session_id, {}).copy()

    async def clear(self, session_id: str) -> None:
        """Clear a session's history.

        Args:
            session_id: Session to clear.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._last_access:
            del self._last_access[session_id]
        self._session_meta.pop(session_id, None)

    async def list_sessions(self) -> List[str]:
        """List active (non-expired) session IDs.

        Returns:
            List of session IDs.
        """
        self._evict_expired()
        return list(self._sessions.keys())

    def session_count(self) -> int:
        """Get number of active sessions."""
        self._evict_expired()
        return len(self._sessions)
