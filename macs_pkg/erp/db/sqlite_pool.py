"""SQLite-backed pool for the ERP demo.

A *very* thin shim that exposes the same ``fetch(sql, params) -> list[dict]``
async interface as :class:`macs_pkg.erp.db.connection.DatabasePool`. The
intentionally small surface lets the inventory tools work against either a
PostgreSQL or a SQLite backend — the SQLite path is what the local demo
falls back to when no Postgres is reachable (e.g. a fresh laptop without
Docker).

Why not just use psycopg's SQLite-mode? Because the inventory tools in
``macs_pkg/erp/tools/inventory_tools.py`` are written in Postgres SQL
(``::int`` casts, ``INTERVAL`` math, ``CURRENT_DATE``, ``NULLS LAST``).
Those queries fail at parse time on SQLite. So we ship *separate* SQLite
tools (see :mod:`macs_pkg.erp.tools.sqlite_tools`) and reuse *this* pool
class with them. The copilot agent picks which tool set to register based
on the pool's :attr:`backend` attribute.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Optional, Sequence, Union

logger = logging.getLogger(__name__)


# A temp-file-backed default so the data survives across requests but
# doesn't pollute the repo. Use ``MACS_SQLITE_PATH`` to override.
DEFAULT_SQLITE_PATH = Path(tempfile.gettempdir()) / "macs_erp_local.sqlite"


# --- DDL + seed (kept here so SQLite pool is self-contained) -------------

_DDL = """
CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    unit_price REAL,
    on_hand INTEGER NOT NULL,
    safety_stock INTEGER NOT NULL,
    supplier TEXT
);
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    rating TEXT CHECK(rating IN ('A','B','C','D')),
    lead_time_days INTEGER,
    on_time_rate REAL
);
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    qty INTEGER NOT NULL,
    unit_cost REAL NOT NULL,
    amount REAL NOT NULL,
    status TEXT CHECK(status IN ('pending','approved','received','paid','cancelled')),
    created_at TEXT NOT NULL,
    approver TEXT
);
CREATE TABLE IF NOT EXISTS sales (
    sale_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL,
    qty INTEGER NOT NULL,
    revenue REAL NOT NULL,
    sale_date TEXT NOT NULL,
    customer TEXT
);
"""

_PRODUCTS = [
    ("SKU-001", "Widget A", "机械配件",  50.0,  12,  30, "SUP-001"),
    ("SKU-002", "Widget B", "机械配件",  80.0,   5,  25, "SUP-001"),
    ("SKU-003", "Gadget C", "电子元件", 150.0,  45,  50, "SUP-002"),
    ("SKU-004", "Gadget D", "电子元件", 200.0, 120,  60, "SUP-002"),
    ("SKU-005", "Bolt M8",  "紧固件",     2.5, 800, 500, "SUP-003"),
    ("SKU-006", "Bolt M10", "紧固件",     3.0,  90, 200, "SUP-003"),
    ("SKU-007", "Cable A",  "电气",      25.0, 300, 150, "SUP-004"),
    ("SKU-008", "Sensor X", "传感器",   450.0,   8,  15, "SUP-005"),
]
_SUPPLIERS = [
    ("SUP-001", "Acme Corp",     "A", 14, 0.97),
    ("SUP-002", "BestParts Ltd", "B", 21, 0.92),
    ("SUP-003", "Fastener Inc",  "A",  7, 0.99),
    ("SUP-004", "ElectroSource", "A", 10, 0.96),
    ("SUP-005", "SensorTech",    "C", 30, 0.85),
]
_POS = [
    ("PO-1001", "SKU-001", "SUP-001", 100,  45.0,  4500.0, "paid",     "2026-05-02", "alice"),
    ("PO-1002", "SKU-002", "SUP-001", 200,  72.0, 14400.0, "pending",  "2026-05-08", None),
    ("PO-1003", "SKU-003", "SUP-002",  50, 135.0,  6750.0, "approved", "2026-05-10", "bob"),
    ("PO-1004", "SKU-005", "SUP-003", 500,   2.2,  1100.0, "received", "2026-05-12", "alice"),
    ("PO-1005", "SKU-008", "SUP-005",  20, 405.0,  8100.0, "pending",  "2026-05-15", None),
    ("PO-1006", "SKU-006", "SUP-003", 800,   2.8,  2240.0, "approved", "2026-05-20", "carol"),
    ("PO-1007", "SKU-004", "SUP-002",  60, 180.0, 10800.0, "pending",  "2026-05-22", None),
    ("PO-1008", "SKU-007", "SUP-004", 200,  22.0,  4400.0, "paid",     "2026-05-25", "bob"),
    ("PO-1009", "SKU-001", "SUP-001",  80,  46.0,  3680.0, "paid",     "2026-06-01", "alice"),
    ("PO-1010", "SKU-002", "SUP-001", 150,  73.0, 10950.0, "paid",     "2026-06-03", "bob"),
]
_SALES = [
    ("S-001", "SKU-001",  50,  2500.0, "2026-05-05", "Customer-A"),
    ("S-002", "SKU-002", 120,  9600.0, "2026-05-08", "Customer-B"),
    ("S-003", "SKU-003",  30,  4500.0, "2026-05-12", "Customer-A"),
    ("S-004", "SKU-004",  90, 18000.0, "2026-05-15", "Customer-C"),
    ("S-005", "SKU-005", 600,  1500.0, "2026-05-18", "Customer-D"),
    ("S-006", "SKU-007", 200,  5000.0, "2026-05-20", "Customer-B"),
    ("S-007", "SKU-001",  70,  3500.0, "2026-05-25", "Customer-A"),
    ("S-008", "SKU-002", 180, 14400.0, "2026-05-28", "Customer-E"),
    ("S-009", "SKU-008",  15,  6750.0, "2026-06-02", "Customer-C"),
    ("S-010", "SKU-006", 500,  1500.0, "2026-06-04", "Customer-D"),
]


def _is_empty(conn: sqlite3.Connection) -> bool:
    cur = conn.execute("SELECT COUNT(*) FROM products")
    return cur.fetchone()[0] == 0


class SQLitePool:
    """SQLite-backed pool with the same async ``fetch()`` surface as
    :class:`macs_pkg.erp.db.connection.DatabasePool`.

    The point is to be a *drop-in* when you don't have Postgres. The
    underlying sqlite3 connection is sync; we run queries via
    :func:`asyncio.to_thread` so the call sites stay ``async``.
    """

    backend = "sqlite"

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_SQLITE_PATH
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        """Open the SQLite connection and ensure the schema + seed exist."""
        if self._conn is not None:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False lets us dispatch queries via
        # ``asyncio.to_thread`` (which runs in a worker thread) without
        # the "SQLite objects created in a thread can only be used in
        # that same thread" error. Safe for our read-mostly demo.
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        if _is_empty(self._conn):
            self._conn.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?)", _PRODUCTS)
            self._conn.executemany("INSERT INTO suppliers VALUES (?,?,?,?,?)", _SUPPLIERS)
            self._conn.executemany(
                "INSERT INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?)", _POS
            )
            self._conn.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?)", _SALES)
            self._conn.commit()
        logger.info("SQLitePool opened: %s", self.db_path)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def fetch(self, sql: str, params: Sequence[Any] = ()) -> list[dict]:
        """Run a SELECT and return a list of dict rows.

        Uses ``?`` placeholders (not ``%s``). Tools written for SQLite
        should use ``?``; tools written for Postgres use ``%s`` — they
        are different files in :mod:`macs_pkg.erp.tools`.
        """
        if self._conn is None:
            self.open()
        return await asyncio.to_thread(self._fetch_sync, sql, tuple(params))

    def _fetch_sync(self, sql: str, params: tuple) -> list[dict]:
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        """Run a write statement (INSERT/UPDATE/DELETE). Not used by the
        read-only demo but exposed for symmetry with the Postgres pool."""
        if self._conn is None:
            self.open()
        await asyncio.to_thread(self._exec_sync, sql, tuple(params))

    def _exec_sync(self, sql: str, params: tuple) -> None:
        self._conn.execute(sql, params)
        self._conn.commit()

    # --- introspection ---
    def health_check(self) -> dict:
        if self._conn is None:
            return {"ok": False, "reason": "not open"}
        try:
            n = self._conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            return {"ok": True, "products": n, "path": str(self.db_path)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


__all__ = ["SQLitePool", "DEFAULT_SQLITE_PATH"]
