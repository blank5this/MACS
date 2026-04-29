"""LLM-powered agent implementations for MACS.

Drop-in replacements for PlannerAgent, ExecutorAgent, and ReviewerAgent that
use a real LLM (Claude by default) instead of heuristic/placeholder logic.

Usage::

    from macs_pkg.llm import ClaudeProvider, LLMPlannerAgent

    provider = ClaudeProvider()          # reads ANTHROPIC_API_KEY
    planner = LLMPlannerAgent("planner", provider=provider)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..core.agent import AgentRole, AgentState, Message
from ..agents.planner import PlannerAgent
from ..agents.executor import ExecutorAgent
from ..agents.reviewer import ReviewerAgent
from .claude import ClaudeAgentMixin
from .openai_compatible import MiniMaxAgentMixin
from .base import LLMProvider


# ──────────────────────────────────────────────────────────────────────────────
# LLM Planner
# ──────────────────────────────────────────────────────────────────────────────

class LLMPlannerAgent(ClaudeAgentMixin, PlannerAgent):
    """Planner Agent that uses an LLM to decompose tasks.

    When an LLM provider is set, the decomposition logic is driven by the model.
    Falls back to heuristic decomposition when no provider is available.
    """

    SYSTEM_PROMPT = (
        "You are a task-planning AI. When given a task, break it down into "
        "clear, actionable subtasks. Always respond with valid JSON in the format:\n"
        '{"subtasks": [{"id": "subtask_1", "description": "...", "type": "execution", "priority": 1}]}\n'
        "Use types: 'analysis', 'execution', 'synthesis', 'review'. Priority 1 = highest."
    )

    def __init__(
        self,
        name: str = "planner",
        model: str = "claude-sonnet-4-6",
        provider: Optional[LLMProvider] = None,
        **kwargs: Any,
    ):
        super().__init__(name=name, model=model, provider=provider, system_prompt=self.SYSTEM_PROMPT, **kwargs)

    async def _decompose_task(self, task: Any) -> List[Dict[str, Any]]:
        """Use the LLM to decompose the task, or fall back to heuristics."""
        if self._provider is None:
            return await super()._decompose_task(task)

        if isinstance(task, dict):
            task_text = task.get("description", json.dumps(task))
        else:
            task_text = str(task)

        try:
            response = await self._llm_chat(
                f"Decompose this task into subtasks:\n\n{task_text}",
                max_tokens=1024,
            )
            data = json.loads(response.content)
            return data.get("subtasks", [])
        except (json.JSONDecodeError, Exception):
            # Graceful fallback
            return await super()._decompose_task(task)


# ──────────────────────────────────────────────────────────────────────────────
# LLM Executor
# ──────────────────────────────────────────────────────────────────────────────

class LLMExecutorAgent(ClaudeAgentMixin, ExecutorAgent):
    """Executor Agent that uses an LLM to perform subtasks.

    Can also invoke tools registered in a ToolRegistry via Claude tool use.
    """

    SYSTEM_PROMPT = (
        "You are an execution AI. You receive a subtask and execute it thoroughly.\n"
        "IMPORTANT: When answering questions about ERP policies, procedures, or company guidelines,\n"
        "you MUST call the 'erp_knowledge_search' tool first to retrieve relevant information.\n"
        "Then synthesize the retrieved information into your answer.\n\n"
        "You have access to:\n"
        "  - erp_knowledge_search: Search ERP knowledge base for policies and procedures\n"
        "Always respond with valid JSON:\n"
        '{"final_output": "...", "steps": [{"step": "...", "result": "..."}]}\n'
        "Be precise and complete. Cite sources from RAG search results."
    )

    def __init__(
        self,
        name: str = "executor",
        model: str = "claude-sonnet-4-6",
        provider: Optional[LLMProvider] = None,
        tool_registry: Optional[Any] = None,  # macs_pkg.tools.ToolRegistry
        **kwargs: Any,
    ):
        super().__init__(name=name, model=model, provider=provider, system_prompt=self.SYSTEM_PROMPT, **kwargs)
        self._tool_registry = tool_registry

    async def _execute_subtask(
        self,
        subtask: Dict[str, Any],
        execution_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use the LLM (and tools) to execute the subtask."""
        if self._provider is None:
            return await super()._execute_subtask(subtask, execution_plan)

        task_text = subtask.get("description", str(subtask))

        # Build tool schemas if a registry is provided
        tools = None
        if self._tool_registry:
            schemas = self._tool_registry.get_specs()
            if schemas:
                tools = schemas

        try:
            response = await self._llm_chat(
                f"Execute this subtask:\n\n{task_text}",
                tools=tools,
                max_tokens=2048,
            )

            # Handle tool calls
            result_data: Dict[str, Any] = {}
            if response.tool_calls and self._tool_registry:
                tool_results = []
                for tc in response.tool_calls:
                    tr = await self._tool_registry.invoke(tc["name"], **tc["input"])
                    tool_results.append({
                        "tool": tc["name"],
                        "result": tr.to_dict(),
                    })
                result_data["tool_calls"] = tool_results

            # Parse LLM JSON response
            try:
                parsed = json.loads(response.content)
                result_data.update(parsed)
            except json.JSONDecodeError:
                result_data["final_output"] = response.content

            result_data.setdefault("subtask_id", subtask.get("id"))
            result_data.setdefault("description", task_text)
            return result_data

        except Exception as e:
            return {"error": str(e), "subtask_id": subtask.get("id")}


