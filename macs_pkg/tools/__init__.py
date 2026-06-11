"""MACS Tools — reusable, LLM-compatible tool primitives."""

from .base import (
    BaseTool,
    FunctionTool,
    ToolParameter,
    ToolResult,
    TypedToolResult,
    ToolSpec,
    tool,
    SearchResultOutput,
)
from .registry import ToolRegistry, get_default_registry, reset_default_registry
from .builtin import (
    CalculatorTool,
    TextFormatterTool,
    FileReaderTool,
    FileWriterTool,
    HttpGetTool,
    JsonParserTool,
    register_builtin_tools,
    create_default_registry,
)
from .web_search import (
    BaseSearchTool,
    DuckDuckGoSearchTool,
    TavilySearchTool,
    SearchResult,       # backward-compat alias for SearchResultOutput
    SearchResultOutput,
    create_search_tool,
)
from .code_executor import (
    PythonCodeExecutorTool,
    DockerCodeExecutorTool,
)

try:
    from .rag_tool import RAGSearchTool
    _has_rag_tool = True
except ImportError:
    _has_rag_tool = False
    RAGSearchTool = None

__all__ = [
    # Base
    "BaseTool", "FunctionTool", "ToolParameter", "ToolResult",
    "TypedToolResult", "ToolSpec", "SearchResultOutput", "tool",
    # Registry
    "ToolRegistry", "get_default_registry", "reset_default_registry",
    # Builtin tools
    "CalculatorTool", "TextFormatterTool", "FileReaderTool", "FileWriterTool",
    "HttpGetTool", "JsonParserTool",
    "register_builtin_tools", "create_default_registry",
    # Search tools
    "BaseSearchTool", "DuckDuckGoSearchTool", "TavilySearchTool",
    "SearchResult", "SearchResultOutput", "create_search_tool",
    # Code executor
    "PythonCodeExecutorTool", "DockerCodeExecutorTool",
]
if _has_rag_tool:
    __all__.append("RAGSearchTool")
