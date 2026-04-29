"""Base classes for MACS tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import asyncio
import inspect


@dataclass
class ToolParameter:
    """Describes a single parameter for a tool."""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None


@dataclass
class ToolSpec:
    """Specification (metadata) for a tool — enables LLM function-calling."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)

    def to_openai_schema(self) -> Dict[str, Any]:
        """Export as OpenAI-style function schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Export as Anthropic tool schema (for Claude API tool use)."""
        schema = self.to_openai_schema()
        return {
            "name": schema["name"],
            "description": schema["description"],
            "input_schema": schema["parameters"],
        }


@dataclass
class ToolResult:
    """Structured result returned by a tool."""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseTool(ABC):
    """Abstract base class for all MACS tools.

    Tools are reusable, testable units of capability that agents can invoke.
    Each tool has a name, description, and executes a single responsibility.
    """

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:
        """Return the tool's specification."""
        pass

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments.

        Args:
            **kwargs: Arguments matching the tool's ToolSpec parameters.

        Returns:
            ToolResult with success/error information.
        """
        pass

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def description(self) -> str:
        return self.spec.description

    async def __call__(self, **kwargs: Any) -> ToolResult:
        """Allow tool to be called like a function."""
        try:
            return await self.run(**kwargs)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def __repr__(self) -> str:
        return f"<Tool(name={self.name})>"


class FunctionTool(BaseTool):
    """Wraps an existing function (sync or async) as a MACS tool.

    Allows registering any callable as a tool without subclassing.
    """

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[List[ToolParameter]] = None,
    ):
        self._func = func
        self._spec = ToolSpec(
            name=name or func.__name__,
            description=description or (func.__doc__ or "").strip(),
            parameters=parameters or [],
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    async def run(self, **kwargs: Any) -> ToolResult:
        try:
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func(**kwargs)
            else:
                result = self._func(**kwargs)

            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, output=result)

        except TypeError as e:
            return ToolResult(success=False, output=None, error=f"Invalid arguments: {e}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[List[ToolParameter]] = None,
):
    """Decorator to convert a function into a FunctionTool.

    Usage:
        @tool(description="Add two numbers together")
        def add(a: int, b: int) -> int:
            return a + b
    """
    def decorator(func: Callable) -> FunctionTool:
        return FunctionTool(
            func,
            name=name or func.__name__,
            description=description or (func.__doc__ or "").strip(),
            parameters=parameters or [],
        )
    return decorator
