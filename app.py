"""Gradio wrapper for the ERP AI Copilot — 3-tab live demo.

Tab 1 (📚 政策问答)     — RAG over 18 Chinese policy docs (no DB needed)
Tab 2 (📊 Text2SQL)      — natural language → safe SQL → SQLite (auto-seeded on first run)
Tab 3 (🚀 Multi-Agent)   — Full Planner→Tools→Reviewer pipeline (auto-runs on startup)

Run locally::

    pip install -r requirements_hf.txt
    export MINIMAX_API_KEY=sk-...
    python app.py          # → http://localhost:7860

Deploy: this file is the entry point for HF Spaces / Render / any Gradio host.
Set MINIMAX_API_KEY (or ANTHROPIC_API_KEY) in the host's env / secrets.
Without a key, all tabs fall back to a deterministic mode so the demo
still shows the retrieval, query, and pipeline layers.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# 跨平台强制 UTF-8 I/O（修 Windows cp936 中文乱码）
from macs_pkg._compat import force_utf8_io
force_utf8_io()

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
# Tab 3 — Multi-Agent End-to-End Demo (Planner → Tools → Reviewer)
# ============================================================================

DEFAULT_AGENT_QUESTION = "分析未来 30 天库存风险并给出采购建议"


def run_multi_agent_demo(question: str) -> tuple[str, str, str]:
    """跑完整多 agent 链路。返回 (链路摘要, 报告 markdown, trace JSON 摘要)。"""
    if not question.strip():
        question = DEFAULT_AGENT_QUESTION
    # 复用 examples/interview_demo.py 的 run_interview（不重写）
    from examples.interview_demo import run_interview
    from pathlib import Path

    try:
        result, latency_ms = asyncio.run(run_interview(question=question))
    except Exception as exc:
        return (
            f"❌ 启动失败: {exc.__class__.__name__}: {exc}\n\n"
            "(检查 .env 里的 MINIMAX_API_KEY / ANTHROPIC_API_KEY，或直接打开 http://localhost:7860 看 mock 模式)",
            "",
            "",
        )

    plan = result.get("plan")
    analyses = result.get("analyses") or []
    recs = result.get("purchase_recs") or []
    final = result.get("final_report") or ""
    success = result.get("success")
    error = result.get("error")

    summary = (
        f"**链路**：用户问题 → Planner → Tools/RAG/SQL → Reviewer → 报告\n\n"
        f"**节点状态**：\n"
        f"- [1/5] Planner   : {'✓' if plan else '✗'}  "
        f"(steps={len(plan.get('steps') or []) if isinstance(plan, dict) else 0})\n"
        f"- [2/5] Tools/RAG : {'✓' if analyses else '✗'}  "
        f"(analyses={len(analyses) if isinstance(analyses, list) else 'n/a'})\n"
        f"- [3/5] SQL       : {'✓' if recs else '✗'}  "
        f"(purchase_recs={len(recs) if isinstance(recs, list) else 'n/a'})\n"
        f"- [4/5] Reviewer  : {'✓' if final else '✗'}  "
        f"(final_report={len(final)} 字符)\n"
        f"- [5/5] 报告落盘  : ✓  (`examples/output/inventory_risk_report.md`)\n\n"
        f"**耗时**：{latency_ms:.0f}ms\n\n"
        f"**成功**：{'✓ ' + str(success) if success else '✗ ' + str(error)}"
    )

    # 报告：如果是 JSON 嵌套就提示；否则原样展示
    report_md = final if final else "_(报告为空)_"
    if final and final.lstrip().startswith("{"):
        report_md = (
            "> ⚠️ 当前 LLM 在 review 阶段返回了结构化 JSON 报文，"
            "demo 已落盘但**未自动渲染为 Markdown**。\n\n"
            "<details><summary>点击展开 raw JSON（截断 3000 字符）</summary>\n\n"
            "```json\n" + final[:3000] + "\n```\n\n</details>\n"
        )

    # trace 摘要：4 个关键字段
    trace_md = (
        f"```json\n{{\n"
        f'  "success": {str(success).lower()},\n'
        f'  "elapsed_ms": {result.get("elapsed_ms", 0)},\n'
        f'  "question": "{result.get("question", "")[:50]}",\n'
        f'  "final_report_chars": {len(final)},\n'
        f'  "plan": {"<dict>" if plan else "None"},\n'
        f'  "analyses": {len(analyses) if isinstance(analyses, list) else "n/a"},\n'
        f'  "purchase_recs": {len(recs) if isinstance(recs, list) else "n/a"}\n'
        f"}}\n```\n\n"
        f"完整 trace JSON 落盘到 `examples/output/inventory_risk_trace.json`"
    )

    return summary, report_md, trace_md


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

            with gr.Tab("🚀 Multi-Agent Demo"):
                gr.Markdown(
                    "**完整 5 节点链路** (Planner → Tools/RAG/SQL → Reviewer → 报告) — "
                    "基于自研 **MACS** 多 Agent 框架。\n\n"
                    "无 API key 也能跑：`_NullProvider` 兜底，6ms 出结构化演示。"
                )
                agent_in = gr.Textbox(
                    label="业务问题",
                    value=DEFAULT_AGENT_QUESTION,
                    placeholder=DEFAULT_AGENT_QUESTION,
                    lines=2,
                )
                agent_btn = gr.Button("🚀 Run Multi-Agent Demo", variant="primary")
                agent_out_summary = gr.Markdown(label="链路摘要")
                agent_out_report = gr.Markdown(label="最终报告")
                agent_out_trace = gr.Markdown(label="Trace 摘要")
                gr.Examples(
                    examples=[
                        [DEFAULT_AGENT_QUESTION],
                        ["哪些 SKU 的库存低于安全库存线？"],
                        ["上个月销售排名前 10 的商品有哪些？"],
                        ["评估所有供应商的交付准时率"],
                    ],
                    inputs=agent_in,
                    label="Example 业务问题 (click to load)",
                )
                agent_btn.click(
                    fn=run_multi_agent_demo,
                    inputs=agent_in,
                    outputs=[agent_out_summary, agent_out_report, agent_out_trace],
                )
                # 注：Gradio 6 startup-events 不允许慢函数（>5s），会 502
                # 不在 demo.load 触发，改为打开页面后用户点按钮启动

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
    print("  ERP AI Copilot — Gradio Demo (3 tabs)")
    print("=" * 60)
    print(f"  KB dir:      {KB_DIR}  (exists={KB_DIR.exists()})")
    print(f"  Provider:    "
          f"{'Claude' if os.getenv('ANTHROPIC_API_KEY') else 'MiniMax' if os.getenv('MINIMAX_API_KEY') else 'NONE (fallback mode)'}")
    print()
    # Pre-warm so first request is fast
    asyncio.run(_get_rag())
    init_db()
    print("[init] Pre-warm complete. Launching UI on :7860 …")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
    )