"""LangChain ReAct Agent for MACS — integrates LangChain Agent framework with MACS tools.

This module provides LangChainReActAgent, which uses LangChain's create_react_agent
to build a ReAct (Reasoning + Action) agent that can:
1. Reason about user requests
2. Select and call appropriate tools
3. Process tool results and respond

Key LangChain concepts demonstrated:
- create_react_agent: Factory function to build ReAct agents
- Tool binding: Converting MACS tools to LangChain tools
- AgentExecutor: The runtime that executes the agent's reasoning loop

ReAct Agent Loop:
    Thought → Action → Observation → Thought → Action → ... → Final Answer

Usage:
    from macs_pkg.langchain import LangChainReActAgent, create_langchain_tool
    from macs_pkg.llm import MiniMaxProvider
    from macs_pkg.tools import CalculatorTool

    # 1. Create LLM provider (MiniMax, OpenAI, Claude, etc.)
    provider = MiniMaxProvider(
        api_key="your-api-key",
        model="MiniMax-Text-01"
    )

    # 2. Convert MACS tool to LangChain tool
    calc = CalculatorTool()
    calc_tool = create_langchain_tool(calc, name="calculator", description="Evaluate math expressions")

    # 3. Create ReAct agent with tools
    agent = LangChainReActAgent(
        name="math_assistant",
        llm_provider=provider,
        tools=[calc_tool],
        verbose=True,  # Log agent thought process
    )

    # 4. Run agent on a task
    result = await agent.run("What is (15 + 23) * 3? Show your reasoning.")
    print(result)

    # Example with multiple tools:
    # - calculator: Evaluate mathematical expressions
    # - search: Search for information online
    # - rag_retriever: Query the knowledge base
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union, Callable

# LangChain imports for ReAct agent
# langchain.agents provides the create_react_agent factory
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import BaseTool, tool as langchain_tool

# For creating Chat models from MACS LLM providers
from langchain_openai import ChatOpenAI

from ..llm.base import LLMMessage, LLMProvider
from ..tools.base import BaseTool, FunctionTool, ToolResult

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("langchain_agent")


def create_langchain_tool(
    macs_tool: Union[BaseTool, FunctionTool, Callable],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> BaseTool:
    """Convert a MACS tool to a LangChain tool.

    This function wraps MACS tools (BaseTool, FunctionTool, or plain callables)
    as LangChain tools that can be used with create_react_agent.

    Args:
        macs_tool: A MACS tool instance or callable.
            - BaseTool: Already implements the MACS tool interface
            - FunctionTool: Wraps a function with MACS tool spec
            - Callable: Plain function, will create FunctionTool with defaults
        name: Optional name override for the LangChain tool.
        description: Optional description override.

    Returns:
        A LangChain BaseTool that wraps the MACS tool.

    Example:
        # Using a MACS BaseTool
        from macs_pkg.tools import CalculatorTool
        calc_tool = CalculatorTool()
        lc_tool = create_langchain_tool(calc_tool)

        # Using a plain function
        def my_search(query: str) -> str:
            return f"Results for: {query}"

        search_tool = create_langchain_tool(
            my_search,
            name="web_search",
            description="Search the web for information"
        )
    """
    # Extract tool metadata
    if isinstance(macs_tool, BaseTool):
        tool_name = name or macs_tool.name
        tool_desc = description or macs_tool.description
        tool_func = _create_async_wrapper(macs_tool)
        parameters = _extract_tool_parameters(macs_tool)
    elif isinstance(macs_tool, FunctionTool):
        tool_name = name or macs_tool.spec.name
        tool_desc = description or macs_tool.spec.description
        tool_func = _create_async_wrapper(macs_tool)
        parameters = macs_tool.spec.parameters
    else:
        # It's a plain callable
        tool_name = name or getattr(macs_tool, "__name__", "unnamed_tool")
        tool_desc = description or (macs_tool.__doc__ or "").strip() or f"Tool: {tool_name}"
        tool_func = _create_async_wrapper(macs_tool)
        parameters = []

    # Build parameter list for LangChain @tool decorator
    # LangChain tools use @tool decorator with function signature
    tool_params = {}
    for p in parameters:
        tool_params[p.name] = p.type if p.type in ("string", "number", "boolean", "integer") else "string"

    # Create LangChain tool using the @tool decorator
    # Note: We create the tool with the appropriate signature
    if tool_params:
        # Create tool with parameters from signature
        sig_parts = [f"{p_name}: {p_type}" for p_name, p_type in tool_params.items()]
        sig_str = f"{sig_parts[0]}" if sig_parts else ""
        for s in sig_parts[1:]:
            sig_str += f", {s}"

        # Build a tool function with proper signature
        exec_globals = {"__wrapped__": tool_func, "_tool_func": tool_func}
        exec_locals = {}

        # Create wrapper function with correct signature
        import asyncio

        async def tool_wrapper(**kwargs):
            return await _execute_macs_tool(tool_func, kwargs)

        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = tool_desc

        return langchain_tool(
            name=tool_name,
            description=tool_desc,
        )(tool_wrapper)
    else:
        # No parameters - create simple tool
        async def simple_tool_wrapper():
            """Empty wrapper for tools with no parameters."""
            return await _execute_macs_tool(tool_func, {})

        simple_tool_wrapper.__name__ = tool_name
        simple_tool_wrapper.__doc__ = tool_desc

        return langchain_tool(
            name=tool_name,
            description=tool_desc,
        )(simple_tool_wrapper)


def _create_async_wrapper(tool_or_func: Any) -> Callable:
    """Create an async wrapper for sync or async tools/functions.

    Args:
        tool_or_func: A MACS BaseTool, FunctionTool, or plain callable.

    Returns:
        An async function that executes the tool.
    """
    import asyncio

    if isinstance(tool_or_func, BaseTool):
        async def wrapper(**kwargs):
            result = await tool_or_func.run(**kwargs)
            if isinstance(result, ToolResult):
                if result.success:
                    return str(result.output) if result.output else "Done"
                else:
                    return f"Error: {result.error}"
            return str(result)
        return wrapper
    elif isinstance(tool_or_func, FunctionTool):
        async def wrapper(**kwargs):
            result = await tool_or_func.run(**kwargs)
            if isinstance(result, ToolResult):
                if result.success:
                    return str(result.output) if result.output else "Done"
                else:
                    return f"Error: {result.error}"
            return str(result)
        return wrapper
    elif asyncio.iscoroutinefunction(tool_or_func):
        async def wrapper(**kwargs):
            return await tool_or_func(**kwargs)
        return wrapper
    else:
        async def wrapper(**kwargs):
            return tool_or_func(**kwargs)
        return wrapper


async def _execute_macs_tool(tool_func: Callable, kwargs: Dict[str, Any]) -> str:
    """Execute a MACS tool and convert result to string.

    Args:
        tool_func: The async wrapper function.
        kwargs: Arguments to pass to the tool.

    Returns:
        String representation of tool result.
    """
    import asyncio
    try:
        result = await tool_func(**kwargs)
        if isinstance(result, ToolResult):
            if result.success:
                return str(result.output) if result.output else "Done"
            else:
                return f"Error: {result.error}"
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


def _extract_tool_parameters(tool: BaseTool) -> List:
    """Extract parameter info from a MACS BaseTool spec.

    Args:
        tool: A MACS BaseTool instance.

    Returns:
        List of ToolParameter objects.
    """
    if hasattr(tool, "spec") and hasattr(tool.spec, "parameters"):
        return tool.spec.parameters
    return []


class LangChainReActAgent:
    """A LangChain ReAct Agent that wraps MACS LLM providers and tools.

    This agent uses LangChain's create_react_agent to implement the ReAct
    (Reasoning + Action) pattern, where the agent:

    1. **Thought**: Reasons about what to do next
    2. **Action**: Calls a tool or provides final answer
    3. **Observation**: (via tool result) Receives feedback for next iteration

    The agent loop continues until it produces a final answer.

    Attributes:
        name: Agent identifier.
        llm_provider: MACS LLM provider for generating responses.
        tools: List of LangChain tools available to the agent.
        verbose: Whether to log detailed thought process.

    Example:
        ```python
        from macs_pkg.langchain import LangChainReActAgent, create_langchain_tool
        from macs_pkg.llm import MiniMaxProvider
        from macs_pkg.tools import CalculatorTool

        # Setup
        provider = MiniMaxProvider(api_key="...", model="MiniMax-Text-01")
        calc = CalculatorTool()
        tools = [create_langchain_tool(calc)]

        # Create agent
        agent = LangChainReActAgent(
            name="rechner",  # German for "calculator"
            llm_provider=provider,
            tools=tools,
        )

        # Run task
        result = await agent.run("What is 2 + 2?")
        ```
    """

    def __init__(
        self,
        name: str = "langchain_react_agent",
        llm_provider: Optional[LLMProvider] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4",
        verbose: bool = False,
        max_iterations: int = 15,
        max_execution_time: Optional[float] = None,
    ):
        """Initialize the LangChain ReAct Agent.

        Args:
            name: Agent name for identification.
            llm_provider: MACS LLM provider (OpenAICompatibleProvider, etc.).
                If not provided, will create ChatOpenAI with OPENAI_API_KEY env var.
            tools: List of LangChain tools (created via create_langchain_tool).
            system_prompt: System prompt defining agent behavior.
            model: Model name (used if llm_provider is None).
            verbose: Enable verbose logging of agent thoughts.
            max_iterations: Maximum number of thought-action iterations.
            max_execution_time: Optional timeout in seconds.
        """
        self.name = name
        self._llm_provider = llm_provider
        self._tools = tools or []
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._model = model
        self._verbose = verbose
        self._max_iterations = max_iterations
        self._max_execution_time = max_execution_time
        self._agent_executor: Optional[AgentExecutor] = None
        self._chat_model: Optional[ChatOpenAI] = None

    def _default_system_prompt(self) -> str:
        """Get the default system prompt for ReAct agent.

        Returns:
            System prompt string instructing the agent on ReAct reasoning.
        """
        return """You are a helpful assistant that uses tools to answer questions.

