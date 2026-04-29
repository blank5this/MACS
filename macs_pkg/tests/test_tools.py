"""Tests for macs_pkg.tools module."""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path

from macs_pkg.tools import (
    ToolResult, ToolParameter, ToolSpec, FunctionTool, tool,
    ToolRegistry, create_default_registry,
    CalculatorTool, TextFormatterTool, FileReaderTool, FileWriterTool,
    JsonParserTool,
)


# ──────────────────────────────────────────────────────────────────────────────
# ToolSpec
# ──────────────────────────────────────────────────────────────────────────────

class TestToolSpec:
    def test_openai_schema(self):
        spec = ToolSpec(
            name="add",
            description="Add two numbers",
            parameters=[
                ToolParameter("a", "number", "First number"),
                ToolParameter("b", "number", "Second number"),
            ],
        )
        schema = spec.to_openai_schema()
        assert schema["name"] == "add"
        assert "a" in schema["parameters"]["properties"]
        assert "b" in schema["parameters"]["required"]

    def test_anthropic_schema(self):
        spec = ToolSpec(name="ping", description="Ping")
        schema = spec.to_anthropic_schema()
        assert "input_schema" in schema
        assert schema["name"] == "ping"


# ──────────────────────────────────────────────────────────────────────────────
# FunctionTool / @tool decorator
# ──────────────────────────────────────────────────────────────────────────────

class TestFunctionTool:
    @pytest.mark.asyncio
    async def test_sync_function(self):
        def double(x: int) -> int:
            return x * 2

        t = FunctionTool(double, name="double", description="Double a number")
        result = await t(x=5)
        assert result.success is True
        assert result.output == 10

    @pytest.mark.asyncio
    async def test_async_function(self):
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        t = FunctionTool(greet, name="greet")
        result = await t(name="Alice")
        assert result.success is True
        assert result.output == "Hello, Alice!"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        def boom(x: int) -> int:
            raise ValueError("Boom!")

        t = FunctionTool(boom)
        result = await t(x=1)
        assert result.success is False
        assert "Boom!" in result.error

    def test_decorator(self):
        @tool(name="inc", description="Increment")
        def inc(n: int) -> int:
            return n + 1

        assert isinstance(inc, FunctionTool)
        assert inc.name == "inc"


# ──────────────────────────────────────────────────────────────────────────────
# ToolRegistry
# ──────────────────────────────────────────────────────────────────────────────

class TestToolRegistry:
    def test_register_and_list(self):
        r = ToolRegistry()
        r.register(CalculatorTool())
        assert "calculator" in r
        assert "calculator" in r.list_tools()

    def test_unregister(self):
        r = ToolRegistry()
        r.register(CalculatorTool())
        assert r.unregister("calculator") is True
        assert "calculator" not in r

    @pytest.mark.asyncio
    async def test_invoke(self):
        r = ToolRegistry()
        r.register(CalculatorTool())
        result = await r.invoke("calculator", expression="2 + 2")
        assert result.success is True
        assert result.output == 4

    @pytest.mark.asyncio
    async def test_invoke_unknown_tool(self):
        r = ToolRegistry()
        result = await r.invoke("nonexistent")
        assert result.success is False

    def test_get_specs(self):
        r = create_default_registry()
        specs = r.get_specs()
        names = [s["name"] for s in specs]
        assert "calculator" in names
        assert "json_parser" in names


# ──────────────────────────────────────────────────────────────────────────────
# Built-in tools
# ──────────────────────────────────────────────────────────────────────────────

class TestCalculatorTool:
    @pytest.mark.asyncio
    async def test_basic_arithmetic(self):
        t = CalculatorTool()
        r = await t(expression="3 * 7")
        assert r.success and r.output == 21

    @pytest.mark.asyncio
    async def test_sqrt(self):
        t = CalculatorTool()
        r = await t(expression="sqrt(81)")
        assert r.success and r.output == 9.0

    @pytest.mark.asyncio
    async def test_division_by_zero(self):
        t = CalculatorTool()
        r = await t(expression="1/0")
        assert r.success is False
        assert "zero" in r.error.lower()


class TestTextFormatterTool:
    @pytest.mark.asyncio
    async def test_upper(self):
        t = TextFormatterTool()
        r = await t(text="hello", operation="upper")
        assert r.output == "HELLO"

    @pytest.mark.asyncio
    async def test_word_count(self):
        t = TextFormatterTool()
        r = await t(text="one two three", operation="word_count")
        assert r.output == 3

    @pytest.mark.asyncio
    async def test_unknown_operation(self):
        t = TextFormatterTool()
        r = await t(text="test", operation="invalid_op")
        assert r.success is False


class TestFileTools:
    @pytest.mark.asyncio
    async def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = FileWriterTool(allowed_dir=tmpdir)
            reader = FileReaderTool(allowed_dir=tmpdir)
            path = str(Path(tmpdir) / "test.txt")

            w_result = await writer(path=path, content="Hello MACS!")
            assert w_result.success is True

            r_result = await reader(path=path)
            assert r_result.success is True
            assert r_result.output == "Hello MACS!"

    @pytest.mark.asyncio
    async def test_read_nonexistent(self):
        t = FileReaderTool()
        r = await t(path="/nonexistent/path/file.txt")
        assert r.success is False


class TestJsonParserTool:
    @pytest.mark.asyncio
    async def test_parse_full(self):
        t = JsonParserTool()
        r = await t(json_string='{"key": "value"}')
        assert r.success and r.output == {"key": "value"}

    @pytest.mark.asyncio
    async def test_path_extraction(self):
        t = JsonParserTool()
        r = await t(json_string='{"a": {"b": 42}}', path="a.b")
        assert r.success and r.output == 42

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        t = JsonParserTool()
        r = await t(json_string="not json")
        assert r.success is False

    @pytest.mark.asyncio
    async def test_array_index(self):
        t = JsonParserTool()
        r = await t(json_string='[10, 20, 30]', path="1")
        assert r.success and r.output == 20
