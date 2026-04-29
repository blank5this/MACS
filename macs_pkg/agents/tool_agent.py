"""Tool Agent - executes specific tools and returns results."""

import json
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
import asyncio

from ..core.agent import BaseAgent, AgentRole, Message, AgentState

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("tool_agent")

if TYPE_CHECKING:
    from ..llm.base import LLMProvider


class ToolAgent(BaseAgent):
    """Tool Agent for executing specific tools and utilities.

    Responsibilities:
    - Execute specific tools/functions
    - Return structured results
    - Handle tool errors gracefully
    - Provide tool metadata
    """

    def __init__(
        self,
        name: str = "tool_agent",
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        provider: Optional["LLMProvider"] = None,
        enable_llm: bool = True,
    ):
        super().__init__(
            name=name,
            role=AgentRole.TOOL,
            model=model,
            system_prompt=system_prompt,
        )
        self._provider = provider
        self._enable_llm = enable_llm and provider is not None
        self._tool_registry: Dict[str, Callable] = {}
        self._execution_history: List[Dict[str, Any]] = []

    def set_provider(self, provider: "LLMProvider") -> None:
        """Set the LLM provider for this agent.

        Args:
            provider: LLM provider instance.
        """
        self._provider = provider
        self._enable_llm = True

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool function.

        Args:
            name: Tool name.
            func: Tool function (sync or async).
        """
        self._tool_registry[name] = func

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name.

        Returns:
            True if tool was registered, False otherwise.
        """
        if name in self._tool_registry:
            del self._tool_registry[name]
            return True
        return False

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tool_registry.keys())

    async def think(self, message: Message) -> Message:
        """Process tool request and prepare for execution.

        Args:
            message: Incoming message with tool request.

        Returns:
            Response with execution plan.
        """
        self.state = AgentState.THINKING
        content = message.content

        action = content.get("action", "execute_tool") if isinstance(content, dict) else "execute_tool"

        if action == "execute_tool":
            # LLM-enhanced tool selection
            if self._enable_llm and self._provider:
                tool_name, tool_args = await self._llm_select_tool(content)
            else:
                tool_name = content.get("tool")
                tool_args = content.get("args", {})

            if tool_name not in self._tool_registry:
                response_content = {
                    "action": "error",
                    "error": f"Tool not found: {tool_name}",
                    "available_tools": self.list_tools(),
                }
            else:
                response_content = {
                    "action": "ready_to_execute",
                    "tool": tool_name,
                    "args": tool_args,
                }

        elif action == "list_tools":
            response_content = {
                "action": "tools_list",
                "tools": self.list_tools(),
            }

        elif action == "describe_tool":
            tool_name = content.get("tool")
            if tool_name in self._tool_registry:
                response_content = {
                    "action": "tool_description",
                    "tool": tool_name,
                    "description": self._get_tool_description(tool_name),
                }
            else:
                response_content = {
                    "action": "error",
                    "error": f"Tool not found: {tool_name}",
                }

        elif action == "propose":
            # Generate tool-based proposal for decentralized mode
            task = content.get("task", content)
            proposal = self._generate_tool_proposal(task)
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
        """Execute tools and return results.

        Args:
            response: The response from think phase.

        Returns:
            List of messages (execution results).
        """
        self.state = AgentState.ACTING
        outgoing = []

        content = response.content
        if content.get("action") == "ready_to_execute":
            tool_name = content.get("tool")
            tool_args = content.get("args", {})

            # Execute tool
            result = await self._execute_tool(tool_name, tool_args)

            # Record execution
            self._execution_history.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
                "success": "error" not in result,
            })

            # Create result message
            result_msg = Message(
                sender=self.name,
                receiver=message.sender,
                content={
                    "action": "tool_result",
                    "tool": tool_name,
                    "result": result,
                    "success": "error" not in result,
                },
                msg_type="result",
                metadata={
                    "parent_id": response.metadata.get("original_id"),
                },
            )
            outgoing.append(result_msg)

        self.add_to_memory(response)
        self.state = AgentState.IDLE
        return outgoing

    async def _execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a tool function.

        Args:
            tool_name: Name of the tool.
            args: Arguments to pass to the tool.

        Returns:
            Execution result.
        """
        if tool_name not in self._tool_registry:
            return {"error": f"Tool not found: {tool_name}"}

        tool = self._tool_registry[tool_name]

        try:
            # Execute based on whether it's async or sync
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**args)
            else:
                result = tool(**args)

            # Wrap result in dict if not already
            if not isinstance(result, dict):
                result = {"output": result}

            return result

        except TypeError as e:
            # Argument mismatch
            return {
                "error": f"Invalid arguments for tool {tool_name}: {e}",
                "tool": tool_name,
            }
        except Exception as e:
            # Other errors
            return {
                "error": f"Tool execution failed: {e}",
                "tool": tool_name,
            }

    def _get_tool_description(self, tool_name: str) -> str:
        """Get description of a tool.

        Args:
            tool_name: Name of the tool.

        Returns:
            Tool description.
        """
        tool = self._tool_registry.get(tool_name)
        if tool:
            doc = tool.__doc__
            return doc.strip() if doc else f"Tool: {tool_name}"
        return "Unknown tool"

    def get_execution_history(
        self,
        limit: Optional[int] = None,
        tool_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get tool execution history.

        Args:
            limit: Maximum number of entries to return.
            tool_name: Filter by specific tool.

        Returns:
            List of execution records.
        """
        history = self._execution_history

        if tool_name:
            history = [h for h in history if h["tool"] == tool_name]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()

    async def _llm_select_tool(self, content: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Use LLM to intelligently select and configure a tool.

        Args:
            content: Message content with task description.

        Returns:
            Tuple of (tool_name, tool_args).
        """
        from ..llm.base import LLMMessage

        task_desc = content.get("description", content.get("task", ""))
        available_tools = self.list_tools()
        tool_descriptions = {name: self._get_tool_description(name) for name in available_tools}

        prompt = f"""Based on the user's request, select the most appropriate tool and its arguments.

User Request: {task_desc}

Available Tools:
{json.dumps(tool_descriptions, indent=2, ensure_ascii=False)}

Respond with JSON:
{{
  "selected_tool": "tool_name",
  "arguments": {{"arg1": "value1", "arg2": "value2"}}
}}

Only respond with JSON."""

        try:
            response = await self._provider.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system=self.system_prompt,
                max_tokens=1024,
                temperature=0.3,
            )

            result_text = response.content.strip()
            if "```json" in result_text:
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
            elif "```" in result_text:
                start = result_text.find("```") + 3
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()

            if result_text.startswith("{"):
                result = json.loads(result_text)
                return result.get("selected_tool", "unknown"), result.get("arguments", {})

        except Exception as e:
            logger.warning(f"LLM tool selection failed: {e}")

        # Fallback: try to find tool by keyword matching
        return self._fallback_tool_selection(task_desc)

    def _fallback_tool_selection(self, task_desc: str) -> tuple[str, Dict[str, Any]]:
        """Fallback tool selection based on keywords.

        Args:
            task_desc: Task description.

        Returns:
            Tuple of (tool_name, tool_args).
        """
        task_lower = task_desc.lower()

        # Keyword to tool mapping
        if "search" in task_lower or "查找" in task_lower or "搜索" in task_lower:
            return "search", {"query": task_desc}
        elif "calcul" in task_lower or "计算" in task_lower:
            return "calculator", {"expression": task_desc}
        elif "format" in task_lower or "格式化" in task_lower:
            return "formatter", {"data": task_desc, "format_type": "json"}

        # Default to first available tool
        available = self.list_tools()
        if available:
            return available[0], {}
        return "unknown", {}

    def _generate_tool_proposal(self, task: Any) -> Dict[str, Any]:
        """Generate a proposal for decentralized collaboration.

        Args:
            task: The task to generate proposal for.

        Returns:
            A proposal dictionary.
        """
        task_desc = task.get('description', task) if isinstance(task, dict) else str(task)
        available_tools = self.list_tools()
        return {
            "type": "tool_proposal",
            "task": task_desc,
            "approach": f"Use tools: {', '.join(available_tools) if available_tools else 'none'}",
            "available_tools": available_tools,
            "confidence": 0.8,
        }

    def _vote_on_proposal(self, proposal: Any) -> str:
        """Vote on a proposal.

        Args:
            proposal: The proposal to vote on.

        Returns:
            "approve" or "reject".
        """
        return BaseAgent.vote_on_proposal(proposal)


# Convenience function to create tool agents with common tools
def create_tool_agent_with_defaults(
    name: str = "tool_agent",
    include_builtin: bool = True,
) -> ToolAgent:
    """Create a Tool Agent with default tools registered.

    Args:
        name: Agent name.
        include_builtin: Whether to include built-in tools.

    Returns:
        Configured ToolAgent instance.
    """
    agent = ToolAgent(name=name)

    if include_builtin:
        # Register some basic tools
        async def search(query: str) -> Dict[str, Any]:
            """Search the web for information."""
            # Placeholder - in production, integrate with search API
            return {"query": query, "results": [], "message": "Search not implemented"}

        async def calculator(expression: str) -> Dict[str, Any]:
            """Evaluate a mathematical expression."""
            try:
                # WARNING: eval can be dangerous, use safe_eval in production
                result = eval(expression, {"__builtins__": {}}, {})  # Safe eval
                return {"expression": expression, "result": result}
            except Exception as e:
                return {"expression": expression, "error": str(e)}

        async def formatter(data: Any, format_type: str = "json") -> Dict[str, Any]:
            """Format data into specified type."""
            import json
            try:
                if format_type == "json":
                    return {"formatted": json.dumps(data, indent=2)}
                else:
                    return {"formatted": str(data)}
            except Exception as e:
                return {"error": str(e)}

        agent.register_tool("search", search)
        agent.register_tool("calculator", calculator)
        agent.register_tool("formatter", formatter)

    return agent