You have access to the following tools:
{tool_names}

Follow the ReAct pattern:
- Think step by step about what to do
- Use a tool when needed to get information or perform an action
- After each tool use, observe the result
- Continue until you can provide a complete answer

Always respond with your final answer clearly marked as 'Final Answer: ...'
"""

    def _get_chat_model(self) -> ChatOpenAI:
        """Get or create a LangChain ChatOpenAI model from MACS provider.

        This converts the MACS LLM provider into a LangChain ChatModel.
        Currently supports OpenAI-compatible providers (MiniMax, DeepSeek, etc.)

        Returns:
            ChatOpenAI instance configured from MACS provider.

        Raises:
            ImportError: If openai package is not installed.
        """
        if self._chat_model is not None:
            return self._chat_model

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required for LangChain integration. "
                "Install with: pip install openai"
            )

        if self._llm_provider is not None:
            # Extract config from MACS provider
            # OpenAICompatibleProvider has _api_key, _base_url, _model attributes
            provider = self._llm_provider

            # Check if it's an OpenAI-compatible provider
            if hasattr(provider, "_api_key") and hasattr(provider, "_base_url"):
                api_key = getattr(provider, "_api_key", None) or ""
                base_url = getattr(provider, "_base_url", "https://api.openai.com/v1")
                model = getattr(provider, "_model", self._model)
            else:
                # Fallback for other provider types
                api_key = ""
                base_url = "https://api.openai.com/v1"
                model = self._model

            self._chat_model = ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=base_url,
                streaming=False,
            )
        else:
            # Use environment variables
            self._chat_model = ChatOpenAI(
                model=self._model,
                streaming=False,
            )

        return self._chat_model

    def _get_tools_for_agent(self) -> List:
        """Get list of tools formatted for LangChain agent.

        Returns:
            List of LangChain tools.
        """
        return self._tools

    def _prepare_tools(self) -> str:
        """Prepare tools and return tool names for system prompt.

        Returns:
            Comma-separated list of tool names.
        """
        tool_names = []
        for t in self._tools:
            if hasattr(t, "name"):
                tool_names.append(t.name)
            elif hasattr(t, "__name__"):
                tool_names.append(t.__name__)
        return ", ".join(tool_names) if tool_names else "None"

    def _build_agent_executor(self) -> AgentExecutor:
        """Build the LangChain AgentExecutor.

        This creates the agent using create_react_agent and wraps it
        in an AgentExecutor that handles the thought-action-observation loop.

        Returns:
            Configured AgentExecutor ready to run.

        Raises:
            ImportError: If langchain.agents is not installed.
        """
        try:
            from langchain.agents import create_react_agent
        except ImportError:
            raise ImportError(
                "langchain.agents required. Install with: pip install langchain langchain-core"
            )

        # Get chat model
        chat_model = self._get_chat_model()

        # Get tools
        tools = self._get_tools_for_agent()

        if not tools:
            logger.warning("No tools provided to LangChainReActAgent")

        # Prepare system prompt with tool names
        tool_names_str = self._prepare_tools()
        system_message = self._system_prompt.format(tool_names=tool_names_str)

        # Create the ReAct agent
        # create_react_agent takes:
        # - llm: The chat model
        # - tools: List of available tools
        # - prompt: System prompt (can be a list of messages or string)
        agent = create_react_agent(
            llm=chat_model,
            tools=tools,
            prompt=system_message,
        )

        # Create executor with configuration
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=self._verbose,
            max_iterations=self._max_iterations,
            max_execution_time=self._max_execution_time,
            handle_parsing_errors=True,
        )

        return executor

    def _ensure_executor(self) -> AgentExecutor:
        """Ensure the agent executor is built.

        Returns:
            The built AgentExecutor.
        """
        if self._agent_executor is None:
            self._agent_executor = self._build_agent_executor()
        return self._agent_executor

    async def run(self, input_text: str) -> str:
        """Run the agent on a user input.

        This executes the full ReAct loop:
        1. Agent thinks about the input
        2. Agent selects and calls a tool (if needed)
        3. Agent observes tool result
        4. Repeat until final answer

        Args:
            input_text: The user query or task.

        Returns:
            The agent's final response as a string.

        Example:
            result = await agent.run("What is the capital of France?")
            print(result)  # "Final Answer: The capital of France is Paris."
        """
        executor = self._ensure_executor()

        # Run the agent (AgentExecutor.invoke is sync but we make it async)
        # LangChain agents are typically sync, but we can run them in a thread
        import asyncio
        import concurrent.futures

        def _sync_run():
            return executor.invoke({"input": input_text})

        loop = asyncio.get_event_loop()
        executor_runner = loop.run_in_executor(None, _sync_run)

        try:
            result = await asyncio.wait_for(executor_runner, timeout=self._max_execution_time)
        except asyncio.TimeoutError:
            return f"Error: Agent execution timed out after {self._max_execution_time}s"
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            return f"Error: {str(e)}"

        # Extract output from result
        if isinstance(result, dict):
            output = result.get("output", "")
            if not output and result.get("result"):
                output = result.get("result", "")
        else:
            output = str(result)

        return output

    async def run_with_history(
        self,
        input_text: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Run agent with conversation history.

        This allows multi-turn conversations where the agent
        remembers previous interactions.

        Args:
            input_text: Current user query.
            chat_history: List of {"role": "user"|"assistant", "content": str}.

        Returns:
            Agent's final response.

        Example:
            history = [
                {"role": "user", "content": "What is 2 + 2?"},
                {"role": "assistant", "content": "Final Answer: 4"},
            ]
            result = await agent.run_with_history("Now multiply by 3", history)
        """
        executor = self._ensure_executor()

        # Build input dict with history
        input_dict: Dict[str, Any] = {"input": input_text}

        if chat_history:
            # Convert to LangChain message format
            lc_messages = []
            for msg in chat_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
            input_dict["chat_history"] = lc_messages

        import asyncio
        import concurrent.futures

        def _sync_run():
            return executor.invoke(input_dict)

        loop = asyncio.get_event_loop()
        executor_runner = loop.run_in_executor(None, _sync_run)

        try:
            result = await asyncio.wait_for(executor_runner, timeout=self._max_execution_time)
        except asyncio.TimeoutError:
            return f"Error: Agent execution timed out after {self._max_execution_time}s"
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            return f"Error: {str(e)}"

        if isinstance(result, dict):
            output = result.get("output", "")
            if not output and result.get("result"):
                output = result.get("result", "")
        else:
            output = str(result)

        return output

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent.

        Call this before running the agent to add new tools.
        If agent is already built, it will be rebuilt on next run.

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


