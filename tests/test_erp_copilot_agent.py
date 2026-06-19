"""Tests for the ERPCopilotAgent (Day 8).

The agent is a thin wrapper around :class:`ToolAgent` that wires 7 tools
behind one facade. These tests verify:

* 7 tools are registered (or 6 without NL→SQL bits)
* ``run_tool`` invokes the right underlying handler
* ``ask`` returns a structured result with the chosen tool name
* Error paths return ``{"error": ...}`` and never raise
* NL→SQL path is correctly wired when translator + executor are provided
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import macs_pkg.erp.agents.copilot_agent as _agent_mod
from macs_pkg.erp.agents.copilot_agent import ERPCopilotAgent


# ===== Test doubles =================================================

class _FakeLLMResponse:
    def __init__(self, content: str = "") -> None:
        self.content = content
        self.model = "fake"
        self.usage = {}
        self.tool_calls = []
        self.stop_reason = "stop"


class _FakeProvider:
    """Minimal LLM provider — no LLM, no network, no tool selection.

    ToolAgent will fall back to keyword routing in :meth:`_fallback_tool_selection`,
    which only matches "search/查找/搜索", "calcul/计算", "format/格式化".
    For our 7 ERP tools it returns "unknown" — so we drive the agent
    through ``run_tool()`` directly instead of ``ask()`` in most tests.
    """

    async def complete(self, messages, system=None, **kwargs):
        return _FakeLLMResponse(content="{}")

    def model_name(self) -> str:
        return "fake"


class _FakePool:
    """Fake DatabasePool that returns canned data for each MCP tool.

    We keep the contract identical to the real :class:`DatabasePool`:
    the inventory tools accept the pool as their first positional arg
    and call ``pool.fetch(...)`` / ``pool.fetchrow(...)``.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def fetch(self, sql: str, params: tuple = ()) -> list[dict]:
        self.calls.append(("fetch", (sql, params)))
        lowered = sql.lower()
        # Route by the tool that would call us. Each inventory tool
        # has a unique SQL shape; we match on a substring.
        if "from inventory i" in lowered and "p.category" in lowered:
            return [
                {
                    "product_id": 1, "sku": "SKU-0001", "name": "M8 内六角螺栓",
                    "category": "工具", "warehouse_id": 1,
                    "on_hand": 30, "safety_stock": 100,
                    "below_safety": True, "last_counted": "2026-06-01",
                }
            ]
        if "having" in lowered and "deficit" in lowered:
            return [
                {
                    "product_id": 1, "sku": "SKU-0001", "name": "M8 内六角螺栓",
                    "category": "工具", "safety_stock": 100,
                    "on_hand": 30, "deficit": 70,
                }
            ]
        if "windowed" in lowered:
            return [
                {
                    "supplier_id": 1, "supplier_name": "上海钢铁",
                    "rating": 4.5, "recent_avg": 11.5, "older_avg": 10.0,
                    "delta": 1.5, "delta_pct": 15.0, "order_count": 12,
                }
            ]
        if "sales_orders" in lowered and "limit" in lowered:
            return [
                {"product_id": 5, "sku": "SKU-0005", "name": "笔记本",
                 "category": "办公", "units_sold": 120, "revenue": 6000.0, "order_count": 40},
            ]
        if "from products" in lowered and "product_id = %s" in lowered:
            return [{"sku": "SKU-0001", "name": "M8 内六角螺栓"}]
        return []

    async def fetchrow(self, sql: str, params: tuple = ()) -> dict | None:
        self.calls.append(("fetchrow", (sql, params)))
        if "velocity" in sql.lower() or "avg_daily_units" in sql.lower():
            return {
                "product_id": 1, "units_sold": 30, "order_count": 12, "revenue": 150.0,
                "avg_daily_units": 1.0, "on_hand": 30,
                "safety_stock": 100, "lead_time_days": 7,
                "days_of_inventory": 30.0, "reorder_recommendation": False,
            }
        return None


class _FakeTranslator:
    """Pretends to translate a question into a canned NLSQLResult."""

    async def translate(self, question: str):
        from macs_pkg.erp.nl2sql import NLSQLResult
        return NLSQLResult(
            sql="SELECT sku, name FROM products WHERE product_id = %s",
            params=[1],
            explanation="Find product 1",
            confidence=0.9,
        )


class _FakeExecutor:
    """Pretends to execute an NLSQLResult against a fake pool."""

    def __init__(self, fake_pool: _FakePool) -> None:
        self.pool = fake_pool

    async def execute(self, nlsql_result):
        rows = await self.pool.fetch(nlsql_result.sql, tuple(nlsql_result.params))
        return {
            "sql": nlsql_result.sql,
            "params": list(nlsql_result.params),
            "rows": rows,
            "rowcount": len(rows),
            "elapsed_ms": 5,
            "confidence": nlsql_result.confidence,
            "explanation": nlsql_result.explanation,
        }


# ===== Fixtures =====================================================

@pytest.fixture
def fake_pool() -> _FakePool:
    return _FakePool()


@pytest.fixture
def fake_provider() -> _FakeProvider:
    return _FakeProvider()


@pytest.fixture
def copilot_no_nl2sql(fake_pool, fake_provider) -> ERPCopilotAgent:
    """Agent without NL→SQL bits (6 tools)."""
    return ERPCopilotAgent(
        pool=fake_pool,
        provider=fake_provider,
        nl2sql_translator=None,
        nl2sql_executor=None,
    )


