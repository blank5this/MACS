"""Claude (Anthropic) LLM provider with prompt caching support."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse

# Default model — Claude Sonnet 4.6 is latest at time of writing
DEFAULT_MODEL = "claude-sonnet-4-6"


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider with prompt caching.

    Uses the Anthropic SDK. Automatically caches the system prompt to reduce
    token costs on repeated calls (cache_control: ephemeral).

    Usage::

        provider = ClaudeProvider()                    # reads ANTHROPIC_API_KEY
        response = await provider.complete(
            messages=[LLMMessage(role="user", content="Hello!")],
            system="You are a helpful assistant.",
        )
        print(response.content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        enable_caching: bool = True,
    ):
        """
        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Claude model ID.
            enable_caching: Whether to send cache_control on system prompts.
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not found. Install it with: pip install anthropic"
            )

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=key)
        self._model = model
        self._enable_caching = enable_caching

    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: List[LLMMessage],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call the Claude API with optional prompt caching and tool use.

        The system prompt is cached (ephemeral) when enable_caching=True, which
        reduces costs significantly on repeated agent calls with the same system prompt.
        """
        # Build message list for Anthropic SDK
        api_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role in ("user", "assistant")
        ]

        # Build kwargs
        call_kwargs: Dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
        }

        # System prompt with optional caching
        if system:
            if self._enable_caching:
                call_kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                call_kwargs["system"] = system

        # Tools
        if tools:
            call_kwargs["tools"] = tools

        call_kwargs.update(kwargs)

        response = await self._client.messages.create(**call_kwargs)

        # Extract text content and any tool calls
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        usage = {}
        if hasattr(response, "usage"):
            u = response.usage
            usage = {
                "input_tokens": getattr(u, "input_tokens", 0),
                "output_tokens": getattr(u, "output_tokens", 0),
                "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0),
            }

        return LLMResponse(
            content="\n".join(text_parts),
            model=response.model,
            usage=usage,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
        )


class ClaudeAgentMixin:
    """Mixin that injects a ClaudeProvider into a BaseAgent subclass.

    Provides a ``_llm_chat`` helper that manages the agent's conversation history
    and calls the Claude API.

    Usage::

        class MyPlannerAgent(ClaudeAgentMixin, PlannerAgent):
            pass

        agent = MyPlannerAgent("planner", provider=ClaudeProvider())
    """

    def __init__(self, *args: Any, provider: Optional["LLMProvider"] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._provider: Optional[LLMProvider] = provider
        self._conversation: List[LLMMessage] = []

    async def _llm_chat(
        self,
        user_content: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a user message to the LLM and return the response.

        Appends both the user turn and the assistant reply to internal history.

        Args:
            user_content: The user message text.
            tools: Optional tool schemas for this call.
            max_tokens: Max tokens for this call.

        Returns:
            LLMResponse from the provider.
        """
        if self._provider is None:
            raise RuntimeError(
                f"No LLM provider configured for agent '{self.name}'. "
                "Pass provider=ClaudeProvider() when constructing the agent."
            )

        self._conversation.append(LLMMessage(role="user", content=user_content))

        response = await self._provider.complete(
            messages=self._conversation,
            system=self.system_prompt,
            tools=tools,
            max_tokens=max_tokens,
        )

        self._conversation.append(LLMMessage(role="assistant", content=response.content))
        return response

    def clear_conversation(self) -> None:
        """Clear the LLM conversation history."""
        self._conversation.clear()
