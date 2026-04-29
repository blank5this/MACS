"""OpenAI-compatible LLM provider — works with MiniMax, DeepSeek, local models, etc.

Any provider that exposes an OpenAI-compatible /v1/chat/completions endpoint can be used.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class TimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class RateLimitError(LLMError):
    """Raised when API rate limit is hit."""
    pass


class OpenAICompatibleProvider(LLMProvider):
    """Generic provider for OpenAI-compatible APIs.

    Supports any provider that follows the OpenAI chat completions format:
      - MiniMax  (https://api.minimax.chat)
      - DeepSeek
      - Azure OpenAI
      - Local models (vLLM, Ollama, etc.)
      - Any OpenAI-compatible proxy

    Usage::

        # MiniMax
        provider = OpenAICompatibleProvider(
            api_key="your_minimax_key",
            base_url="https://api.minimax.chat/v1",
            model="MiniMax-Text-01",
        )

        # DeepSeek
        provider = OpenAICompatibleProvider(
            api_key="your_deepseek_key",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        timeout: float = 60.0,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        """
        Args:
            api_key: API key for the provider.
            base_url: Base URL of the OpenAI-compatible endpoint.
            model: Model identifier.
            timeout: Request timeout in seconds.
            extra_headers: Optional additional HTTP headers.
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._extra_headers = extra_headers or {}

    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: List[LLMMessage],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call an OpenAI-compatible endpoint with error handling.

        Args:
            messages: Conversation messages.
            system: System prompt.
            tools: Tool definitions for function calling.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.
            **kwargs: Additional provider-specific options.

        Returns:
            LLMResponse with content and usage.

        Raises:
            TimeoutError: If request times out.
            RateLimitError: If API rate limit is hit.
            LLMError: For other LLM-related errors.
        """
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package not found. Install it with: pip install openai"
            )

        # Build full URL
        url = f"{self._base_url}/chat/completions"

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }

        # Build message list
        api_messages: List[Dict[str, Any]] = []

        if system:
            api_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg.role in ("user", "assistant"):
                api_messages.append({"role": msg.role, "content": msg.content})

        # Build request payload
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        payload.update(kwargs)

        # Make request with error handling
        try:
            async with openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=openai._utils.DEFAULT_TIMEOUT_CONFIG.merge(timeout=timeout),
                default_headers=headers,
            ) as client:
                response = await client.chat.completions.create(**payload)
        except openai.APITimeoutError as e:
            raise TimeoutError(f"LLM request timed out after {timeout}s: {e}") from e
        except openai.RateLimitError as e:
            raise RateLimitError(f"Rate limit hit: {e}") from e
        except openai.BadRequestError as e:
            raise LLMError(f"Bad request: {e}") from e
        except openai.APIError as e:
            raise LLMError(f"LLM API error: {e}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error during LLM call: {e}") from e

        # Extract response
        choice = response.choices[0]
        message = choice.message

        # Collect tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": tc.function.arguments,
                })

        # Parse arguments if they're a string
        if tool_calls and isinstance(tool_calls[0]["input"], str):
            import json
            for tc in tool_calls:
                try:
                    tc["input"] = json.loads(tc["input"])
                except json.JSONDecodeError:
                    pass

        # Usage
        usage: Dict[str, int] = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens or 0,
                "output_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        return LLMResponse(
            content=message.content or "",
            model=response.model,
            usage=usage,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
        )


class MiniMaxProvider(OpenAICompatibleProvider):
    """MiniMax AI provider — shortcut for MiniMax-Text / MiniMax-VL models.

    MiniMax API docs: https://www.minimaxi.com/document
    Pricing: https://www.minimaxi.com/document
    """

    # MiniMax uses a specific base URL and group ID concept
    BASE_URL = "https://api.minimax.chat/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        model: str = "MiniMax-Text-01",
        **kwargs: Any,
    ):
        """
        Args:
            api_key: MiniMax API key (from console.minimax.com).
            group_id: MiniMax Group ID (required for some endpoints).
            model: MiniMax model — MiniMax-Text-01, abab6.5s-chat, etc.
            **kwargs: Passed to OpenAICompatibleProvider.
        """
        key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        group_id = group_id or os.environ.get("MINIMAX_GROUP_ID", "")

        headers = kwargs.pop("extra_headers", {})
        if group_id:
            headers["GroupId"] = group_id

        super().__init__(
            api_key=key,
            base_url=self.BASE_URL,
            model=model,
            extra_headers=headers,
            **kwargs,
        )


class MiniMaxAgentMixin:
    """Mixin that injects a MiniMaxProvider into an agent.

    Usage::

        class MyPlannerAgent(MiniMaxAgentMixin, PlannerAgent):
            pass

        provider = MiniMaxProvider(api_key="...", model="MiniMax-Text-01")
        planner = MyPlannerAgent("planner", provider=provider)
    """

    def __init__(self, *args: Any, provider: Optional[LLMProvider] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._provider: Optional[LLMProvider] = provider
        self._conversation: List[LLMMessage] = []

    async def _llm_chat(
        self,
        user_content: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        if self._provider is None:
            raise RuntimeError(
                f"No LLM provider configured for agent '{self.name}'. "
                "Pass provider=MiniMaxProvider() when constructing the agent."
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
        self._conversation.clear()
