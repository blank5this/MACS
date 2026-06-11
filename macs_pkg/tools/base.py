"""Base classes for MACS tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
import asyncio
import inspect

try:
    from pydantic import BaseModel, Field, ValidationError
    _HAS_PYDANTIC = True
except ImportError:
    BaseModel = None  # type: ignore[assignment, unused-ignore]
    ValidationError = None  # type: ignore[assignment, unused-ignore]
    _HAS_PYDANTIC = False


T = TypeVar("T", bound="SearchResultOutput")


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas for structured tool outputs
# ─────────────────────────────────────────────────────────────────────────────


class SearchResultOutput(BaseModel if _HAS_PYDANTIC else object):
    """Pydantic schema for a single search result.

    Provides strict field validation and automatic serialization.
    Used by DuckDuckGoSearchTool, TavilySearchTool, RAG tools, etc.
    """
    if _HAS_PYDANTIC:
        url: str = Field(description="URL of the source")
        title: str = Field(description="Title of the result")
        snippet: str = Field(default="", description="Relevant excerpt or snippet")
        source: str = Field(default="", description="Source engine name (e.g. DuckDuckGo)")
        score: Optional[float] = Field(
            default=None,
            description="Relevance score (0.0–1.0), if available"
        )

        def to_citation_dict(self) -> Dict[str, Any]:
            """Return a dict suitable for CitationTracker.track()."""
            return {
                "url": self.url,
                "title": self.title,
                "snippet": self.snippet,
            }
    else:
        # Minimal fallback when pydantic unavailable
        url: str = ""
        title: str = ""
        snippet: str = ""
        source: str = ""
        score: Optional[float] = None

        def __init__(self, **data: Any) -> None:
            for k, v in data.items():
                setattr(self, k, v)

        def to_citation_dict(self) -> Dict[str, Any]:
            return {"url": self.url, "title": self.title, "snippet": self.snippet}


# ─────────────────────────────────────────────────────────────────────────────
# Typed tool result
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ToolResult:
    """Structured result returned by a tool."""
    success: bool
    output: Any = None          # Primary output (str, dict, None)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class TypedToolResult:
    """Tool result with a typed `items` field for structured outputs.

    Args:
        success: Whether the tool executed successfully.
        items: List of structured output objects (e.g. SearchResultOutput).
               Use this instead of `output` when the tool returns typed records.
        error: Error message if success=False.
        metadata: Additional context (query, count, latency_ms, etc.).
    """
    success: bool
    items: List[Any] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def output(self) -> Any:
        """Alias for backward compatibility: returns items as a formatted string."""
        if not self.items:
            return None
        if all(isinstance(it, SearchResultOutput) for it in self.items):
            return "\n".join(
                f"[{i+1}] {it.title}\n   URL: {it.url}\n   {it.snippet}"
                for i, it in enumerate(self.items)
            )
        return str(self.items)

    def to_tool_result(self) -> ToolResult:
        """Convert to legacy ToolResult for backward compatibility."""
        return ToolResult(
            success=self.success,
            output=self.output,
            error=self.error,
            metadata=self.metadata,
        )

    @classmethod
    def from_search_results(
        cls,
        results: List[SearchResultOutput],
        *,
        query: str = "",
        error: Optional[str] = None,
    ) -> "TypedToolResult":
        """Factory: build from a list of SearchResultOutput."""
        return cls(
            success=error is None and len(results) >= 0,
            items=results,
            error=error,
            metadata={"query": query, "count": len(results)},
        )

    def first(self: "TypedToolResult") -> Optional[Any]:
        """Return the first item, or None."""
        return self.items[0] if self.items else None


# ─────────────────────────────────────────────────────────────────────────────
# ToolParameter / ToolSpec — unchanged
# ─────────────────────────────────────────────────────────────────────────────


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                }
                for p in self.parameters
            ],
        }

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


# ─────────────────────────────────────────────────────────────────────────────
# BaseTool
# ─────────────────────────────────────────────────────────────────────────────


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
            Consider returning TypedToolResult for structured outputs.
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
    """Wraps an existing function (sync or async) as a MACS tool."""

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
    """Decorator to convert a function into a FunctionTool."""
    def decorator(func: Callable) -> FunctionTool:
        return FunctionTool(
            func,
            name=name or func.__name__,
            description=description or (func.__doc__ or "").strip(),
            parameters=parameters or [],
        )
    return decorator
