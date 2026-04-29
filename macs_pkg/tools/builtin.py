"""Built-in tools for MACS.

Provides ready-to-use tools for common operations:
- calculator: evaluate math expressions
- text_formatter: format / transform text
- file_reader: read text files from the local filesystem
- file_writer: write text to files
- http_get: perform a simple HTTP GET request
- json_parser: parse and query JSON data
"""

from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseTool, FunctionTool, ToolParameter, ToolResult, ToolSpec
from .registry import ToolRegistry


# ──────────────────────────────────────────────────────────────────────────────
# 1. Calculator
# ──────────────────────────────────────────────────────────────────────────────

class CalculatorTool(BaseTool):
    """Safe arithmetic expression evaluator.

    Supports: +, -, *, /, **, %, abs, round, sqrt, and common math constants.
    """

    _SAFE_NAMES = {
        name: getattr(math, name)
        for name in dir(math)
        if not name.startswith("_")
    }
    _SAFE_NAMES.update({"abs": abs, "round": round})

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="calculator",
            description="Evaluate a safe arithmetic expression. Supports +,-,*,/,**,%,sqrt,abs,round and math constants.",
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Math expression to evaluate (e.g. '2 ** 10', 'sqrt(16) + 3')",
                )
            ],
        )

    async def run(self, expression: str) -> ToolResult:  # type: ignore[override]
        try:
            result = eval(  # noqa: S307
                expression,
                {"__builtins__": {}},
                self._SAFE_NAMES,
            )
            return ToolResult(success=True, output=result, metadata={"expression": expression})
        except ZeroDivisionError:
            return ToolResult(success=False, output=None, error="Division by zero")
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Evaluation error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 2. Text Formatter
# ──────────────────────────────────────────────────────────────────────────────

