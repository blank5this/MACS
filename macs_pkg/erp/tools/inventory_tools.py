"""Async ERP query tools — the backend of the MCP server.

Each function takes a :class:`DatabasePool` as its first argument so the
functions are pure (and directly testable). The MCP layer in ``server.py``
closes a pool over them via the ``@server.tool`` decorator.

Tool contract
-------------
* All parameters are keyword-only by convention; positional args accepted for
  ergonomics inside the codebase.
* All return values are JSON-serialisable ``list[dict]`` or ``dict``. Dates
  are ISO-8601 strings, decimals are ``float`` (with 2dp rounding for money).
* No mutating / write tools in this module — read-only by design. Write
  tools (PO creation, approval, etc.) are intentionally out of scope for
  the v1 demo and require a separate audit-logged path.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from ..db.connection import DatabasePool

logger = logging.getLogger(__name__)


# ===== Helpers =====================================================

def _to_jsonable(value: Any) -> Any:
    """Recursively convert dates / datetimes / decimals to JSON primitives.

    MCP serializes tool outputs as JSON, so the values we return must be
    JSON-compatible out of the box (no Decimal, no datetime).
    """
    if isinstance(value, Decimal):
        # Money uses 2dp; ratios/counts use 3dp
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    return value


def _round_money(value: Any) -> Any:
    """Round ``Decimal``/``float`` to 2dp for currency fields."""
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return value


# ===== Tool 1: get_inventory_levels =================================

async def get_inventory_levels(
    pool: DatabasePool,
    product_id: Optional[int] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Return current on-hand inventory per (product × warehouse).

    Args:
        product_id: filter to a single product; ``None`` for all.
        category:   filter to a product category; ``None`` for all.

    Returns:
        list of dicts: ``[{product_id, sku, name, category, warehouse_id,
        on_hand, safety_stock, last_counted, below_safety}, ...]``
        ``below_safety`` is a boolean convenience flag.
    """
    sql = """
        SELECT p.product_id,
               p.sku,
               p.name,
               p.category,
               p.safety_stock,
               i.warehouse_id,
               i.on_hand,
               i.last_counted,
               (i.on_hand < p.safety_stock) AS below_safety
        FROM inventory i
        JOIN products p ON p.product_id = i.product_id
        WHERE (%s::INTEGER IS NULL OR p.product_id = %s)
          AND (%s::TEXT    IS NULL OR p.category  = %s)
        ORDER BY p.sku, i.warehouse_id
    """
    rows = await pool.fetch(sql, (product_id, product_id, category, category))
    return [_to_jsonable(r) for r in rows]


# ===== Tool 2: get_low_stock_products ===============================

async def get_low_stock_products(
    pool: DatabasePool,
    threshold: int = 0,
) -> list[dict]:
    """Return products whose TOTAL on-hand stock is below their safety_stock.

    This answers the question *"哪些商品库存低于安全库存？"*.

    Args:
        threshold: only include products with ``safety_stock >= threshold``.
                   Defaults to 0, which means include all products. Use a
                   higher value to focus on items with material safety
                   thresholds (e.g. ``threshold=100`` to ignore low-value
                   items like screws and washers).

    Returns:
        list of dicts ordered by largest deficit first, with
        ``on_hand``, ``safety_stock``, and ``deficit`` columns. ``deficit``
        is always positive for returned rows (= ``safety_stock - on_hand``).
    """
    sql = """
        SELECT p.product_id,
               p.sku,
               p.name,
               p.category,
               p.safety_stock,
               COALESCE(SUM(i.on_hand), 0)::int AS on_hand,
               (p.safety_stock - COALESCE(SUM(i.on_hand), 0))::int AS deficit
        FROM products p
        LEFT JOIN inventory i ON i.product_id = p.product_id
        WHERE p.safety_stock >= %s
        GROUP BY p.product_id, p.sku, p.name, p.category, p.safety_stock
        HAVING COALESCE(SUM(i.on_hand), 0) < p.safety_stock
        ORDER BY deficit DESC
    """
    rows = await pool.fetch(sql, (threshold,))
    return [_to_jsonable(r) for r in rows]


# ===== Tool 3: get_supplier_price_history ===========================

