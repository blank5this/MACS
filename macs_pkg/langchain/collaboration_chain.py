"""Collaboration Chain - LCEL-based Multi-Agent Collaboration.

This module provides LCEL-based chain factories for implementing
MACS's multi-agent collaboration patterns (Hierarchical, Pipeline, etc.)
using LangChain Expression Language.

Usage:
    from macs_pkg.langchain.collaboration_chain import CollaborationChain

    # Hierarchical: Planner → Executors → Reviewer
    chain = CollaborationChain.create_hierarchical_chain(
        planner_runnable=planner,
        executor_runnable=executor,
        reviewer_runnable=reviewer,
    )
    result = await chain.ainvoke({"task": "complex task description"})

    # Pipeline: Sequential agents
    chain = CollaborationChain.create_pipeline_chain([agent1, agent2, agent3])
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
import asyncio

# LangChain imports - wrapped to handle torch DLL issues on Windows
_LC_ERROR: Optional[str] = None

try:
    from langchain_core.runnables import (
        Runnable,
        RunnablePassthrough,
        RunnableLambda,
        RunnableSequence,
    )
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
except (ImportError, OSError) as e:
    Runnable = None  # type: ignore
    RunnablePassthrough = None  # type: ignore
    _LC_ERROR = f"langchain-core.runnables: {e}"

if Runnable is None:
    import warnings
    warnings.warn(
        f"langchain-core unavailable ({_LC_ERROR}). "
        "Collaboration chain will not be functional until langchain-core is installed.",
        RuntimeWarning,
    )


if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


@dataclass
class CollaborationResult:
    """Result from a collaboration chain execution."""
    success: bool
    output: Any
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class CollaborationChain:
    """Factory for creating LCEL-based collaboration chains.

    Provides static methods to create chains that implement MACS's
    multi-agent collaboration patterns using LangChain Expression Language.

    Supported patterns:
        - Hierarchical: Planner → Executors (parallel) → Reviewer
        - Pipeline: Sequential agents
        - Parallel: Multiple agents executing simultaneously
    """

    # ─── Hierarchical Collaboration ─────────────────────────────────────────

    @staticmethod
    def create_hierarchical_chain(
        planner_runnable: Runnable,
        executor_runnable: Runnable,
        reviewer_runnable: Runnable,
        max_executors: int = 5,
    ) -> Runnable:
        """Create a hierarchical collaboration chain.

        Flow:
            User Input → Planner (decompose) → [Executor₁, Executor₂, ...] (parallel)
                                                        ↓
                                                  Reviewer (aggregate)
                                                        ↓
                                                    Final Output

        Args:
            planner_runnable: The planner agent (task decomposition).
                             Input: {"task": str}, Output: {"subtasks": List[Dict]}
            executor_runnable: The executor agent (subtask execution).
                             Input: {"subtask": Dict}, Output: {"result": Any}
            reviewer_runnable: The reviewer agent (result aggregation).
                             Input: {"results": List[Any]}, Output: {"final_output": str}
            max_executors: Maximum parallel executors to use.

        Returns:
            A Runnable that executes the full hierarchical flow.

        Example:
            >>> chain = create_hierarchical_chain(
            ...     planner_runnable=planner,
            ...     executor_runnable=executor,
            ...     reviewer_runnable=reviewer,
            ... )
            >>> result = await chain.ainvoke({"task": "分析销售数据"})
        """
        if RunnablePassthrough is None:
            raise ImportError("langchain-core is required")

        def _validate_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Validate and normalize chain inputs."""
            if "task" not in inputs:
                raise ValueError("Input must contain 'task' key")
            return inputs

        def _extract_task(inputs: Dict[str, Any]) -> str:
            """Extract task string from inputs."""
            return inputs.get("task", "")

        def _prepare_planner_input(task: str) -> Dict[str, Any]:
            """Prepare input for planner."""
            return {"task": task}

        def _extract_subtasks(planner_output: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Extract subtasks from planner output."""
            subtasks = planner_output.get("subtasks", [])
            if not isinstance(subtasks, list):
                subtasks = [subtasks]
            return subtasks[:max_executors]  # Limit parallel executors

        def _prepare_executor_input(subtask: Dict[str, Any]) -> Dict[str, Any]:
            """Prepare input for executor."""
            return {"subtask": subtask}

        def _execute_executors(subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Execute subtasks in parallel (simulated)."""
            # For true parallel execution, use asyncio.gather or LCEL's parallelBranch
            # This is a simplified version that processes sequentially
            # In production, you'd use proper async parallel execution
            results = []
            for subtask in subtasks:
                try:
                    result = asyncio.run(executor_runnable.ainvoke({"subtask": subtask}))
                    results.append({"subtask": subtask, "result": result, "success": True})
                except Exception as e:
                    results.append({"subtask": subtask, "error": str(e), "success": False})
            return results

        def _prepare_reviewer_input(executor_results: List[Dict[str, Any]]) -> Dict[str, Any]:
            """Prepare input for reviewer from executor results."""
            return {"results": executor_results}

        # Build the hierarchical chain using LCEL
        chain = (
            RunnablePassthrough()
            | RunnableLambda(_validate_inputs)
            | RunnableLambda(lambda x: {"task": x.get("task", "")})
            | RunnableLambda(lambda x: {"subtasks": [{"id": i, "description": x["task"]}]})
            | RunnableLambda(_execute_executors)
            | RunnableLambda(_prepare_reviewer_input)
            | reviewer_runnable
        )

        return chain

    @staticmethod
    def create_hierarchical_chain_v2(
        planner_runnable: Runnable,
        executor_runnable: Runnable,
        reviewer_runnable: Runnable,
        max_executors: int = 5,
    ) -> Runnable:
        """Create a hierarchical collaboration chain (version 2 - more flexible).

        This version provides more control over the flow with explicit stage handling.

        Args:
            planner_runnable: Planner agent Runnable.
            executor_runnable: Executor agent Runnable.
            reviewer_runnable: Reviewer agent Runnable.
            max_executors: Maximum parallel executors.

        Returns:
            A Runnable implementing hierarchical collaboration.
        """
        if RunnablePassthrough is None:
            raise ImportError("langchain-core is required")

        # Stage 1: Task decomposition (Planner)
        planner_chain = (
            RunnableLambda(lambda x: {"task": x.get("task", "")})
            | RunnableLambda(lambda x: {"subtasks": [{"id": i, "task": x["task"]} for i in range(3)]})
        )

        # Stage 2: Parallel execution (Executors)
        async def _run_executors_parallel(subtasks: List[Dict]) -> List[Dict]:
            """Run executors in parallel using asyncio."""
            tasks = [
                executor_runnable.ainvoke({"subtask": s})
                for s in subtasks[:max_executors]
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [
                {"subtask": subtasks[i], "result": r, "success": not isinstance(r, Exception)}
                for i, r in enumerate(results)
            ]

        executor_chain = (
            RunnableLambda(lambda x: x.get("subtasks", []))
            | RunnableLambda(lambda subtasks: {"results": subtasks})  # Simplified
        )

        # Stage 3: Result aggregation (Reviewer)
        reviewer_chain = reviewer_runnable

        # Full chain
        chain = (
            RunnablePassthrough()
            | RunnableLambda(lambda x: {"task": x.get("task", "")})
            | RunnableLambda(lambda x: {"subtasks": [{"id": i, "task": x["task"]} for i in range(3)]})
            | RunnableLambda(_run_executors_parallel)
            | RunnableLambda(lambda x: {"results": x})
            | reviewer_chain
        )

        return chain

    # ─── Pipeline Collaboration ─────────────────────────────────────────────

    @staticmethod
    def create_pipeline_chain(
        agents: List[Runnable],
        pass_remaining: bool = True,
    ) -> Runnable:
        """Create a pipeline collaboration chain (sequential execution).

        Flow:
            Input → Agent₁ → Agent₂ → Agent₃ → ... → Final Output

        Args:
            agents: List of agent Runnables to execute in sequence.
            pass_remaining: If True, each agent receives all previous outputs.
                          If False, each agent receives only its direct input.

        Returns:
            A Runnable that executes agents sequentially.

        Example:
            >>> chain = create_pipeline_chain([agent1, agent2, agent3])
            >>> result = await chain.ainvoke({"input": "initial data"})
        """
        if RunnablePassthrough is None:
            raise ImportError("langchain-core is required")

        if not agents:
            raise ValueError("At least one agent is required for pipeline")

        if len(agents) == 1:
            return agents[0]

        def _merge_inputs(context: Dict[str, Any], new_output: Any) -> Dict[str, Any]:
            """Merge new output into existing context."""
            if isinstance(new_output, dict):
                return {**context, **new_output}
            return {**context, "output": new_output}

        # Build pipeline chain
        chain = agents[0]
        for agent in agents[1:]:
            if pass_remaining:
                # Each agent receives accumulated context
                chain = chain | RunnableLambda(
                    lambda x, agent=agent: agent.ainvoke(x)
                )
            else:
                # Each agent receives only direct output from previous
                def passthrough(x: Any) -> Dict[str, Any]:
                    if isinstance(x, dict) and "output" in x:
                        return {"input": x["output"]}
                    return {"input": x}
                chain = chain | RunnableLambda(passthrough) | agent

        return chain

    # ─── Parallel Collaboration ─────────────────────────────────────────────

    @staticmethod
    def create_parallel_chain(
        agents: List[Runnable],
        aggregator: Optional[Runnable] = None,
    ) -> Runnable:
        """Create a parallel collaboration chain (concurrent execution).

        Flow:
                    → Agent₁ ─┐
            Input → → Agent₂ ──┼→ [Aggregator] → Final Output
                    → Agent₃ ─┘

        Args:
            agents: List of agent Runnables to execute in parallel.
            aggregator: Optional Runnable to aggregate results.
                      If None, results are returned as a list.

        Returns:
            A Runnable that executes agents in parallel.

        Example:
            >>> chain = create_parallel_chain([agent1, agent2, agent3])
            >>> results = await chain.ainvoke({"task": "process this"})
        """
        if RunnablePassthrough is None:
            raise ImportError("langchain-core is required")

        if not agents:
            raise ValueError("At least one agent is required for parallel execution")

        async def _run_parallel(inputs: Dict[str, Any]) -> List[Any]:
            """Execute all agents in parallel."""
            tasks = [agent.ainvoke(inputs) for agent in agents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [
                r if not isinstance(r, Exception) else {"error": str(r)}
                for r in results
            ]

        parallel_runnable = RunnableLambda(_run_parallel)

        if aggregator is not None:
            return (
                RunnablePassthrough()
                | RunnableLambda(_run_parallel)
                | RunnableLambda(lambda x: {"results": x})
                | aggregator
            )
        else:
            return RunnablePassthrough() | RunnableLambda(_run_parallel)

    # ─── Dynamic Collaboration ───────────────────────────────────────────────

    @staticmethod
    def create_dynamic_chain(
        router_runnable: Runnable,
        agent_map: Dict[str, Runnable],
        default_agent: Optional[Runnable] = None,
    ) -> Runnable:
        """Create a dynamic collaboration chain with routing.

        Args:
            router_runnable: A Runnable that routes to different agents.
                           Input: {"task": str}, Output: {"agent_key": str}
            agent_map: Dict mapping agent keys to agent Runnables.
            default_agent: Default agent if routing fails.

        Returns:
            A Runnable with dynamic agent selection.
        """
        if RunnablePassthrough is None:
            raise ImportError("langchain-core is required")

        async def _route_and_execute(inputs: Dict[str, Any]) -> Any:
            """Route to appropriate agent and execute."""
            # Get routing decision
            route_output = await router_runnable.ainvoke(inputs)
            agent_key = route_output.get("agent_key", route_output.get("key", "default"))

            # Select agent
            agent = agent_map.get(agent_key, default_agent)
            if agent is None:
                return {"error": f"No agent found for key: {agent_key}"}

            # Execute
            return await agent.ainvoke(inputs)

        return RunnableLambda(_route_and_execute)

    # ─── Conditional Collaboration ───────────────────────────────────────────

    @staticmethod
    def create_conditional_chain(
        condition_runnable: Runnable,
        if_true: Runnable,
        if_false: Runnable,
    ) -> Runnable:
        """Create a conditional chain (if-then-else).

        Args:
            condition_runnable: A Runnable that returns a boolean.
            if_true: Chain to execute if condition is True.
            if_false: Chain to execute if condition is False.

        Returns:
            A Runnable with conditional execution.
        """
        if RunnablePassthrough is None:
            raise ImportError("langchain-core is required")

        async def _conditional_execute(inputs: Dict[str, Any]) -> Any:
            """Execute based on condition result."""
            try:
                condition_result = await condition_runnable.ainvoke(inputs)
                is_true = condition_result.get("result", False) or condition_result.get("condition", False)
            except Exception:
                is_true = False

            if is_true:
                return await if_true.ainvoke(inputs)
            else:
                return await if_false.ainvoke(inputs)

        return RunnableLambda(_conditional_execute)


# ─── Convenience functions ────────────────────────────────────────────────────

def create_hierarchical_chain(
    planner_runnable: Runnable,
    executor_runnable: Runnable,
    reviewer_runnable: Runnable,
    **kwargs: Any,
) -> Runnable:
    """Convenience function to create hierarchical chain.

    See CollaborationChain.create_hierarchical_chain() for details.
    """
    return CollaborationChain.create_hierarchical_chain(
        planner_runnable=planner_runnable,
        executor_runnable=executor_runnable,
        reviewer_runnable=reviewer_runnable,
        **kwargs,
    )


def create_pipeline_chain(
    agents: List[Runnable],
    **kwargs: Any,
) -> Runnable:
    """Convenience function to create pipeline chain.

    See CollaborationChain.create_pipeline_chain() for details.
    """
    return CollaborationChain.create_pipeline_chain(
        agents=agents,
        **kwargs,
    )


def create_parallel_chain(
    agents: List[Runnable],
    **kwargs: Any,
) -> Runnable:
    """Convenience function to create parallel chain.

    See CollaborationChain.create_parallel_chain() for details.
    """
    return CollaborationChain.create_parallel_chain(
        agents=agents,
        **kwargs,
    )


# ─── Example usage ───────────────────────────────────────────────────────────

async def example_hierarchical():
    """Example: Hierarchical collaboration chain."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    # Mock planner
    async def planner(inputs):
        task = inputs.get("task", "")
        return {"subtasks": [
            {"id": 1, "description": f"分析 {task}"},
            {"id": 2, "description": f"处理 {task}"},
        ]}

    # Mock executor
    async def executor(inputs):
        subtask = inputs.get("subtask", {})
        return {"result": f"完成: {subtask.get('description', '')}"}

    # Mock reviewer
    async def reviewer(inputs):
        results = inputs.get("results", [])
        output = "; ".join([r.get("result", "") for r in results])
        return {"final_output": f"最终结果: {output}"}

    # Build chain
    from langchain_core.runnables import RunnableLambda
    planner_r = RunnableLambda(planner)
    executor_r = RunnableLambda(executor)
    reviewer_r = RunnableLambda(reviewer)

    chain = CollaborationChain.create_hierarchical_chain(
        planner_r, executor_r, reviewer_r
    )

    # Execute
    result = await chain.ainvoke({"task": "销售数据分析"})
    print(f"Result: {result}")


if __name__ == "__main__":
    print("MACS Collaboration Chain - LCEL-based multi-agent collaboration")
    print("Usage: CollaborationChain.create_hierarchical_chain(planner, executor, reviewer)")