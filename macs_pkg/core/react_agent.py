"""ReAct (Reasoning + Acting) agent base class.

Enforces the think → act lifecycle:
- `think()` MUST be called before `act()` — RuntimeError otherwise.
- The combined `run()` method executes the full think+act cycle.
- Subclasses implement `_think_impl()` (planning) and `_act_impl()` (execution).
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from .agent import AgentState, BaseAgent, Message


class ReactAgent(BaseAgent):
    """ReAct agent with enforced think→act lifecycle.

    Usage::

        class MyAgent(ReactAgent):
            async def _think_impl(self, message: Message) -> Message:
                # LLM planning happens here
                ...

            async def _act_impl(self, response: Message) -> List[Message]:
                # Tool calls / LLM generation happen here
                ...

        agent = MyAgent(name="assistant")
        # Correct usage — via run():
        result = await agent.run(input_message)
        # Or manually (enforced order):
        response = await agent.think(message)
        actions = await agent.act(response)  # RuntimeError if think() not called first

    The think/act split mirrors the ReAct pattern:
      - think(): prepare a plan / decide what to do next
      - act(): execute tools, generate output, produce messages

    Enforcement: `_think_called` flag. If `act()` is invoked before
    `think()`, raises RuntimeError("act() called before think() — "
    "you must call think() first, or use run()").
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._think_called: bool = False

    # ── Public think+act API ────────────────────────────────────────────────

    async def think(self, message: Message) -> Message:
        """Think phase: plan what to do.

        Raises:
            RuntimeError: if called while already in THINKING state.

        Returns:
            Response message from the think phase.
        """
        if self.state == AgentState.THINKING:
            raise RuntimeError(
                f"[{self.name}] think() called while already in THINKING state — "
                "wait for the current think+act cycle to complete"
            )
        self.state = AgentState.THINKING
        self._think_called = False

        try:
            response = await self._think_impl(message)
            self._think_called = True
            return response
        finally:
            self.state = AgentState.IDLE

    async def act(self, response: Message) -> List[Message]:
        """Act phase: execute tools / generate output.

        Raises:
            RuntimeError: if think() was not called first,
                         or if act() is called while already in ACTING state.

        Returns:
            List of outgoing messages.
        """
        if not self._think_called:
            raise RuntimeError(
                f"[{self.name}] act() called before think() — "
                "you MUST call think() first, or use run() for the combined cycle"
            )
        if self.state == AgentState.ACTING:
            raise RuntimeError(
                f"[{self.name}] act() called while already in ACTING state — "
                "wait for the current cycle to complete"
            )
        self.state = AgentState.ACTING

        try:
            return await self._act_impl(response)
        finally:
            self.state = AgentState.IDLE
            self._think_called = False  # Reset for next cycle

    async def run(self, message: Message) -> List[Message]:
        """Convenience: run the full think + act cycle in one call.

        This is the recommended entry point for simple use-cases.
        Equivalent to::

            response = await agent.think(message)
            return await agent.act(response)

        Args:
            message: Incoming message.

        Returns:
            List of outgoing messages from the act phase.
        """
        response = await self.think(message)
        return await self.act(response)

    # ── Abstract implementation hooks ──────────────────────────────────────────

    @abstractmethod
    async def _think_impl(self, message: Message) -> Message:
        """Actual think implementation (LLM planning, state analysis, etc.).

        Called by think() after state management.
        Return the response message from this phase.
        """

    @abstractmethod
    async def _act_impl(self, response: Message) -> List[Message]:
        """Actual act implementation (tool calls, LLM generation, etc.).

        Called by act() after think() has been confirmed.
        Return the list of outgoing messages.
        """
