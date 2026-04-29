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
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("llm_agents")
from ..agents.planner import PlannerAgent
from ..agents.executor import ExecutorAgent
from ..agents.reviewer import ReviewerAgent
from .claude import ClaudeAgentMixin
from .openai_compatible import MiniMaxAgentMixin, TimeoutError as LLMTimeoutError, RateLimitError as LLMRateLimitError
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
        max_correction_attempts: int = 3,
        min_quality_score: float = 0.7,
    ) -> Dict[str, Any]:
        if self._provider is None:
            return await super()._execute_subtask(subtask, execution_plan)

        task_text = subtask.get("description", str(subtask))
        task_id = subtask.get("id", "unknown")

        # Agentic RAG: detect ERP questions and do RAG search proactively
        rag_context = ""
        if self._tool_registry and self._provider is not None:
            erp_keywords = ["采购", "供应商", "库存", "财务", "审批", "销售", "订单", "报销", "付款", "管理"]
            if any(kw in task_text for kw in erp_keywords):
                try:
                    rag_tool = self._tool_registry.get_tool("erp_knowledge_search")
                    if rag_tool:
                        rag_result = await rag_tool.execute(query=task_text)
                        if rag_result.success:
                            rag_context = f"\n\n[RAG检索结果]\n{rag_result.output}\n\n"
                except Exception:
                    pass

        prompt_base = f"Execute:\n\n{task_text}"
        if rag_context:
            prompt_base = f"{rag_context}\n请基于上述检索结果回答：\n\n{task_text}"

        tools = None
        if self._tool_registry:
            schemas = self._tool_registry.get_specs()
            if schemas:
                tools = schemas

        # Self-correction loop
        last_error = None
        feedback_text = ""
        for attempt in range(max_correction_attempts):
            try:
                prompt = prompt_base
                if feedback_text and attempt > 0:
                    prompt = f"{prompt_base}\n\n[自我修正反馈 (Attempt {attempt})]\n{feedback_text}\n请基于上述反馈改进你的回答。"

                response = await self._llm_chat(prompt, tools=tools, max_tokens=2048)

                result_data: Dict[str, Any] = {}

                if response.tool_calls and self._tool_registry:
                    tool_results = []
                    for tc in response.tool_calls:
                        args = tc["input"] if isinstance(tc["input"], dict) else json.loads(tc["input"])
                        tr = await self._tool_registry.invoke(tc["name"], **args)
                        tool_results.append({"tool": tc["name"], "result": tr.to_dict()})
                    result_data["tool_calls"] = tool_results

                try:
                    parsed = json.loads(response.content)
                    result_data.update(parsed)
                except json.JSONDecodeError:
                    result_data["final_output"] = response.content

                result_data.setdefault("subtask_id", task_id)
                result_data.setdefault("description", task_text)

                # Self-correction: judge quality if LLM returned structured output
                if "final_output" in result_data and attempt < max_correction_attempts - 1:
                    quality_score = await self._judge_quality(
                        result_data["final_output"], task_text
                    )
                    result_data["quality_score"] = quality_score

                    if quality_score < min_quality_score:
                        feedback_text = result_data.get("feedback", [])
                        if isinstance(feedback_text, list):
                            feedback_text = "; ".join(str(f) for f in feedback_text)
                        feedback_text = feedback_text or f"Score {quality_score} < {min_quality_score}. Please provide a more complete/correct answer."
                        result_data["corrected"] = True
                        continue  # Retry

                result_data["attempts"] = attempt + 1
                return result_data

            except LLMTimeoutError as e:
                logger.warning(f"LLM timeout for task (attempt {attempt+1}): {e}")
                last_error = f"LLM timeout: {e}"
                feedback_text = f"上次尝试超时了，请换一种方式回答这个问题。"
                continue

            except LLMRateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt+1}): {e}")
                last_error = f"Rate limit: {e}"
                feedback_text = f"服务繁忙，请稍后重试或换一种更简洁的方式回答。"
                continue

            except Exception as e:
                logger.error(f"LLM execution failed (attempt {attempt+1}): {e}")
                last_error = str(e)
                feedback_text = f"发生错误: {e}。请换一种方式回答。"
                continue

        # All attempts failed
        return {
            "error": last_error or "Max correction attempts reached",
            "subtask_id": task_id,
            "description": task_text,
            "corrected": False,
            "attempts": max_correction_attempts,
        }

    async def _judge_quality(self, output: str, task: str) -> float:
        """Judge the quality of an LLM output. Returns 0.0-1.0 score."""
        try:
            judge_prompt = (
                f"Task: {task}\n\n"
                f"Output to evaluate: {output[:500]}\n\n"
                f"Score the quality of this output for the task above.\n"
                f"Consider: completeness (did it fully answer?), correctness (is it accurate?), relevance (is it on-topic?).\n"
                f"Respond ONLY with a JSON object: {{\"quality_score\": 0.0-1.0}}"
            )
            response = await self._llm_chat(judge_prompt, max_tokens=256)

            import json as _json
            parsed = _json.loads(response.content)
            score = float(parsed.get("quality_score", 0.5))
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5  # Default to 0.5 on error


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
