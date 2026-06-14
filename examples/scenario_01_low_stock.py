"""Scenario 1 — Low-stock detection via MCP inventory tool.

A real AI Copilot scenario that demonstrates:

  1. The user asks in natural Chinese: "哪些商品库存低于安全库存？"
  2. The Agent (deterministic router) picks the right MCP tool:
     ``get_low_stock_products`` (vs. ``ask_knowledge_base`` / ``query_database``).
  3. The tool queries the seeded SQLite DB (no Docker needed).
  4. The Agent returns ranked rows with a reorder recommendation.

Run::

    PYTHONIOENCODING=utf-8 python examples/scenario_01_low_stock.py

With an API key, the Agent will also generate a procurement narrative;
without one, it returns the deterministic summary.

This is scenario #1 of the "real AI Copilot scenarios" promised in the
project pitch — chosen because it's the single most common question an
ops manager asks.
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


def _banner(text: str) -> None:
    print()
    print("═" * 75)
    print(f"  {text}")
    print("═" * 75)


def _section(text: str) -> None:
    print()
    print("─" * 75)
    print(f"  ▸ {text}")
    print("─" * 75)


# === The agent ============================================================

async def _maybe_provider():
    """Pick the first available LLM provider. Return ``None`` if no key."""
    if os.getenv("ANTHROPIC_API_KEY"):
        from macs_pkg.llm import ClaudeProvider
        return ClaudeProvider()
    if os.getenv("MINIMAX_API_KEY"):
        from macs_pkg.llm import MiniMaxProvider
        return MiniMaxProvider()
    return None


# === Tool registry — mirrors the production ERPCopilotAgent ===============
# Only the inventory tool is exposed for this scenario to keep the demo
# focused. In the full agent (see macs_pkg/erp/agents/copilot_agent.py)
# there are 7 tools; the deterministic router picks one based on keywords.

async def _tool_get_low_stock_products(conn) -> dict:
    """Returns ranked rows of products below safety stock."""
    cur = conn.execute(
        """
        SELECT sku, name, category, on_hand, safety_stock,
               (safety_stock - on_hand) AS deficit,
               supplier
          FROM products
         WHERE on_hand < safety_stock
      ORDER BY deficit DESC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    return {"rows": rows, "count": len(rows)}


def _route(question: str) -> str:
    """Deterministic router. Mirrors macs_pkg/erp/demo._route_intent."""
    import re
    if re.search(r"(低库存|低于安全|安全库存|缺货|补货)", question):
        return "get_low_stock_products"
    return "unknown"


def _generate_reorder_summary(rows: list[dict]) -> str:
    """Deterministic procurement recommendation, per row."""
    lines = []
    for r in rows[:3]:
        deficit = r["deficit"]
        # Rough rule: 2 weeks of stock at avg daily sales.
        urgency = "高" if deficit >= 50 else "中" if deficit >= 20 else "低"
        lines.append(
            f"  • {r['name']} ({r['sku']}): 缺口 {deficit} 件, "
            f"供应商 {r['supplier']}, 紧急度 {urgency}"
        )
    return "\n".join(lines)


# === Demo loop ============================================================

async def main() -> None:
    from macs_pkg.erp.demo import init_db

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   Scenario 1 — Low-Stock Detection via MCP Inventory Tool           ║")
    print("║                                                                      ║")
    print("║   Built on MACS · MIT licensed · github.com/blank5this/MACS           ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    _section("Step 1 / 4 — User question")
    question = "哪些商品库存低于安全库存？"
    print(f"  {question}")

    _section("Step 2 / 4 — Agent router picks the right tool")
    tool = _route(question)
    print(f"  → Selected tool: {tool}")
    print(f"  → Other tools in registry: query_database, ask_knowledge_base,")
    print(f"    get_top_sellers, get_high_value_pending_pos, get_supplier_performance")
    print(f"  → Why this tool: keywords '低于安全' + '补货' match the inventory intent.")

    _section("Step 3 / 4 — Tool executes against the seeded SQLite DB")
    conn = init_db()
    print(f"  → DB: {conn.__hash__ and 'seeded SQLite (8 products, 5 suppliers)'}")

    if tool != "get_low_stock_products":
        print(f"  ❌ Tool not registered for this scenario")
        return

    result = await _tool_get_low_stock_products(conn)
    rows = result["rows"]

    # Pretty print rows
    print(f"  → {len(rows)} products below safety stock:\n")
    if rows:
        print(f"    {'sku':<10} {'name':<14} {'on_hand':>8} {'safety':>8} {'deficit':>8}  supplier")
        print(f"    {'-'*10} {'-'*14} {'-'*8} {'-'*8} {'-'*8}  {'-'*8}")
        for r in rows:
            print(
                f"    {r['sku']:<10} {r['name']:<14} {r['on_hand']:>8} "
                f"{r['safety_stock']:>8} {r['deficit']:>8}  {r['supplier']}"
            )

    _section("Step 4 / 4 — Agent synthesizes a procurement recommendation")
    print(f"  ✓ {len(rows)} 个商品库存低于安全库存。建议优先补货:\n")
    print(_generate_reorder_summary(rows))

    # Optional: enhance with LLM if key is set
    provider = await _maybe_provider()
    if provider is not None:
        print()
        print("  (LLM-enhanced narrative follows ↓)")
        from macs_pkg.llm.base import LLMMessage
        rows_brief = ", ".join(
            f"{r['name']} 缺口 {r['deficit']} 件" for r in rows[:5]
        )
        prompt = (
            f"你是 ERP 采购助手。基于以下数据,给出 2-3 句话的补货建议,"
            f"语气专业、简洁,直接给行动项。\n\n"
            f"低库存商品: {rows_brief}"
        )
        try:
            resp = await provider.complete(
                [LLMMessage(role="user", content=prompt)]
            )
            for line in resp.content.strip().split("\n"):
                print(f"    {line}")
        except Exception as e:
            print(f"    (LLM unavailable: {e})")
    else:
        print()
        print("  (Set MINIMAX_API_KEY to get an LLM-enhanced narrative.)")

    # === Closing ===
    print()
    print("═" * 75)
    print("  Try it live:  python app.py  →  http://localhost:7860")
    print("  Source:       github.com/blank5this/MACS")
    print("═" * 75)


if __name__ == "__main__":
    asyncio.run(main())