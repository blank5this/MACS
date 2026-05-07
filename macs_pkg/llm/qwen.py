"""Alibaba Qwen 通义千问 LLM Provider.

使用阿里云 DashScope API，支持 Qwen-Turbo/Qwen-Max 等模型。
文档: https://help.aliyun.com/zh/dashscope/
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse


class QwenProvider(LLMProvider):
    """阿里云通义千问 Provider.

    支持模型:
    - qwen-turbo (快速，便宜)
    - qwen-plus (平衡)
    - qwen-max (最强)
    - qwen-max-longcontext (长上下文)

    使用方式::

        from macs_pkg.llm import QwenProvider

        provider = QwenProvider(
            api_key="your_dashscope_key",
            model="qwen-plus",
        )
        response = await provider.complete([
            LLMMessage(role="user", content="Hello!")
        ])
    """

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-plus",
        timeout: float = 60.0,
    ):
        """
        Args:
            api_key: DashScope API Key. Defaults to DASHSCOPE_API_KEY env var.
            model: Qwen model name.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        self._model = model
        self._timeout = timeout

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
        """Call Qwen API.

        Args:
            messages: Conversation history.
            system: System prompt.
            tools: Tool definitions for function calling.
            max_tokens: Max tokens to generate.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content and usage.
        """
        import urllib.request
        import urllib.error
        import json

        # Build messages with system prompt
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        # Build request
        payload: Dict[str, Any] = {
            "model": self._model,
            "input": {"messages": all_messages},
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs,
            },
        }

        if tools:
            payload["model"] = self._model  # Qwen supports tools in compatible mode
            payload["extra_body"] = {"tools": tools}

        try:
            req = urllib.request.Request(
                f"{self.BASE_URL}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # Parse response
            if "output" in data and "choices" in data:
                # DashScope compatible mode response
                choice = data["choices"][0]
                content = choice.get("message", {}).get("content", "")
                finish_reason = choice.get("finish_reason", "")
                usage = data.get("usage", {})
                tool_calls = []
                
                # Check for tool calls
                if choice.get("message", {}).get("tool_calls"):
                    tool_calls = choice["message"]["tool_calls"]
                
                return LLMResponse(
                    content=content,
                    model=self._model,
                    usage={
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                    },
                    tool_calls=tool_calls,
                    stop_reason=finish_reason,
                )
            else:
                # Fallback parsing
                content = data.get("output", {}).get("text", "")
                return LLMResponse(content=content, model=self._model)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Qwen API error {e.code}: {error_body}") from e
        except Exception as e:
            raise RuntimeError(f"Qwen request failed: {e}") from e


class QwenAgentMixin:
    """Mixin for Qwen-powered agents."""

    @classmethod
    def create_with_qwen(
        cls,
        name: str,
        api_key: Optional[str] = None,
        model: str = "qwen-plus",
        **kwargs,
    ):
        """Factory method to create agent with Qwen provider."""
        provider = QwenProvider(api_key=api_key, model=model)
        return cls(name=name, provider=provider, **kwargs)
