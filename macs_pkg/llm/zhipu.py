"""Zhipu AI (智谱 GLM) LLM Provider.

使用智谱 AI API，支持 GLM-4/GLM-3 等模型。
文档: https://open.bigmodel.cn/dev/api
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse


class ZhipuProvider(LLMProvider):
    """智谱 GLM Provider.

    支持模型:
    - glm-4 (最强)
    - glm-4-flash (快速)
    - glm-3-turbo (便宜)

    使用方式::

        from macs_pkg.llm import ZhipuProvider

        provider = ZhipuProvider(
            api_key="your_zhipu_key",
            model="glm-4",
        )
        response = await provider.complete([
            LLMMessage(role="user", content="Hello!")
        ])
    """

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "glm-4",
        timeout: float = 60.0,
    ):
        """
        Args:
            api_key: Zhipu API Key. Defaults to ZHIPU_API_KEY env var.
            model: GLM model name.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key or os.environ.get("ZHIPU_API_KEY", "")
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
        """Call Zhipu API."""
        import urllib.request
        import urllib.error
        import json

        # Build messages
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        # Build request payload
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        if tools:
            payload["tools"] = tools

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
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "")
            usage = data.get("usage", {})
            tool_calls = choice.get("message", {}).get("tool_calls", [])

            return LLMResponse(
                content=content,
                model=self._model,
                usage={
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                },
                tool_calls=tool_calls,
                stop_reason=finish_reason,
            )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Zhipu API error {e.code}: {error_body}") from e
        except Exception as e:
            raise RuntimeError(f"Zhipu request failed: {e}") from e
