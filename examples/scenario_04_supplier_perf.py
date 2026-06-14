"""Scenario 4 — Supplier performance ranking & recommendation.

A real AI Copilot scenario that demonstrates:

  1. The user asks in natural Chinese: "哪几家供应商最准时？"
  2. The Agent routes to the supplier-performance query (not RAG — this
     is structured data, not a policy document).
  3. The query returns the 5 seeded suppliers, ranked by on-time rate,
     with rating, lead time, and a derived "preferred / acceptable /
     risky" classification.
  4. The synthesized answer includes a one-line procurement recommendation
     per supplier.

Run::

    PYTHONIOENCODING=utf-8 python examples/scenario_04_supplier_perf.py

This is scenario #4 of the curated set — the procurement-flavoured
companion to scenario 1 (low-stock). Where scenario 1 answers "what to
*buy*", scenario 4 answers "whom to *buy from*". Together they cover
the two halves of any re-order decision.
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


def _bar(value: float, width: int = 20) -> str:
    """Tiny ASCII bar for the on-time rate."""
    filled = int(round(value * width))
    return "█" * filled + "░" * (width - filled)


def _classify(rating: str, on_time: float, lead: int) -> str:
    """Procurement-style classification — derived rule, no LLM."""
    if rating == "A" and on_time >= 0.95 and lead <= 14:
        return "✓ preferred"
    if rating == "A" and on_time >= 0.90:
        return "○ acceptable"
    return "△ risky"


# === Demo loop ==========================================================

async def main() -> None:
    from macs_pkg.erp.demo import init_db

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   Scenario 4 — Supplier Performance Ranking & Recommendation        ║")
    print("║                                                                      ║")
    print("║   Built on MACS · MIT licensed · github.com/blank5this/MACS           ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    _section("Step 1 / 4 — User question (自然语言)")
    question = "哪几家供应商最准时？请按表现排名。"
    print(f"  {question}")

    _section("Step 2 / 4 — Agent router picks the right tool")
    print("  → Selected tool: query_database (NL→SQL, single-row aggregates)")
    print("  → Other tools in registry: ask_knowledge_base, get_low_stock_products, ...")
    print("  → Why this tool: '准时' + '排名' = structured numeric question,")
    print("    not a free-text policy question (which would route to RAG).")

    _section("Step 3 / 4 — Query executes against the seeded SQLite DB")
    conn = init_db()
    rows = conn.execute(
        """
        SELECT supplier_id, name, rating, lead_time_days, on_time_rate
          FROM suppliers
      ORDER BY on_time_rate DESC
        """
    ).fetchall()

    print(f"  → DB: seeded SQLite (5 suppliers)")
    print()
    print(f"    {'id':<10} {'name':<18} {'rate':<6} "
          f"{'lead':>5}  {'on-time':<22} {'class':<12}")
    print(f"    {'-'*10} {'-'*18} {'-'*6} {'-'*5}  {'-'*22} {'-'*12}")
    for r in rows:
        bar = _bar(r["on_time_rate"])
        klass = _classify(r["rating"], r["on_time_rate"], r["lead_time_days"])
        print(
            f"    {r['supplier_id']:<10} {r['name']:<18} {r['rating']:<6} "
            f"{r['lead_time_days']:>4}d  {bar} {int(round(r['on_time_rate']*100)):>3}%  {klass}"
        )

    _section("Step 4 / 4 — Procurement recommendation")
    recs = []
    for r in rows:
        klass = _classify(r["rating"], r["on_time_rate"], r["lead_time_days"])
        recs.append(
            f"  • {r['name']} ({r['supplier_id']}): "
            f"评级 {r['rating']}, 准时率 {int(round(r['on_time_rate']*100))}%, "
            f"Lead Time {r['lead_time_days']}d → {klass}"
        )
    print("\n".join(recs))

    print()
    print("═" * 75)
    print("  ✓ Sup-003 Fastener Inc 是首选 (Lead Time 7d, 准时率 99%, A 级).")
    print("  ✓ Sup-005 SensorTech 风险最高 (Lead Time 30d, 准时率 85%, C 级).")
    print("  Try it live:  python -m macs_pkg.erp.web")
    print("  Source:       github.com/blank5this/MACS")
    print("═" * 75)


if __name__ == "__main__":
    asyncio.run(main())
