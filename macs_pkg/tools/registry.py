"""Tool registry — central catalog for all registered tools."""

from typing import Any, Dict, List, Optional
from .base import BaseTool, ToolResult


class ToolRegistry:
    """Central registry for MACS tools.

    Provides a single namespace for discovering, registering, and invoking tools.
    Can be used as a global singleton or as an instance per agent/runtime.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register.
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name.

        Returns:
            True if the tool was registered, False otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_specs(self) -> List[Dict[str, Any]]:
        """Return all tool specs as Anthropic-compatible schemas."""
        return [t.spec.to_anthropic_schema() for t in self._tools.values()]

    def get_openai_specs(self) -> List[Dict[str, Any]]:
        """Return all tool specs as OpenAI-compatible function schemas."""
        return [t.spec.to_openai_schema() for t in self._tools.values()]

    async def invoke(self, name: str, **kwargs: Any) -> ToolResult:
        """Invoke a tool by name.

        Args:
            name: Tool name.
            **kwargs: Arguments forwarded to the tool.

        Returns:
            ToolResult.
        """
        tool = self.get(name)
        if tool is None:
            from .base import ToolResult
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool not found: '{name}'. Available: {self.list_tools()}",
            )
        return await tool(**kwargs)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        return f"<ToolRegistry(tools={self.list_tools()})>"


# Global default registry — shared across the process
_default_registry: Optional[ToolRegistry] = None


def get_default_registry() -> ToolRegistry:
    """Get the global default tool registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


def reset_default_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _default_registry
    _default_registry = None
