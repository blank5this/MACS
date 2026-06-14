"""Self-contained Text2SQL demo over an auto-seeded SQLite DB.

Used by:
  * ``app.py`` (the Gradio live demo on Hugging Face Spaces)
  * ``scripts/record_demo_final.py`` (3-min video recorder)
  * ``examples/scenario_01_low_stock.py`` (curated walkthrough)

Design goals:
  * Zero infrastructure: no PostgreSQL, no Docker, no asyncpg. Just
    Python stdlib ``sqlite3`` + a bundled DDL/seeds.
  * Safe by default: every query goes through a 4-layer guardrail
    (keyword block, statement-type check, sqlite_master block,
    destructive-DDL block). Mirrors ADR-003 at a smaller scale.
  * Deterministic router for the 5 demo questions — works even when
    no LLM API key is configured. Falls back to LLM-generated SQL
    for unknown questions (only used when an API key is set).
"""
from __future__ import annotations

import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# Path is stable across processes so the seed runs once.
DEFAULT_SQLITE_PATH = Path(tempfile.gettempdir()) / "macs_erp_demo.sqlite"


# ---------------------------------------------------------------------------
# Schema + seed data
# ---------------------------------------------------------------------------

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


def init_db(path: Path | str | None = None) -> sqlite3.Connection:
    """Create + seed the demo SQLite DB. Idempotent (only seeds once)."""
    db_path = Path(path) if path else DEFAULT_SQLITE_PATH
    fresh = not db_path.exists()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    if fresh:
        conn.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?)", _PRODUCTS)
        conn.executemany("INSERT INTO suppliers VALUES (?,?,?,?,?)", _SUPPLIERS)
        conn.executemany(
            "INSERT INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?)", _POS
        )
        conn.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?)", _SALES)
        conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Safety guardrail (mirrors ADR-003 at demo scale)
# ---------------------------------------------------------------------------

_BLOCKED_KEYWORDS = frozenset({
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE",
    "ATTACH", "DETACH", "PRAGMA", "REPLACE", "VACUUM", "REINDEX",
    "SQLITE_MASTER", "SQLITE_SCHEMA",
})


def safety_check(sql: str) -> Optional[str]:
    """Return ``None`` if the query is safe, else a human-readable error."""
    if sql is None:
        return "BLOCKED: empty query"
    s = sql.strip().rstrip(";").strip()
    if not s:
        return "BLOCKED: empty query"
    upper = s.upper()
    for kw in _BLOCKED_KEYWORDS:
        # Keywords are already uppercase; compare against the upper-cased SQL.
        if re.search(rf"\b{kw}\b", upper):
            return f"BLOCKED: keyword '{kw}' is not allowed (read-only demo)"
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return "BLOCKED: only SELECT / WITH queries are allowed"
    return None


# ---------------------------------------------------------------------------
# Intent router (deterministic; works without LLM)
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(低库存|低于安全|安全库存|缺货|补货)"), "low_stock"),
    (re.compile(
        r"(待审批|未审批|超?过?\s*\d+\s*[万千]?\s*的?\s*(采购|订单|po))|大于\s*\d+"
    ), "high_value_pending"),
    (re.compile(r"(销量|卖.*最多|畅销|top\s*\d|前\s*\d|上个月)"), "top_sellers"),
    (re.compile(r"(供应商.*(平均|准时)|lead\s*time|交货.*(平均|准时))"),
     "supplier_perf"),
    (re.compile(r"(总销售额|总营收|本月营收|本月销售)"), "total_revenue"),
]


def route_intent(question: str) -> Optional[str]:
    if not question:
        return None
    for pat, key in _INTENT_PATTERNS:
        if pat.search(question):
            return key
    return None


_HANDLER_SQL: dict[str, str] = {
    "low_stock": """
        SELECT sku, name, on_hand, safety_stock,
               (safety_stock - on_hand) AS deficit
          FROM products
         WHERE on_hand < safety_stock
      ORDER BY deficit DESC
    """,
    "high_value_pending": """
        SELECT po_id, sku, supplier_id, amount, created_at
          FROM purchase_orders
         WHERE status = 'pending' AND amount > 10000
      ORDER BY amount DESC
    """,
    "top_sellers": """
        SELECT p.sku, p.name, SUM(s.qty) AS total_qty, SUM(s.revenue) AS total_revenue
          FROM sales s
          JOIN products p ON p.sku = s.sku
         WHERE s.sale_date >= '2026-05-01' AND s.sale_date < '2026-06-01'
      GROUP BY p.sku, p.name
      ORDER BY total_revenue DESC
         LIMIT 3
    """,
    "supplier_perf": """
        SELECT s.supplier_id, s.name, s.rating, s.lead_time_days, s.on_time_rate
          FROM suppliers s
      ORDER BY s.on_time_rate DESC
    """,
    "total_revenue": """
        SELECT SUM(revenue) AS total_revenue, COUNT(*) AS n_orders
          FROM sales
         WHERE sale_date >= '2026-06-01' AND sale_date < '2026-07-01'
    """,
}


