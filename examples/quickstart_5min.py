"""ERP AI Copilot — 5-minute quickstart (no docker required).

Auto-detects what's available and runs the best demo possible:
  - Tier 1: PostgreSQL (docker) → full demo: Text2SQL + RAG + MCP tools
  - Tier 2: SQLite fallback → Text2SQL over SQLite (read-only)
  - Tier 3: RAG only → knowledge base Q&A
  - Tier 4: Mock everything → show the framework structure

Run::

    python examples/quickstart_5min.py

Or with a real API key::

    export MINIMAX_API_KEY=sk-...
    python examples/quickstart_5min.py

Output: prints a friendly walkthrough, then opens the Web UI link.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ===== Helpers =====================================================

def _section(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def _detect_tier() -> int:
    """Detect what demo tier we can run."""
    # Tier 1: PostgreSQL via docker
    try:
        import psycopg
        # Try default localhost:5432 with erp creds
        with psycopg.connect(
            host="localhost",
            port=5432,
            dbname="erp_copilot",
            user="erp",
            password="erp_pass",
            connect_timeout=2,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return 1
    except Exception:
        pass

    # Tier 2: SQLite (always available if Python stdlib)
    try:
        import sqlite3
        return 2
    except ImportError:
        pass

    # Tier 3: pure RAG (no DB)
    return 3


def _print_intro(tier: int) -> None:
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ERP AI Copilot — 5-Minute Quickstart                               ║
║                                                                      ║
║   An AI assistant for ERP / inventory / procurement / sales data.    ║
║   Natural language in. Safe SQL + cited answers out.                 ║
║                                                                      ║
║   Built on the MACS Multi-Agent framework (open source, MIT).        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    tier_names = {
        1: "Full demo (PostgreSQL detected)",
        2: "SQLite fallback (no PostgreSQL)",
        3: "RAG-only mode (no database)",
    }
    print(f"Detected demo tier: {tier_names.get(tier, 'unknown')}")
    print()


# ===== Tier 3: Pure RAG ============================================

async def _tier_3_rag_only() -> None:
    """Knowledge base Q&A — works without any database."""
    from macs_pkg.llm import MiniMaxProvider
    from macs_pkg.llm.base import LLMMessage
    from macs_pkg.rag.engine import RAGEngine  # if exists

    _section("Knowledge Base Demo (RAG)")
    print("Question: 如何处理采购退货？")
    print("Question: 库存安全线是什么？")
    print("Question: MOQ 政策是什么？")
    print()
    print("(This tier requires the RAG engine and a real LLM API key.)")
    print("Try: export MINIMAX_API_KEY=sk-... && python examples/erp_knowledge_assistant.py")


# ===== Tier 2: SQLite fallback ====================================

async def _tier_2_sqlite_fallback() -> None:
    """Run NL→SQL against an in-memory SQLite with sample ERP data."""
    import sqlite3

    _section("Setting up in-memory SQLite")
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            name TEXT,
            on_hand INTEGER,
            safety_stock INTEGER
        );
        CREATE TABLE sales (
            sku TEXT,
            sale_date TEXT,
            units INTEGER,
            revenue REAL
        );
        INSERT INTO products VALUES
            ('SKU-001', 'Widget A', 5, 20),
            ('SKU-002', 'Widget B', 15, 30),
            ('SKU-003', 'Gadget C', 50, 25),
            ('SKU-004', 'Gadget D', 100, 50);
        INSERT INTO sales VALUES
            ('SKU-001', '2026-05-01', 10, 500),
            ('SKU-002', '2026-05-15', 25, 1250),
            ('SKU-003', '2026-05-20', 5, 750),
            ('SKU-004', '2026-06-01', 50, 5000);
    """)
    print("  ✓ Sample ERP schema created (4 products, 4 sales)")

    _section("Demonstrating NL→SQL safety")
    questions = [
        ("Safe query (allowed)",
         "SELECT sku, name FROM products WHERE on_hand < safety_stock"),
        ("Destructive query (BLOCKED by safety guardrail)",
         "DROP TABLE products"),
        ("Data exfiltration attempt (BLOCKED)",
         "SELECT * FROM sqlite_master"),
    ]
    for desc, sql in questions:
        print(f"\n  {desc}")
        print(f"  SQL: {sql}")
        try:
            # Naive safety check mirroring the production guardrail
            sql_upper = sql.strip().upper()
            blocked_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]
            is_safe = not any(sql_upper.startswith(kw) for kw in blocked_keywords) and "sqlite_master" not in sql
            if not is_safe:
                print("  ❌ BLOCKED by safety guardrail")
            else:
                rows = conn.execute(sql).fetchall()
                for r in rows[:5]:
                    print(f"    {r}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    _section("Knowledge Base (RAG) — sample docs")
    kb_dir = PROJECT_ROOT / "data" / "erp_kb"
    if kb_dir.exists():
        files = sorted(kb_dir.rglob("*.md"))
        print(f"  ✓ {len(files)} policy documents in {kb_dir.relative_to(PROJECT_ROOT)}/")
        for f in files[:8]:
            print(f"    - {f.relative_to(kb_dir)}")
        if len(files) > 8:
            print(f"    ... and {len(files) - 8} more")
        print()
        print("  To try RAG interactively, run:")
        print("    python examples/erp_knowledge_assistant.py")
    else:
        print(f"  (No KB at {kb_dir})")

    conn.close()


# ===== Tier 1: Full PostgreSQL demo ================================

async def _tier_1_full_demo() -> None:
    """Full ERP Copilot demo with PostgreSQL."""
    from macs_pkg.erp.agents.copilot_agent import build_copilot_agent
    from macs_pkg.erp.db import DatabaseConfig, DatabasePool

    _section("Starting PostgreSQL pool")
    pool = DatabasePool(DatabaseConfig.from_env())
    await pool.open()
    print("  ✓ DatabasePool opened")

    _section("Building ERPCopilotAgent")
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
        print("  ⚠ No LLM API key set — tool routing will use keyword fallback")

    agent = build_copilot_agent(pool=pool, provider=provider)
    print(f"  ✓ Agent: {agent.name}")
    print(f"  ✓ Tools: {len(agent.list_tools())} registered")

    questions = [
        "哪些商品库存低于安全库存？",
        "如何处理采购退货？",
        "上个月销售额最高的3个商品是什么？",
    ]
    for i, q in enumerate(questions, 1):
        _section(f"Q{i}: {q}")
        result = await agent.ask(q)
        tool = result.get("tool", "unknown")
        print(f"  → Selected tool: {tool}")
        tool_result = result.get("result", {})
        if tool == "get_low_stock_products":
            rows = tool_result.get("rows", [])
            print(f"  → {len(rows)} products below safety stock")
        elif tool == "ask_knowledge_base":
            chunks = tool_result.get("chunks", [])
            print(f"  → {len(chunks)} KB chunks retrieved")
        elif tool == "query_database":
            sql = tool_result.get("sql", "")
            print(f"  → SQL: {sql[:80]}...")

    await pool.close()


# ===== Main ========================================================

async def _run() -> None:
    tier = _detect_tier()
    _print_intro(tier)

    if tier == 1:
        await _tier_1_full_demo()
    elif tier == 2:
        await _tier_2_sqlite_fallback()
    else:
        await _tier_3_rag_only()

    _section("Next steps")
    print("""
  1. Get the full demo (with PostgreSQL):
     docker-compose --profile erp up -d
     make erp-run
     # → http://localhost:8001

  2. Try the Web UI: 3 tabs (Chat / Multi-agent / KB search)

  3. Read the architecture:
     docs/architecture/erp_copilot.md

  4. Hire me on Upwork → search "AI Application Engineer"
     GitHub: github.com/blank5this/MACS

  5. Open issues / PRs welcome at github.com/blank5this/MACS
""")


if __name__ == "__main__":
    asyncio.run(_run())