# =============================================================================
# Utility functions for working with MACS tools and LangChain
# =============================================================================

def create_calculator_tool() -> BaseTool:
    """Create a LangChain tool wrapping the MACS CalculatorTool.

    Returns:
        A LangChain tool for evaluating mathematical expressions.
    """
    from ..tools.calculator import CalculatorTool
    calc = CalculatorTool()

    @langchain_tool(name="calculator", description="Evaluate a mathematical expression. Input should be a valid math expression like '2 + 2' or 'sqrt(16) * 3'.")
    def calculator(expression: str) -> str:
        """Evaluate a mathematical expression.

        Args:
            expression: A mathematical expression string.

        Returns:
            The result of the evaluation.
        """
        result = calc.evaluate(expression)
        if result.get("success", False):
            return f"Result: {result['result']}"
        else:
            return f"Error: {result.get('error', 'Unknown error')}"

    return calculator


def create_search_tool(api_key: Optional[str] = None) -> BaseTool:
    """Create a LangChain tool wrapping the MACS SearchTool.

    Args:
        api_key: Optional API key for search service.

    Returns:
        A LangChain tool for searching information.
    """
    from ..tools.search import SearchTool

    search = SearchTool(api_key=api_key)

    @langchain_tool(name="search", description="Search the web for information. Takes a query string and returns search results.")
    async def search_tool(query: str) -> str:
        """Search for information.

        Args:
            query: The search query.

        Returns:
            Search results as a formatted string.
        """
        result = await search.search(query, num_results=5)
        if result.get("results"):
            items = []
            for r in result["results"][:3]:
                items.append(f"- {r.get('title', 'N/A')}: {r.get('snippet', 'N/A')}")
            return "\n".join(items)
        return f"No results found for: {query}"

    return search_tool


