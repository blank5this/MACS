"""Gradio wrapper for the ERP AI Copilot — 2-tab live demo.

Tab 1 (📚 政策问答)  — RAG over 18 Chinese policy docs (no DB needed)
Tab 2 (📊 Text2SQL)   — natural language → safe SQL → SQLite (auto-seeded on first run)

Run locally::

    pip install -r requirements_hf.txt
    export MINIMAX_API_KEY=sk-...
    python app.py          # → http://localhost:7860

Deploy: this file is the entry point for HF Spaces / Render / any Gradio host.
Set MINIMAX_API_KEY (or ANTHROPIC_API_KEY) in the host's env / secrets.
Without a key, both tabs fall back to a deterministic mode so the demo
still shows the retrieval and query execution layers.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import gradio as gr

from macs_pkg.erp.demo import (
    INTENT_EXAMPLES,
    Text2SQLResult,
    init_db,
    route_intent,
    run as run_text2sql,
    safety_check,
)
from macs_pkg.llm import MiniMaxProvider, ClaudeProvider
from macs_pkg.llm.base import LLMMessage
from macs_pkg.rag.rag_engine import RAGEngine


KB_DIR = PROJECT_ROOT / "data" / "erp_kb"


# ============================================================================
# Tab 1 — Knowledge-base RAG
# ============================================================================

_rag_engine = None
_provider = None


def _get_provider():
    global _provider
    if _provider is not None:
        return _provider
    if os.getenv("ANTHROPIC_API_KEY"):
        _provider = ClaudeProvider()
        print(f"[init] Claude provider: {_provider.model_name()}")
    elif os.getenv("MINIMAX_API_KEY"):
        _provider = MiniMaxProvider()
        print(f"[init] MiniMax provider: {_provider.model_name()}")
    else:
        print("[init] No LLM API key — RAG-only mode")
    return _provider


async def _get_rag():
    global _rag_engine
    if _rag_engine is not None:
        return _rag_engine

    _rag_engine = RAGEngine()
    _rag_engine.config.enable_hybrid = True
    _rag_engine.config.similarity_threshold = 0.0  # char-ngram scores are low

    docs_text = []
    docs_meta = []
    if KB_DIR.exists():
        for f in sorted(KB_DIR.rglob("*.md")):
            docs_text.append(f.read_text(encoding="utf-8"))
            docs_meta.append({
                "title": f.stem,
                "source": str(f.relative_to(PROJECT_ROOT)),
            })

    n = await _rag_engine.add_documents(texts=docs_text, metadatas=docs_meta)
    print(f"[init] RAG indexed: {n} chunks from {len(docs_text)} docs")
    return _rag_engine


async def ask_kb(question: str) -> tuple[str, str]:
    """Knowledge-base Q&A. Returns (answer, retrieval_log)."""
    if not question.strip():
        return "(empty question)", ""

    rag = await _get_rag()
    chunks = await rag.search(question, top_k=3)

    log_lines = []
    for i, c in enumerate(chunks, 1):
        title = c.metadata.get("title", "?") if hasattr(c, "metadata") else "?"
        score = c.score if hasattr(c, "score") else 0
        content = c.content if hasattr(c, "content") else ""
        preview = content[:200].replace("\n", " ")
        log_lines.append(f"[{i}] {title}  (score: {score:.2f})")
        log_lines.append(f"    {preview}...")
        log_lines.append("")
    retrieval_log = "\n".join(log_lines) if log_lines else "(no chunks retrieved)"

    provider = _get_provider()
    if provider is None:
        return (
            "⚠ No LLM API key configured (set MINIMAX_API_KEY or ANTHROPIC_API_KEY).\n"
            "Showing RAG retrieval only:",
            retrieval_log,
        )

    context_parts = []
    for i, c in enumerate(chunks, 1):
        content = c.content if hasattr(c, "content") else ""
        context_parts.append(f"[{i}] " + content[:500])
    context = "\n\n".join(context_parts)

    prompt = f"""你是 ERP 知识助手。基于以下知识库片段回答用户问题。
必须引用片段编号（如 [1]、[2]）。

知识库片段：
{context}

用户问题：{question}

请用简洁的中文回答（3-5 句话），并在末尾列出引用。"""

    try:
        response = await provider.complete([LLMMessage(role="user", content=prompt)])
        return response.content, retrieval_log
    except Exception as e:
        return f"❌ LLM error: {e}", retrieval_log


def ask_kb_sync(question: str) -> tuple[str, str]:
    return asyncio.run(ask_kb(question))


# ============================================================================
# Tab 2 — Text2SQL over SQLite (auto-seeded)
# ============================================================================

async def _maybe_llm_sql(question: str) -> Optional[str]:
    """If the question doesn't match a known pattern AND we have an LLM,
    ask it to write a safe SELECT query."""
    if route_intent(question) is not None:
        return None  # deterministic router handled it
    provider = _get_provider()
    if provider is None:
        return None

    schema_desc = """
Tables:
- products(sku, name, category, unit_price, on_hand, safety_stock, supplier)
- suppliers(supplier_id, name, rating, lead_time_days, on_time_rate)
- purchase_orders(po_id, sku, supplier_id, qty, unit_cost, amount, status, created_at, approver)
- sales(sale_id, sku, qty, revenue, sale_date, customer)
"""
    prompt = f"""你是 SQL 助手。基于下面的 SQLite schema 生成 SELECT 查询来回答用户问题。
仅输出 SQL,不要解释,不要用 markdown 包裹。

{schema_desc}

