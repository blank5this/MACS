"""MACS LLM integration — provider abstraction and LLM-powered agents."""

from .base import LLMMessage, LLMProvider, LLMResponse
from .claude import ClaudeProvider, ClaudeAgentMixin
from .openai_compatible import (
    OpenAICompatibleProvider,
    MiniMaxProvider,
    MiniMaxAgentMixin,
)
from .qwen import QwenProvider, QwenAgentMixin
from .zhipu import ZhipuProvider
from .deepseek import (
    DeepSeekProvider,
    DeepSeekAgentMixin,
    DeepSeekPlannerAgent,
    DeepSeekExecutorAgent,
    DeepSeekReviewerAgent,
)
from .hunyuan import (
    HunyuanProvider,
    HunyuanAgentMixin,
    HunyuanPlannerAgent,
    HunyuanExecutorAgent,
    HunyuanReviewerAgent,
)
from .agents import (
    LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent,
    MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent,
)

__all__ = [
    # Base classes
    "LLMMessage", "LLMProvider", "LLMResponse",
    # Providers
    "ClaudeProvider", "ClaudeAgentMixin",
    "OpenAICompatibleProvider", "MiniMaxProvider", "MiniMaxAgentMixin",
    "QwenProvider", "QwenAgentMixin",
    "ZhipuProvider",
    "DeepSeekProvider", "DeepSeekAgentMixin",
    "DeepSeekPlannerAgent", "DeepSeekExecutorAgent", "DeepSeekReviewerAgent",
    "HunyuanProvider", "HunyuanAgentMixin",
    "HunyuanPlannerAgent", "HunyuanExecutorAgent", "HunyuanReviewerAgent",
    # Agents
    "LLMPlannerAgent", "LLMExecutorAgent", "LLMReviewerAgent",
    "MiniMaxPlannerAgent", "MiniMaxExecutorAgent", "MiniMaxReviewerAgent",
]
