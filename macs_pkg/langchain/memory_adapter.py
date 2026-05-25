"""Memory Adapter - Bridge MACS AgentMemory to LangChain Memory.

This module provides adapters to use MACS's AgentMemory (MemPalace-based)
with LangChain's Memory interface, enabling LangChain chains to access
MACS's distributed memory system.

Usage:
    from macs_pkg.langchain.memory_adapter import MACSMemoryAdapter
    from macs_pkg.core.agent import BaseAgent

    # Initialize shared memory
    await BaseAgent.init_shared_memory()

    # Create adapter
    memory = MACSMemoryAdapter(agent_memory)

    # Use with LangChain chain
    chain = prompt | chat_model | output_parser
    chain_with_memory = chain.with_history(memory=memory)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

# LangChain imports
_LC_ERROR: Optional[str] = None
_LC_AVAILABLE = False

try:
    from langchain_core.memory import BaseMemory as LCBaseMemory
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
    _LC_AVAILABLE = True
except (ImportError, OSError) as e:
    LCBaseMemory = None  # type: ignore
    _LC_ERROR = str(e)

if not _LC_AVAILABLE:
    import warnings
    warnings.warn(
        f"langchain-core unavailable ({_LC_ERROR}). "
        "Memory adapter will work in fallback mode without LangChain integration.",
        RuntimeWarning,
    )

# MACS imports
from macs_pkg.memory.agent_memory import AgentMemory, SharedMemory


# ─── Fallback class (when langchain-core unavailable) ─────────────────────────

class _FallbackMemoryAdapter:
    """Fallback Memory adapter when langchain-core is unavailable.

    This provides a minimal interface that can be upgraded to real LangChain
    Memory once langchain-core is available.
    """

    def __init__(
        self,
        agent_memory: Optional[AgentMemory] = None,
        memory_key: str = "agent_history",
        return_messages: bool = False,
        output_key: Optional[str] = None,
        input_key: Optional[str] = None,
        **kwargs: Any,
    ):
        self._agent_memory = agent_memory or AgentMemory()
        self._memory_key = memory_key
        self._return_messages = return_messages
        self._output_key = output_key
        self._input_key = input_key

    @property
    def memory_variables(self) -> List[str]:
        return [self._memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        history = self._agent_memory.get_short_term()
        if self._return_messages:
            messages = []
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append({"type": "human", "data": {"content": content}})
                else:
                    messages.append({"type": "ai", "data": {"content": content}})
            return {self._memory_key: messages}
        else:
            if not history:
                return {self._memory_key: ""}
            lines = []
            for msg in history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"{role}: {content}")
            return {self._memory_key: "\n".join(lines)}

    async def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        input_value = inputs.get(self._input_key, "") if self._input_key else ""
        output_value = outputs.get(self._output_key, "") if self._output_key else ""

        if input_value:
            await self._agent_memory.remember_interaction(
                message_content=str(input_value),
                sender="user",
                receiver="agent",
            )

        if output_value:
            await self._agent_memory.remember_interaction(
                message_content=str(output_value),
                sender="agent",
                receiver="user",
            )

    async def save_message(self, role: str, content: str) -> None:
        await self._agent_memory.remember_interaction(
            message_content=content,
            sender=role,
            receiver="user" if role == "assistant" else "agent",
        )

    def clear(self) -> None:
        self._agent_memory.clear()

    @property
    def agent_memory(self) -> AgentMemory:
        return self._agent_memory


# ─── LangChain-compatible Memory (when langchain-core available) ───────────────

if _LC_AVAILABLE:
    class MACSMemoryAdapter(LCBaseMemory):
        """LangChain Memory interface backed by MACS AgentMemory.

        This adapter bridges MACS's AgentMemory (which supports MemPalace
        distributed memory) to LangChain's BaseMemory interface, enabling:
        - LangChain chains with MACS memory backend
        - Multi-agent shared memory across LangChain agents
        - Persistent memory with MACS's memory management

        Attributes:
            memory_variables: List of variable names this memory exports.
            agent_memory: The underlying MACS AgentMemory instance.
        """

        def __init__(
            self,
            agent_memory: Optional[AgentMemory] = None,
            memory_key: str = "agent_history",
            return_messages: bool = False,
            output_key: Optional[str] = None,
            input_key: Optional[str] = None,
            **kwargs: Any,
        ):
            """Initialize the memory adapter.

            Args:
                agent_memory: MACS AgentMemory instance. If None, creates a new one.
                memory_key: Key to use for memory variable in chains.
                return_messages: If True, return messages instead of string.
                output_key: Key for output to save to memory.
                input_key: Key for input to save to memory.
            """
            super().__init__(
                return_messages=return_messages,
                output_key=output_key,
                input_key=input_key,
                **kwargs,
            )

            self._agent_memory = agent_memory or AgentMemory()
            self._memory_key = memory_key

        @property
        def memory_variables(self) -> List[str]:
            """List of variable names this memory exports.

            Returns:
                List containing the memory key (e.g., ["agent_history"]).
            """
            return [self._memory_key]

        def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Load memory variables for use in a chain.

            Args:
                inputs: Input dict from the chain (not used, but required by interface).

            Returns:
                Dict with memory key mapping to memory contents.
            """
            # Get short-term memory / conversation history
            history = self._agent_memory.get_short_term()

            if self.return_messages:
                # Return as LangChain messages
                messages = []
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
                    else:
                        messages.append(HumanMessage(content=content))
                return {self._memory_key: messages}
            else:
                # Return as formatted string
                if not history:
                    return {self._memory_key: ""}

                formatted = self._format_history(history)
                return {self._memory_key: formatted}

        def _format_history(self, history: List[Dict[str, Any]]) -> str:
            """Format history as a string for prompt injection.

            Args:
                history: List of message dicts.

            Returns:
                Formatted string representation.
            """
            lines = []
            for msg in history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"{role}: {content}")
            return "\n".join(lines) if lines else ""

        async def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
            """Save context from a chain execution to memory.

            Args:
                inputs: Input dict from chain.
                outputs: Output dict from chain.
            """
            # Extract input if input_key is set
            input_value = inputs.get(self.input_key, "") if self.input_key else ""

            # Extract output if output_key is set
            output_value = outputs.get(self.output_key, "") if self.output_key else ""

            # Save to agent memory
            if input_value:
                await self._agent_memory.remember_interaction(
                    message_content=str(input_value),
                    sender="user",
                    receiver="agent",
                )

            if output_value:
                await self._agent_memory.remember_interaction(
                    message_content=str(output_value),
                    sender="agent",
                    receiver="user",
                )

        async def save_message(self, role: str, content: str) -> None:
            """Save a single message to memory.

            Args:
                role: Message role ("user" or "assistant").
                content: Message content.
            """
            await self._agent_memory.remember_interaction(
                message_content=content,
                sender=role,
                receiver="user" if role == "assistant" else "agent",
            )

        def clear(self) -> None:
            """Clear memory contents."""
            self._agent_memory.clear()

        @property
        def agent_memory(self) -> AgentMemory:
            """Get the underlying MACS AgentMemory instance."""
            return self._agent_memory