class TextFormatterTool(BaseTool):
    """Transform text using common formatting operations."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="text_formatter",
            description="Transform text: uppercase, lowercase, title case, strip, split by lines, or count words/chars.",
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="The input text to transform.",
                ),
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to apply.",
                    enum=["upper", "lower", "title", "strip", "lines", "word_count", "char_count", "reverse"],
                ),
            ],
        )

    async def run(self, text: str, operation: str = "strip") -> ToolResult:  # type: ignore[override]
        ops = {
            "upper": text.upper,
            "lower": text.lower,
            "title": text.title,
            "strip": text.strip,
            "lines": lambda: text.splitlines(),
            "word_count": lambda: len(text.split()),
            "char_count": lambda: len(text),
            "reverse": lambda: text[::-1],
        }
        fn = ops.get(operation)
        if fn is None:
            return ToolResult(success=False, output=None, error=f"Unknown operation: {operation}")
        result = fn()
        return ToolResult(success=True, output=result)


# ──────────────────────────────────────────────────────────────────────────────
# 3. File Reader
# ──────────────────────────────────────────────────────────────────────────────

class FileReaderTool(BaseTool):
    """Read text content from a local file."""

    def __init__(self, allowed_dir: Optional[str] = None):
        """
        Args:
            allowed_dir: If set, restrict reads to this directory tree for safety.
        """
        self._allowed_dir = Path(allowed_dir).resolve() if allowed_dir else None

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_reader",
            description="Read text from a local file. Returns the file content as a string.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Absolute or relative path to the file.",
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8).",
                    required=False,
                    default="utf-8",
                ),
            ],
        )

    async def run(self, path: str, encoding: str = "utf-8") -> ToolResult:  # type: ignore[override]
        resolved = Path(path).resolve()

        if self._allowed_dir and not str(resolved).startswith(str(self._allowed_dir)):
            return ToolResult(success=False, output=None, error=f"Access denied: path outside allowed directory")

        if not resolved.exists():
            return ToolResult(success=False, output=None, error=f"File not found: {path}")

        if not resolved.is_file():
            return ToolResult(success=False, output=None, error=f"Not a file: {path}")

        try:
            content = resolved.read_text(encoding=encoding)
            return ToolResult(
                success=True,
                output=content,
                metadata={"path": str(resolved), "size_bytes": resolved.stat().st_size},
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 4. File Writer
# ──────────────────────────────────────────────────────────────────────────────

class FileWriterTool(BaseTool):
    """Write text content to a local file."""

    def __init__(self, allowed_dir: Optional[str] = None):
        self._allowed_dir = Path(allowed_dir).resolve() if allowed_dir else None

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_writer",
            description="Write text to a local file. Creates parent directories if needed.",
            parameters=[
                ToolParameter(name="path", type="string", description="Path to write to."),
                ToolParameter(name="content", type="string", description="Text content to write."),
                ToolParameter(
                    name="mode",
                    type="string",
                    description="Write mode: 'write' (overwrite) or 'append'.",
                    required=False,
                    default="write",
                    enum=["write", "append"],
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8).",
                    required=False,
                    default="utf-8",
                ),
            ],
        )

    async def run(  # type: ignore[override]
        self,
        path: str,
        content: str,
        mode: str = "write",
        encoding: str = "utf-8",
    ) -> ToolResult:
        resolved = Path(path).resolve()

        if self._allowed_dir and not str(resolved).startswith(str(self._allowed_dir)):
            return ToolResult(success=False, output=None, error="Access denied: path outside allowed directory")

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            open_mode = "w" if mode == "write" else "a"
            resolved.open(open_mode, encoding=encoding).write(content)
            return ToolResult(
                success=True,
                output=str(resolved),
                metadata={"bytes_written": len(content.encode(encoding))},
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 5. HTTP GET
# ──────────────────────────────────────────────────────────────────────────────

class HttpGetTool(BaseTool):
    """Perform an HTTP GET request and return the response body."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="http_get",
            description="Perform an HTTP GET request and return the response text or JSON.",
            parameters=[
                ToolParameter(name="url", type="string", description="URL to fetch."),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Request timeout in seconds (default: 10).",
                    required=False,
                    default=10,
                ),
                ToolParameter(
                    name="as_json",
                    type="boolean",
                    description="Parse response as JSON if True (default: False).",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def run(self, url: str, timeout: float = 10.0, as_json: bool = False) -> ToolResult:  # type: ignore[override]
        try:
            import urllib.request
            import urllib.error

            def _fetch() -> str:
                with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
                    return resp.read().decode("utf-8", errors="replace")

            body = await asyncio.get_event_loop().run_in_executor(None, _fetch)

            output: Any = json.loads(body) if as_json else body
            return ToolResult(success=True, output=output, metadata={"url": url})

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 6. JSON Parser / Query
# ──────────────────────────────────────────────────────────────────────────────

class JsonParserTool(BaseTool):
    """Parse JSON strings and extract values by dot-path."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="json_parser",
            description=(
                "Parse a JSON string and optionally extract a value by dot-path "
                "(e.g. 'data.items.0.name')."
            ),
            parameters=[
                ToolParameter(name="json_string", type="string", description="Valid JSON string to parse."),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Dot-separated path to extract (e.g. 'user.address.city'). Leave empty for full object.",
                    required=False,
                    default="",
                ),
            ],
        )

    async def run(self, json_string: str, path: str = "") -> ToolResult:  # type: ignore[override]
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            return ToolResult(success=False, output=None, error=f"Invalid JSON: {e}")

        if not path:
            return ToolResult(success=True, output=data)

        current: Any = data
        for key in path.split("."):
            try:
                if isinstance(current, list):
                    current = current[int(key)]
                elif isinstance(current, dict):
                    current = current[key]
                else:
                    return ToolResult(success=False, output=None, error=f"Cannot traverse into {type(current).__name__} at key '{key}'")
            except (KeyError, IndexError, ValueError) as e:
                return ToolResult(success=False, output=None, error=f"Path error at '{key}': {e}")

        return ToolResult(success=True, output=current)


# ──────────────────────────────────────────────────────────────────────────────
# Factory: register all built-ins into a registry
# ──────────────────────────────────────────────────────────────────────────────

def register_builtin_tools(
    registry: ToolRegistry,
    allowed_dir: Optional[str] = None,
) -> None:
    """Register all built-in tools into a ToolRegistry.

    Args:
        registry: Target registry.
        allowed_dir: Optional directory restriction for file tools.
    """
    registry.register(CalculatorTool())
    registry.register(TextFormatterTool())
    registry.register(FileReaderTool(allowed_dir=allowed_dir))
    registry.register(FileWriterTool(allowed_dir=allowed_dir))
    registry.register(HttpGetTool())
    registry.register(JsonParserTool())


def create_default_registry(allowed_dir: Optional[str] = None) -> ToolRegistry:
    """Create a ToolRegistry pre-loaded with all built-in tools.

    Args:
        allowed_dir: Optional directory restriction for file tools.

    Returns:
        Populated ToolRegistry.
    """
    registry = ToolRegistry()
    register_builtin_tools(registry, allowed_dir=allowed_dir)
    return registry
