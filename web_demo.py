"""最简浏览器 demo：单文件 FastAPI + 内嵌 HTML + JSON→Markdown 渲染。

启动时跑一次 multi-agent demo，浏览器打开 http://localhost:8000/ 立即看到结果。
用户可在输入框换问题实时重跑，报告**自动从 raw JSON 渲染为可读 Markdown**。

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
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "examples"))

# 修 Windows 中文乱码
from macs_pkg._compat import force_utf8_io
force_utf8_io()

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

from examples.interview_demo import run_interview, OUTPUT_DIR

DEFAULT_QUESTION = "分析未来 30 天库存风险并给出采购建议"

app = FastAPI(title="ERP AI Copilot — Browser Demo")

# 全局状态：启动时跑一次 + /ask 重新跑
_state: dict[str, Any] = {
    "result": None,
    "latency_ms": 0.0,
    "question": DEFAULT_QUESTION,
    "error": None,
}


async def _run_once(question: str) -> None:
    """跑一次 demo，写到 _state。"""
    _state["question"] = question
    try:
        result, latency_ms = await run_interview(question=question)
        _state["result"] = result
        _state["latency_ms"] = latency_ms
        _state["error"] = result.get("error") if isinstance(result, dict) else None
    except Exception as exc:
        _state["error"] = f"{exc.__class__.__name__}: {exc}"
        _state["result"] = None


# ===== JSON → Markdown 渲染 =========================================

def _render_value(v: Any, indent: int = 0) -> str:
    """把任意 JSON 值渲染为 Markdown 片段。"""
    pad = "  " * indent
    if v is None:
        return f"{pad}_null_"
    if isinstance(v, bool):
        return f"{pad}`{v}`"
    if isinstance(v, (int, float)):
        return f"{pad}`{v}`"
    if isinstance(v, str):
        # 长字符串当代码块
        if len(v) > 80 or "\n" in v:
            return f"{pad}\n{pad}```\n{v}\n{pad}```"
        return f"{pad}{v}"
    if isinstance(v, list):
        if not v:
            return f"{pad}_(empty list)_"
        lines = []
        for i, item in enumerate(v):
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}- **[{i}]**")
                lines.append(_render_value(item, indent + 1))
            else:
                lines.append(f"{pad}- {_render_value(item, 0).lstrip()}")
        return "\n".join(lines)
    if isinstance(v, dict):
        if not v:
            return f"{pad}_(empty dict)_"
        lines = []
        for k, val in v.items():
            if isinstance(val, (dict, list)) and val:
                lines.append(f"{pad}- **{k}**:")
                lines.append(_render_value(val, indent + 1))
            else:
                inline = _render_value(val, 0).lstrip()
                lines.append(f"{pad}- **{k}**: {inline}")
        return "\n".join(lines)
    return f"{pad}{v!r}"


def _try_parse_json(text: str) -> Optional[Any]:
    """从 LLM 输出中尝试提取 JSON（兼容 ```json ... ``` 包裹 + 前后有杂讯）。"""
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    # 找 ```json ... ``` 块
    if "```json" in text:
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        try:
            return json.loads(text[start:end].strip())
        except json.JSONDecodeError:
            pass
    # 找第一个 { 到最后一个 } 的内容
    if "{" in text and "}" in text:
        try:
            return json.loads(text[text.index("{"):text.rindex("}") + 1])
        except json.JSONDecodeError:
            pass
    return None


def _render_report_md(final_report: str) -> str:
    """只显示 LLM 的业务结论纯文本，**不**渲染 JSON 嵌套结构。

    策略:
    1. final_report 是 JSON → 提取 final_output 字段（LLM 写的 prose），
       原样显示（不再 _render_value 渲染为列表）
    2. final_report 是 prose → 原样显示
    3. 完整 raw 字符串折叠在 <details>
    """
    if not final_report:
        return "_(报告为空)_"
    parsed = _try_parse_json(final_report)
    if parsed is None:
        return final_report  # prose
    # 提取 LLM 业务结论的 prose
    prose = _extract_prose(parsed)
    return prose or final_report


def _extract_prose(parsed: Any, max_depth: int = 15) -> Optional[str]:
    """递归找 LLM 的 prose 结论（final_output / summary / recommendations）。

    **收集所有** final_output，取**最长**（业务结论通常在 purchase_specialist
    详细分析里，inventory_analyst 那段是"如何做"开场较短）。
    """
    if max_depth <= 0:
        return None
    found: list[str] = []

    def _walk(obj: Any, depth: int) -> None:
        if depth <= 0:
            return
        if isinstance(obj, dict):
            # 跳过 reviewer 类 agent
            agent = obj.get("agent", "")
            if isinstance(agent, str) and any(
                kw in agent.lower() for kw in ("reviewer", "report_writer", "review")
            ):
                return
            for k, v in obj.items():
                if k in ("final_output", "summary", "conclusion", "answer",
                         "recommendations", "next_actions", "report", "content"):
                    if isinstance(v, str) and len(v.strip()) >= 20:
                        found.append(v.strip())
                        # 不 early return — 收集所有
            for v in obj.values():
                _walk(v, depth - 1)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item, depth - 1)

    _walk(parsed, max_depth)
    if not found:
        return None
    # 取最长（purchase_specialist 业务分析通常最长）
    return max(found, key=len)



# ===== HTML 渲染 =====================================================

def _render_html(extra: str = "") -> str:
    """渲染单页 HTML。`extra` 是 rerun 后的临时通知。"""
    if _state["error"] and not _state["result"]:
        return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>ERP AI Copilot</title>
<style>body{{font-family:system-ui;max-width:920px;margin:40px auto;padding:0 20px;color:#222}}
h1{{color:#0b5fff}}.err{{background:#fee;border-left:4px solid #c00;padding:12px 16px;
border-radius:6px}}</style></head><body>
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
    question = _state["question"]

    summary_md = (
        f"**问题**：{question}\n\n"
        f"**链路**：用户问题 → Planner → Tools/RAG/SQL → Reviewer → 报告\n\n"
        f"**节点**：\n"
        f"- [1/5] Planner   : {'✓' if plan else '✗'}\n"
        f"- [2/5] Tools/RAG : {'✓' if analyses else '✗'}\n"
        f"- [3/5] SQL       : {'✓' if recs else '✗'}\n"
        f"- [4/5] Reviewer  : {'✓' if final else '✗'}  ({len(final)} 字符)\n"
        f"- [5/5] 报告落盘  : ✓  (`examples/output/inventory_risk_report.md`)\n\n"
        f"**耗时**：{latency_ms:.0f}ms  |  **成功**：{success}"
    )

    report_md = _render_report_md(final)

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
pre{{background:#fff;border:1px solid #e5e8ed;padding:14px;border-radius:6px;
  overflow-x:auto;font-size:13px;white-space:pre-wrap;word-wrap:break-word}}
.btn{{display:inline-block;background:#0b5fff;color:#fff;padding:8px 18px;
  border-radius:6px;text-decoration:none;font-size:14px;border:none;cursor:pointer}}
.btn:hover{{background:#0949cc}}.btn:disabled{{background:#aaa;cursor:wait}}
textarea{{width:100%;box-sizing:border-box;padding:10px;font-size:14px;
  border:1px solid #d0d7de;border-radius:6px;font-family:inherit}}
.note{{color:#666;font-size:13px;font-style:italic}}
.status{{padding:6px 12px;border-radius:4px;display:inline-block;margin-left:8px}}
.status.ok{{background:#d4edda;color:#155724}}
.status.err{{background:#f8d7da;color:#721c24}}
</style>
</head>
<body>
<h1>🤖 ERP AI Copilot — Multi-Agent Demo</h1>
<div class="subtitle">
  基于自研 <b>MACS</b> 多 Agent 框架 | 5 节点链路: Planner → Tools/RAG/SQL → Reviewer → 报告
</div>

<div class="card">
<h2>💬 输入业务问题</h2>
<form id="qform" onsubmit="return ask(event)">
<textarea name="q" id="qin" rows="3"
  placeholder="例：分析未来 30 天库存风险并给出采购建议">{html.escape(question)}</textarea>
<div style="margin-top:10px">
<button class="btn" type="submit" id="askbtn">🚀 跑一次</button>
<span class="note" id="askstatus">真实 LLM 25-50s | 无 key 用 mock 6ms</span>
{extra}
</div>
</form>
</div>

<div class="card">
<h2>📊 链路摘要</h2>
<pre>{html.escape(summary_md)}</pre>
</div>

<div class="card">
<h2>📄 最终报告</h2>
<pre>{html.escape(report_md)}</pre>
<details><summary>📂 展开 raw final_report 字符串（{len(final)} 字符）</summary>

```
{html.escape(final[:3000])}
```

</details>
</div>

<div class="card">
<h2>🔍 Trace 摘要</h2>
<pre>{html.escape(trace_md)}</pre>
</div>

<script>
async function ask(ev) {{
  ev.preventDefault();
  const q = document.getElementById('qin').value.trim();
  if (!q) return false;
  const btn = document.getElementById('askbtn');
  const status = document.getElementById('askstatus');
  btn.disabled = true;
  status.textContent = '⏳ 跑中... (25-50s)';
  try {{
    const fd = new FormData();
    fd.append('q', q);
    const r = await fetch('/ask', {{method: 'POST', body: fd}});
    const d = await r.json();
    if (d.ok) {{
      status.innerHTML = '<span class="status ok">✓ 已重跑 (' + d.latency_ms + 'ms)，刷新页面看新结果</span>';
      setTimeout(() => location.reload(), 500);
    }} else {{
      status.innerHTML = '<span class="status err">✗ 失败: ' + d.error + '</span>';
    }}
  }} catch (e) {{
    status.innerHTML = '<span class="status err">✗ ' + e + '</span>';
  }} finally {{
    btn.disabled = false;
  }}
  return false;
}}
</script>
</body>
</html>"""


# ===== FastAPI endpoints =============================================

@app.on_event("startup")
async def _startup_run():
    """启动时跑一次 multi-agent demo。"""
    await _run_once(DEFAULT_QUESTION)


@app.get("/", response_class=HTMLResponse)
async def index():
    return _render_html()


@app.post("/ask")
async def ask(q: str = Form(...)):
    """用户输入新问题后重跑。"""
    q = (q or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}
    await _run_once(q)
    if _state["error"] and not _state["result"]:
        return {"ok": False, "error": _state["error"]}
    return {"ok": True, "latency_ms": int(_state["latency_ms"])}


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