# ──────────────────────────────────────────────────────────────────────────────
# LLM Reviewer
# ──────────────────────────────────────────────────────────────────────────────

class LLMReviewerAgent(ClaudeAgentMixin, ReviewerAgent):
    """Reviewer Agent that uses an LLM to validate and critique results."""

    SYSTEM_PROMPT = (
        "You are a quality-review AI. Given execution results, evaluate them on "
        "completeness, correctness, and relevance. Respond with valid JSON:\n"
        '{"overall_score": 0.9, "criterion_scores": {"completeness": 1.0, "correctness": 0.9, '
        '"relevance": 0.8}, "feedback": ["issue1", "issue2"], "approved": true}\n'
        "overall_score is between 0 and 1. approved is true if overall_score >= 0.7."
    )

    def __init__(
        self,
        name: str = "reviewer",
        model: str = "claude-sonnet-4-6",
        provider: Optional[LLMProvider] = None,
        **kwargs: Any,
    ):
        super().__init__(name=name, model=model, provider=provider, system_prompt=self.SYSTEM_PROMPT, **kwargs)

    async def _review_result(
        self,
        result: Any,
        review_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use the LLM to review a result."""
        if self._provider is None:
            return await super()._review_result(result, review_plan)

        result_text = json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result)

        try:
            response = await self._llm_chat(
                f"Review this execution result:\n\n{result_text}",
                max_tokens=1024,
            )
            review_data = json.loads(response.content)
            review_data["result"] = result
            return review_data
        except (json.JSONDecodeError, Exception):
            return await super()._review_result(result, review_plan)


# ──────────────────────────────────────────────────────────────────────────────
# MiniMax-powered agents  (use OpenAI-compatible MiniMax API)
# ──────────────────────────────────────────────────────────────────────────────

class MiniMaxPlannerAgent(MiniMaxAgentMixin, PlannerAgent):
    """Planner Agent backed by MiniMax LLM."""

    SYSTEM_PROMPT = (
        "You are a task-planning AI. When given a task, break it down into "
        "clear, actionable subtasks. Always respond with valid JSON in the format:\n"
        '{"subtasks": [{"id": "subtask_1", "description": "...", "type": "execution", "priority": 1}]}\n'
        "Use types: 'analysis', 'execution', 'synthesis', 'review'. Priority 1 = highest."
    )

    def __init__(
        self,
        name: str = "planner",
        model: str = "MiniMax-Text-01",
        provider: Optional[LLMProvider] = None,
        **kwargs: Any,
    ):
        super().__init__(name=name, model=model, provider=provider, system_prompt=self.SYSTEM_PROMPT, **kwargs)

    async def _decompose_task(self, task: Any) -> List[Dict[str, Any]]:
        if self._provider is None:
            return await super()._decompose_task(task)

        task_text = task.get("description", json.dumps(task)) if isinstance(task, dict) else str(task)

        try:
            response = await self._llm_chat(f"Decompose this task:\n\n{task_text}", max_tokens=1024)
            data = json.loads(response.content)
            return data.get("subtasks", [])
        except (json.JSONDecodeError, Exception):
            return await super()._decompose_task(task)


class MiniMaxExecutorAgent(MiniMaxAgentMixin, ExecutorAgent):
    """Executor Agent backed by MiniMax LLM."""

    SYSTEM_PROMPT = (
        "You are an execution AI. You receive a subtask and execute it thoroughly.\n"
        "When answering ERP-related questions, ALWAYS search the knowledge base first.\n\n"
        "Always respond with valid JSON:\n"
        '{"final_output": "...", "steps": [{"step": "...", "result": "..."}]}\n'
        "Be precise and complete."
    )

    def __init__(
        self,
        name: str = "executor",
        model: str = "MiniMax-Text-01",
        provider: Optional[LLMProvider] = None,
        tool_registry: Optional[Any] = None,
        **kwargs: Any,
    ):
        super().__init__(name=name, model=model, provider=provider, system_prompt=self.SYSTEM_PROMPT, **kwargs)
        self._tool_registry = tool_registry

    async def _execute_subtask(
        self,
        subtask: Dict[str, Any],
        execution_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self._provider is None:
            return await super()._execute_subtask(subtask, execution_plan)

        task_text = subtask.get("description", str(subtask))

        # Agentic RAG: detect ERP questions and do RAG search proactively
        rag_context = ""
        if self._tool_registry and self._provider is not None:
            erp_keywords = ["采购", "供应商", "库存", "财务", "审批", "销售", "订单", "报销", "付款", "管理"]
            if any(kw in task_text for kw in erp_keywords):
                # Proactively call RAG tool before LLM
                try:
                    rag_tool = self._tool_registry.get_tool("erp_knowledge_search")
                    if rag_tool:
                        rag_result = await rag_tool.execute(query=task_text)
                        if rag_result.success:
                            rag_context = f"\n\n[RAG检索结果]\n{rag_result.output}\n\n"
                except Exception:
                    pass  # RAG failed, continue without it

        # Build prompt with RAG context
        prompt = f"Execute:\n\n{task_text}"
        if rag_context:
            prompt = f"{rag_context}\n请基于上述检索结果回答：\n\n{task_text}"

        tools = None
        if self._tool_registry:
            schemas = self._tool_registry.get_specs()
            if schemas:
                tools = schemas

        try:
            response = await self._llm_chat(prompt, tools=tools, max_tokens=2048)

            result_data: Dict[str, Any] = {}

            if response.tool_calls and self._tool_registry:
                tool_results = []
                for tc in response.tool_calls:
                    import json as _json
                    args = tc["input"] if isinstance(tc["input"], dict) else _json.loads(tc["input"])
                    tr = await self._tool_registry.invoke(tc["name"], **args)
                    tool_results.append({"tool": tc["name"], "result": tr.to_dict()})
                result_data["tool_calls"] = tool_results

            try:
                parsed = json.loads(response.content)
                result_data.update(parsed)
            except json.JSONDecodeError:
                result_data["final_output"] = response.content

            result_data.setdefault("subtask_id", subtask.get("id"))
            result_data.setdefault("description", task_text)
            return result_data

        except TimeoutError as e:
            # LLM timeout - try fallback or partial result
            logger.warning(f"LLM timeout for task: {e}")
            return {
                "error": f"LLM timeout: {e}",
                "subtask_id": subtask.get("id"),
                "description": task_text,
                "fallback": True,
            }
        except RateLimitError as e:
            # Rate limit - could implement backoff here
            logger.warning(f"Rate limit hit: {e}")
            return {
                "error": f"Rate limit: {e}",
                "subtask_id": subtask.get("id"),
                "description": task_text,
                "retry_after": True,
            }
        except Exception as e:
            logger.error(f"LLM execution failed: {e}")
            return {"error": str(e), "subtask_id": subtask.get("id")}


class MiniMaxReviewerAgent(MiniMaxAgentMixin, ReviewerAgent):
    """Reviewer Agent backed by MiniMax LLM."""

    SYSTEM_PROMPT = (
        "You are a quality-review AI. Given execution results, evaluate them on "
        "completeness, correctness, and relevance. Respond with valid JSON:\n"
        '{"overall_score": 0.9, "criterion_scores": {"completeness": 1.0, "correctness": 0.9, '
        '"relevance": 0.8}, "feedback": ["issue1"], "approved": true}\n'
        "overall_score is between 0 and 1. approved is true if overall_score >= 0.7."
    )

    def __init__(
        self,
        name: str = "reviewer",
        model: str = "MiniMax-Text-01",
        provider: Optional[LLMProvider] = None,
        **kwargs: Any,
    ):
        super().__init__(name=name, model=model, provider=provider, system_prompt=self.SYSTEM_PROMPT, **kwargs)

    async def _review_result(
        self,
        result: Any,
        review_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self._provider is None:
            return await super()._review_result(result, review_plan)

        result_text = json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result)

        try:
            response = await self._llm_chat(f"Review:\n\n{result_text}", max_tokens=1024)
            review_data = json.loads(response.content)
            review_data["result"] = result
            return review_data
        except (json.JSONDecodeError, Exception):
            return await super()._review_result(result, review_plan)
