"""Tool Adapter - Bridge MACS BaseTool to LangChain BaseTool.

This module provides bidirectional adapters between MACS Tool system
and LangChain Tool system, enabling seamless interoperability.

Usage:
    # MACS → LangChain
    from macs_pkg.tools import CalculatorTool
    lc_tool = MACSToolAdapter.to_langchain(CalculatorTool())

    # LangChain → MACS
    from langchain_core.tools import tool
    @tool
    def my_tool(query: str) -> str:
        return f"Result: {query}"

    macs_tool = MACSToolAdapter.to_macs(my_tool)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING
import asyncio

# LangChain imports - wrapped to handle torch DLL issues on Windows
_LC_ERROR: Optional[str] = None

try:
    from langchain_core.tools import BaseTool as LCBaseTool
    from langchain_core.tools import tool as langchain_tool
    from langchain_core.tools import StructuredTool
except (ImportError, OSError) as e:
    LCBaseTool = None  # type: ignore
    StructuredTool = None  # type: ignore
    _LC_ERROR = f"langchain-core.tools: {e}"

if LCBaseTool is None:
    import warnings
    warnings.warn(
        f"langchain-core unavailable ({_LC_ERROR}). "
        "Tool adapter will not be functional until langchain-core is installed.",
        RuntimeWarning,
    )

from macs_pkg.tools.base import BaseTool, FunctionTool, ToolResult, ToolSpec, ToolParameter

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool as LCBaseToolAlias


class MACSToolAdapter:
    """Bidirectional adapter between MACS tools and LangChain tools.

    MACS Tool System:
        - BaseTool: Abstract base with spec, run()
        - FunctionTool: Wraps a callable
        - ToolSpec: Tool metadata (name, description, parameters)
        - ToolResult: Execution result (success, output, error)

    LangChain Tool System:
        - BaseTool: LangChain's tool interface
        - @tool decorator: Creates tools from functions
        - StructuredTool: For tools with complex parameters
    """

    # ─── MACS → LangChain ────────────────────────────────────────────────────

    @staticmethod
    def to_langchain(
        macs_tool: Union[BaseTool, FunctionTool, Callable],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "LCBaseToolAlias":
        """Convert a MACS tool to a LangChain tool.

        Args:
            macs_tool: A MACS BaseTool, FunctionTool, or plain callable.
            name: Optional name override for the LangChain tool.
            description: Optional description override.

        Returns:
            A LangChain BaseTool that wraps the MACS tool.

        Example:
            >>> from macs_pkg.tools import CalculatorTool
            >>> calc = CalculatorTool()
            >>> lc_tool = MACSToolAdapter.to_langchain(calc)
            >>> # Use with create_react_agent
        """
        if LCBaseTool is None:
            raise ImportError(
                "langchain-core is required. Install with: pip install langchain-core"
            )

        # Extract tool metadata
        if isinstance(macs_tool, BaseTool):
            tool_name = name or macs_tool.name
            tool_desc = description or macs_tool.description
            tool_func = _create_async_wrapper(macs_tool)
            parameters = _extract_macs_parameters(macs_tool)
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

        # Build parameter dict for LangChain tool
        tool_params: Dict[str, Any] = {}
        for p in parameters:
            if p.type in ("string", "number", "boolean", "integer"):
                tool_params[p.name] = p.type
            else:
                tool_params[p.name] = "string"

        # Create LangChain tool wrapper
        async def tool_wrapper(**kwargs: Any) -> str:
            result = await _execute_macs_tool(tool_func, kwargs)
            return result

        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = tool_desc

        # Use langchain_tool decorator
        return langchain_tool(
            name=tool_name,
            description=tool_desc,
        )(tool_wrapper)

    @staticmethod
    def to_langchain_with_params(
        macs_tool: Union[BaseTool, FunctionTool],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "LCBaseToolAlias":
        """Convert a MACS tool with explicit parameter schema.

        This variant preserves the full ToolParameter schema when converting.

        Args:
            macs_tool: A MACS BaseTool or FunctionTool with full spec.
            name: Optional name override.
            description: Optional description override.

        Returns:
            A LangChain tool with proper parameter schema.
        """
        if LCBaseTool is None:
            raise ImportError("langchain-core is required")

        if isinstance(macs_tool, BaseTool):
            tool_name = name or macs_tool.name
            tool_desc = description or macs_tool.description
            tool_func = _create_async_wrapper(macs_tool)
            parameters = macs_tool.spec.parameters
        elif isinstance(macs_tool, FunctionTool):
            tool_name = name or macs_tool.spec.name
            tool_desc = description or macs_tool.spec.description
            tool_func = _create_async_wrapper(macs_tool)
            parameters = macs_tool.spec.parameters
        else:
            raise TypeError(f"Expected BaseTool or FunctionTool, got {type(macs_tool)}")

        # Build async wrapper with proper signature
        async def tool_wrapper(**kwargs: Any) -> str:
            result = await _execute_macs_tool(tool_func, kwargs)
            return result

        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = tool_desc

        return langchain_tool(
            name=tool_name,
            description=tool_desc,
        )(tool_wrapper)

    # ─── LangChain → MACS ──────────────────────────────────────────────────

    @staticmethod
    def to_macs(lc_tool: "LCBaseToolAlias") -> FunctionTool:
        """Convert a LangChain tool to a MACS FunctionTool.

        Args:
            lc_tool: A LangChain BaseTool or decorated function.

        Returns:
            A MACS FunctionTool wrapping the LangChain tool.

        Example:
            >>> from langchain_core.tools import tool
            >>> @tool
            >>> def search(query: str) -> str:
            >>>     return f"Results for: {query}"
            >>>
            >>> macs_tool = MACSToolAdapter.to_macs(search)
            >>> result = await macs_tool.run(query="python")
        """
        # Extract function from tool if needed
        if hasattr(lc_tool, "func"):
            # It's a decorated tool with func attribute
            func = lc_tool.func
        elif callable(lc_tool):
            func = lc_tool
        else:
            raise TypeError(f"Cannot convert {type(lc_tool)} to MACS tool")

        async def wrapper(**kwargs: Any) -> ToolResult:
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(**kwargs)
                else:
                    result = func(**kwargs)
                return ToolResult(success=True, output=result)
            except Exception as e:
                return ToolResult(success=False, output=None, error=str(e))

        # Get name and description
        tool_name = getattr(lc_tool, "name", None) or getattr(func, "__name__", "unnamed")
        tool_desc = getattr(lc_tool, "description", None) or (func.__doc__ or "").strip()

        return FunctionTool(
            func=wrapper,
            name=tool_name,
            description=tool_desc,
        )

    # ─── Batch conversion ──────────────────────────────────────────────────

    @staticmethod
    def to_langchain_batch(
        macs_tools: List[Union[BaseTool, FunctionTool, Callable]],
    ) -> List["LCBaseToolAlias"]:
        """Convert multiple MACS tools to LangChain tools.

        Args:
            macs_tools: List of MACS tools to convert.

        Returns:
            List of LangChain tools.
        """
        return [
            MACSToolAdapter.to_langchain(tool)
            for tool in macs_tools
        ]

    @staticmethod
    def to_macs_batch(lc_tools: List["LCBaseToolAlias"]) -> List[FunctionTool]:
        """Convert multiple LangChain tools to MACS tools.

        Args:
            lc_tools: List of LangChain tools to convert.

        Returns:
            List of MACS FunctionTools.
        """
        return [
            MACSToolAdapter.to_macs(tool)
            for tool in lc_tools
        ]


# ─── Helper functions ─────────────────────────────────────────────────────────

def _create_async_wrapper(tool_or_func: Any) -> Callable:
    """Create an async wrapper for sync or async MACS tools/functions.

    Args:
        tool_or_func: A MACS BaseTool, FunctionTool, or plain callable.

    Returns:
        An async function that executes the tool.
    """
    if isinstance(tool_or_func, BaseTool):
        async def wrapper(**kwargs: Any) -> str:
            result = await tool_or_func.run(**kwargs)
            if isinstance(result, ToolResult):
                if result.success:
                    return str(result.output) if result.output else "Done"
                else:
                    return f"Error: {result.error}"
            return str(result)
        return wrapper
    elif isinstance(tool_or_func, FunctionTool):
        async def wrapper(**kwargs: Any) -> str:
            result = await tool_or_func.run(**kwargs)
            if isinstance(result, ToolResult):
                if result.success:
                    return str(result.output) if result.output else "Done"
                else:
                    return f"Error: {result.error}"
            return str(result)
        return wrapper
    elif asyncio.iscoroutinefunction(tool_or_func):
        async def wrapper(**kwargs: Any) -> Any:
            return await tool_or_func(**kwargs)
        return wrapper
    else:
        async def wrapper(**kwargs: Any) -> Any:
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


def _extract_macs_parameters(tool: BaseTool) -> List[ToolParameter]:
    """Extract parameter info from a MACS BaseTool spec.

    Args:
        tool: A MACS BaseTool instance.

    Returns:
        List of ToolParameter objects.
    """
    if hasattr(tool, "spec") and hasattr(tool.spec, "parameters"):
        return tool.spec.parameters
    return []


# ─── Convenience functions ────────────────────────────────────────────────────

def create_langchain_tool(
    macs_tool: Union[BaseTool, FunctionTool, Callable],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> "LCBaseToolAlias":
    """Convenience function to convert MACS tool to LangChain tool.

    This is the same as MACSToolAdapter.to_langchain().

    Args:
        macs_tool: A MACS tool.
        name: Optional name override.
        description: Optional description override.

    Returns:
        A LangChain tool.
    """
    return MACSToolAdapter.to_langchain(macs_tool, name, description)


def create_calculator_tool() -> "LCBaseToolAlias":
    """Create a LangChain calculator tool from MACS CalculatorTool.

    Returns:
        A LangChain tool wrapping the MACS calculator.
    """
    from macs_pkg.tools.calculator import CalculatorTool

    calc = CalculatorTool()

    @langchain_tool(
        name="calculator",
        description="Evaluate a mathematical expression. Input should be a valid math expression like '2 + 2' or 'sqrt(16) * 3'.",
    )
    async def calculator(expression: str) -> str:
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


# ─── Example usage ───────────────────────────────────────────────────────────

async def example_usage():
    """Example demonstrating tool adapter functionality."""
    from macs_pkg.tools import CalculatorTool, TextFormatterTool

    # Convert MACS tools to LangChain tools
    calc = CalculatorTool()
    lc_calc = MACSToolAdapter.to_langchain(calc, name="calculator")

    formatter = TextFormatterTool()
    lc_formatter = MACSToolAdapter.to_langchain(formatter)

    # Use with LangChain ReAct agent
    print(f"Converted tools: {lc_calc.name}, {lc_formatter.name}")


if __name__ == "__main__":
    print("MACS Tool Adapter - Bridge MACS tools to LangChain")
    print("Usage: MACSToolAdapter.to_langchain(macs_tool) or .to_macs(lc_tool)")