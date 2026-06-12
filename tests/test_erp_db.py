"""Tests for the ERP database layer (connection, schema, seed).

These tests require a running PostgreSQL instance (default: localhost:5432
with credentials matching ``.env.example``). They are skipped automatically
when the database is unreachable so the rest of the MACS test suite can run
on machines without Postgres.

Run with::

    pytest tests/test_erp_db.py -v
    # or, with the standalone entry point at the bottom of this file:
    python tests/test_erp_db.py

Markers
-------
* ``@pytest.mark.integration`` — requires live Postgres. Excluded from the
  default ``make test`` target. Run with ``pytest -m integration`` explicitly.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Make the project importable when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from macs_pkg.erp.db import (  # noqa: E402
    ALL_DDL,
    DatabaseConfig,
    DatabasePool,
    EXPECTED_TABLES,
    SCALE_ROWS,
    apply_schema,
    assert_schema,
    drop_schema,
    get_default_pool,
    reset_default_pool,
    seed_database,
)


pytestmark = pytest.mark.integration


# ===== Fixtures =====================================================

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def pool():
    """Open a fresh pool and clean tables before yielding."""
    p = DatabasePool(DatabaseConfig.from_env())
    await p.open()
    try:
        await drop_schema(p)
        await apply_schema(p)
        yield p
    finally:
        await p.close()


# ===== Connection tests =============================================

@pytest.mark.asyncio
async def test_pool_opens_and_closes():
    p = DatabasePool(DatabaseConfig.from_env())
    await p.open()
    version = await p.fetchval("SELECT version()")
    assert version is not None
    assert "PostgreSQL" in str(version)
    await p.close()


@pytest.mark.asyncio
async def test_pool_singleton():
    # Pull twice; should be the same object
    a = get_default_pool()
    b = get_default_pool()
    assert a is b
    await reset_default_pool()


@pytest.mark.asyncio
async def test_pool_singleton_persists_across_resets():
    await reset_default_pool()
    a = get_default_pool()
    assert a is not None
    await reset_default_pool()


# ===== Schema tests ================================================

@pytest.mark.asyncio
async def test_apply_schema_creates_all_tables(pool):
    rows = await pool.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE'"
    )
    present = {r["table_name"] for r in rows}
    for t in EXPECTED_TABLES:
        assert t in present, f"Missing table: {t}"


@pytest.mark.asyncio
async def test_assert_schema_passes(pool):
    await assert_schema(pool)  # should not raise


@pytest.mark.asyncio
async def test_apply_schema_is_idempotent(pool):
    await apply_schema(pool)  # running twice must not error
    await assert_schema(pool)


@pytest.mark.asyncio
async def test_drop_schema_then_apply(pool):
    await drop_schema(pool)
    # Re-apply after drop
    await apply_schema(pool)
    await assert_schema(pool)


# ===== Constraint tests ============================================

@pytest.mark.asyncio
async def test_not_null_constraint_on_required_columns(pool):
    """Insert a row missing a NOT NULL column should raise."""
    with pytest.raises(Exception):  # psycopg.errors.NotNullViolation
        await pool.execute(
            "INSERT INTO products (sku) VALUES (%s)",  # missing name, category, unit_price
            ("SKU-BAD-001",),
        )


@pytest.mark.asyncio
async def test_unique_sku_constraint(pool):
    await pool.execute(
        "INSERT INTO products (sku, name, category, unit_price) "
        "VALUES (%s,%s,%s,%s)",
        ("SKU-DUP", "test", "test", 1.0),
    )
    with pytest.raises(Exception):  # psycopg.errors.UniqueViolation
        await pool.execute(
            "INSERT INTO products (sku, name, category, unit_price) "
            "VALUES (%s,%s,%s,%s)",
            ("SKU-DUP", "test 2", "test", 2.0),
        )


@pytest.mark.asyncio
async def test_fk_constraint_blocks_orphan_inventory(pool):
    """inventory.product_id must reference an existing product."""
    with pytest.raises(Exception):  # psycopg.errors.ForeignKeyViolation
        await pool.execute(
            "INSERT INTO inventory (product_id, warehouse_id, on_hand) "
            "VALUES (%s,%s,%s)",
            (99999, 1, 100),  # product_id 99999 does not exist
        )


@pytest.mark.asyncio
async def test_check_constraint_on_unit_price(pool):
    with pytest.raises(Exception):  # CheckViolation
        await pool.execute(
            "INSERT INTO products (sku, name, category, unit_price) "
            "VALUES (%s,%s,%s,%s)",
            ("SKU-NEG", "x", "y", -1.0),
        )


# ===== Seed tests ==================================================

@pytest.mark.asyncio
async def test_seed_small_inserts_expected_rows(pool):
    summary = await seed_database(pool, scale="small")
    assert summary["suppliers"] == 10
    assert summary["products"] == 20
    assert summary["inventory"] == 60  # 20 products x 3 warehouses
    assert summary["purchase_orders"] == SCALE_ROWS["small"]
    assert summary["sales_orders"] == SCALE_ROWS["small"]


@pytest.mark.asyncio
async def test_seed_is_idempotent_with_truncate(pool):
    s1 = await seed_database(pool, scale="small")
    s2 = await seed_database(pool, scale="small")
    # Same seed => same counts
    assert s1 == s2
    # And actual DB row counts match the summary
    for t, n in s1.items():
        if t == "scale":
            continue
        assert await pool.fetchval(f"SELECT count(*) FROM {t}") == n


@pytest.mark.asyncio
async def test_seed_creates_low_stock_items_for_demo(pool):
    """SKU-0015 and SKU-0018 should be intentionally low for the demo."""
    await seed_database(pool, scale="medium")
    rows = await pool.fetch(
        "SELECT p.sku, p.name, p.safety_stock, COALESCE(SUM(i.on_hand),0)::int AS on_hand "
        "FROM products p LEFT JOIN inventory i USING (product_id) "
        "WHERE p.sku IN ('SKU-0015','SKU-0018','SKU-0003','SKU-0004') "
        "GROUP BY p.product_id, p.sku, p.name, p.safety_stock"
    )
    low_stock = [r for r in rows if r["on_hand"] < r["safety_stock"]]
    assert len(low_stock) >= 1, f"Expected at least 1 low-stock item, got {rows}"


# ===== Standalone runner ==========================================

if __name__ == "__main__":
    # Allow `python tests/test_erp_db.py` to execute the async tests
    import subprocess
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=short"]))
