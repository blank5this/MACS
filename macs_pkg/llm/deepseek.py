"""DeepSeek 大模型 LLM Provider.

支持 DeepSeek 系列模型，API 完全兼容 OpenAI 格式。
文档: https://platform.deepseek.com/

使用方式::

    from macs_pkg.llm import DeepSeekProvider

    provider = DeepSeekProvider(
        api_key="your_deepseek_key",
        model="deepseek-chat",
    )
    
    # 使用 v3 模型
    provider = DeepSeekProvider(
        api_key="your_key",
        model="deepseek-v3",
    )
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse
from .agents import LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent


class DeepSeekProvider(LLMProvider):
    """DeepSeek 大模型 Provider.

    支持模型:
    - deepseek-chat (DeepSeek-V2.5)
    - deepseek-coder (代码专用)
    - deepseek-v3 (最新版本)

    使用方式::

        from macs_pkg.llm import DeepSeekProvider

        # 通用对话
        provider = DeepSeekProvider(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            model="deepseek-chat",
        )

        # 代码专用
        provider = DeepSeekProvider(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            model="deepseek-coder",
        )
    """

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        timeout: float = 60.0,
    ):
        """
        Args:
            api_key: DeepSeek API Key. Defaults to DEEPSEEK_API_KEY env var.
            model: DeepSeek 模型名称.
                - deepseek-chat: 通用对话 (DeepSeek-V2.5)
                - deepseek-v3: 最新版本
                - deepseek-coder: 代码专用
            timeout: 请求超时时间(秒).
        """
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
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
        """调用 DeepSeek API.

        Args:
            messages: 对话历史.
            system: 系统提示词.
            tools: 工具定义 (function calling).
            max_tokens: 最大生成 token 数.
            temperature: 采样温度.

        Returns:
            LLMResponse 包含内容和 usage.
        """
        import json
        import urllib.request
        import urllib.error

        # 构建消息
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend([
            {"role": m.role, "content": m.content}
            for m in messages
        ])

        # 构建请求 payload
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "parameters": t["function"].get("parameters", {}),
                    }
                }
                for t in tools
                if "function" in t
            ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            req = urllib.request.Request(
                f"{self.BASE_URL}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # 解析响应
            if "error" in result:
                raise Exception(f"DeepSeek API Error: {result['error']}")

            choices = result.get("choices", [])
            if not choices:
                raise Exception("No choices in response")

            assistant_message = choices[0].get("message", {})
            content = assistant_message.get("content", "")

            # 检查 tool_calls
            tool_calls = assistant_message.get("tool_calls", [])

            return LLMResponse(
                content=content,
                tool_calls=[
                    {
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", ""),
                        }
                    }
                    for tc in tool_calls
                ] if tool_calls else None,
                raw=result,
                usage={
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                },
            )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e.reason}")


class DeepSeekAgentMixin:
    """DeepSeek Agent Mixin，提供便捷的 Agent 创建方法."""

    def as_planner(self) -> "DeepSeekPlannerAgent":
        """创建 Planner Agent，使用 DeepSeek 模型."""
        from .agents import LLMPlannerAgent
        return LLMPlannerAgent(provider=DeepSeekProvider())

    def as_executor(self) -> "DeepSeekExecutorAgent":
        """创建 Executor Agent，使用 DeepSeek 模型."""
        from .agents import LLMExecutorAgent
        return LLMExecutorAgent(provider=DeepSeekProvider())

    def as_reviewer(self) -> "DeepSeekReviewerAgent":
        """创建 Reviewer Agent，使用 DeepSeek 模型."""
        from .agents import LLMReviewerAgent
        return LLMReviewerAgent(provider=DeepSeekProvider())


class DeepSeekPlannerAgent(LLMPlannerAgent):
    """使用 DeepSeek 的 Planner Agent."""
    def __init__(self, **kwargs):
        super().__init__(provider=DeepSeekProvider(), **kwargs)


class DeepSeekExecutorAgent(LLMExecutorAgent):
    """使用 DeepSeek 的 Executor Agent."""
    def __init__(self, **kwargs):
        super().__init__(provider=DeepSeekProvider(), **kwargs)


class DeepSeekReviewerAgent(LLMReviewerAgent):
    """使用 DeepSeek 的 Reviewer Agent."""
    def __init__(self, **kwargs):
        super().__init__(provider=DeepSeekProvider(), **kwargs)