else:
    MACSMemoryAdapter = _FallbackMemoryAdapter


class SharedMemoryAdapter(MACSMemoryAdapter):
    """Memory adapter backed by MACS SharedMemory (multi-agent shared memory).

    This variant uses MACS's SharedMemory for cross-agent memory sharing,
    enabling multiple LangChain agents to share context.

    Usage:
        from macs_pkg.core.agent import BaseAgent

        # Initialize shared memory globally
        await BaseAgent.init_shared_memory()

        # Create adapters for different agents (they'll share the same memory)
        memory1 = SharedMemoryAdapter()
        memory2 = SharedMemoryAdapter()
    """

    def __init__(
        self,
        namespace: str = "shared",
        memory_key: str = "shared_history",
        return_messages: bool = False,
        **kwargs: Any,
    ):
        """Initialize shared memory adapter.

        Args:
            namespace: Namespace for shared memory.
            memory_key: Key to use for memory variable.
            return_messages: If True, return messages instead of string.
            **kwargs: Additional options.
        """
        # Get or create shared memory
        shared_memory = SharedMemory.get_instance(namespace)

        super().__init__(
            agent_memory=shared_memory,
            memory_key=memory_key,
            return_messages=return_messages,
            **kwargs,
        )


# ─── Memory factories ──────────────────────────────────────────────────────────

def create_memory_adapter(
    memory_type: str = "agent",
    namespace: str = "default",
    **kwargs: Any,
) -> MACSMemoryAdapter:
    """Factory function to create memory adapters.

    Args:
        memory_type: Type of memory ("agent" or "shared").
        namespace: Namespace for shared memory.
        **kwargs: Additional options.

    Returns:
        Configured memory adapter.
    """
    if memory_type == "shared":
        return SharedMemoryAdapter(namespace=namespace, **kwargs)
    else:
        return MACSMemoryAdapter(**kwargs)


def create_memory_for_chain(
    agent_memory: Optional[AgentMemory] = None,
    memory_key: str = "chat_history",
) -> MACSMemoryAdapter:
    """Create a memory adapter configured for use with LangChain chains.

    Args:
        agent_memory: MACS AgentMemory instance.
        memory_key: Key for memory variable.

    Returns:
        Configured memory adapter ready for chain use.
    """
    return MACSMemoryAdapter(
        agent_memory=agent_memory,
        memory_key=memory_key,
        return_messages=False,
    )


if __name__ == "__main__":
    print("MACS Memory Adapter - LangChain Memory backed by MACS AgentMemory")
    print("Usage: MACSMemoryAdapter(agent_memory) or SharedMemoryAdapter(namespace='shared')")