用户问题: {question}
"""
    try:
        response = await provider.complete([LLMMessage(role="user", content=prompt)])
        sql = response.content.strip().strip("`").strip()
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
        return sql
    except Exception:
        return None


async def ask_sql(question: str) -> tuple[str, str, str]:
    """Text2SQL. Returns (summary, sql, rows_text)."""
    if not question.strip():
        return "(empty question)", "", ""

    # Pre-init the DB so the first request isn't slow.
    init_db()

    # Try deterministic router first.
    if route_intent(question) is not None:
        result = run_text2sql(question)
        return result.summary, result.sql, result.rows_text

    # Fall back to LLM-generated SQL.
    sql = await _maybe_llm_sql(question)
    if sql is None:
        return (
            "⚠ No LLM API key and the question didn't match a known pattern.\n"
            "Try one of the example questions or set MINIMAX_API_KEY.",
            "",
            "",
        )
    safety_error = safety_check(sql)
    if safety_error:
        return f"❌ {safety_error}", sql, ""
    try:
        conn = init_db()
        cur = conn.execute(sql)
        rows = cur.fetchall()
        from macs_pkg.erp.demo.text2sql_demo import _format_rows
        return (
            f"✓ LLM-generated query returned {len(rows)} rows.",
            sql,
            _format_rows(rows),
        )
    except Exception as e:
        return f"❌ SQL error: {e}", sql, ""


def ask_sql_sync(question: str) -> tuple[str, str, str]:
    return asyncio.run(ask_sql(question))


# ============================================================================
# Gradio UI
# ============================================================================

KB_EXAMPLES = [
    ["如何处理采购退货？"],
    ["库存安全线是什么？如何设置补货策略？"],
    ["供应商评级有哪些等级？"],
    ["ABC 分析法是什么？"],
    ["采购审批流程是什么？"],
    ["三方匹配的容差规则是什么？"],
]

SQL_EXAMPLES = [[q] for q, _ in INTENT_EXAMPLES]


def _build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="ERP AI Copilot — Live Demo",
        theme=gr.themes.Soft(primary_hue="blue"),
    ) as demo:
        gr.Markdown(
            """
# 🤖 ERP AI Copilot — Live Demo

An AI assistant for ERP / inventory / procurement questions.
Built on [MACS (Multi-Agent Collaboration Stack)](https://github.com/blank5this/MACS) — MIT licensed, 256 tests passing.
"""
        )

        with gr.Tabs():
            with gr.Tab("📚 政策问答 (RAG)"):
                gr.Markdown(
                    "**Hybrid retrieval over 18 Chinese policy documents** — "
                    "char-ngram + BM25 + RRF (see ADR-004)."
                )
                kb_in = gr.Textbox(
                    label="Ask a question (Chinese)",
                    placeholder="如何处理采购退货？",
                    lines=2,
                )
                kb_btn = gr.Button("Ask", variant="primary")
                kb_out_answer = gr.Textbox(label="AI Answer", lines=6)
                kb_out_log = gr.Textbox(label="RAG Retrieval (top-3 chunks)", lines=12)
                gr.Examples(
                    examples=KB_EXAMPLES,
                    inputs=kb_in,
                    label="Example questions (click to load)",
                )
                kb_btn.click(
                    fn=ask_kb_sync,
                    inputs=kb_in,
                    outputs=[kb_out_answer, kb_out_log],
                )

            with gr.Tab("📊 Text2SQL"):
                gr.Markdown(
                    "**Natural language → safe SQL → SQLite** — "
                    "auto-seeded with 8 products, 5 suppliers, 10 POs, 10 sales.\n\n"
                    "Read-only SQL guardrail (no DROP / DELETE / INSERT / UPDATE). "
                    "See ADR-003 for the 4-layer production version."
                )
                sql_in = gr.Textbox(
                    label="Ask a question",
                    placeholder="上个月销售额最高的 3 个商品是什么？",
                    lines=2,
                )
                sql_btn = gr.Button("Query", variant="primary")
                sql_out_answer = gr.Textbox(label="Summary", lines=3)
                sql_out_sql = gr.Textbox(label="Generated SQL", lines=4)
                sql_out_rows = gr.Textbox(label="Result rows", lines=12)
                gr.Examples(
                    examples=SQL_EXAMPLES,
                    inputs=sql_in,
                    label="Example questions (click to load)",
                )
                sql_btn.click(
                    fn=ask_sql_sync,
                    inputs=sql_in,
                    outputs=[sql_out_answer, sql_out_sql, sql_out_rows],
                )

        gr.Markdown(
            """
---
**Source**: [github.com/blank5this/MACS](https://github.com/blank5this/MACS) · **License**: MIT · **Tech**: Python · FastAPI · Gradio · SQLite · Hybrid RAG
"""
        )

    return demo


demo = _build_ui()


if __name__ == "__main__":
    print("=" * 60)
    print("  ERP AI Copilot — Gradio Demo (2 tabs)")
    print("=" * 60)
    print(f"  KB dir:      {KB_DIR}  (exists={KB_DIR.exists()})")
    print(f"  Provider:    "
          f"{'Claude' if os.getenv('ANTHROPIC_API_KEY') else 'MiniMax' if os.getenv('MINIMAX_API_KEY') else 'NONE (fallback mode)'}")
    print()
    # Pre-warm so first request is fast
    asyncio.run(_get_rag())
    init_db()
    print("[init] Pre-warm complete. Launching UI on :7860 …")
    demo.launch(server_name="0.0.0.0", server_port=7860)