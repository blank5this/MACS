"""Planner Agent - task decomposition and planning with LLM integration."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import asyncio
import json

from ..core.agent import AgentRole, Message, AgentState
from ..core.react_agent import ReactAgent
from ..core.utils import extract_json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("planner")

if TYPE_CHECKING:
    from ..llm.base import LLMProvider, LLMResponse

# Default system prompt for planner
DEFAULT_SYSTEM_PROMPT = """You are a Planner Agent specialized in task decomposition.

Your responsibilities:
1. Analyze complex tasks and understand requirements
2. Break them down into smaller, manageable subtasks
3. Determine dependencies and execution order
4. Assign appropriate priorities to subtasks
5. Consider potential challenges and edge cases

When decomposing a task:
- Create subtasks that are atomic (single responsibility)
- Assign clear descriptions and acceptance criteria
- Set realistic priorities based on dependencies
- Consider parallel vs sequential execution

Respond in JSON format with your decomposition."""


class PlannerAgent(ReactAgent):
    """Planner Agent for task decomposition and planning.

    Responsibilities:
    - Analyze complex tasks
    - Break them down into smaller subtasks
    - Determine task dependencies
    - Create execution plans
    - Assign subtasks to appropriate agents

    Inherits from :class:`ReactAgent`, which enforces the think→act
    lifecycle. Use ``agent.run(msg)`` for the combined cycle, or call
    ``think()`` and ``act()`` in order — calling ``act()`` first will
    raise ``RuntimeError``.
    """

    def __init__(
        self,
        name: str = "planner",
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        provider: Optional["LLMProvider"] = None,
        enable_llm: bool = True,
    ):
        super().__init__(
            name=name,
            role=AgentRole.PLANNER,
            model=model,
            system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        )
        self._provider = provider
        self._enable_llm = enable_llm and provider is not None
        self._plans: Dict[str, Dict[str, Any]] = {}
        self._current_plan: Optional[Dict[str, Any]] = None

    def set_provider(self, provider: "LLMProvider") -> None:
        """Set the LLM provider for this agent.

        Args:
            provider: LLM provider instance.
        """
        self._provider = provider
        self._enable_llm = True

    async def _think_impl(self, message: Message) -> Message:
        """Process task and create decomposition plan.

        Args:
            message: Incoming message with task details.

        Returns:
            Response message containing subtask decomposition.
        """
        content = message.content

        # Extract task information
        action = content.get("action", "decompose") if isinstance(content, dict) else "decompose"
        task = content.get("task", content) if isinstance(content, dict) else content

        if action == "decompose":
            subtasks = await self._decompose_task(task)
            response_content = {
                "action": "decompose",
                "original_task": task,
                "subtasks": subtasks,
                "plan_id": f"plan_{message.id}",
            }
        elif action == "replan":
            subtasks = await self._replan_task(task, content.get("feedback"))
            response_content = {
                "action": "replan",
                "original_task": task,
                "subtasks": subtasks,
                "plan_id": content.get("plan_id"),
            }
        elif action == "propose":
            # Generate a solution proposal for decentralized mode
            proposal = await self._generate_proposal(task)
            response_content = {
                "action": "propose",
                "proposal": proposal,
                "proposer": self.name,
            }
        elif action == "vote":
            # Vote on a proposal
            vote_result = await self._vote_on_proposal(content.get("proposal"), content.get("proposal_id"))
            response_content = {
                "action": "vote",
                "vote": vote_result,
                "voter": self.name,
            }
        else:
            response_content = {
                "action": "unknown",
                "error": f"Unknown action: {action}",
            }

        return Message(
            sender=self.name,
            receiver=message.sender,
            content=response_content,
            msg_type="result",
            metadata={
                "original_id": message.id,
                "role": self.role.value,
            },
        )

    async def _act_impl(self, response: Message) -> List[Message]:
        """Send subtasks to assigned executors.

        Args:
            response: The response from think phase.

        Returns:
            List of messages to send to executors.
        """
        outgoing = []

        content = response.content
        if content.get("action") == "decompose" and "subtasks" in content:
            subtasks = content["subtasks"]
            executors = content.get("executors", [])

            for i, subtask in enumerate(subtasks):
                # Round-robin assignment
                executor = executors[i % len(executors)] if executors else "*"

                task_msg = Message(
                    sender=self.name,
                    receiver=executor,
                    content={
                        "action": "execute",
                        "subtask": subtask,
                        "task_id": content.get("plan_id"),
                    },
                    msg_type="task",
                    metadata={
                        "parent_id": response.id,
                        "subtask_index": i,
                        "total_subtasks": len(subtasks),
                    },
                )
                outgoing.append(task_msg)

        self.add_to_memory(response)
        return outgoing

    async def _decompose_task_with_llm(self, task: Any) -> List[Dict[str, Any]]:
        """Use LLM to decompose a complex task into subtasks.

        Args:
            task: The task to decompose.

        Returns:
            List of subtask dictionaries.
        """
        if not self._enable_llm or self._provider is None:
            # Fallback to simple decomposition
            return self._decompose_task_simple(task)

        from ..llm.base import LLMMessage

        # Build prompt for task decomposition
        task_desc = task.get("description", str(task)) if isinstance(task, dict) else str(task)

        prompt = f"""Analyze the following task and decompose it into smaller subtasks.

