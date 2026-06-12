"""Tests for the ERP MCP tool layer (5 read-only tools + server wiring).

Markers
-------
* ``@pytest.mark.integration`` — requires live Postgres. The MCP server
  tests are still run without DB by passing a dummy pool; only the
  tool-invocation tests need real data.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from macs_pkg.erp.db import (  # noqa: E402
    DatabaseConfig,
    DatabasePool,
    apply_schema,
    drop_schema,
    seed_database,
)
from macs_pkg.erp.tools import (  # noqa: E402
    build_erp_mcp_server,
    list_tool_names,
)
from macs_pkg.erp.tools.inventory_tools import (  # noqa: E402
    get_inventory_levels,
    get_low_stock_products,
    get_sales_velocity,
    get_supplier_price_history,
    get_top_selling_products,
)


pytestmark = pytest.mark.integration


# ===== Fixtures =====================================================

@pytest.fixture
async def seeded_pool():
    """Fresh DB pool with the medium seed loaded."""
    pool = DatabasePool(DatabaseConfig.from_env())
    await pool.open()
    await drop_schema(pool)
    await apply_schema(pool)
    await seed_database(pool, scale="medium")
    yield pool
    await pool.close()


# ===== Tool function tests =========================================

@pytest.mark.asyncio
async def test_get_inventory_levels_returns_all_rows(seeded_pool):
    rows = await get_inventory_levels(seeded_pool)
    # 20 products x 3 warehouses = 60 rows
    assert len(rows) == 60
    assert all("below_safety" in r for r in rows)
    assert all(r["warehouse_id"] in (1, 2, 3) for r in rows)


@pytest.mark.asyncio
async def test_get_inventory_levels_filter_by_category(seeded_pool):
    rows = await get_inventory_levels(seeded_pool, category="工具")
    # 4 tools products × 3 warehouses
    assert len(rows) == 12
    assert all(r["category"] == "工具" for r in rows)


@pytest.mark.asyncio
async def test_get_inventory_levels_filter_by_product(seeded_pool):
    rows = await get_inventory_levels(seeded_pool, product_id=1)
    assert len(rows) == 3  # 3 warehouses
    assert all(r["product_id"] == 1 for r in rows)


@pytest.mark.asyncio
async def test_get_low_stock_products_finds_demo_items(seeded_pool):
    rows = await get_low_stock_products(seeded_pool, threshold=0)
    # SKU-0003, SKU-0004, SKU-0015, SKU-0018 are intentionally seeded low
    skus = {r["sku"] for r in rows}
    assert "SKU-0015" in skus or "SKU-0003" in skus
    # All returned rows have positive deficit (below safety_stock)
    assert all(r["deficit"] > 0 for r in rows)
    # Ordered by deficit DESC
    deficits = [r["deficit"] for r in rows]
    assert deficits == sorted(deficits, reverse=True)


@pytest.mark.asyncio
async def test_get_supplier_price_history_returns_suppliers(seeded_pool):
    rows = await get_supplier_price_history(seeded_pool, product_id=1, days=180)
    # product_id=1 should have multiple suppliers
    assert len(rows) >= 1
    # Each row has the trend fields
    for r in rows:
        assert "supplier_name" in r
        assert "recent_avg" in r
        assert "older_avg" in r
        assert "delta" in r
        assert "delta_pct" in r
        assert "order_count" in r
    # Ordered by delta DESC
    deltas = [r["delta"] or 0 for r in rows]
    assert deltas == sorted(deltas, reverse=True)


@pytest.mark.asyncio
async def test_get_top_selling_products_orders_by_units(seeded_pool):
    rows = await get_top_selling_products(seeded_pool, limit=5)
    assert len(rows) == 5
    qty = [r["units_sold"] for r in rows]
    assert qty == sorted(qty, reverse=True)
    # All rows have revenue and order_count
    for r in rows:
        assert r["revenue"] >= 0
        assert r["order_count"] >= 1


@pytest.mark.asyncio
async def test_get_top_selling_products_with_date_range(seeded_pool):
    today = date.today().isoformat()
    rows = await get_top_selling_products(
        seeded_pool, start_date="2020-01-01", end_date=today, limit=10
    )
    assert 1 <= len(rows) <= 10


@pytest.mark.asyncio
async def test_get_sales_velocity_returns_metrics(seeded_pool):
    result = await get_sales_velocity(seeded_pool, product_id=1, days=30)
    assert "units_sold" in result
    assert "avg_daily_units" in result
    assert "days_of_inventory" in result
    assert "reorder_recommendation" in result
    assert "on_hand" in result
    assert "lead_time_days" in result


@pytest.mark.asyncio
async def test_get_sales_velocity_unknown_product(seeded_pool):
    result = await get_sales_velocity(seeded_pool, product_id=99999, days=30)
    assert "error" in result


# ===== MCP server tests ============================================

def test_list_tool_names_returns_five():
    names = list_tool_names()
    assert names == [
        "get_inventory_levels",
        "get_low_stock_products",
        "get_supplier_price_history",
        "get_top_selling_products",
        "get_sales_velocity",
    ]


def test_build_erp_mcp_server_registers_five_tools(seeded_pool):
    server = build_erp_mcp_server(pool=seeded_pool)
    tools = server.list_tools()
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == set(list_tool_names())


def test_tools_have_descriptions_and_input_schemas(seeded_pool):
    server = build_erp_mcp_server(pool=seeded_pool)
    for t in server.list_tools():
        assert t.description, f"Tool {t.name} has empty description"
        assert t.inputSchema is not None
        assert t.inputSchema.get("type") == "object"
        assert "properties" in t.inputSchema


@pytest.mark.asyncio
async def test_server_can_dispatch_tool_call(seeded_pool):
    """End-to-end: build server, dispatch a tool call via the internal handler."""
    server = build_erp_mcp_server(pool=seeded_pool)
    result = await server._handle_tool_call(
        "get_low_stock_products", {"threshold": 0}
    )
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all("sku" in r for r in result)


@pytest.mark.asyncio
async def test_server_rejects_unknown_tool(seeded_pool):
    server = build_erp_mcp_server(pool=seeded_pool)
    with pytest.raises(ValueError, match="Tool not found"):
        await server._handle_tool_call("nonexistent_tool", {})


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=short"]))