async def get_supplier_price_history(
    pool: DatabasePool,
    product_id: int,
    days: int = 180,
) -> list[dict]:
    """Return per-supplier unit_cost trend for a product over the last N days.

    Groups by supplier and returns, for each, the average unit_cost in two
    windows: the first half and the second half of the period. The
    ``delta_pct`` field is the % change recent-vs-older — positive means
    the supplier's price has been climbing.

    Returns:
        list of dicts: ``[{supplier_id, supplier_name, rating, recent_avg,
        older_avg, delta, delta_pct, order_count}, ...]`` ordered by delta
        descending so the "fastest-rising" supplier appears first.
    """
    sql = """
        WITH windowed AS (
            SELECT po.supplier_id,
                   po.unit_cost,
                   po.order_date,
                   (po.order_date >= CURRENT_DATE - (%s || ' days')::interval / 2)
                       AS is_recent
            FROM purchase_orders po
            WHERE po.product_id = %s
              AND po.order_date >= CURRENT_DATE - (%s || ' days')::interval
        )
        SELECT s.supplier_id,
               s.name                                       AS supplier_name,
               s.rating,
               ROUND(AVG(CASE WHEN w.is_recent THEN w.unit_cost END)::numeric, 2)
                                                          AS recent_avg,
               ROUND(AVG(CASE WHEN NOT w.is_recent THEN w.unit_cost END)::numeric, 2)
                                                          AS older_avg,
               ROUND(
                   (AVG(CASE WHEN w.is_recent THEN w.unit_cost END) -
                    AVG(CASE WHEN NOT w.is_recent THEN w.unit_cost END))::numeric, 2
               )                                            AS delta,
               ROUND(
                   100.0 * (AVG(CASE WHEN w.is_recent THEN w.unit_cost END) -
                            AVG(CASE WHEN NOT w.is_recent THEN w.unit_cost END)) /
                   NULLIF(AVG(CASE WHEN NOT w.is_recent THEN w.unit_cost END), 0)::numeric,
                   2
               )                                            AS delta_pct,
               COUNT(*)::int                                AS order_count
        FROM windowed w
        JOIN suppliers s ON s.supplier_id = w.supplier_id
        GROUP BY s.supplier_id, s.name, s.rating
        HAVING COUNT(*) >= 1
        ORDER BY delta DESC NULLS LAST
    """
    rows = await pool.fetch(sql, (str(days), product_id, str(days)))
    return [_to_jsonable(r) for r in rows]


# ===== Tool 4: get_top_selling_products =============================

async def get_top_selling_products(
    pool: DatabasePool,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Return top-N products by units sold in a date range.

    Args:
        start_date: ISO-8601 date string; defaults to 30 days ago.
        end_date:   ISO-8601 date string; defaults to today.
        limit:      max rows to return (default 10).

    Returns:
        list of dicts: ``[{product_id, sku, name, category, units_sold,
        revenue, order_count}, ...]`` ordered by units_sold DESC.
    """
    sql = """
        SELECT p.product_id,
               p.sku,
               p.name,
               p.category,
               SUM(s.quantity)::int                            AS units_sold,
               ROUND(SUM(s.quantity * s.unit_price)::numeric, 2) AS revenue,
               COUNT(*)::int                                  AS order_count
        FROM sales_orders s
        JOIN products p ON p.product_id = s.product_id
        WHERE (%s::DATE IS NULL OR s.sale_date >= %s)
          AND (%s::DATE IS NULL OR s.sale_date <= %s)
        GROUP BY p.product_id, p.sku, p.name, p.category
        ORDER BY units_sold DESC
        LIMIT %s
    """
    rows = await pool.fetch(
        sql, (start_date, start_date, end_date, end_date, limit)
    )
    return [_to_jsonable(r) for r in rows]


# ===== Tool 5: get_sales_velocity ===================================

async def get_sales_velocity(
    pool: DatabasePool,
    product_id: int,
    days: int = 30,
) -> dict:
    """Return sales velocity metrics for a product over the last N days.

    Computes:
        * ``units_sold``        — total units in the window
        * ``avg_daily_units``   — units / days
        * ``days_of_inventory`` — current on_hand / avg_daily_units
        * ``reorder_recommendation`` — boolean: True if days_of_inventory < lead_time_days

    Returns:
        A single dict (not a list) since the call is keyed on one product.
    """
    sql = """
        WITH velocity AS (
            SELECT COALESCE(SUM(s.quantity), 0)::int                AS units_sold,
                   COALESCE(COUNT(*), 0)::int                       AS order_count,
                   COALESCE(ROUND(SUM(s.quantity * s.unit_price)::numeric, 2), 0)
                                                                     AS revenue
            FROM sales_orders s
            WHERE s.product_id = %s
              AND s.sale_date >= CURRENT_DATE - (%s || ' days')::interval
        ),
        stock AS (
            SELECT COALESCE(SUM(i.on_hand), 0)::int AS on_hand
            FROM inventory i
            WHERE i.product_id = %s
        ),
        prod AS (
            SELECT p.safety_stock, p.lead_time_days
            FROM products p
            WHERE p.product_id = %s
        )
        SELECT v.units_sold,
               v.order_count,
               v.revenue,
               ROUND((v.units_sold::numeric / NULLIF(%s, 0))::numeric, 3)
                                                          AS avg_daily_units,
               st.on_hand,
               pr.safety_stock,
               pr.lead_time_days,
               ROUND((st.on_hand::numeric /
                      NULLIF(v.units_sold::numeric / NULLIF(%s, 0), 0))::numeric, 1)
                                                          AS days_of_inventory,
               ((st.on_hand::numeric /
                 NULLIF(v.units_sold::numeric / NULLIF(%s, 0), 0))
                < pr.lead_time_days)                      AS reorder_recommendation
        FROM velocity v, stock st, prod pr
    """
    row = await pool.fetchrow(
        sql,
        (product_id, str(days), product_id, product_id, days, days, days),
    )
    if row is None:
        return {"product_id": product_id, "error": "product not found"}
    return _to_jsonable(row)


__all__ = [
    "get_inventory_levels",
    "get_low_stock_products",
    "get_supplier_price_history",
    "get_top_selling_products",
    "get_sales_velocity",
]