Task: {task_desc}

{"Requirements: " + ", ".join(task.get("requirements", [])) if isinstance(task, dict) and "requirements" in task else ""}

Consider:
1. What are the main components/steps?
2. Are there any dependencies between parts?
3. What can be done in parallel?
4. What are the acceptance criteria for each subtask?

Respond ONLY with a JSON array of subtasks in this format:
[
  {{
    "id": "subtask_1",
    "description": "Clear description of what this subtask does",
    "type": "analysis|execution|synthesis|review",
    "priority": 1-5 (5 being highest),
    "dependencies": ["subtask_id"] (if any),
    "acceptance_criteria": "What defines completion"
  }}
]

Only respond with JSON, no other text."""

        try:
            response = await self._provider.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system=self.system_prompt,
                max_tokens=2048,
                temperature=0.5,
            )

            subtasks = extract_json(response.content)
            if not isinstance(subtasks, list):
                logger.warning("LLM decomposition returned non-list JSON, using simple fallback")
                return self._decompose_task_simple(task)

            # Validate and normalize subtasks
            validated_subtasks = []
            for i, subtask in enumerate(subtasks):
                if isinstance(subtask, dict) and "description" in subtask:
                    validated_subtasks.append({
                        "id": subtask.get("id", f"subtask_{i+1}"),
                        "description": subtask["description"],
                        "type": subtask.get("type", "execution"),
                        "priority": subtask.get("priority", 3),
                        "dependencies": subtask.get("dependencies", []),
                        "acceptance_criteria": subtask.get("acceptance_criteria", ""),
                    })

            if validated_subtasks:
                return validated_subtasks

        except Exception as e:
            # LLM call itself failed (network/timeout/etc.), fallback to simple decomposition
            logger.warning(f"LLM decomposition failed: {e}, using simple fallback")

        return self._decompose_task_simple(task)

    def _decompose_task_simple(self, task: Any) -> List[Dict[str, Any]]:
        """Simple fallback decomposition without LLM.

        Args:
            task: The task to decompose.

        Returns:
            List of subtask dictionaries.
        """
        if isinstance(task, dict):
            task_desc = task.get("description", str(task))
        else:
            task_desc = str(task)

        subtasks = []

        # Heuristic: split long tasks into chunks
        if len(task_desc) > 500:
            # Split into 3 parts for complex tasks
            parts = self._split_task(task_desc, 3)
            for i, part in enumerate(parts):
                subtasks.append({
                    "id": f"subtask_{i + 1}",
                    "description": part,
                    "type": "analysis" if i == 0 else "execution" if i == 1 else "synthesis",
                    "priority": 3 - i,
                    "dependencies": [],
                    "acceptance_criteria": f"Part {i+1} completed",
                })
        elif isinstance(task, list):
            # Each item becomes a subtask
            for i, item in enumerate(task):
                subtasks.append({
                    "id": f"subtask_{i + 1}",
                    "description": str(item),
                    "type": "execution",
                    "priority": 1,
                    "dependencies": [],
                    "acceptance_criteria": f"Item {i+1} completed",
                })
        else:
            # Single task
            subtasks.append({
                "id": "subtask_1",
                "description": task_desc,
                "type": "execution",
                "priority": 1,
                "dependencies": [],
                "acceptance_criteria": "Task completed",
            })

        return subtasks

    async def _decompose_task(self, task: Any) -> List[Dict[str, Any]]:
        """Decompose a complex task into subtasks.

        Uses LLM if available, otherwise falls back to simple decomposition.

        Args:
            task: The task to decompose.

        Returns:
            List of subtask dictionaries.
        """
        if self._enable_llm and self._provider is not None:
            return await self._decompose_task_with_llm(task)
        return self._decompose_task_simple(task)

    def _split_task(self, task_desc: str, num_parts: int) -> List[str]:
        """Split task description into parts."""
        words = task_desc.split()
        part_size = len(words) // num_parts
        parts = []
        for i in range(num_parts):
            start = i * part_size
            end = start + part_size if i < num_parts - 1 else len(words)
            parts.append(" ".join(words[start:end]))
        return parts

    async def _replan_task(self, task: Any, feedback: Any) -> List[Dict[str, Any]]:
        """Create a new plan based on feedback.

        Args:
            task: The original task.
            feedback: Feedback from failed or rejected subtasks.

        Returns:
            New list of subtasks.
        """
        # Incorporate feedback into new plan
        base_subtasks = await self._decompose_task(task)

        if feedback:
            # Add a review subtask at the end
            base_subtasks.append({
                "id": "subtask_review",
                "description": "Review and incorporate feedback",
                "type": "review",
                "priority": 0,
            })

        return base_subtasks

    async def _generate_proposal(self, task: Any) -> Dict[str, Any]:
        """Generate a solution proposal for decentralized collaboration.

        Args:
            task: The task to generate proposal for.

        Returns:
            A proposal dictionary with analysis and recommendations.
        """
        if self._enable_llm and self._provider:
            return await self._generate_proposal_with_llm(task)
        return self._generate_proposal_simple(task)

    async def _generate_proposal_with_llm(self, task: Any) -> Dict[str, Any]:
        """Generate proposal using LLM."""
        from ..llm.base import LLMMessage

        prompt = f"""As a planner agent, analyze the following task and generate a solution proposal.

