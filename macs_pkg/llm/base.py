"""LLM provider abstraction for MACS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMMessage:
    """A single turn in an LLM conversation."""
    role: str   # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)   # input_tokens, output_tokens
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    stop_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Concrete implementations:
      - ClaudeProvider  (Anthropic)
      - OpenAIProvider  (OpenAI-compatible)
    """

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a conversation to the LLM and return its response.

        Args:
            messages: Conversation history (user + assistant turns).
            system: Optional system prompt (cached automatically when supported).
            tools: Optional list of tool schemas for function-calling.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            **kwargs: Provider-specific options.

        Returns:
            LLMResponse with content and usage metadata.
        """

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier used by this provider."""
