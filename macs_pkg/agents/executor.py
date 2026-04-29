"""Executor Agent - executes subtasks assigned by planner with LLM integration."""

import asyncio
import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..core.agent import BaseAgent, AgentRole, Message, AgentState

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("executor")

if TYPE_CHECKING:
    from ..llm.base import LLMProvider

# Default system prompt for executor
DEFAULT_SYSTEM_PROMPT = """You are an Executor Agent specialized in executing tasks efficiently.

Your responsibilities:
1. Execute subtasks accurately according to specifications
2. Use appropriate tools when available
3. Validate inputs and outputs
4. Handle errors gracefully with proper error messages
5. Report results clearly and completely

When executing:
- Follow the subtask description precisely
- Use any provided tools
- Validate your work before reporting
- Provide clear, actionable results

Be thorough but efficient. Report both success and any issues encountered."""


class ExecutorAgent(BaseAgent):
    """Executor Agent for running subtasks.

    Responsibilities:
    - Receive subtasks from planner
    - Execute subtasks using available tools and LLM
    - Report results back
    - Handle errors and retries
    """

    def __init__(
        self,
        name: str = "executor",
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        provider: Optional["LLMProvider"] = None,
        max_retries: int = 3,
        enable_llm: bool = True,
    ):
        super().__init__(
            name=name,
            role=AgentRole.EXECUTOR,
            model=model,
            system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        )
        self._provider = provider
        self._enable_llm = enable_llm and provider is not None
        self.max_retries = max_retries
        self._task_results: Dict[str, Any] = {}
        self._tools: Dict[str, callable] = {}

    def set_provider(self, provider: "LLMProvider") -> None:
        """Set the LLM provider for this agent.

        Args:
            provider: LLM provider instance.
        """
        self._provider = provider
        self._enable_llm = True

    def register_tool(self, name: str, tool: callable) -> None:
        """Register a tool for this executor to use.

        Args:
            name: Tool name.
            tool: Callable tool function.
        """
        self._tools[name] = tool

    async def think(self, message: Message) -> Message:
        """Process subtask and prepare for execution.

        Args:
            message: Incoming message with subtask details.

        Returns:
            Response with execution plan.
        """
        self.state = AgentState.THINKING
        content = message.content

        action = content.get("action", "execute") if isinstance(content, dict) else "execute"

        if action == "execute":
            # Handle both "tasks" (list) and "subtask" (single dict) formats
            tasks_content = content.get("tasks") or content.get("subtask") or content
            if isinstance(tasks_content, list) and tasks_content:
                # Use the first task if multiple are provided
                subtask = tasks_content[0] if tasks_content else tasks_content
            else:
                subtask = tasks_content
            execution_plan = self._create_execution_plan(subtask)

            response_content = {
                "action": "ready_to_execute",
                "subtask": subtask,
                "execution_plan": execution_plan,
                "tools_available": list(self._tools.keys()),
            }
        elif action == "propose":
            # Generate execution proposal for decentralized mode
            task = content.get("task", content)
            proposal = self._generate_execution_proposal(task)
            response_content = {
                "action": "propose",
                "proposal": proposal,
                "proposer": self.name,
            }
        elif action == "vote":
            # Vote on a proposal
            vote_result = self._vote_on_proposal(content.get("proposal"))
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

        response = Message(
            sender=self.name,
            receiver=message.sender,
            content=response_content,
            msg_type="result",
            metadata={
                "original_id": message.id,
                "role": self.role.value,
            },
        )

        self.state = AgentState.IDLE
        return response

    async def act(self, response: Message) -> List[Message]:
        """Execute the subtask and report results.

        Args:
            response: The response from think phase.

        Returns:
            List of messages (result to sender).
        """
        self.state = AgentState.ACTING
        outgoing = []

        content = response.content
        if content.get("action") == "ready_to_execute":
            subtask = content.get("subtask", {})
            execution_plan = content.get("execution_plan", [])

            # Execute with retries
            result = None
            last_error = None

            for attempt in range(self.max_retries):
                try:
                    result = await self._execute_subtask(subtask, execution_plan)
                    break
                except Exception as e:
                    last_error = str(e)
                    if attempt == self.max_retries - 1:
                        result = {"error": last_error, "subtask": subtask}

            # Store result
            task_id = subtask.get("id", response.id)
            self._task_results[task_id] = result

            # Create result message
            result_msg = Message(
                sender=self.name,
                receiver=response.sender,
                content={
                    "action": "result",
                    "subtask_id": task_id,
                    "result": result,
                    "success": "error" not in result,
                },
                msg_type="result",
                metadata={
                    "parent_id": response.metadata.get("original_id"),
                    "subtask_index": response.metadata.get("subtask_index"),
                },
            )
            outgoing.append(result_msg)

            # Remember this execution
            if self.has_long_term_memory():
                await self.remember_result(
                    action=f"Executed: {subtask.get('description', '')[:50]}...",
                    result=str(result)[:200],
                    success="error" not in result,
                    task_id=task_id,
                )

        self.add_to_memory(response)
        self.state = AgentState.IDLE
        return outgoing

    def _create_execution_plan(self, subtask: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create an execution plan for a subtask.

        Args:
            subtask: Subtask details.

        Returns:
            List of execution steps.
        """
        plan = []
        task_type = subtask.get("type", "execution")

        if task_type == "analysis":
            plan.append({"step": "analyze_input", "tool": None})
            plan.append({"step": "process_data", "tool": "calculator" if self._tools else None})
        elif task_type == "execution":
            plan.append({"step": "validate_input", "tool": None})
            plan.append({"step": "process", "tool": None})
            plan.append({"step": "validate_output", "tool": None})
        elif task_type == "synthesis":
            plan.append({"step": "collect_inputs", "tool": None})
            plan.append({"step": "combine", "tool": None})
            plan.append({"step": "format_output", "tool": None})
        else:
            plan.append({"step": "execute", "tool": None})

        return plan

    def _generate_execution_proposal(self, task: Any) -> Dict[str, Any]:
        """Generate an execution proposal for decentralized collaboration.

        Args:
            task: The task to generate proposal for.

        Returns:
            A proposal dictionary.
        """
        task_desc = task.get('description', task) if isinstance(task, dict) else str(task)
        return {
            "type": "execution_proposal",
            "task": task_desc,
            "approach": "Execute with available tools and LLM",
            "estimated_duration": "Medium",
            "required_resources": ["executor", "llm"],
            "confidence": 0.7,
        }

    def _vote_on_proposal(self, proposal: Any) -> str:
        """Vote on a proposal.

        Args:
            proposal: The proposal to vote on.

        Returns:
            "approve" or "reject".
        """
        return BaseAgent.vote_on_proposal(proposal)

    async def _execute_subtask_with_llm(
        self,
        subtask: Dict[str, Any],
        execution_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a subtask using LLM for intelligent processing.

        Args:
            subtask: Subtask details.
            execution_plan: Plan steps to execute.

        Returns:
            Execution result.
        """
        if not self._enable_llm or self._provider is None:
            return await self._execute_subtask_simple(subtask, execution_plan)

        from ..llm.base import LLMMessage

        subtask_desc = subtask.get("description", "")
        acceptance_criteria = subtask.get("acceptance_criteria", "")

        prompt = f"""Execute the following subtask according to the plan.

Subtask: {subtask_desc}
{"Acceptance Criteria: " + acceptance_criteria if acceptance_criteria else ""}

Available Tools: {", ".join(self._tools.keys()) if self._tools else "None"}

Steps to execute:
{chr(10).join(f"- {step.get('step')}: {step.get('tool', 'no tool')}" for step in execution_plan)}

Provide your execution results in JSON format:
{{
  "subtask_id": "{subtask.get('id', 'unknown')}",
  "description": "{subtask_desc}",
  "steps": [
    {{"step": "step_name", "input": "...", "output": "...", "tool_used": "tool_name or None"}}
  ],
  "final_output": "The final result of executing this subtask",
  "validation": "How the output meets or fails the acceptance criteria"
}}

Only respond with JSON."""

        try:
            response = await self._provider.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system=self.system_prompt,
                max_tokens=2048,
                temperature=0.5,
            )

            # Parse JSON response
            result_text = response.content.strip() if response.content else ""

            if not result_text:
                raise ValueError("LLM returned empty response")

            # Try to extract JSON from markdown code blocks if present
            json_match = None
            if "```json" in result_text:
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                json_match = result_text[start:end].strip()
            elif "```" in result_text:
                start = result_text.find("```") + 3
                end = result_text.find("```", start)
                json_match = result_text[start:end].strip()
            elif result_text.startswith("{"):
                json_match = result_text

            if json_match:
                result = json.loads(json_match)
                return result

            # Response is not valid JSON, treat as text output
            return {
                "subtask_id": subtask.get("id"),
                "description": subtask.get("description"),
                "steps": [],
                "final_output": result_text,
                "validation": "Output from LLM (non-JSON response)",
            }

        except (json.JSONDecodeError, ValueError, Exception) as e:
            logger.warning(f"LLM execution failed: {e}, using simple fallback")
            return await self._execute_subtask_simple(subtask, execution_plan)

    async def _execute_subtask_simple(
        self,
        subtask: Dict[str, Any],
        execution_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Simple fallback execution without LLM.

        Args:
            subtask: Subtask details.
            execution_plan: Plan steps to execute.

        Returns:
            Execution result.
        """
        results = []
        current_input = subtask.get("description", "")

        for step in execution_plan:
            step_name = step.get("step")
            tool_name = step.get("tool")

            # Execute tool if specified and available
            if tool_name and tool_name in self._tools:
                tool = self._tools[tool_name]
                if asyncio.iscoroutinefunction(tool):
                    current_input = await tool(current_input)
                else:
                    current_input = tool(current_input)
            else:
                # Simulate processing
                await asyncio.sleep(0.01)
                current_input = f"Processed: {current_input}"

            results.append({
                "step": step_name,
                "input": current_input,
                "output": current_input,
                "tool_used": tool_name,
            })

        return {
            "subtask_id": subtask.get("id"),
            "description": subtask.get("description"),
            "steps": results,
            "final_output": current_input,
        }

    async def _execute_subtask(
        self,
        subtask: Dict[str, Any],
        execution_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a subtask according to the plan.

        Uses LLM if available for intelligent execution.

        Args:
            subtask: Subtask details.
            execution_plan: Plan steps to execute.

        Returns:
            Execution result.
        """
        if self._enable_llm and self._provider is not None:
            return await self._execute_subtask_with_llm(subtask, execution_plan)
        return await self._execute_subtask_simple(subtask, execution_plan)

    def get_result(self, task_id: str) -> Optional[Any]:
        """Get a stored result by task ID."""
        return self._task_results.get(task_id)

    def get_all_results(self) -> Dict[str, Any]:
        """Get all stored results."""
        return self._task_results.copy()
