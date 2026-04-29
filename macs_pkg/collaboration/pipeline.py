"""Pipeline collaboration mode (sequential processing)."""

from typing import Any, Dict, List, Optional, Callable
import asyncio

from ..core.agent import BaseAgent, AgentRole, Message
from .base import CollaborationMode, CollaborationConfig


class PipelineMode(CollaborationMode):
    """Pipeline (sequential) collaboration mode.

    In this mode:
    1. Agents are arranged in a pipeline (chain)
    2. Each agent processes the input and passes to the next
    3. Data flows sequentially through the chain
    4. Each agent transforms or enhances the result

    Flow:
    User Input → Agent₁ → Agent₂ → Agent₃ → Final Output
                (每步处理后传递给下一步)

    Example use cases:
    - ETL pipelines: Extract → Transform → Load
    - Processing chains: Parse → Analyze → Generate
    - Verification chains: Input → Check → Validate → Output
    """

    name = "pipeline"
    description = "Sequential pipeline with data flowing through chained agents"

    def __init__(
        self,
        config: Optional[CollaborationConfig] = None,
        pipeline_order: Optional[List[str]] = None,
    ):
        super().__init__(config)
        self.pipeline_order = pipeline_order or []  # Ordered list of agent names
        self._chain: List[BaseAgent] = []

    def select_agents(
        self,
        task: Any,
        available_agents: List[BaseAgent],
    ) -> List[BaseAgent]:
        """Select and order agents for pipeline collaboration.

        Agents are ordered based on:
        1. Explicit pipeline_order if provided
        2. Agent role (Tool → Executor → Reviewer is typical)
        """
        if self.pipeline_order:
            # Use explicit order
            name_to_agent = {a.name: a for a in available_agents}
            self._chain = [name_to_agent[name] for name in self.pipeline_order if name in name_to_agent]
        else:
            # Auto-order by role: Tool -> Executor -> Reviewer -> Planner
            role_priority = {
                AgentRole.TOOL: 0,
                AgentRole.EXECUTOR: 1,
                AgentRole.REVIEWER: 2,
                AgentRole.PLANNER: 3,
            }
            self._chain = sorted(
                available_agents,
                key=lambda a: role_priority.get(a.role, 99),
            )

        return self._chain

    async def execute(
        self,
        task: Any,
        agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute pipeline collaboration.

        Args:
            task: The input to the pipeline.
            agents: Dictionary of agents by name.
            context: Optional shared context.

        Returns:
            Final output after flowing through the pipeline.
        """
        if not self._chain:
            self.select_agents(task, list(agents.values()))

        context = context or {}
        current_input = task

        # Process through each agent in sequence
        for i, agent in enumerate(self._chain):
            # Create input message for this stage
            input_msg = Message(
                sender="pipeline" if i == 0 else self._chain[i - 1].name,
                receiver=agent.name,
                content={
                    "action": "process",
                    "input": current_input,
                    "pipeline_stage": i + 1,
                    "total_stages": len(self._chain),
                },
                msg_type="task",
                metadata={
                    "phase": "pipeline",
                    "stage": i + 1,
                    "context": context,
                },
            )

            # Execute this stage
            try:
                response = await agent.think(input_msg)
                actions = await agent.act(response)

                # Use response content as input for next stage
                current_input = response.content

                # Update context with stage results
                context[f"stage_{i + 1}_output"] = response.content
                context[f"stage_{i + 1}_agent"] = agent.name

            except Exception as e:
                if self.config.stop_on_error:
                    raise RuntimeError(f"Pipeline failed at stage {i + 1} ({agent.name}): {e}") from e
                current_input = {"error": str(e), "stage": i + 1, "agent": agent.name}

        return current_input

    def get_required_roles(self) -> List[AgentRole]:
        """Pipeline typically involves executors and reviewers."""
        return [AgentRole.EXECUTOR, AgentRole.REVIEWER, AgentRole.TOOL]

    def set_pipeline_order(self, agent_names: List[str]) -> None:
        """Set explicit pipeline order.

        Args:
            agent_names: Ordered list of agent names.
        """
        self.pipeline_order = agent_names


class ParallelPipelineMode(PipelineMode):
    """Parallel pipeline mode - multiple pipelines run concurrently.

    Splits input, processes through parallel chains, then merges results.
    """

    name = "parallel_pipeline"
    description = "Multiple parallel pipelines with result merging"

    def __init__(
        self,
        config: Optional[CollaborationConfig] = None,
        num_parallel: int = 2,
        merge_strategy: str = "concat",
    ):
        super().__init__(config)
        self.num_parallel = num_parallel
        self.merge_strategy = merge_strategy
        self._pipelines: List[List[BaseAgent]] = []

    def setup_pipelines(
        self,
        available_agents: List[BaseAgent],
        num_pipelines: int = 2,
    ) -> None:
        """Setup multiple parallel pipelines.

        Args:
            available_agents: List of available agents.
            num_pipelines: Number of parallel pipelines to create.
        """
        # Distribute agents among pipelines
        agents_per_pipeline = len(available_agents) // num_pipelines
        self._pipelines = []

        for i in range(num_pipelines):
            start = i * agents_per_pipeline
            end = start + agents_per_pipeline if i < num_pipelines - 1 else len(available_agents)
            self._pipelines.append(available_agents[start:end])

    async def execute(
        self,
        task: Any,
        agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute parallel pipeline collaboration.

        Splits input, processes through parallel chains, merges results.
        """
        if not self._pipelines:
            self.setup_pipelines(list(agents.values()), self.num_parallel)

        context = context or {}

        # Split input if it's a collection
        if isinstance(task, (list, tuple)):
            inputs = task
        else:
            inputs = [task] * len(self._pipelines)

        # Ensure we have same number of inputs as pipelines
        while len(inputs) < len(self._pipelines):
            inputs.append(inputs[-1])

        # Execute pipelines in parallel
        async def run_pipeline(pipeline_agents: List[BaseAgent], pipeline_input: Any) -> Any:
            temp_chain = self._chain
            self._chain = pipeline_agents
            result = await PipelineMode.execute(self, pipeline_input, agents, context)
            self._chain = temp_chain
            return result

        results = await asyncio.gather(
            *[
                run_pipeline(pipeline, inp)
                for pipeline, inp in zip(self._pipelines, inputs[:len(self._pipelines)])
            ],
            return_exceptions=True,
        )

        # Merge results
        return self._merge_results(results)

    def _merge_results(self, results: List[Any]) -> Any:
        """Merge parallel pipeline results."""
        if self.merge_strategy == "concat":
            return {"parallel_results": results, "count": len(results)}
        elif self.merge_strategy == "first":
            return results[0] if results else None
        elif self.merge_strategy == "last":
            return results[-1] if results else None
        else:
            return results
