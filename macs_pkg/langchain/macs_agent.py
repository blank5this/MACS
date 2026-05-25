"""MACS Agent - LangChain-based Agent with think/act interface.

This module provides MACSReActAgent, a LangChain-powered agent that
preserves the MACS think/act pattern while leveraging LangChain's
agent framework (create_react_agent, tool binding, etc.).

Usage:
    from macs_pkg.langchain.macs_agent import MACSReActAgent

    agent = MACSReActAgent(
        name="assistant",
        llm=chat_model,
        tools=[calc_tool, search_tool],
        system_prompt="You are a helpful assistant.",
    )

    # think + act pattern (MACS native)
    response = await agent.think(message)
    actions = await agent.act(response)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Union
import asyncio

# LangChain imports
_LC_ERROR: Optional[str] = None

try:
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
    from langchain_core.runnables import Runnable, RunnableLambda
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.tools import BaseTool
except (ImportError, OSError) as e:
    create_react_agent = None  # type: ignore
    AgentExecutor = None  # type: ignore
    _LC_ERROR = f"langchain-core: {e}"

if create_react_agent is None:
    import warnings
    warnings.warn(
        f"langchain-core unavailable ({_LC_ERROR}). "
        "MACSReActAgent will not be functional until langchain-core is installed.",
        RuntimeWarning,
    )

from macs_pkg.core.agent import BaseAgent, AgentRole, Message, AgentState
from macs_pkg.llm.base import LLMMessage


class MACSReActAgent:
    """MACS Agent implemented on top of LangChain's ReAct agent.

    Preserves the MACS think/act pattern:
        - think(): Process message and generate response
        - act(): Execute actions (tool calls) from response

    Internally uses LangChain's create_react_agent and AgentExecutor.

    Attributes:
        name: Agent identifier.
        role: Agent role (planner/executor/reviewer/tool).
        state: Current agent state.
    """

    DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant.

You have access to the following tools:
{tool_names}

Follow the ReAct pattern:
- Think step by step about what to do
- Use a tool when needed to get information or perform an action
- After each tool use, observe the result
- Continue until you can provide a complete answer

Always respond with your final answer clearly marked as 'Final Answer: ...'
"""

    def __init__(
        self,
        name: str,
        llm: Runnable,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        role: AgentRole = AgentRole.EXECUTOR,
        verbose: bool = False,
        max_iterations: int = 15,
        max_execution_time: Optional[float] = None,
        **kwargs: Any,
    ):
        """Initialize the MACS LangChain Agent.

        Args:
            name: Agent name for identification.
            llm: LangChain ChatModel or Runnable (e.g., MACSChatModelWrapper).
            tools: List of LangChain tools available to the agent.
            system_prompt: System prompt defining agent behavior.
            role: MACS AgentRole (planner/executor/reviewer/tool).
            verbose: Enable verbose logging of agent thoughts.
            max_iterations: Maximum number of thought-action iterations.
            max_execution_time: Optional timeout in seconds.
            **kwargs: Additional options passed to AgentExecutor.
        """
        self.name = name
        self._llm = llm
        self._tools = tools or []
        self._system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self._role = role
        self._verbose = verbose
        self._max_iterations = max_iterations
        self._max_execution_time = max_execution_time
        self._kwargs = kwargs

        self._state = AgentState.IDLE
        self._agent_executor: Optional[AgentExecutor] = None

    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state

    @property
    def role(self) -> AgentRole:
        """Get agent role."""
        return self._role

    @property
    def system_prompt(self) -> str:
        """Get system prompt."""
        return self._system_prompt

    def _get_tool_names(self) -> str:
        """Get formatted tool names for system prompt."""
        tool_names = []
        for t in self._tools:
            if hasattr(t, "name"):
                tool_names.append(t.name)
            elif hasattr(t, "__name__"):
                tool_names.append(t.__name__)
        return ", ".join(tool_names) if tool_names else "None"

    def _prepare_system_prompt(self) -> str:
        """Prepare system prompt with tool names substituted."""
        tool_names = self._get_tool_names()
        return self._system_prompt.format(tool_names=tool_names)

    def _build_agent_executor(self) -> AgentExecutor:
        """Build the LangChain AgentExecutor.

        Returns:
            Configured AgentExecutor ready to run.
        """
        if create_react_agent is None:
            raise ImportError(
                "langchain.agents is required. Install with: pip install langchain langchain-core"
            )

        # Get chat model
        chat_model = self._llm

        # Get tools
        tools = self._get_tools()

        # Prepare system prompt
        system_message = self._prepare_system_prompt()

        # Create the ReAct agent
        agent = create_react_agent(
            llm=chat_model,
            tools=tools,
            prompt=system_message,
        )

        # Create executor
        executor = AgentExecutor.from_agent(
            agent=agent,
            tools=tools,
            verbose=self._verbose,
            max_iterations=self._max_iterations,
            max_execution_time=self._max_execution_time,
            handle_parsing_errors=True,
            **self._kwargs,
        )

        return executor

    def _ensure_executor(self) -> AgentExecutor:
        """Ensure the agent executor is built."""
        if self._agent_executor is None:
            self._agent_executor = self._build_agent_executor()
        return self._agent_executor

    def _get_tools(self) -> List[BaseTool]:
        """Get list of tools formatted for LangChain agent."""
        return self._tools

    # ─── Think/Act Pattern (MACS Native Interface) ──────────────────────────

    async def think(self, message: Union[str, Message, Dict[str, Any]]) -> Message:
        """Process message and generate response (think phase).

        This corresponds to the "Thought" step in ReAct:
        - Analyze the input
        - Decide if actions are needed
        - Generate response or action plan

        Args:
            message: Input message (string, Message object, or dict).

        Returns:
            Message with response or action plan.
        """
        self._state = AgentState.THINKING

        # Normalize input to string
        if isinstance(message, Message):
            content = message.content
        elif isinstance(message, dict):
            content = message.get("content", str(message))
        else:
            content = str(message)

        try:
            # Run the agent to generate response
            executor = self._ensure_executor()

            # Execute agent in executor
            loop = asyncio.get_event_loop()

            def _sync_run():
                return executor.invoke({"input": content})

            runner = loop.run_in_executor(None, _sync_run)
            result = await asyncio.wait_for(
                runner,
                timeout=self._max_execution_time
            )

            # Extract output
            if isinstance(result, dict):
                output = result.get("output", result.get("result", ""))
            else:
                output = str(result)

            self._state = AgentState.IDLE
            return Message(
                sender=self.name,
                content=str(output),
                msg_type="response",
            )

        except asyncio.TimeoutError:
            self._state = AgentState.IDLE
            return Message(
                sender=self.name,
                content=f"Error: Agent execution timed out after {self._max_execution_time}s",
                msg_type="error",
            )
        except Exception as e:
            self._state = AgentState.IDLE
            return Message(
                sender=self.name,
                content=f"Error: {str(e)}",
                msg_type="error",
            )

    async def act(self, response: Message) -> List[Message]:
        """Execute actions from response (act phase).

        For LangChain ReAct agent, actions are already executed by AgentExecutor.
        This method provides a way to post-process actions if needed.

        Args:
            response: Response from think() containing action plan.

        Returns:
            List of result messages from action execution.
        """
        self._state = AgentState.ACTING

        # In LangChain ReAct, actions are already executed by AgentExecutor
        # This method is provided for compatibility with MACS pattern
        # In most cases, actions are embedded in the response content

        actions = []

        # Check if response contains actions to execute
        if response.content:
            # Parse potential actions from content
            # This is a simplified version - real implementation would need
            # action extraction from specific formats
            pass

        self._state = AgentState.IDLE
        return actions

    async def run(self, input_text: str) -> str:
        """Run the agent on a user input (combined think + act).

        Args:
            input_text: The user query or task.

        Returns:
            The agent's final response as a string.
        """
        response = await self.think(input_text)
        return response.content

    # ─── Tool Management ─────────────────────────────────────────────────────

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent.

        Args:
            tool: A LangChain tool (created via create_langchain_tool).
        """
        self._tools.append(tool)
        self._agent_executor = None  # Reset so it rebuilds

    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the agent.

        Args:
            tool_name: Name of the tool to remove.

        Returns:
            True if tool was found and removed, False otherwise.
        """
        for i, t in enumerate(self._tools):
            t_name = getattr(t, "name", None) or getattr(t, "__name__", "")
            if t_name == tool_name:
                self._tools.pop(i)
                self._agent_executor = None
                return True
        return False

    @property
    def tool_names(self) -> List[str]:
        """Get list of tool names available to this agent."""
        names = []
        for t in self._tools:
            if hasattr(t, "name"):
                names.append(t.name)
            elif hasattr(t, "__name__"):
                names.append(t.__name__)
        return names