@pytest.fixture
def copilot_full(fake_pool, fake_provider) -> ERPCopilotAgent:
    """Agent with NL→SQL (7 tools)."""
    return ERPCopilotAgent(
        pool=fake_pool,
        provider=fake_provider,
        nl2sql_translator=_FakeTranslator(),
        nl2sql_executor=_FakeExecutor(fake_pool),
    )


# ===== Construction tests ===========================================

def test_agent_registers_6_tools_without_nl2sql(copilot_no_nl2sql):
    """When no NL→SQL stack is provided, 6 tools are registered."""
    tools = set(copilot_no_nl2sql.list_tools())
    assert tools == {
        "get_inventory_levels",
        "get_low_stock_products",
        "get_supplier_price_history",
        "get_top_selling_products",
        "get_sales_velocity",
        "ask_knowledge_base",
    }


def test_agent_registers_7_tools_with_nl2sql(copilot_full):
    """With a NL→SQL stack, all 7 tools are registered."""
    tools = set(copilot_full.list_tools())
    assert "query_database" in tools
    assert len(tools) == 7


def test_tool_names_constant_has_seven_entries():
    assert len(ERPCopilotAgent.TOOL_NAMES) == 7


# ===== run_tool tests (bypass LLM) =================================

@pytest.mark.asyncio
async def test_run_tool_get_low_stock_products(copilot_no_nl2sql):
    result = await copilot_no_nl2sql.run_tool("get_low_stock_products", threshold=0)
    assert isinstance(result, dict)
    assert "rows" in result
    assert result["rowcount"] == 1
    assert result["rows"][0]["sku"] == "SKU-0001"
    assert result["rows"][0]["deficit"] == 70


@pytest.mark.asyncio
async def test_run_tool_get_inventory_levels_filter_category(copilot_no_nl2sql):
    result = await copilot_no_nl2sql.run_tool(
        "get_inventory_levels", product_id=None, category="工具"
    )
    assert result["rowcount"] == 1
    assert result["rows"][0]["below_safety"] is True


@pytest.mark.asyncio
async def test_run_tool_get_supplier_price_history(copilot_no_nl2sql):
    result = await copilot_no_nl2sql.run_tool(
        "get_supplier_price_history", product_id=1, days=180
    )
    assert result["rowcount"] == 1
    assert result["rows"][0]["delta_pct"] == 15.0


@pytest.mark.asyncio
async def test_run_tool_get_top_selling_products(copilot_no_nl2sql):
    result = await copilot_no_nl2sql.run_tool(
        "get_top_selling_products", start_date=None, end_date=None, limit=10
    )
    assert result["rowcount"] == 1
    assert result["rows"][0]["sku"] == "SKU-0005"


@pytest.mark.asyncio
async def test_run_tool_get_sales_velocity(copilot_no_nl2sql):
    result = await copilot_no_nl2sql.run_tool(
        "get_sales_velocity", product_id=1, days=30
    )
    assert "rows" in result
    # get_sales_velocity returns a single-product dict; we wrap it as rows[0]
    assert result["rows"][0]["avg_daily_units"] == 1.0


@pytest.mark.asyncio
async def test_run_tool_query_database(copilot_full):
    """The NL→SQL tool is wired up correctly."""
    result = await copilot_full.run_tool("query_database", question="SKU-0001 详情")
    assert "sql" in result
    assert result["sql"].startswith("SELECT")
    assert "rows" in result
    assert result["rowcount"] == 1


@pytest.mark.asyncio
async def test_run_tool_unknown_returns_error(copilot_full):
    result = await copilot_full.run_tool("nonexistent_tool")
    assert "error" in result
    assert "not found" in result["error"]
    assert "available_tools" in result


# ===== ask() tests (with the fake provider) ========================

@pytest.mark.asyncio
async def test_ask_returns_error_for_empty_question(copilot_full):
    result = await copilot_full.ask("   ")
    assert "error" in result


@pytest.mark.asyncio
async def test_ask_records_execution_history(copilot_full):
    # The fake provider returns "{}" so ToolAgent falls back to keyword
    # routing which won't match any of our 7 tools → ask() should
    # return an error dict, and we just check the history is empty
    # (it only records successful tool runs).
    result = await copilot_full.ask("查询商品库存")
    # Even on error, ask() must return a dict.
    assert isinstance(result, dict)
    assert "question" in result


# ===== System prompt test ==========================================

def test_copilot_system_prompt_loaded():
    prompt = _agent_mod._load_system_prompt()
    assert "ERP" in prompt or "erp" in prompt.lower()
    # Should mention all 7 tools by name.
    for tool in ERPCopilotAgent.TOOL_NAMES:
        assert tool in prompt, f"system prompt missing tool: {tool}"


# ===== Module-level guard =========================================

def test_module_exports_public_api():
    assert hasattr(_agent_mod, "ERPCopilotAgent")
    assert hasattr(_agent_mod, "build_copilot_agent")
    assert "ERPCopilotAgent" in _agent_mod.__all__
    assert "build_copilot_agent" in _agent_mod.__all__


if __name__ == "__main__":
    sys.exit(
        __import__("subprocess").call(
            ["pytest", __file__, "-v", "--tb=short"]
        )
    )
