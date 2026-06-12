"""MCP server wiring the 5 ERP tools to :class:`MCPServer`.

Example::

    from macs_pkg.erp.db import DatabasePool, DatabaseConfig
    from macs_pkg.erp.tools import build_erp_mcp_server

    pool = DatabasePool(DatabaseConfig.from_env())
    await pool.open()
    server = build_erp_mcp_server(pool=pool)
    print(server.list_tools())      # 5 Tool definitions
    # To actually run:  await server.run_stdio()  or  await server.run_http(...)

List tools programmatically::

    from macs_pkg.erp.tools import list_tool_names
    print(list_tool_names())  # ['get_inventory_levels', 'get_low_stock_products', ...]
"""
from __future__ import annotations

import logging
from typing import Optional

from ..db.connection import DatabasePool, get_default_pool
from .inventory_tools import (
    get_inventory_levels,
    get_low_stock_products,
    get_sales_velocity,
    get_supplier_price_history,
    get_top_selling_products,
)

logger = logging.getLogger(__name__)


def build_erp_mcp_server(
    pool: Optional[DatabasePool] = None,
    name: str = "erp-copilot-mcp",
    version: str = "0.1.0-erp-copilot",
):
    """Build (do not start) an :class:`MCPServer` exposing the 5 ERP tools.

    Args:
        pool:    Open or un-opened :class:`DatabasePool`. If un-opened, the
                 tool handlers will lazily open it on first call. If ``None``,
                 the module-level singleton from :func:`get_default_pool` is
                 used.
        name:    Server name surfaced in MCP ``initialize`` handshake.
        version: Server version surfaced in MCP ``initialize`` handshake.

    Returns:
        An :class:`MCPServer` instance with 5 tools registered and ready
        to be started via ``server.run_stdio()`` or ``server.run_http(...)``.
    """
    # Import here so the macs_pkg top-level __init__ is not loaded unless
    # the user actually wants MCP transport — keeps the day-1/2/3 imports
    # fast and side-effect-free.
    from macs_pkg.mcp.server import MCPServer

    if pool is None:
        pool = get_default_pool()
        logger.info("Using default DatabasePool for ERP MCP server")

    server = MCPServer(name=name, version=version)

    # ---- Tool 1: get_inventory_levels ---------------------------------
    @server.tool(
        name="get_inventory_levels",
        description=(
            "Return current on-hand inventory per (product x warehouse). "
            "Optionally filter by product_id and/or category. Each row "
            "includes a `below_safety` boolean flag indicating whether "
            "on_hand is below the product's safety_stock threshold."
        ),
    )
    async def _get_inventory_levels(
        product_id: int = None,
        category: str = None,
    ) -> list[dict]:
        return await get_inventory_levels(pool, product_id=product_id, category=category)

    # ---- Tool 2: get_low_stock_products -------------------------------
    @server.tool(
        name="get_low_stock_products",
        description=(
            "Return products whose total on-hand stock across all warehouses "
            "is BELOW their per-product safety_stock threshold. Use this to "
            "answer 'which products are running low?'. The optional "
            "`threshold` parameter is a lower bound on safety_stock, used to "
            "skip low-value items (e.g. threshold=100 ignores washers and "
            "screws). Default 0 = include everything."
        ),
    )
    async def _get_low_stock_products(threshold: int = 0) -> list[dict]:
        return await get_low_stock_products(pool, threshold=threshold)

    # ---- Tool 3: get_supplier_price_history ---------------------------
    @server.tool(
        name="get_supplier_price_history",
        description=(
            "Return per-supplier unit_cost trend for a product over the last "
            "N days. Compares the most recent half of the window to the "
            "older half; positive `delta_pct` means the supplier's price is "
            "rising. Ordered by largest increase first. Use this to answer "
            "'which supplier is raising prices the fastest?'."
        ),
    )
    async def _get_supplier_price_history(
        product_id: int,
        days: int = 180,
    ) -> list[dict]:
        return await get_supplier_price_history(
            pool, product_id=product_id, days=days
        )

    # ---- Tool 4: get_top_selling_products -----------------------------
    @server.tool(
        name="get_top_selling_products",
        description=(
            "Return top-N products by units sold within an optional date "
            "range. Defaults to the last 30 days when no range is given. "
            "Each row includes units_sold, revenue (CNY), and order_count."
        ),
    )
    async def _get_top_selling_products(
        start_date: str = None,
        end_date: str = None,
        limit: int = 10,
    ) -> list[dict]:
        return await get_top_selling_products(
            pool,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    # ---- Tool 5: get_sales_velocity -----------------------------------
    @server.tool(
        name="get_sales_velocity",
        description=(
            "Return sales velocity metrics for one product over the last N "
            "days: units_sold, avg_daily_units, days_of_inventory (based on "
            "current stock), and a `reorder_recommendation` boolean (True "
            "when days_of_inventory < lead_time_days). Use this for "
            "purchase-planning scenarios."
        ),
    )
    async def _get_sales_velocity(product_id: int, days: int = 30) -> dict:
        return await get_sales_velocity(pool, product_id=product_id, days=days)

    logger.info(
        "ERP MCP server built with %d tools: %s",
        len(server.list_tools()),
        [t.name for t in server.list_tools()],
    )
    return server


def list_tool_names() -> list[str]:
    """Return the names of the 5 tools this server registers.

    Convenience helper for sanity checks and tests; does not open a DB.
    """
    from macs_pkg.mcp.server import MCPServer

    # Build a transient server without a real pool to introspect the names.
    # The handlers will never be called here.
    class _DummyPool:
        async def fetch(self, *args, **kwargs):
            raise RuntimeError("dummy pool — do not call")

        async def fetchrow(self, *args, **kwargs):
            raise RuntimeError("dummy pool — do not call")

    server = build_erp_mcp_server(pool=_DummyPool())  # type: ignore[arg-type]
    return [t.name for t in server.list_tools()]


__all__ = ["build_erp_mcp_server", "list_tool_names"]
