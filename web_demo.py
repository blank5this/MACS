"""最简浏览器 demo：单文件 FastAPI + 内嵌 HTML。

启动时跑一次 multi-agent demo，浏览器打开 http://localhost:8000/ 立即看到结果。
无 API key 也能跑（_NullProvider 兜底）。

跑法::

    pip install fastapi uvicorn
    MINIMAX_API_KEY=sk-... python web_demo.py
    # → http://localhost:8000/
"""
from __future__ import annotations

import asyncio
import html
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "examples"))

# 修 Windows 中文乱码
from macs_pkg._compat import force_utf8_io
force_utf8_io()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

from examples.interview_demo import run_interview, OUTPUT_DIR

DEFAULT_QUESTION = "分析未来 30 天库存风险并给出采购建议"

app = FastAPI(title="ERP AI Copilot — Browser Demo")

# 全局状态：启动时跑一次 + /rerun 重新跑
_state: dict[str, Any] = {"result": None, "latency_ms": 0.0, "error": None}


async def _run_once(question: str = DEFAULT_QUESTION) -> None:
    """跑一次 demo，写到 _state。"""
    try:
        result, latency_ms = await run_interview(question=question)
        _state["result"] = result
        _state["latency_ms"] = latency_ms
        _state["error"] = result.get("error") if isinstance(result, dict) else None
    except Exception as exc:
        _state["error"] = f"{exc.__class__.__name__}: {exc}"


def _render_html() -> str:
    """渲染单页 HTML（启动时一次结果 + rerun 按钮）。"""
    if _state["result"] is None and _state["error"]:
        return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>ERP AI Copilot</title>
<style>body{{font-family:system-ui;max-width:920px;margin:40px auto;padding:0 20px;color:#222}}
h1{{color:#0b5fff}}.err{{background:#fee;border-left:4px solid #c00;padding:12px 16px}}</style>
</head><body>
<h1>🤖 ERP AI Copilot — Multi-Agent Demo</h1>
<div class="err">❌ 启动失败: {html.escape(_state['error'])}<br>
请检查 .env 里的 MINIMAX_API_KEY / ANTHROPIC_API_KEY</div>
</body></html>"""

    result = _state["result"] or {}
    plan = result.get("plan")
    analyses = result.get("analyses") or []
    recs = result.get("purchase_recs") or []
    final = result.get("final_report") or ""
    success = result.get("success")
    error = result.get("error")
    latency_ms = _state["latency_ms"]

    summary_md = (
        f"**链路**：用户问题 → Planner → Tools/RAG/SQL → Reviewer → 报告\n\n"
        f"**节点**：\n"
        f"- [1/5] Planner   : {'✓' if plan else '✗'}\n"
        f"- [2/5] Tools/RAG : {'✓' if analyses else '✗'}\n"
        f"- [3/5] SQL       : {'✓' if recs else '✗'}\n"
        f"- [4/5] Reviewer  : {'✓' if final else '✗'}  ({len(final)} 字符)\n"
        f"- [5/5] 报告落盘  : ✓  (`examples/output/inventory_risk_report.md`)\n\n"
        f"**耗时**：{latency_ms:.0f}ms  |  **成功**：{success}"
    )

    # 报告：raw JSON → Markdown 警告
    if final.lstrip().startswith("{"):
        report_md = (
            f"⚠️ LLM review 阶段返回了结构化 JSON，**未自动渲染为 Markdown**。\n\n"
            f"<details><summary>点击展开 raw JSON（截断 3000 字符）</summary>\n\n"
            f"```json\n{final[:3000]}\n```\n\n</details>"
        )
    else:
        report_md = final or "_(报告为空)_"

    # 关键 trace
    trace_md = (
        f"- success: `{success}`\n"
        f"- elapsed_ms: `{result.get('elapsed_ms', 0)}`\n"
        f"- final_report: `{len(final)}` 字符\n"
        f"- plan: `{bool(plan)}`  / analyses: `{len(analyses) if isinstance(analyses, list) else 'n/a'}`  / recs: `{len(recs) if isinstance(recs, list) else 'n/a'}`\n"
        f"- 完整 trace 落盘: `examples/output/inventory_risk_trace.json`"
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>ERP AI Copilot — Multi-Agent Demo</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  max-width:1080px;margin:32px auto;padding:0 20px;color:#1a1a1a;line-height:1.6}}
h1{{color:#0b5fff;margin-bottom:6px}}
.subtitle{{color:#666;font-size:14px;margin-bottom:24px}}
.card{{background:#f8f9fb;border:1px solid #e5e8ed;border-radius:8px;
  padding:18px 22px;margin:18px 0}}
.card h2{{margin:0 0 12px;font-size:17px;color:#0b5fff}}
pre{{background:#0d1117;color:#c9d1d9;padding:14px;border-radius:6px;
  overflow-x:auto;font-size:13px}}
.metric{{display:inline-block;background:#e8f0ff;padding:4px 10px;border-radius:12px;
  margin:2px 6px 2px 0;font-size:13px}}
.btn{{display:inline-block;background:#0b5fff;color:#fff;padding:8px 18px;
  border-radius:6px;text-decoration:none;font-size:14px;border:none;cursor:pointer}}
.btn:hover{{background:#0949cc}}
.note{{color:#666;font-size:13px;font-style:italic}}
</style>
</head>
<body>
<h1>🤖 ERP AI Copilot — Multi-Agent Demo</h1>
<div class="subtitle">
  基于自研 <b>MACS</b> 多 Agent 框架 | 5 节点链路: Planner → Tools/RAG/SQL → Reviewer → 报告
</div>

<div class="card">
<h2>📊 链路摘要</h2>
<pre>{html.escape(summary_md)}</pre>
<button class="btn" onclick="rerun()">🔄 重新跑一次</button>
<span class="note" id="rerun-status"></span>
</div>

<div class="card">
<h2>📄 最终报告</h2>
<pre>{html.escape(report_md)}</pre>
</div>

<div class="card">
<h2>🔍 Trace 摘要</h2>
<pre>{html.escape(trace_md)}</pre>
</div>

<script>
async function rerun() {{
  const el = document.getElementById('rerun-status');
  el.textContent = '⏳ 跑中... (真实 LLM 25-50s)';
  try {{
    const r = await fetch('/rerun');
    const d = await r.json();
    if (d.ok) {{
      el.textContent = '✓ 已重跑，刷新页面看新结果';
      setTimeout(() => location.reload(), 1000);
    }} else {{
      el.textContent = '✗ 失败: ' + d.error;
    }}
  }} catch (e) {{
    el.textContent = '✗ ' + e;
  }}
}}
</script>
</body>
</html>"""


@app.on_event("startup")
async def _startup_run():
    """启动时跑一次 multi-agent demo，让用户打开浏览器立即看到结果。"""
    await _run_once()


@app.get("/", response_class=HTMLResponse)
async def index():
    return _render_html()


@app.get("/rerun")
async def rerun():
    """手动触发重跑（前端按钮调用）。"""
    await _run_once()
    if _state["error"] and not _state["result"]:
        return {"ok": False, "error": _state["error"]}
    return {"ok": True, "latency_ms": _state["latency_ms"]}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8000"))
    print("=" * 60)
    print("  ERP AI Copilot — Browser Demo")
    print("=" * 60)
    print(f"  → http://127.0.0.1:{port}/")
    print(f"  Provider: {'MiniMax' if os.getenv('MINIMAX_API_KEY') else 'Claude' if os.getenv('ANTHROPIC_API_KEY') else 'NONE (fallback mode)'}")
    print()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
