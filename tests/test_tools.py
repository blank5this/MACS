"""Tests for tools module."""

import pytest
from macs_pkg.tools.base import BaseTool, FunctionTool, ToolParameter, ToolResult, ToolSpec
from macs_pkg.tools.builtin import CalculatorTool, TextFormatterTool
from macs_pkg.tools.web_search import DuckDuckGoSearchTool, SearchResult
from macs_pkg.tools.code_executor import PythonCodeExecutorTool


class TestToolSpec:
    """Tests for ToolSpec."""

    def test_tool_spec_creation(self):
        spec = ToolSpec(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input data",
                ),
            ],
        )

        assert spec.name == "test_tool"
        assert len(spec.parameters) == 1
        assert spec.parameters[0].name == "input"

    def test_tool_spec_to_dict(self):
        spec = ToolSpec(
            name="test",
            description="Test",
            parameters=[],
        )

        d = spec.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "Test"


class TestToolParameter:
    """Tests for ToolParameter."""

    def test_parameter_required(self):
        param = ToolParameter(
            name="required_param",
            type="string",
            description="Required param",
        )
        assert param.required is True

    def test_parameter_optional(self):
        param = ToolParameter(
            name="optional_param",
            type="string",
            description="Optional param",
            required=False,
            default="default_value",
        )
        assert param.required is False
        assert param.default == "default_value"


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_result(self):
        result = ToolResult(
            success=True,
            output="test output",
            metadata={"key": "value"},
        )
        assert result.success is True
        assert result.output == "test output"
        assert result.error is None

    def test_error_result(self):
        result = ToolResult(
            success=False,
            output=None,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"


class TestCalculatorTool:
    """Tests for CalculatorTool."""

    @pytest.fixture
    def tool(self):
        return CalculatorTool()

    def test_spec(self, tool):
        spec = tool.spec
        assert spec.name == "calculator"
        assert "expression" in [p.name for p in spec.parameters]

    @pytest.mark.asyncio
    async def test_basic_arithmetic(self, tool):
        result = await tool.run(expression="2 + 3")
        assert result.success is True
        assert result.output == 5

    @pytest.mark.asyncio
    async def test_complex_expression(self, tool):
        result = await tool.run(expression="(10 + 5) * 2 - 3")
        assert result.success is True
        assert result.output == 27

    @pytest.mark.asyncio
    async def test_division(self, tool):
        result = await tool.run(expression="10 / 2")
        assert result.success is True
        assert result.output == 5.0

    @pytest.mark.asyncio
    async def test_power(self, tool):
        result = await tool.run(expression="2 ** 10")
        assert result.success is True
        assert result.output == 1024

    @pytest.mark.asyncio
    async def test_sqrt(self, tool):
        result = await tool.run(expression="sqrt(16)")
        assert result.success is True
        assert result.output == 4.0

    @pytest.mark.asyncio
    async def test_division_by_zero(self, tool):
        result = await tool.run(expression="1 / 0")
        assert result.success is False
        assert "Division by zero" in result.error

    @pytest.mark.asyncio
    async def test_invalid_expression(self, tool):
        result = await tool.run(expression="invalid ++ syntax")
        assert result.success is False
        assert result.error is not None


class TestTextFormatterTool:
    """Tests for TextFormatterTool."""

    @pytest.fixture
    def tool(self):
        return TextFormatterTool()

    @pytest.mark.asyncio
    async def test_uppercase(self, tool):
        result = await tool.run(text="hello world", operation="upper")
        assert result.success is True
        assert result.output == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_lowercase(self, tool):
        result = await tool.run(text="HELLO", operation="lower")
        assert result.success is True
        assert result.output == "hello"

    @pytest.mark.asyncio
    async def test_title_case(self, tool):
        result = await tool.run(text="hello world", operation="title")
        assert result.success is True
        assert result.output == "Hello World"

    @pytest.mark.asyncio
    async def test_trim(self, tool):
        result = await tool.run(text="  hello  ", operation="strip")
        assert result.success is True
        assert result.output == "hello"

    @pytest.mark.asyncio
    async def test_word_count(self, tool):
        result = await tool.run(text="hello world", operation="word_count")
        assert result.success is True
        assert result.output == 2

    @pytest.mark.asyncio
    async def test_reverse(self, tool):
        result = await tool.run(text="hello", operation="reverse")
        assert result.success is True
        assert result.output == "olleh"


class TestDuckDuckGoSearchTool:
    """Tests for DuckDuckGoSearchTool."""

    @pytest.fixture
    def tool(self):
        return DuckDuckGoSearchTool()

    def test_spec(self, tool):
        spec = tool.spec
        assert spec.name == "web_search"
        assert "query" in [p.name for p in spec.parameters]

    @pytest.mark.asyncio
    async def test_search_returns_results(self, tool):
        # This is a placeholder test - actual search may fail in CI
        result = await tool.run(query="test", num_results=3)
        # Should return results or error, not crash
        assert hasattr(result, "success")
        assert hasattr(result, "output")


class TestPythonCodeExecutorTool:
    """Tests for PythonCodeExecutorTool."""

    @pytest.fixture
    def tool(self):
        return PythonCodeExecutorTool(timeout=10)

    def test_spec(self, tool):
        spec = tool.spec
        assert spec.name == "python_executor"
        assert "code" in [p.name for p in spec.parameters]

    @pytest.mark.asyncio
    async def test_simple_print(self, tool):
        result = await tool.run(code="print('Hello')")
        assert result.success is True
        assert "Hello" in result.output

    @pytest.mark.asyncio
    async def test_math(self, tool):
        result = await tool.run(code="result = 2 + 2\nprint(result)")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_list_comprehension(self, tool):
        code = "squares = [x**2 for x in range(5)]\nprint(squares)"
        result = await tool.run(code=code)
        assert result.success is True
        assert "0" in result.output
        assert "16" in result.output

    @pytest.mark.asyncio
    async def test_json_import(self, tool):
        code = "import json\nprint(json.dumps({'key': 'value'}))"
        result = await tool.run(code=code)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling(self, tool):
        code = "print(undefined_variable)"
        result = await tool.run(code=code)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_timeout(self, tool):
        # Very short timeout
        short_timeout_tool = PythonCodeExecutorTool(timeout=0.1)
        code = "import time; time.sleep(10)"
        result = await short_timeout_tool.run(code=code)
        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_syntax_error(self, tool):
        code = "print("  # Missing closing quote
        result = await tool.run(code=code)
        assert result.success is False
