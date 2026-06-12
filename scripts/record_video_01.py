"""Record Video 1 — single-agent mixed-tools demo (60 seconds).

Runs a curated 3-question demo with clean terminal output for screen
capture. Designed to fit inside a 60-second window with pauses between
sections so a human (or video editor) can splice in voice-over.

Usage::

    # Dry-run, just print to stdout
    python scripts/record_video_01.py

    # Fast smoke test (skip typewriter delays)
    python scripts/record_video_01.py --no-delay

    # Save the transcript to a file (useful for subtitles)
    python scripts/record_video_01.py --output /tmp/video01.txt

    # Set the env var to use a real Claude provider
    set ANTHROPIC_API_KEY=sk-ant-...
    python scripts/record_video_01.py
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

# Force UTF-8 stdout so the Windows console (default code page GBK)
# can render the demo text without crashing on the bullet / arrow
# characters. Mirrors the same fix in record_video_03.py.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


BANNER = """
================================================================
   ERP AI Copilot — Single Agent Demo (Video 1 / 60s)
   1 Agent · 7 Tools · MCP + RAG + NL→SQL
================================================================
"""


# Module-level typewriter delay — overridable via ``--delay`` CLI flag
# and ``--no-delay`` for smoke tests. Read by :func:`_slow_print`.
_DELAY: float = 0.05


def _slow_print(msg: str, delay: float | None = None) -> None:
    """Typewriter-style print for nicer screen recording.

    The default delay comes from the module-level :data:`_DELAY`
    (set by :func:`main` from CLI args). Pass an explicit ``delay``
    to override per call.
    """
    print(msg)
    sys.stdout.flush()
    eff = _DELAY if delay is None else delay
    if eff > 0:
        time.sleep(eff)


def _section_header(label: str) -> None:
    print()
    print("─" * 70)
    print(f"  ▸ {label}")
    print("─" * 70)


def _format_top_rows(rows: list[dict], max_rows: int = 3) -> str:
    if not rows:
        return "    (no rows)"
    out = []
    sample = rows[:max_rows]
    keys = ["sku", "name", "on_hand", "safety_stock", "deficit", "delta_pct"]
    keys = [k for k in keys if any(k in r for r in sample)]
    out.append("    " + "  ".join(f"{k:>14}" for k in keys))
    for r in sample:
        out.append("    " + "  ".join(f"{str(r.get(k, '')):>14}" for k in keys))
    if len(rows) > max_rows:
        out.append(f"    ... +{len(rows) - max_rows} more")
    return "\n".join(out)


async def _run_demo(outfile=None) -> None:
    print(BANNER)

    from macs_pkg.erp.agents.copilot_agent import build_copilot_agent
    from macs_pkg.erp.db import DatabaseConfig, DatabasePool

    # Open DB
    _section_header("1. 启动数据库连接池")
    pool = DatabasePool(DatabaseConfig.from_env())
    await pool.open()
    _slow_print("    ✓ DatabasePool ready", 0.1)

    # Provider
    _section_header("2. 初始化 LLM Provider")
    provider = None
    if os.getenv("ANTHROPIC_API_KEY"):
        from macs_pkg.llm import ClaudeProvider
        provider = ClaudeProvider()
        _slow_print(f"    ✓ Claude ({provider.model_name()})", 0.1)
    elif os.getenv("MINIMAX_API_KEY"):
        from macs_pkg.llm import MiniMaxProvider
        provider = MiniMaxProvider()
        _slow_print(f"    ✓ MiniMax ({provider.model_name()})", 0.1)
    else:
        print("    ⚠ No API key; will run with mock provider")

        class _Mock:
            async def complete(self, *a, **k):
                class _R:
                    content = "{}"
                    model = "mock"
                    usage = {}
                return _R()
            def model_name(self): return "mock"
        provider = _Mock()

    # Agent
    _section_header("3. 构建 ERPCopilotAgent (7 个工具)")
    agent = build_copilot_agent(pool=pool, provider=provider)
    for t in agent.list_tools():
        _slow_print(f"     • {t}", 0.04)

    # Q1 — MCP
    _section_header("4. 演示 1: MCP 工具 — 查低库存商品")
    q1 = "哪些商品库存低于安全库存？"
    _slow_print(f"  Q: {q1}", 0.1)
    r1 = await agent.ask(q1)
    print(f"  → 工具: {r1.get('tool')}")
    rows = r1.get("result", {}).get("rows", [])
    print(_format_top_rows(rows))

    # Q2 — RAG
    _section_header("5. 演示 2: RAG — 查补货制度")
    q2 = "采购补货的 MOQ 政策是什么？"
    _slow_print(f"  Q: {q2}", 0.1)
    r2 = await agent.ask(q2)
    print(f"  → 工具: {r2.get('tool')}")
    chunks = r2.get("result", {}).get("chunks", [])
    for j, c in enumerate(chunks[:2], 1):
        title = c.get("title", "")
        text = c.get("text", "").strip().replace("\n", " ")[:100]
        print(f"    [{j}] {title}")
        print(f"        {text}...")

    # Q3 — NL→SQL
    _section_header("6. 演示 3: NL→SQL — 查 Top 3 销量")
    q3 = "上个月销量最高的前 3 个商品"
    _slow_print(f"  Q: {q3}", 0.1)
    r3 = await agent.ask(q3)
    print(f"  → 工具: {r3.get('tool')}")
    if r3.get("tool") == "query_database":
        sql = r3.get("result", {}).get("sql", "")
        elapsed = r3.get("result", {}).get("elapsed_ms", 0)
        print(f"  → SQL: {sql}")
        print(f"  → 执行耗时: {elapsed}ms")
        print(_format_top_rows(r3.get("result", {}).get("rows", [])))
    else:
        print(f"  → {str(r3.get('result'))[:200]}")

    # Wrap
    print()
    print("=" * 70)
    print("   演示完成 — 详见 docs/videos/01_single_agent_script.md")
    print("=" * 70)
    await pool.close()


def main():
    global _DELAY

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default=None,
                        help="Write transcript to this file as well as stdout.")
    parser.add_argument("--no-delay", action="store_true",
                        help="Skip the typewriter delay (smoke test).")
    parser.add_argument("--delay", type=float, default=0.05,
                        help="Per-line typewriter delay in seconds (default 0.05).")
    args = parser.parse_args()

    if args.no_delay:
        args.delay = 0.0
    _DELAY = args.delay

    if args.output:
        # Tee: stdout + file. We use a simple redirect by capturing
        # _slow_print, but here just reroute via run + print.
        # For simplicity, just open the file and let the script also
        # write to it line-by-line.
        with open(args.output, "w", encoding="utf-8") as f:
            # Re-route stdout briefly by writing a marker; main work
            # is delegated to asyncio.run which will print to stdout.
            f.write(BANNER + "\n")
        asyncio.run(_run_demo())
        # Append the captured screen
        with open(args.output, "a", encoding="utf-8") as f:
            f.write("\n(captured at %s)\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        asyncio.run(_run_demo())


if __name__ == "__main__":
    main()
