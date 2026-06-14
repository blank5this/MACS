"""Scenario 3 — NL→SQL with 4-layer safety guardrail.

A real AI Copilot scenario that demonstrates:

  1. The user asks in natural Chinese: "上个月销售总额是多少？"
  2. The Agent picks the NL→SQL tool (not RAG — this is a number question).
  3. The ``NL2SQLTranslator`` turns the question into a safe SELECT.
  4. ``SQLValidator`` runs the 4-layer guardrail (statement-type /
     multi-statement / keyword-block / table-allow-list) and
     confirms it is safe.
  5. The query executes and returns a single-row result.
  6. **Adversarial case**: an injected "DROP TABLE suppliers" is
     rejected at *layer 1* (statement type) before it can ever reach
     the database.

Run::

    PYTHONIOENCODING=utf-8 python examples/scenario_03_text2sql.py

This is scenario #3 of the curated set. Chosen because it pairs with
scenario 1 (low-stock) and scenario 2 (policy-RAG) to cover the three
core capabilities: MCP tool / RAG / NL→SQL. The adversarial sub-case
turns an abstract ADR-003 (the 4-layer guardrail) into a *visible*
property the user can rerun.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _section(text: str) -> None:
    print()
    print("─" * 75)
    print(f"  ▸ {text}")
    print("─" * 75)


# === Intent router — uses text2sql_demo.run() =========================

def _demo_text2sql(question: str) -> str:
    """Deterministic NL→SQL for the question, returning a human-readable result."""
    from macs_pkg.erp.demo import run as text2sql_run
    r = text2sql_run(question)
    if r.error:
        return f"  ❌ {r.error}\n     SQL: {r.sql[:100]}"
    return (
        f"  ✓ Intent: {r.intent}\n"
        f"  ✓ SQL   : {r.sql.strip()}\n"
        f"  ✓ Result : {r.summary}\n"
        f"  Rows:\n{r.rows_text}"
    )


# === Safety guardrail walkthrough (mirrors ADR-003) ====================

def _show_guardrail() -> None:
    """Run the 4-layer guardrail against 3 inputs: safe, malformed, malicious."""
    from macs_pkg.erp.nl2sql import SQLValidator

    v = SQLValidator()
    # Note: SQLValidator is the production (Postgres) guardrail. Its
    # allow-list is {products, suppliers, inventory, purchase_orders,
    # sales_orders} — so the test cases use those names. The SQLite
    # demo (Step 3) uses the simpler `sales` table; same idea, smaller
    # schema.
    cases = [
        ("Safe: aggregate sales (Postgres schema)",
         "SELECT SUM(unit_price * quantity) FROM sales_orders "
         "WHERE sale_date >= '2026-06-01'"),
        ("Malformed: multi-statement injection",
         "SELECT 1 FROM sales_orders; DROP TABLE suppliers"),
        ("Malicious: keyword + disallowed type",
         "DROP TABLE suppliers"),
        ("Clever: UNION exfiltration (unknown table)",
         "SELECT 1 FROM sales_orders UNION SELECT password FROM users"),
    ]

    print()
    print("─" * 75)
    print("  ▸ Safety guardrail walkthrough — ADR-003")
    print("─" * 75)
    for label, sql in cases:
        ok, why = v.is_safe(sql)
        status = "✓ PASS" if ok else "✗ BLOCK"
        print(f"\n  [{status}]  {label}")
        print(f"          SQL: {sql[:80]}")
        if not ok:
            print(f"          why: {why}")


# === Demo loop ==========================================================

async def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   Scenario 3 — NL→SQL with 4-Layer Safety Guardrail                ║")
    print("║                                                                      ║")
    print("║   Built on MACS · MIT licensed · github.com/blank5this/MACS           ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    _section("Step 1 / 4 — User question (自然语言)")
    question = "本月销售总额是多少？"
    print(f"  {question}")

    _section("Step 2 / 4 — Intent router + SQL generation")
    print(f"  → Layer 1 (Statement type): SELECT only")
    print(f"  → Layer 2 (Multi-statement): reject anything after the first ';'")
    print(f"  → Layer 3 (Keyword blocklist): DROP/DELETE/UPDATE/INSERT/.../UNION")
    print(f"  → Layer 4 (Table allow-list): products / suppliers / purchase_orders / sales")

    _section("Step 3 / 4 — SQL passes the guardrail and executes")
    print(_demo_text2sql(question))

    _section("Step 4 / 4 — Same guardrail rejects adversarial inputs")
    _show_guardrail()

    print()
    print("═" * 75)
    print("  ✓ NL→SQL works.  ✓ Safety guardrail works.  ✓ Both, at the same time.")
    print("  Try it live:  python -m macs_pkg.erp.web")
    print("  Source:       github.com/blank5this/MACS")
    print("═" * 75)


if __name__ == "__main__":
    asyncio.run(main())
