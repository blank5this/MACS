"""SQLite-compatible implementations of the 5 ERP inventory tools.

Mirrors the API of :mod:`macs_pkg.erp.tools.inventory_tools` but uses
SQLite syntax and the smaller 4-table schema in
:mod:`macs_pkg.erp.db.sqlite_pool` (products / suppliers / purchase_orders /
sales). The Postgres tool set stays the production path; this one is what
the local web demo uses when no Postgres is reachable.

Function signatures are **identical** to the Postgres versions — the
copilot agent picks one or the other based on ``pool.backend``.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

try:
    from loguru import logger  # type: ignore
except ImportError:  # pragma: no cover
    import logging
    logger = logging.getLogger(__name__)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


# ===== Tool 1: get_inventory_levels =================================

async def get_inventory_levels(
    pool,
    product_id: Optional[int] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Mirror of the Postgres tool — see inventory_tools.py for full docs."""
    # SQLite schema doesn't have a separate inventory table; current stock
    # lives on ``products.on_hand``. We still allow the same filter shape.
    sql = """
        SELECT sku AS product_id,
               sku,
               name,
               category,
               on_hand,
               safety_stock,
               supplier
          FROM products
         WHERE (? IS NULL OR category = ?)
      ORDER BY sku
    """
    rows = await pool.fetch(sql, (category, category))
    out = []
    for r in rows:
        out.append({
            "product_id":   r["product_id"],
            "sku":          r["sku"],
            "name":         r["name"],
            "category":     r["category"],
            "warehouse_id": 1,  # single-warehouse demo
            "on_hand":      r["on_hand"],
            "safety_stock": r["safety_stock"],
            "last_counted": date.today().isoformat(),
            "below_safety": r["on_hand"] < r["safety_stock"],
        })
    return out


# ===== Tool 2: get_low_stock_products ===============================

async def get_low_stock_products(pool, threshold: int = 0) -> list[dict]:
    """Mirror of the Postgres tool — see inventory_tools.py for full docs."""
    sql = """
        SELECT sku,
               name,
               category,
               on_hand,
               safety_stock,
               (safety_stock - on_hand) AS deficit,
               supplier
          FROM products
         WHERE on_hand < safety_stock
           AND safety_stock >= ?
      ORDER BY deficit DESC
    """
    rows = await pool.fetch(sql, (threshold,))
    return [_to_jsonable(r) for r in rows]


# ===== Tool 3: get_supplier_price_history ===========================

async def get_supplier_price_history(
    pool, product_id: str, days: int = 180
) -> list[dict]:
    """Per-supplier price trend for one product. SQLite version uses
    string dates on ``purchase_orders.created_at``; we compute the
    midpoint window in Python for portability."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    midpoint = (date.today() - timedelta(days=days // 2)).isoformat()
    sql = """
        SELECT po.supplier_id,
               s.name AS supplier_name,
               s.rating,
               po.unit_cost,
               po.created_at
          FROM purchase_orders po
          JOIN suppliers s ON s.supplier_id = po.supplier_id
         WHERE po.sku = ? AND po.created_at >= ?
    """
    rows = await pool.fetch(sql, (product_id, cutoff))
    by_supplier: dict[str, dict] = {}
    for r in rows:
        s = by_supplier.setdefault(r["supplier_id"], {
            "supplier_id":   r["supplier_id"],
            "supplier_name": r["supplier_name"],
            "rating":        r["rating"],
            "recent":        [],
            "older":         [],
            "order_count":   0,
        })
        s["order_count"] += 1
        if r["created_at"] >= midpoint:
            s["recent"].append(r["unit_cost"])
        else:
            s["older"].append(r["unit_cost"])

    out = []
    for s in by_supplier.values():
        recent_avg = round(sum(s["recent"]) / len(s["recent"]), 2) if s["recent"] else None
        older_avg = round(sum(s["older"]) / len(s["older"]), 2) if s["older"] else None
        delta = (
            round(recent_avg - older_avg, 2)
            if (recent_avg is not None and older_avg is not None)
            else None
        )
        delta_pct = (
            round(100.0 * delta / older_avg, 2)
            if (delta is not None and older_avg)
            else None
        )
        out.append({
            "supplier_id":   s["supplier_id"],
            "supplier_name": s["supplier_name"],
            "rating":        s["rating"],
            "recent_avg":    recent_avg,
            "older_avg":     older_avg,
            "delta":         delta,
            "delta_pct":     delta_pct,
            "order_count":   s["order_count"],
        })
    out.sort(key=lambda r: r["delta"] if r["delta"] is not None else 0, reverse=True)
    return out


# ===== Tool 4: get_top_selling_products =============================

async def get_top_selling_products(
    pool,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    sql = """
        SELECT p.sku,
               p.name,
               p.category,
               SUM(s.qty)   AS units_sold,
               SUM(s.revenue) AS revenue,
               COUNT(*)     AS order_count
          FROM sales s
          JOIN products p ON p.sku = s.sku
         WHERE (? IS NULL OR s.sale_date >= ?)
           AND (? IS NULL OR s.sale_date <= ?)
      GROUP BY p.sku, p.name, p.category
      ORDER BY units_sold DESC
         LIMIT ?
    """
    rows = await pool.fetch(
        sql, (start_date, start_date, end_date, end_date, limit)
    )
    return [_to_jsonable(r) for r in rows]


# ===== Tool 5: get_sales_velocity ===================================

async def get_sales_velocity(pool, product_id: str, days: int = 30) -> dict:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    sales_sql = """
        SELECT COALESCE(SUM(qty), 0)      AS units_sold,
               COUNT(*)                   AS order_count,
               COALESCE(SUM(revenue), 0)  AS revenue
          FROM sales
         WHERE sku = ? AND sale_date >= ?
    """
    sales_rows = await pool.fetch(sales_sql, (product_id, cutoff))
    s = sales_rows[0] if sales_rows else {"units_sold": 0, "order_count": 0, "revenue": 0}

    prod_sql = "SELECT on_hand, safety_stock FROM products WHERE sku = ?"
    prod_rows = await pool.fetch(prod_sql, (product_id,))
    if not prod_rows:
        return {"error": f"product {product_id} not found"}
    p = prod_rows[0]

    avg_daily = round(s["units_sold"] / days, 3) if days else 0
    days_of_inventory = (
        round(p["on_hand"] / avg_daily, 1) if avg_daily > 0 else None
    )
    return {
        "product_id":      product_id,
        "days":            days,
        "units_sold":      s["units_sold"],
        "order_count":     s["order_count"],
        "revenue":         round(float(s["revenue"]), 2),
        "avg_daily_units": avg_daily,
        "on_hand":         p["on_hand"],
        "safety_stock":    p["safety_stock"],
        "days_of_inventory": days_of_inventory,
        "reorder_recommendation": (
            days_of_inventory is not None and days_of_inventory < 14
        ),
    }
