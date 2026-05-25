"""LLM Adapter - Bridge MACS LLMProvider to LangChain ChatModel.

This module provides adapters to use MACS LLM providers (MiniMax, DeepSeek, etc.)
as LangChain ChatModel instances, enabling seamless integration with LangChain LCEL.

Usage:
    from macs_pkg.langchain.llm_adapter import MACSChatModelWrapper
    from macs_pkg.llm import MiniMaxProvider

    # From MACS provider
    provider = MiniMaxProvider(api_key="...", model="MiniMax-Text-01")
    chat_model = MACSChatModelWrapper.from_provider(provider)

    # Use with LangChain
    chain = prompt | chat_model | output_parser
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import asyncio

# LangChain imports - wrapped to handle torch DLL issues on Windows
_LC_ERROR: Optional[str] = None
_LC_AVAILABLE = False

try:
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.language_models import BaseChatModel
    from langchain_core.callbacks import CallbackManagerForLLMRun
    _LC_AVAILABLE = True
except (ImportError, OSError) as e:
    BaseMessage = None  # type: ignore
    HumanMessage = None  # type: ignore
    AIMessage = None  # type: ignore
    SystemMessage = None  # type: ignore
    ChatGeneration = None  # type: ignore
    ChatResult = None  # type: ignore
    BaseChatModel = None  # type: ignore
    CallbackManagerForLLMRun = None  # type: ignore
    _LC_ERROR = str(e)

if not _LC_AVAILABLE:
    import warnings
    warnings.warn(
        f"langchain-core unavailable ({_LC_ERROR}). "
        "LLM adapter will work in fallback mode without LangChain integration.",
        RuntimeWarning,
    )

if TYPE_CHECKING:
    from openai import AsyncOpenAI

from macs_pkg.llm.base import LLMMessage, LLMProvider, LLMResponse
from macs_pkg.llm.openai_compatible import OpenAICompatibleProvider, MiniMaxProvider

# Default timeout settings
DEFAULT_TIMEOUT = 60.0
DEFAULT_CONNECT_TIMEOUT = 10.0


# ─── Fallback implementations (when langchain-core unavailable) ────────────────

class _FallbackChatModelWrapper:
    """Fallback ChatModel wrapper when langchain-core is unavailable.

    This provides a minimal interface that can be upgraded to real LangChain
    ChatModel once langchain-core is available.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ):
        self._provider = provider
        self._timeout = timeout
        self._default_max_tokens = max_tokens
        self._default_temperature = temperature
        self._client: Optional[Any] = None

    @property
    def provider(self) -> Optional[LLMProvider]:
        return self._provider

    @property
    def model_name(self) -> str:
        if self._provider is not None:
            return self._provider.model_name()
        return "unknown"

    @property
    def _llm_type(self) -> str:
        return "macs_wrapper_fallback"

    async def _agenerate(
        self,
        messages: List[Any],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Fallback async generation."""
        if self._provider is None:
            raise ValueError("No LLM provider configured")

        macs_messages = self._convert_messages(messages)
        response = await self._provider.complete(
            messages=macs_messages,
            max_tokens=kwargs.pop("max_tokens", self._default_max_tokens),
            temperature=kwargs.pop("temperature", self._default_temperature),
            **kwargs,
        )
        return self._convert_to_dict(response)

    def _convert_messages(self, messages: List[Any]) -> List[LLMMessage]:
        """Convert messages to MACS format."""
        result = []
        for msg in messages:
            content = getattr(msg, 'content', str(msg))
            role = getattr(msg, 'role', 'user')
            result.append(LLMMessage(role=role, content=content))
        return result

    def _convert_to_dict(self, response: LLMResponse) -> Dict[str, Any]:
        """Convert to dict format."""
        return {
            "content": response.content,
            "model": response.model,
            "usage": response.usage,
        }

    def bind_tools(self, tools: List[Dict[str, Any]], **kwargs: Any) -> "_FallbackChatModelWrapper":
        """Bind tools (no-op in fallback)."""
        return self


# ─── LangChain-compatible ChatModel (when langchain-core available) ───────────

if _LC_AVAILABLE:
    class MACSChatModelWrapper(BaseChatModel):
        """Wrap a MACS LLMProvider as a LangChain ChatModel.

        This allows using MACS providers (MiniMax, DeepSeek, OpenAI-compatible)
        with LangChain's LCEL and Agent frameworks.
        """

        @classmethod
        def from_provider(
            cls,
            provider: LLMProvider,
            **kwargs: Any,
        ) -> "MACSChatModelWrapper":
            """Create a ChatModel wrapper from a MACS LLMProvider."""
            wrapper = cls(provider=provider, **kwargs)
            return wrapper

        @classmethod
        def from_config(
            cls,
            api_key: Optional[str] = None,
            base_url: str = "https://api.openai.com/v1",
            model: str = "gpt-4",
            provider_type: str = "openai",
            **kwargs: Any,
        ) -> "MACSChatModelWrapper":
            """Create a ChatModel from configuration."""
            if provider_type == "minimax":
                provider = MiniMaxProvider(api_key=api_key, model=model, **kwargs)
            elif provider_type == "deepseek":
                provider = OpenAICompatibleProvider(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1",
                    model=model,
                    **kwargs,
                )
            else:
                provider = OpenAICompatibleProvider(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    **kwargs,
                )
            return cls.from_provider(provider)

        def __init__(
            self,
            provider: Optional[LLMProvider] = None,
            timeout: float = DEFAULT_TIMEOUT,
            max_tokens: int = 4096,
            temperature: float = 0.7,
            **kwargs: Any,
        ):
            super().__init__(**kwargs)
            self._provider = provider
            self._timeout = timeout
            self._default_max_tokens = max_tokens
            self._default_temperature = temperature
            self._client: Optional["AsyncOpenAI"] = None

        @property
        def provider(self) -> Optional[LLMProvider]:
            return self._provider

        @property
        def model_name(self) -> str:
            if self._provider is not None:
                return self._provider.model_name()
            return "unknown"

        def _get_client(self) -> "AsyncOpenAI":
            if self._client is not None:
                return self._client
            if self._provider is None or not isinstance(self._provider, OpenAICompatibleProvider):
                raise ValueError("Provider must be OpenAICompatibleProvider")
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=getattr(self._provider, "_api_key", ""),
                base_url=getattr(self._provider, "_base_url", "https://api.openai.com/v1"),
                timeout=openai.Timeout(
                    connect=DEFAULT_CONNECT_TIMEOUT,
                    read=self._timeout,
                    write=self._timeout,
                    pool=self._timeout,
                ),
            )
            return self._client

        def _convert_messages(self, messages: List[BaseMessage]) -> List[LLMMessage]:
            result = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    result.append(LLMMessage(role="user", content=msg.content))
                elif isinstance(msg, AIMessage):
                    result.append(LLMMessage(role="assistant", content=msg.content))
                elif isinstance(msg, SystemMessage):
                    result.append(LLMMessage(role="system", content=msg.content))
                else:
                    result.append(LLMMessage(role="user", content=str(msg.content)))
            return result

        def _convert_to_lc_result(self, response: LLMResponse) -> ChatResult:
            from langchain_core.outputs import Generation
            generation = Generation(
                text=response.content,
                message=AIMessage(content=response.content),
                generation_info=dict(
                    model=response.model,
                    finish_reason=response.stop_reason,
                    usage=response.usage,
                ),
            )
            return ChatResult(generations=[generation])

        @property
        def _llm_type(self) -> str:
            return "macs_wrapper"

        def _generate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
        ) -> ChatResult:
            macs_messages = self._convert_messages(messages)
            system_prompt = None
            non_system_messages = []
            for msg in macs_messages:
                if msg.role == "system":
                    system_prompt = msg.content
                else:
                    non_system_messages.append(msg)

            max_tokens = kwargs.pop("max_tokens", self._default_max_tokens)
            temperature = kwargs.pop("temperature", self._default_temperature)

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            future = loop.create_task(
                self._provider.complete(
                    messages=non_system_messages,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )
            )

            try:
                timeout = kwargs.pop("timeout", self._timeout)
                response = loop.run_until_complete(
                    asyncio.wait_for(future, timeout=timeout)
                )
            except asyncio.TimeoutError:
                from macs_pkg.llm.openai_compatible import TimeoutError
                raise TimeoutError(f"LLM request timed out after {timeout}s")
            except Exception as e:
                from macs_pkg.llm.openai_compatible import LLMError
                raise LLMError(f"LLM generation failed: {e}")

            return self._convert_to_lc_result(response)

        async def _agenerate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
        ) -> ChatResult:
            if self._provider is None:
                raise ValueError("No LLM provider configured")

            macs_messages = self._convert_messages(messages)
            system_prompt = None
            non_system_messages = []
            for msg in macs_messages:
                if msg.role == "system":
                    system_prompt = msg.content
                else:
                    non_system_messages.append(msg)

            max_tokens = kwargs.pop("max_tokens", self._default_max_tokens)
            temperature = kwargs.pop("temperature", self._default_temperature)

            try:
                response = await self._provider.complete(
                    messages=non_system_messages,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )
            except asyncio.TimeoutError:
                from macs_pkg.llm.openai_compatible import TimeoutError
                raise TimeoutError("LLM request timed out")
            except Exception as e:
                from macs_pkg.llm.openai_compatible import LLMError
                raise LLMError(f"LLM generation failed: {e}")

            return self._convert_to_lc_result(response)

        def bind_tools(self, tools: List[Dict[str, Any]], **kwargs: Any) -> "MACSChatModelWrapper":
            if not hasattr(self, "_bound_tools"):
                self._bound_tools = []
            self._bound_tools = tools
            return self

else:
    MACSChatModelWrapper = _FallbackChatModelWrapper


class MiniMaxChatModel(MACSChatModelWrapper):
    """Convenience class specifically for MiniMax provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "MiniMax-Text-01",
        group_id: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ):
        provider = MiniMaxProvider(
            api_key=api_key,
            model=model,
            group_id=group_id,
            timeout=timeout,
        )
        super().__init__(
            provider=provider,
            timeout=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    @property
    def _llm_type(self) -> str:
        return "minimax"


class DeepSeekChatModel(MACSChatModelWrapper):
    """Convenience class specifically for DeepSeek provider."""

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ):
        provider = OpenAICompatibleProvider(
            api_key=api_key,
            base_url=self.BASE_URL,
            model=model,
            timeout=timeout,
        )
        super().__init__(
            provider=provider,
            timeout=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    @property
    def _llm_type(self) -> str:
        return "deepseek"


def create_chat_model(
    provider_type: str = "minimax",
    api_key: Optional[str] = None,
    model: str = "MiniMax-Text-01",
    **kwargs: Any,
) -> MACSChatModelWrapper:
    """Factory function to create a ChatModel from provider type."""
    if provider_type == "minimax":
        return MiniMaxChatModel(api_key=api_key, model=model, **kwargs)
    elif provider_type == "deepseek":
        return DeepSeekChatModel(api_key=api_key, model=model, **kwargs)
    else:
        return MACSChatModelWrapper.from_config(
            api_key=api_key,
            model=model,
            provider_type=provider_type,
            **kwargs,
        )


if __name__ == "__main__":
    print("MACS LLM Adapter - LangChain ChatModel wrapper for MACS providers")
    print("Usage: MACSChatModelWrapper.from_provider(your_llm_provider)")