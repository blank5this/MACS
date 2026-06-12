"""ERP Copilot — single-agent demo (Day 8 deliverable).

Showcases a single :class:`ERPCopilotAgent` using three capability
layers at once (MCP tools, RAG, NL→SQL) to answer three realistic
ERP questions end-to-end.

Run::

    python examples/erp_copilot_single_agent.py

The script prints the agent's tool selection + a short answer for
each question. If no LLM API key is set, it falls back to keyword
routing (the same fallback ``ToolAgent._fallback_tool_selection``
uses) so the demo still produces output.

Demo questions:
    1. "哪些商品库存低于安全库存？"               — MCP (get_low_stock_products)
    2. "如何处理采购退货？"                       — RAG  (ask_knowledge_base)
    3. "上个月销售额最高的 3 个商品是什么？"       — NL→SQL (query_database)
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Make the package importable when running from the repo root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ===== Helpers =====================================================

def _section(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def _format_rows_for_humans(rows: list[dict], max_rows: int = 5) -> str:
    """Best-effort pretty-printer for list[dict] tool results."""
    if not rows:
        return "  (no rows)"
    sample = rows[:max_rows]
    # Pick a few common columns if present.
    keys = []
    for k in (
        "sku", "name", "category", "on_hand", "safety_stock", "deficit",
        "units_sold", "revenue", "delta_pct", "supplier_name",
        "avg_daily_units", "days_of_inventory", "reorder_recommendation",
    ):
        if any(k in r for r in sample):
            keys.append(k)
    if not keys:
        keys = list(sample[0].keys())[:6]
    out = []
    out.append("  " + " | ".join(keys))
    out.append("  " + "-+-".join("-" * len(k) for k in keys))
    for r in sample:
        out.append("  " + " | ".join(str(r.get(k, "")) for k in keys))
    if len(rows) > max_rows:
        out.append(f"  ... ({len(rows) - max_rows} more rows)")
    return "\n".join(out)


async def _run_demo() -> None:
    from macs_pkg.erp.agents.copilot_agent import build_copilot_agent
    from macs_pkg.erp.db import DatabaseConfig, DatabasePool

    # ----- 1. Database pool -----
    _section("1/4  启动数据库连接池")
    pool = DatabasePool(DatabaseConfig.from_env())
    await pool.open()
    print("  ✓ DatabasePool 已打开")

    # ----- 2. LLM provider -----
    _section("2/4  初始化 LLM Provider")
    provider = None
    if os.getenv("ANTHROPIC_API_KEY"):
        from macs_pkg.llm import ClaudeProvider
        provider = ClaudeProvider()
        print(f"  ✓ Provider: Claude ({provider.model_name()})")
    elif os.getenv("MINIMAX_API_KEY"):
        from macs_pkg.llm import MiniMaxProvider
        provider = MiniMaxProvider()
        print(f"  ✓ Provider: MiniMax ({provider.model_name()})")
    else:
        print("  ⚠ 未设置 ANTHROPIC_API_KEY / MINIMAX_API_KEY, 使用 mock provider")
        print("    (脚本仍会跑, 但 LLM 工具选择走关键词兜底)")

        class _MockResponse:
            def __init__(self, content: str) -> None:
                self.content = content
                self.model = "mock"
                self.usage = {}
                self.tool_calls = []
                self.stop_reason = "stop"

        class _MockProvider:
            """Mock provider that forces a tool by keyword match."""
            def __init__(self, tool_hint: str) -> None:
                self._hint = tool_hint

            async def complete(self, messages, system=None, **kwargs):
                # Tool selection happens in ToolAgent._llm_select_tool via the
                # system prompt + the user description; for the mock, return
                # an empty content so ToolAgent falls back to keyword routing.
                return _MockResponse(content="{}")

            def model_name(self) -> str:
                return "mock-model"

        provider = _MockProvider("")

    # ----- 3. Build the agent -----
    _section("3/4  构建 ERPCopilotAgent")
    agent = build_copilot_agent(pool=pool, provider=provider)
    print(f"  ✓ Agent 名称: {agent.name}")
    print(f"  ✓ 注册工具 ({len(agent.list_tools())} 个):")
    for t in agent.list_tools():
        print(f"     - {t}")

    # ----- 4. Demo questions -----
    _section("4/4  演示 — 单 Agent 混合工具调用")
    questions = [
        "哪些商品库存低于安全库存？",
        "如何处理采购退货？",
        "上个月销售额最高的 3 个商品是什么？",
    ]

    for i, q in enumerate(questions, 1):
        print(f"\n【问题 {i}】{q}")
        print("-" * 70)
        result = await agent.ask(q)

        if "error" in result:
            print(f"  ✗ 出错: {result['error']}")
            continue

        tool = result.get("tool")
        tool_result = result.get("result", {})
        print(f"  → 选中工具: {tool}")

        # Pretty-print the result based on tool family.
        if tool == "get_low_stock_products":
            rows = tool_result.get("rows", [])
            print(f"  → 返回 {len(rows)} 个低库存商品:")
            print(_format_rows_for_humans(rows))
        elif tool == "ask_knowledge_base":
            chunks = tool_result.get("chunks", [])
            print(f"  → 命中 {len(chunks)} 个知识库片段:")
            for j, c in enumerate(chunks[:3], 1):
                print(f"    [{j}] {c.get('title','(no title)')} (score={c.get('score',0):.2f})")
                text = c.get("text", "").strip().replace("\n", " ")
                print(f"        {text[:140]}...")
        elif tool == "query_database":
            rows = tool_result.get("rows", [])
            sql = tool_result.get("sql", "")
            print(f"  → 生成 SQL ({tool_result.get('elapsed_ms', 0)}ms):")
            print(f"    {sql}")
            print(f"  → 返回 {len(rows)} 行:")
            print(_format_rows_for_humans(rows))
        else:
            print(f"  → 原始结果: {str(tool_result)[:300]}...")

    # ----- Cleanup -----
    await pool.close()
    print()
    print("=" * 70)
    print("  ERP Copilot 单 Agent 演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(_run_demo())
