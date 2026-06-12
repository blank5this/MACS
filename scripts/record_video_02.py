"""Day 11 — Video 2 recorder: clean 60s multi-agent demo.

This script drives :class:`InventoryRiskWorkflow` end-to-end with a
**scripted LLM provider** (mirroring the pattern used in
``tests/test_inventory_workflow.py``) so the demo always succeeds and
produces deterministic output suitable for a screen-recorded 60s
video.

The script is designed to be recorded straight to the terminal:

    1. A banner with project name + version.
    2. Build the 4 agents (planner, inventory analyst, purchase
       specialist, report writer).
    3. Run the workflow.
    4. Print the 4 stages with section headers, with typewriter
       delays so a screen recorder can capture each section in turn.

Usage::

    # Full 60s demo with typewriter delays
    python scripts/record_video_02.py

    # Fast smoke test (no delays)
    python scripts/record_video_02.py --no-delay

    # Save transcript to a file as well
    python scripts/record_video_02.py --output transcript.md

    # Both
    python scripts/record_video_02.py --no-delay --output transcript.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

# --- Make sure ``macs_pkg`` is importable when run from anywhere ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from macs_pkg.erp.workflows import (  # noqa: E402
    InventoryRiskWorkflow,
    run_inventory_risk_analysis,
)

# === Demo configuration =============================================

__version__ = "1.0.0-erp-copilot"

DEMO_QUESTION = "分析未来 30 天库存风险并给出采购建议"
DEMO_DATE = "2026-06-12"  # matches the project timeline (Day 11)


# === Scripted provider (same pattern as tests/test_inventory_workflow.py) ===


class _ScriptedProvider:
    """Deterministic, no-network LLM provider for the demo.

    Each call to :meth:`complete` returns the next canned response
    from ``responses``. The final response is reused for any extra
    calls so the workflow never raises on an empty queue.

    Mirrors ``_ScriptedProvider`` in
    ``tests/test_inventory_workflow.py`` so behavior is identical to
    the CI smoke test.
    """

    def __init__(self, responses: List[str]) -> None:
        self._responses = list(responses)
        self._idx = 0
        self.calls: List[dict] = []

    async def complete(self, messages=None, system=None, **kwargs):  # noqa: ANN001
        self.calls.append(
            {
                "system_snippet": (system or "")[:60] if system else "",
                "user": (messages[-1].content if messages else ""),
            }
        )
        if self._idx < len(self._responses):
            content = self._responses[self._idx]
            self._idx += 1
        else:
            content = self._responses[-1] if self._responses else "{}"

        class _R:
            pass

        r = _R()
        r.content = content
        r.model = "scripted-demo"
        r.usage = {}
        r.tool_calls = []
        r.stop_reason = "stop"
        return r

    def model_name(self) -> str:  # noqa: D401
        return "scripted-demo"


# === Canned LLM responses (Chinese, deterministic) ==================

_PLAN_OUT = json.dumps(
    {
        "subtasks": [
            {
                "id": "s1",
                "role": "erp_inventory_analyst",
                "description": "查 30 天内的低库存商品",
                "depends_on": [],
                "expected_output": "JSON",
            },
            {
                "id": "s2",
                "role": "erp_purchase_specialist",
                "description": "为低库存 SKU 匹配供应商与采购量",
                "depends_on": ["s1"],
                "expected_output": "JSON",
            },
            {
                "id": "s3",
                "role": "erp_report_writer",
                "description": "汇总成中文 Markdown 报告",
                "depends_on": ["s1", "s2"],
                "expected_output": "markdown",
            },
        ]
    },
    ensure_ascii=False,
)

_ANALYST_OUT = json.dumps(
    {
        "low_stock_count": 2,
        "items": [
            {
                "sku": "SKU-0003",
                "name": "M8 内六角螺栓",
                "category": "工具",
                "on_hand": 30,
                "safety_stock": 100,
                "deficit": 70,
                "days_of_inventory": 10.0,
                "reorder_recommendation": True,
                "trend": "rising",
                "risk_score": 8,
                "risk_level": "critical",
            },
            {
                "sku": "SKU-0007",
                "name": "PVC 绝缘手套",
                "category": "劳保",
                "on_hand": 45,
                "safety_stock": 80,
                "deficit": 35,
                "days_of_inventory": 18.0,
                "reorder_recommendation": True,
                "trend": "flat",
                "risk_score": 5,
                "risk_level": "warning",
            },
        ],
        "summary": "2 个商品低于安全库存, 其中 1 个 critical.",
    },
    ensure_ascii=False,
)

_BUYER_OUT = json.dumps(
    {
        "recommendations": [
            {
                "sku": "SKU-0003",
                "name": "M8 内六角螺栓",
                "recommended_supplier": "上海钢铁贸易",
                "supplier_id": 1,
                "recommended_quantity": 100,
                "expected_unit_cost": 10.5,
                "expected_total_cost": 1050.0,
                "lead_time_days": 7,
                "moq_note": "A 类物料 MOQ=100",
                "payment_terms": "Net 30",
                "rationale": "rating 4.5 + 报价最低",
            },
            {
                "sku": "SKU-0007",
                "name": "PVC 绝缘手套",
                "recommended_supplier": "华东劳保供应",
                "supplier_id": 2,
                "recommended_quantity": 60,
                "expected_unit_cost": 18.0,
                "expected_total_cost": 1080.0,
                "lead_time_days": 5,
                "moq_note": "MOQ=60, 可拼整箱",
                "payment_terms": "Net 30",
                "rationale": "交货最快, 一次拼满整箱",
            },
        ],
        "total_estimated_cost": 2130.0,
        "kb_citations": [
            "01_operations/06_订单审批流程.md",
            "02_procurement/03_供应商评估标准.md",
        ],
    },
    ensure_ascii=False,
)

_WRITER_OUT = (
    "# 库存风险与采购建议报告\n\n"
    "## 概览\n"
    "周期内共发现 2 个低库存 SKU, 其中 1 个为 critical 风险, "
    "建议立即下单, 总预算约 2,130 元。\n\n"
    "## 风险商品\n"
    "- **SKU-0003** M8 内六角螺栓 — critical, 缺口 70\n"
    "- **SKU-0007** PVC 绝缘手套 — warning, 缺口 35\n\n"
    "## 采购建议\n"
    "1. SKU-0003: 上海钢铁贸易 ×100 件, 7 天交货\n"
    "2. SKU-0007: 华东劳保供应 ×60 件, 5 天交货\n\n"
    "—— 由 ERPCopilotAgent (Day 8) 自动生成"
)


# === Printing helpers ===============================================


def _print_line(s: str = "", *, delay: float = 0.0) -> None:
    """Print a single line, optionally with a short delay."""
    print(s, flush=True)
    if delay > 0:
        time.sleep(delay)


def _banner() -> None:
    width = 60
    print("=" * width)
    print("  MACS ERP Copilot".center(width))
    print(f"  Day 11 — 多 Agent 协作演示  (v{__version__})".center(width))
    print("=" * width)
    print()


def _print_section(title: str, body: str, *, char: str = "-", delay: float = 0.0) -> None:
    bar = char * max(40, len(title) + 4)
    print(bar)
    print(f"  {title}")
    print(bar)
    print(body)
    print()
    if delay > 0:
        time.sleep(delay)


def _build_agents(provider: _ScriptedProvider) -> InventoryRiskWorkflow:
    """Construct the workflow (the 4 agents live inside it)."""
    wf = InventoryRiskWorkflow(
        provider=provider,
        pool=None,  # no DB needed for scripted demo
        enable_tracing=True,
        current_date=DEMO_DATE,
        project_context="MACS ERP Copilot demo (Video 2)",
    )
    return wf


async def _run_demo(delay: float, transcript_path: Optional[Path]) -> List[str]:
    """Run the workflow and return a list of transcript lines."""
    transcript: List[str] = []

    def emit(s: str) -> None:
        transcript.append(s)

    # --- 1. Banner ---------------------------------------------------
    banner_lines = [
        "=" * 60,
        "  MACS ERP Copilot",
        f"  Day 11 — 多 Agent 协作演示  (v{__version__})",
        "=" * 60,
        "",
        f"问题: {DEMO_QUESTION}",
        f"日期: {DEMO_DATE}",
        "",
    ]
    for line in banner_lines:
        _print_line(line, delay=delay * 0.3)
        emit(line)

    # --- 2. Build the 4 agents --------------------------------------
    _print_line("[1/4] 正在构建 4 个 Agent ...", delay=delay)
    emit("[1/4] 正在构建 4 个 Agent ...")
    provider = _ScriptedProvider(
        responses=[_PLAN_OUT, _ANALYST_OUT, _BUYER_OUT, _WRITER_OUT]
    )
    wf = _build_agents(provider)
    agent_names = wf.list_agents()
    for name in agent_names:
        line = f"  - {name}"
        _print_line(line, delay=delay * 0.5)
        emit(line)
    _print_line("", delay=delay * 0.5)
    emit("")

    # --- 3. Run the workflow ----------------------------------------
    _print_line("[2/4] 启动 InventoryRiskWorkflow ...", delay=delay)
    emit("[2/4] 启动 InventoryRiskWorkflow ...")
    t0 = time.monotonic()
    result = await wf.run(DEMO_QUESTION)
    elapsed = int((time.monotonic() - t0) * 1000)
    line = f"      workflow.run() 完成, 耗时 {elapsed} ms, success={result['success']}"
    _print_line(line, delay=delay)
    emit(line)
    _print_line("", delay=delay * 0.5)
    emit("")

    # --- 4. Print the 4 stages --------------------------------------
    sections = [
        (
            "Step 1/4  erp_planner — 拆解问题",
            json.dumps(result.get("plan"), ensure_ascii=False, indent=2),
        ),
        (
            "Step 2/4  erp_inventory_analyst — 风险分析",
            json.dumps(result.get("analyses"), ensure_ascii=False, indent=2),
        ),
        (
            "Step 3/4  erp_purchase_specialist — 采购建议",
            json.dumps(result.get("purchase_recs"), ensure_ascii=False, indent=2),
        ),
        (
            "Step 4/4  erp_report_writer — 最终报告",
            str(result.get("final_report") or ""),
        ),
    ]

    for title, body in sections:
        _print_section(title, body or "(empty)", char="-", delay=delay)
        emit("-" * 60)
        emit(f"  {title}")
        emit("-" * 60)
        emit(body or "(empty)")
        emit("")

    # --- 5. Summary card --------------------------------------------
    summary = [
        "=" * 60,
        "  4 Agents · 1 Question · 4 Outputs",
        f"  github.com/<org>/MACS   v{__version__}",
        "=" * 60,
        "",
    ]
    for line in summary:
        _print_line(line, delay=delay)
        emit(line)

    if transcript_path is not None:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text("\n".join(transcript), encoding="utf-8")
        print(f"[transcript saved] {transcript_path}", flush=True)

    return transcript


# === CLI =============================================================


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Day 11 — Video 2: clean 60s multi-agent demo recorder.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Also save the on-screen transcript to this file (utf-8).",
    )
    p.add_argument(
        "--no-delay",
        action="store_true",
        help="Skip typewriter delays (use for fast smoke testing).",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    delay = 0.0 if args.no_delay else 0.35

    try:
        asyncio.run(_run_demo(delay=delay, transcript_path=args.output))
    except KeyboardInterrupt:
        print("\n[aborted by user]", flush=True)
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())