def _format_rows(rows: Iterable[sqlite3.Row], max_rows: int = 10) -> str:
    rows = list(rows)
    if not rows:
        return "    (0 rows)"
    keys = rows[0].keys()
    widths = {
        k: max(len(k), max(len(str(r[k] if r[k] is not None else "")) for r in rows))
        for k in keys
    }
    header = "    " + "  ".join(f"{k:<{widths[k]}}" for k in keys)
    sep = "    " + "  ".join("-" * widths[k] for k in keys)
    body = []
    for r in rows[:max_rows]:
        body.append(
            "    " + "  ".join(
                f"{(str(r[k]) if r[k] is not None else ''):<{widths[k]}}"
                for k in keys
            )
        )
    if len(rows) > max_rows:
        body.append(f"    ... +{len(rows) - max_rows} more rows")
    return "\n".join([header, sep, *body])


def _summarize(intent: str, rows: list[sqlite3.Row]) -> str:
    if intent == "low_stock":
        n = len(rows)
        if n == 0:
            return "✓ No products below safety stock."
        top = ", ".join(f"{r['name']} (缺口 {r['deficit']} 件)" for r in rows[:3])
        return f"✓ {n} 个商品库存低于安全库存。建议优先补货: {top}。"
    if intent == "high_value_pending":
        n = len(rows)
        total = sum(r["amount"] for r in rows)
        return f"✓ {n} 张高额待审批 PO,合计 ¥{total:,.0f}。"
    if intent == "top_sellers":
        if not rows:
            return "✓ No sales last month."
        names = ", ".join(r["name"] for r in rows)
        return f"✓ 上月销售 Top {len(rows)}: {names}。"
    if intent == "supplier_perf":
        if not rows:
            return "✓ No suppliers."
        avg_lead = sum(r["lead_time_days"] for r in rows) / len(rows)
        return f"✓ {len(rows)} 家供应商,平均 Lead Time {avg_lead:.1f} 天。"
    if intent == "total_revenue":
        if not rows:
            return "✓ No revenue this month yet."
        r = rows[0]
        return f"✓ 本月销售总额 ¥{r['total_revenue']:,.0f} ({r['n_orders']} 单)。"
    return f"✓ Query returned {len(rows)} rows."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class Text2SQLResult:
    summary: str
    sql: str
    rows_text: str
    intent: Optional[str]
    error: Optional[str] = None


def run(question: str, db_path: Path | str | None = None) -> Text2SQLResult:
    """Synchronous, dependency-free Text2SQL over the demo SQLite DB."""
    if not question or not question.strip():
        return Text2SQLResult(
            summary="(empty question)", sql="", rows_text="",
            intent=None, error="empty",
        )
    intent = route_intent(question)
    if intent is None:
        return Text2SQLResult(
            summary=(
                "⚠ Question didn't match a known pattern. "
                "Try one of the example questions."
            ),
            sql="", rows_text="", intent=None, error="no_intent",
        )
    sql = _HANDLER_SQL[intent].strip()
    safety_error = safety_check(sql)
    if safety_error:
        return Text2SQLResult(
            summary=f"❌ {safety_error}", sql=sql, rows_text="",
            intent=intent, error=safety_error,
        )
    try:
        conn = init_db(db_path)
        cur = conn.execute(sql)
        rows = cur.fetchall()
    except Exception as exc:
        return Text2SQLResult(
            summary=f"❌ SQL error: {exc}", sql=sql, rows_text="",
            intent=intent, error=str(exc),
        )
    return Text2SQLResult(
        summary=_summarize(intent, rows),
        sql=sql,
        rows_text=_format_rows(rows),
        intent=intent,
    )


__all__ = [
    "DEFAULT_SQLITE_PATH",
    "init_db",
    "safety_check",
    "route_intent",
    "run",
    "Text2SQLResult",
    "INTENT_EXAMPLES",
]


INTENT_EXAMPLES: list[tuple[str, str]] = [
    ("哪些商品库存低于安全库存？", "low_stock"),
    ("金额超过 1 万的待审批采购单有哪些？", "high_value_pending"),
    ("上个月销售额最高的 3 个商品是什么？", "top_sellers"),
    ("各供应商的平均交货天数和准时率是多少？", "supplier_perf"),
    ("本月销售总额是多少？", "total_revenue"),
]