"""Tencent Hunyuan 混元大模型 LLM Provider.

使用腾讯云混元 API，支持混元系列模型。
文档: https://cloud.tencent.com/document/product/1729-97741

使用方式::

    from macs_pkg.llm import HunyuanProvider

    # 使用腾讯云 SecretId/SecretKey
    provider = HunyuanProvider(
        secret_id="your_secret_id",
        secret_key="your_secret_key",
        model="hunyuan-turb",
    )
    
    # 或使用混元 API Key (新版)
    provider = HunyuanProvider(
        api_key="your_hunyuan_api_key",
        model="hunyuan-turb",
    )
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Dict, List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse
from .agents import LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent


class HunyuanProvider(LLMProvider):
    """腾讯混元大模型 Provider.

    支持模型:
    - hunyuan-turb (快速响应)
    - hunyuan-plus (更强理解)
    - hunyuan-pro (最新增强版)
    - hunyuan-large (超大参数)

    使用腾讯云 TCCLI 认证或混元 API Key。

    使用方式::

        from macs_pkg.llm import HunyuanProvider

        # 方式1: 腾讯云 SecretId/SecretKey (推荐企业用户)
        provider = HunyuanProvider(
            secret_id=os.environ["TENCENT_SECRET_ID"],
            secret_key=os.environ["TENCENT_SECRET_KEY"],
        )

        # 方式2: 混元 API Key (新版简化认证)
        provider = HunyuanProvider(
            api_key=os.environ["HUNYUAN_API_KEY"],
        )
    """

    BASE_URL = "https://hunyuan.cloud.tencent.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        model: str = "hunyuan-turb",
        timeout: float = 60.0,
    ):
        """
        Args:
            api_key: 混元 API Key (新版). Defaults to HUNYUAN_API_KEY env var.
            secret_id: 腾讯云 SecretId. Defaults to TENCENT_SECRET_ID env var.
            secret_key: 腾讯云 SecretKey. Defaults to TENCENT_SECRET_KEY env var.
            model: 混元模型名称.
            timeout: 请求超时时间(秒).
        """
        self._api_key = api_key or os.environ.get("HUNYUAN_API_KEY", "")
        self._secret_id = secret_id or os.environ.get("TENCENT_SECRET_ID", "")
        self._secret_key = secret_key or os.environ.get("TENCENT_SECRET_KEY", "")
        self._model = model
        self._timeout = timeout

    def model_name(self) -> str:
        return self._model

    def _generate_signature(
        self,
        secret_id: str,
        secret_key: str,
        timestamp: int,
    ) -> str:
        """生成 TC3-HMAC-SHA256 签名.

        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            timestamp: 当前时间戳

        Returns:
            签名字符串
        """
        # 拼接字符串
        http_request_method = "POST"
        canonical_uri = "/invoke/hunyuan/v1/chat/completions"
        canonical_query_string = ""
        canonical_headers = f"content-type:application/json\nhost:hunyuan.cloud.tencent.com\nx-tc-timestamp:{timestamp}\n"
        signed_headers = "content-type;host;x-tc-timestamp"
        hashed_request_payload = ""

        # 计算 payload hash (空 payload 的 SHA256)
        import hashlib
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )

        # 签名字符串
        algorithm = "TC3-HMAC-SHA256"
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        service = "hunyuan"
        credential_scope = f"{date}/{service}/tc3_request"

        def _sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        # Step 1: signing_key
        k_date = _sign(("TC3" + secret_key).encode("utf-8"), date)
        k_service = _sign(k_date, service)
        k_signing = _sign(k_service, "tc3_request")

        # Step 2: string_to_sign
        payload_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
        canonical_request_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()

        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{canonical_request_hash}"
        )

        # Step 3: signature
        signature = hmac.new(
            k_signing,
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def complete(
        self,
        messages: List[LLMMessage],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """调用混元 API.

        Args:
            messages: 对话历史.
            system: 系统提示词.
            tools: 工具定义 (function calling).
            max_tokens: 最大生成 token 数.
            temperature: 采样温度.
            stream: 是否流式返回.

        Returns:
            LLMResponse 包含内容和 usage.
        """
        import json

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
            "stream": stream,
            **kwargs,
        }

        if tools:
            # 转换为混元工具格式
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
        }

        # 根据认证方式选择请求头
        if self._api_key:
            # 使用新版 API Key 认证
            headers["Authorization"] = f"Bearer {self._api_key}"
            url = f"{self.BASE_URL}/invoke/hunyuan/v1/chat/completions"
        elif self._secret_id and self._secret_key:
            # 使用腾讯云 SecretId/SecretKey 认证
            timestamp = int(time.time())
            signature = self._generate_signature(
                self._secret_id,
                self._secret_key,
                timestamp
            )
            headers.update({
                "X-TC-Action": "ChatCompletions",
                "X-TC-Version": "2023-09-01",
                "X-TC-Timestamp": str(timestamp),
                "X-TC-Region": "ap-guangzhou",
                "X-TC-Key": self._secret_id,
                "X-TC-Signature": signature,
            })
            url = f"{self.BASE_URL}/invoke/hunyuan/v1/chat/completions"
        else:
            raise ValueError(
                "需要提供 api_key 或 secret_id/secret_key。"
                "设置 HUNYUAN_API_KEY 或 TENCENT_SECRET_ID/TENCENT_SECRET_KEY 环境变量。"
            )

        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                response_body = resp.read().decode("utf-8")

            if stream:
                # 流式响应暂不支持简化解析
                return LLMResponse(
                    content=response_body,
                    raw=response_body,
                )

            result = json.loads(response_body)

            # 解析混元响应
            if "error" in result:
                raise Exception(f"Hunyuan API Error: {result['error']}")

            # 提取 assistant 消息
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


class HunyuanAgentMixin:
    """混元 Agent Mixin，提供便捷的 Agent 创建方法."""

    def as_planner(self) -> "HunyuanPlannerAgent":
        """创建Planner Agent，使用混元模型."""
        from .agents import LLMPlannerAgent
        return LLMPlannerAgent(provider=HunyuanProvider())

    def as_executor(self) -> "HunyuanExecutorAgent":
        """创建Executor Agent，使用混元模型."""
        from .agents import LLMExecutorAgent
        return LLMExecutorAgent(provider=HunyuanProvider())

    def as_reviewer(self) -> "HunyuanReviewerAgent":
        """创建Reviewer Agent，使用混元模型."""
        from .agents import LLMReviewerAgent
        return LLMReviewerAgent(provider=HunyuanProvider())


class HunyuanPlannerAgent(LLMPlannerAgent):
    """使用混元的Planner Agent."""
    def __init__(self, **kwargs):
        super().__init__(provider=HunyuanProvider(), **kwargs)


class HunyuanExecutorAgent(LLMExecutorAgent):
    """使用混元的Executor Agent."""
    def __init__(self, **kwargs):
        super().__init__(provider=HunyuanProvider(), **kwargs)


class HunyuanReviewerAgent(LLMReviewerAgent):
    """使用混元的Reviewer Agent."""
    def __init__(self, **kwargs):
        super().__init__(provider=HunyuanProvider(), **kwargs)