class MACSReActAgentFactory:
    """Factory for creating MACSReActAgent instances with common configurations."""

    @staticmethod
    def create_planner(
        name: str = "planner",
        llm: Optional[Runnable] = None,
        tools: Optional[List[BaseTool]] = None,
        **kwargs: Any,
    ) -> MACSReActAgent:
        """Create a planner agent.

        Args:
            name: Agent name.
            llm: LangChain ChatModel.
            tools: Optional tools for planning.
            **kwargs: Additional options.

        Returns:
            Configured planner agent.
        """
        system_prompt = """You are an expert task planner.

Your role is to:
1. Analyze complex tasks and break them into subtasks
2. Identify dependencies between subtasks
3. Estimate complexity and resource requirements
4. Create a clear execution plan

Follow the ReAct pattern for thinking and tool use."""

        return MACSReActAgent(
            name=name,
            llm=llm,
            tools=tools or [],
            system_prompt=system_prompt,
            role=AgentRole.PLANNER,
            **kwargs,
        )

    @staticmethod
    def create_executor(
        name: str = "executor",
        llm: Optional[Runnable] = None,
        tools: Optional[List[BaseTool]] = None,
        **kwargs: Any,
    ) -> MACSReActAgent:
        """Create an executor agent.

        Args:
            name: Agent name.
            llm: LangChain ChatModel.
            tools: Tools for execution.
            **kwargs: Additional options.

        Returns:
            Configured executor agent.
        """
        system_prompt = """You are an expert task executor.

Your role is to:
1. Execute subtasks assigned by the planner
2. Use appropriate tools to complete tasks
3. Report results clearly and concisely
4. Handle errors gracefully and provide feedback

Follow the ReAct pattern for thinking and tool use."""

        return MACSReActAgent(
            name=name,
            llm=llm,
            tools=tools or [],
            system_prompt=system_prompt,
            role=AgentRole.EXECUTOR,
            **kwargs,
        )

    @staticmethod
    def create_reviewer(
        name: str = "reviewer",
        llm: Optional[Runnable] = None,
        tools: Optional[List[BaseTool]] = None,
        **kwargs: Any,
    ) -> MACSReActAgent:
        """Create a reviewer agent.

        Args:
            name: Agent name.
            llm: LangChain ChatModel.
            tools: Optional tools for review.
            **kwargs: Additional options.

        Returns:
            Configured reviewer agent.
        """
        system_prompt = """You are an expert quality reviewer.

Your role is to:
1. Review results from executors
2. Validate quality and completeness
3. Identify issues or areas for improvement
4. Provide constructive feedback and final summary

Follow the ReAct pattern for thinking and tool use."""

        return MACSReActAgent(
            name=name,
            llm=llm,
            tools=tools or [],
            system_prompt=system_prompt,
            role=AgentRole.REVIEWER,
            **kwargs,
        )


# ─── Example usage ───────────────────────────────────────────────────────────

async def example_usage():
    """Example demonstrating MACSReActAgent usage."""
    from macs_pkg.langchain.llm_adapter import MiniMaxChatModel
    from macs_pkg.langchain.tool_adapter import create_langchain_tool
    from macs_pkg.tools import CalculatorTool

    # Create ChatModel
    chat_model = MiniMaxChatModel(
        api_key="your-api-key",
        model="MiniMax-Text-01",
    )

    # Create tools
    calc = CalculatorTool()
    calc_tool = create_langchain_tool(calc, name="calculator")

    # Create agent
    agent = MACSReActAgent(
        name="math_assistant",
        llm=chat_model,
        tools=[calc_tool],
        verbose=True,
    )

    # Use think/act pattern
    print("Thinking...")
    response = await agent.think("What is (25 + 17) * 2?")
    print(f"Response: {response.content}")

    # Or use run() for combined think + act
    result = await agent.run("What is 100 / 4?")
    print(f"Result: {result}")


if __name__ == "__main__":
    print("MACS LangChain Agent - think/act pattern with LangChain")
    print("Usage: MACSReActAgent(name='assistant', llm=chat_model, tools=[...])")