def create_rag_tool(rag_module) -> BaseTool:
    """Create a LangChain tool wrapping a RAG retriever.

    Args:
        rag_module: A RAG module with a search(query) method.

    Returns:
        A LangChain tool for querying the knowledge base.
    """
    @langchain_tool(name="rag_retriever", description="Query the knowledge base for relevant documents. Best for questions about company policies, procedures, or documentation.")
    async def rag_retriever(query: str) -> str:
        """Search the knowledge base.

        Args:
            query: The search query.

        Returns:
            Relevant document excerpts.
        """
        try:
            results = await rag_module.search(query)
            if results:
                return "\n---\n".join(str(r) for r in results[:3])
            return "No relevant documents found."
        except Exception as e:
            return f"Error searching knowledge base: {e}"

    return rag_retriever


# =============================================================================
# Example usage
# =============================================================================

async def example_basic():
    """Basic example of using LangChainReActAgent with MACS tools.

    Run with: python -c "asyncio.run(example_basic())"
    """
    from ..llm.openai_compatible import MiniMaxProvider

    # 1. Setup LLM provider
    # Using MiniMax as example - works with any OpenAI-compatible provider
    provider = MiniMaxProvider(
        api_key="your-api-key",
        model="MiniMax-Text-01"
    )

    # 2. Create tools
    # Option A: Create LangChain tool from MACS tool
    calc = CalculatorTool()
    calc_tool = create_langchain_tool(calc, name="calculator", description="Evaluate math expressions")

    # Option B: Use convenience functions
    search_tool = create_search_tool()

    # 3. Create ReAct agent
    agent = LangChainReActAgent(
        name="assistant",
        llm_provider=provider,
        tools=[calc_tool, search_tool],
        verbose=True,
    )

    # 4. Run tasks
    print("Task 1: Simple calculation")
    result1 = await agent.run("What is 25 * 4?")
    print(f"Result: {result1}\n")

    print("Task 2: Multi-step calculation")
    result2 = await agent.run("What is the square root of 144, plus 10?")
    print(f"Result: {result2}\n")


