"""Hierarchical collaboration mode (Leader-Agent pattern)."""

from typing import Any, Dict, List, Optional
import asyncio

from ..core.agent import BaseAgent, AgentRole, Message
from .base import CollaborationMode, CollaborationConfig


class HierarchicalMode(CollaborationMode):
    """Hierarchical (Leader-Agent) collaboration mode.

    In this mode:
    1. A leader/planner agent decomposes the task into subtasks
    2. Executor agents work on subtasks in parallel
    3. A reviewer agent aggregates and validates results
    4. The leader produces the final output

    Flow:
    User Input → Planner (decompose) → [Executor₁, Executor₂, ...] (parallel)
                                           ↓
                                    Reviewer (review)
                                           ↓
                                       Leader (finalize)
    """

    name = "hierarchical"
    description = "Leader-Agent pattern with task decomposition and parallel execution"

    def __init__(self, config: Optional[CollaborationConfig] = None):
        super().__init__(config)
        self._leader: Optional[BaseAgent] = None
        self._executors: List[BaseAgent] = []
        self._reviewer: Optional[BaseAgent] = None

    def select_agents(
        self,
        task: Any,
        available_agents: List[BaseAgent],
    ) -> List[BaseAgent]:
        """Select agents for hierarchical collaboration.

        Requires at minimum: 1 planner, 1+ executors, optionally 1 reviewer.
        """
        selected = []
        agent_by_role = {agent.role: agent for agent in available_agents}

        # Get planner
        if AgentRole.PLANNER in agent_by_role:
            self._leader = agent_by_role[AgentRole.PLANNER]
            selected.append(self._leader)
        elif AgentRole.EXECUTOR in agent_by_role:
            # Fallback: use executor as leader
            self._leader = agent_by_role[AgentRole.EXECUTOR]
            selected.append(self._leader)

        # Get executors
        for agent in available_agents:
            if agent.role == AgentRole.EXECUTOR and agent not in selected:
                self._executors.append(agent)
                selected.append(agent)

        # Get reviewer
        if AgentRole.REVIEWER in agent_by_role:
            self._reviewer = agent_by_role[AgentRole.REVIEWER]
            if self._reviewer not in selected:
                selected.append(self._reviewer)

        return selected

    async def execute(
        self,
        task: Any,
        agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute hierarchical collaboration.

        Args:
            task: The task to execute (dict with 'type', 'description', etc.)
            agents: Dictionary of agents by name.
            context: Optional shared context.

        Returns:
            Final result from the hierarchical process.
        """
        context = context or {}
        max_iterations = self.config.max_iterations

        # Ensure agents are selected before execution
        if self._leader is None and not self._executors:
            self.select_agents(task, list(agents.values()))

        # Phase 1: Planning (decompose task)
        planner_msg = Message(
            sender="system",
            receiver=self._leader.name if self._leader else list(agents.values())[0].name,
            content={
                "action": "decompose",
                "task": task,
                "executors": [a.name for a in self._executors],
            },
            msg_type="task",
            metadata={"phase": "planning"},
        )

        if self._leader:
            # Phase 1: think + act to trigger LLM decomposition
            leader_response = await self._leader.think(planner_msg)
            leader_actions = await self._leader.act(leader_response)

            # Extract subtasks from act() result messages
            subtasks = []
            for action_msg in leader_actions:
                if isinstance(action_msg.content, dict) and "subtask" in action_msg.content:
                    subtask = action_msg.content["subtask"]
                    if isinstance(subtask, dict):
                        subtasks.append(subtask)
                    elif isinstance(subtask, list):
                        subtasks.extend(subtask)

            # Fallback: also check response content
            if not subtasks:
                content = leader_response.content
                if isinstance(content, dict):
                    st = content.get("subtasks", [])
                    if isinstance(st, list) and st:
                        subtasks = st
                    elif "subtask" in content:
                        subtasks = [content["subtask"]] if isinstance(content["subtask"], dict) else []

            if not subtasks:
                # Last fallback: treat the task as single subtask
                task_desc = task.get("description", str(task)) if isinstance(task, dict) else str(task)
                subtasks = [{"id": "subtask_1", "description": task_desc, "type": "execution", "priority": 1}]
        else:
            # Fallback: treat entire task as single subtask
            task_desc = task.get("description", str(task)) if isinstance(task, dict) else str(task)
            subtasks = [{"id": "main", "description": task_desc, "assigned_executor": list(agents.keys())[0]}]

        # Phase 2: Parallel execution
        executor_results = []
        if self._executors and subtasks:
            # Distribute subtasks among executors
            task_assignments = self._distribute_subtasks(subtasks, self._executors)

            # Execute in parallel
            execution_tasks = []
            for executor, assigned_tasks in task_assignments.items():
                exec_msg = Message(
                    sender="system",
                    receiver=executor.name,
                    content={
                        "action": "execute",
                        "tasks": assigned_tasks,
                    },
                    msg_type="task",
                    metadata={"phase": "execution"},
                )
                execution_tasks.append(self._execute_single(executor, exec_msg))

            results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    if self.config.stop_on_error:
                        raise result
                    executor_results.append({"error": str(result)})
                else:
                    executor_results.append(result)
        else:
            # No executors, leader does everything
            if self._leader:
                result = await self._leader.think(Message(
                    sender="system",
                    receiver=self._leader.name,
                    content=task,
                    msg_type="task",
                ))
                executor_results.append(result.content)

        # Phase 3: Review (think + act)
        if self._reviewer and executor_results:
            review_msg = Message(
                sender="system",
                receiver=self._reviewer.name,
                content={
                    "action": "review",
                    "results": executor_results,
                },
                msg_type="review",
                metadata={"phase": "review"},
            )
            reviewed_think = await self._reviewer.think(review_msg)
            reviewed_actions = await self._reviewer.act(reviewed_think)

            # Extract final result from act() messages
            final_result = None
            for action_msg in reviewed_actions:
                if isinstance(action_msg.content, dict) and action_msg.content.get("action") == "review_complete":
                    final_result = action_msg.content
                    break
            if final_result is None:
                final_result = reviewed_think.content
        else:
            final_result = executor_results[0] if executor_results else None

        return final_result

    async def _execute_single(self, agent: BaseAgent, message: Message) -> Any:
        """Execute tasks on a single agent."""
        response = await agent.think(message)
        actions = await agent.act(response)
        return {
            "agent": agent.name,
            "response": response.content,
            "actions": [a.content for a in actions],
        }

    def _distribute_subtasks(
        self,
        subtasks: List[Dict[str, Any]],
        executors: List[BaseAgent],
    ) -> Dict[BaseAgent, List[Dict[str, Any]]]:
        """Distribute subtasks among executors (round-robin)."""
        assignments = {executor: [] for executor in executors}
        for i, subtask in enumerate(subtasks):
            executor = executors[i % len(executors)]
            subtask["assigned_executor"] = executor.name
            assignments[executor].append(subtask)
        return assignments

    def get_required_roles(self) -> List[AgentRole]:
        """Roles required: Planner (leader), Executor, optionally Reviewer."""
        return [AgentRole.PLANNER, AgentRole.EXECUTOR, AgentRole.REVIEWER]
