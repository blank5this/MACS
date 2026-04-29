"""MACS Tools — reusable, LLM-compatible tool primitives."""

from .base import BaseTool, FunctionTool, ToolParameter, ToolResult, ToolSpec, tool
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

try:
    from .rag_tool import RAGSearchTool
    _has_rag_tool = True
except ImportError:
    _has_rag_tool = False
    RAGSearchTool = None

__all__ = [
    "BaseTool", "FunctionTool", "ToolParameter", "ToolResult", "ToolSpec", "tool",
    "ToolRegistry", "get_default_registry", "reset_default_registry",
    "CalculatorTool", "TextFormatterTool", "FileReaderTool", "FileWriterTool",
    "HttpGetTool", "JsonParserTool",
    "register_builtin_tools", "create_default_registry",
]
if _has_rag_tool:
    __all__.append("RAGSearchTool")