async def example_with_macs_tools():
    """Example using MACS built-in tools with LangChainReActAgent.

    Demonstrates how to integrate the full MACS tool ecosystem.
    """
    from ..llm.openai_compatible import MiniMaxProvider
    from ..tools import (
        CalculatorTool,
        TextFormatterTool,
        FileReaderTool,
    )

    # Setup
    provider = MiniMaxProvider(
        api_key="your-api-key",
        model="MiniMax-Text-01"
    )

    # Convert MACS tools to LangChain tools
    calc_tool = create_langchain_tool(
        CalculatorTool(),
        name="calculator",
        description="Evaluate mathematical expressions"
    )

    formatter_tool = create_langchain_tool(
        TextFormatterTool(),
        name="formatter",
        description="Format and parse text/JSON data"
    )

    # Create agent
    agent = LangChainReActAgent(
        name="multi_tool_assistant",
        llm_provider=provider,
        tools=[calc_tool, formatter_tool],
        verbose=True,
    )

    # Run
    result = await agent.run(
        'Format the number 1234567 as JSON, then calculate its square root.'
    )
    print(result)


if __name__ == "__main__":
    print("LangChainReActAgent for MACS")
    print("=" * 50)
    print("See docstrings for usage examples.")
    print("Run examples with:")
    print("  python -c 'asyncio.run(example_basic())'")
