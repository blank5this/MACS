"""ERP AI Copilot 面试一键 demo。

一个命令跑完整链路::

    python examples/interview_demo.py

输出三件套：

1. **终端** — 5 节点链路摘要（用户问题 → Planner → Tools/RAG/SQL → Reviewer → 报告）
2. ``examples/output/inventory_risk_report.md`` — 最终报告（UTF-8）
3. ``examples/output/inventory_risk_trace.json`` — 完整 trace JSON（UTF-8, ``ensure_ascii=False``）

**无 API key 也能跑**：复用 :mod:`examples.erp_copilot_multi_agent` 的 ``_NullProvider``
兜底，会输出结构化空报告 + 完整 trace 骨架，方便面试时离线演示。

不要在这个文件里重新实现 LLM 调用、agent 编排或报告生成逻辑。
全部复用 :mod:`examples.erp_copilot_multi_agent` 已实现的阶段函数。
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Tuple

# 跨平台强制 UTF-8 I/O（修 Windows cp936 中文乱码）
from macs_pkg._compat import force_utf8_io

force_utf8_io()

# 复用（不重写）：100% 使用 erp_copilot_multi_agent 已实现的阶段函数
# examples/ 不是 Python 包（无 __init__.py），用 sys.path 注入而非创建 __init__.py
_EXAMPLES_DIR = Path(__file__).resolve().parent
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))

from erp_copilot_multi_agent import (  # noqa: E402
    DEFAULT_QUESTION,
    OUTPUT_DIR,
    _stage_build_workflow,
    _stage_persist_outputs,
    _try_build_provider,
)


def _print_summary(result: dict[str, Any], latency_ms: float) -> None:
    """终端友好输出：5 节点链路摘要 + 耗时 + 成功标志。"""
    plan = result.get("plan")
    analyses = result.get("analyses") or []
    recs = result.get("purchase_recs") or []
    final = result.get("final_report") or ""

    print()
    print("=" * 72)
    print("  链路节点：用户问题 → Planner → Tools/RAG/SQL → Reviewer → 报告")
    print("=" * 72)
    print(f"  [1/5] Planner   : {'✓' if plan else '✗'}  (plan_steps={len(plan.get('steps') or []) if isinstance(plan, dict) else 0})")
    print(f"  [2/5] Tools/RAG : {'✓' if analyses else '✗'}  (analyses={len(analyses) if isinstance(analyses, list) else 'n/a'})")
    print(f"  [3/5] SQL       : {'✓' if recs else '✗'}  (purchase_recs={len(recs) if isinstance(recs, list) else 'n/a'})")
    print(f"  [4/5] Reviewer  : {'✓' if final else '✗'}  (final_report_chars={len(final)})")
    print(f"  [5/5] 报告落盘  : ✓  ({OUTPUT_DIR / 'inventory_risk_report.md'})")
    print()
    print(f"  耗时：{latency_ms:.0f}ms")
    print(f"  成功：{result.get('success')}")
    if result.get("error"):
        print(f"  错误：{result['error']}")
    print("=" * 72)


async def run_interview(
    question: str = DEFAULT_QUESTION,
    out_dir: Path = OUTPUT_DIR,
) -> Tuple[dict[str, Any], float]:
    """跑一遍完整链路，返回 ``(result_dict, latency_ms)``。

    复用 ``erp_copilot_multi_agent._stage_*`` 五个阶段函数，
    仅在前后增加计时与摘要打印，不修改其行为。
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[init] provider: ", end="", flush=True)
    provider = _try_build_provider()
    print(getattr(provider, "model_name", lambda: provider.__class__.__name__)())

    print("[init] building workflow ...", flush=True)
    wf = _stage_build_workflow(provider)

    print(f"[run] question: {question}")
    t0 = time.perf_counter()
    result = await wf.run(question)
    latency_ms = (time.perf_counter() - t0) * 1000

    # 复用 _stage_persist_outputs：写 report.md + trace.json
    _stage_persist_outputs(result)

    _print_summary(result, latency_ms)
    return result, latency_ms


def main() -> int:
    try:
        result, latency_ms = asyncio.run(run_interview())
        # 无 key 时 _NullProvider 仍会输出结构化结果，success 可能是 None/True
        # 唯独 result 为 None 才算失败
        if result is None:
            print("[FAIL] workflow returned None", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