Task: {task.get('description', task) if isinstance(task, dict) else task}

Requirements:
{chr(10).join(f"- {req}" for req in (task.get('requirements', []) if isinstance(task, dict) else []))}

Provide your proposal in JSON format:
{{
  "title": "Proposal title",
  "summary": "Brief summary of approach",
  "analysis": "Detailed analysis of the task",
  "approach": "Proposed solution approach",
  "risks": ["risk1", "risk2"],
  "timeline": "Estimated timeline",
  "confidence": 0.8
}}

Only respond with JSON."""

        try:
            response = await self._provider.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system=self.system_prompt,
                max_tokens=2048,
                temperature=0.7,
            )
            parsed = extract_json(response.content)
            if isinstance(parsed, dict):
                return parsed
        except Exception as e:
            logger.warning(f"LLM proposal generation failed: {e}, using simple fallback")
        return self._generate_proposal_simple(task)

    def _generate_proposal_simple(self, task: Any) -> Dict[str, Any]:
        """Generate a simple proposal without LLM."""
        task_desc = task.get('description', task) if isinstance(task, dict) else str(task)
        return {
            "title": f"Proposal for: {task_desc[:50]}",
            "summary": f"Analysis and approach for: {task_desc}",
            "analysis": f"Task requires multi-agent collaboration",
            "approach": "Use decentralized协商 with voting",
            "risks": ["coordination overhead", "consensus delays"],
            "timeline": "Depends on complexity",
            "confidence": 0.6,
        }

    async def _vote_on_proposal(self, proposal: Any, proposal_id: str) -> str:
        """Vote on a proposal.

        Args:
            proposal: The proposal to vote on.
            proposal_id: ID of the proposal.

        Returns:
            "approve" or "reject".
        """
        # Simple voting logic - approve if confidence > 0.5
        if isinstance(proposal, dict):
            confidence = proposal.get("confidence", 0.5)
            return "approve" if confidence >= 0.5 else "reject"
        return "approve"

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a stored plan by ID."""
        return self._plans.get(plan_id)

    def store_plan(self, plan_id: str, plan: Dict[str, Any]) -> None:
        """Store a plan for later reference."""
        self._plans[plan_id] = plan
        self._current_plan = plan
