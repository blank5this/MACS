"""
erp_copilot_multi_agent.py
==========================

Day 11 deliverable: end-to-end multi-agent workflow demo for the
MACS ERP Copilot project.

This script wires together the three core MACS ERP subsystems
(database layer, NL2SQL provider factory, and the multi-agent
`InventoryRiskWorkflow`) and runs a single natural-language question
through the full agent pipeline:

    "分析未来 30 天库存风险并给出采购建议"

Stages
------
1. Initialize the async database pool via `DatabaseConfig.from_env()`.
2. Initialize an LLM provider (Claude by default, MiniMax as fallback,
   or a `_NullProvider` if no API key is available).
3. Build the `InventoryRiskWorkflow` with optional tracing enabled.
4. Run a single question and stream intermediate stage outputs as they
   become available (plan, analyses, purchase_recs, final_report).
5. Persist the final markdown report to
   `E:\MACS\examples\output\inventory_risk_report.md` and the raw
   workflow trace (JSON) to `E:\MACS\examples\output\inventory_risk_trace.json`.

Run
---
    python examples/erp_copilot_multi_agent.py

The script is safe to run without an API key: it will fall back to a
`_NullProvider` and print a "no LLM" path showing what the workflow
*would* output structurally.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

BANNER = "=" * 72
SUB    = "-" * 72

OUTPUT_DIR = Path(r"E:\MACS\examples\output")
REPORT_PATH = OUTPUT_DIR / "inventory_risk_report.md"
TRACE_PATH  = OUTPUT_DIR / "inventory_risk_trace.json"

DEFAULT_QUESTION = "分析未来 30 天库存风险并给出采购建议"


def _print_banner() -> None:
    print(BANNER)
    print("  MACS ERP Copilot  -  Day 11 Multi-Agent End-to-End Demo")
    print("  Workflow : InventoryRiskWorkflow")
    print(f"  Question : {DEFAULT_QUESTION}")
    print(BANNER)


def _print_stage(stage_no: int, title: str, detail: str = "") -> None:
    print()
    print(BANNER)
    print(f"  STAGE {stage_no}: {title}")
    if detail:
        print(f"           {detail}")
    print(BANNER)


def _print_section(title: str, body: Any, max_chars: int = 800) -> None:
    """Print a short summary of an intermediate stage result."""
    print()
    print(SUB)
    print(f"[{title}]")
    print(SUB)
    if body is None:
        print("  <empty>")
        return
    if isinstance(body, (dict, list)):
        try:
            text = json.dumps(body, ensure_ascii=False, indent=2, default=str)
        except Exception:  # pragma: no cover - defensive
            text = repr(body)
    else:
        text = str(body)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n  ... (truncated, {len(text) - max_chars} more chars)"
    print(text)


def _short_summary(text: str, max_chars: int = 240) -> str:
    text = (text or "").strip().replace("\r\n", "\n")
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


# ---------------------------------------------------------------------------
# Null provider fallback
# ---------------------------------------------------------------------------

class _NullProvider:
    """Stand-in provider used when no LLM API key is configured.

    It implements only the subset of the provider surface area that
    `InventoryRiskWorkflow` actually calls, so the workflow can still
    run and produce its structural outputs without contacting an LLM.
    """

    def __init__(self, name: str = "null", reason: str = "no API key") -> None:
        self._name = name
        self._reason = reason

    def model_name(self) -> str:
        return self._name

    def is_null(self) -> bool:
        return True

    def reason(self) -> str:
        return self._reason

    # The workflow may call a chat/complete method. We return a short
    # placeholder so downstream agents can fall back to template output.
    async def chat(self, *args: Any, **kwargs: Any) -> str:  # pragma: no cover
        return (
            "[NullProvider] No LLM call performed "
            f"(reason: {self._reason})."
        )

    async def complete(self, *args: Any, **kwargs: Any) -> str:  # pragma: no cover
        return await self.chat(*args, **kwargs)

    async def generate(self, *args: Any, **kwargs: Any) -> str:  # pragma: no cover
        return await self.chat(*args, **kwargs)


def _try_build_provider() -> Any:
    """Try to build the real LLM provider; fall back to NullProvider.

    Selection order:
      1. macs_pkg.erp.nl2sql.build_default_provider(prefer='claude')
         (or 'minimax' if MACS_LLM_PROVIDER=minimax is set in env)
      2. _NullProvider - so the demo stays runnable in CI / offline.
    """
    prefer = os.environ.get("MACS_LLM_PROVIDER", "claude").strip().lower() or "claude"
    try:
        from macs_pkg.erp.nl2sql import build_default_provider
    except Exception as exc:  # pragma: no cover - import failure
        print(f"  [warn] could not import build_default_provider: {exc}")
        return _NullProvider(reason="provider factory not importable")

    try:
        provider = build_default_provider(prefer=prefer)
        return provider
    except Exception as exc:
        print(f"  [warn] no live LLM provider available ({exc.__class__.__name__}: {exc})")
        print("         falling back to _NullProvider for structural demo only.")
        return _NullProvider(reason=str(exc) or "no API key")


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------

async def _stage_init_db():
    """Stage 1: initialize the async database pool."""
    from macs_pkg.erp.db import DatabaseConfig, DatabasePool

    cfg = DatabaseConfig.from_env()
    pool = DatabasePool(cfg)
    await pool.open()
    print(f"  [ok] database pool opened (driver={getattr(cfg, 'driver', '?')}, "
          f"host={getattr(cfg, 'host', '?')}, db={getattr(cfg, 'database', '?')})")
    return pool


def _stage_init_provider():
    """Stage 2: initialize the LLM provider."""
    provider = _try_build_provider()
    name = getattr(provider, "model_name", lambda: provider.__class__.__name__)()
    print(f"  [ok] provider ready: {name} ({type(provider).__name__})")
    return provider


def _stage_build_workflow(provider, pool=None):
    """Stage 3: build the InventoryRiskWorkflow."""
    from macs_pkg.erp.workflows import InventoryRiskWorkflow

    wf = InventoryRiskWorkflow(
        provider=provider,
        pool=pool,
        enable_tracing=True,
        current_date="2026-06-12",
        project_context="MACS ERP Copilot demo",
    )
    print("  [ok] InventoryRiskWorkflow instantiated "
          f"(tracing={wf.enable_tracing if hasattr(wf, 'enable_tracing') else 'n/a'})")
    return wf


async def _stage_run_question(wf, question: str) -> Dict[str, Any]:
    """Stage 4: run a single question and stream intermediate results."""
    print(f"  [run] question: {question}")
    print("  [run] awaiting workflow result (this may call the LLM)...")

    result = await wf.run(question)

    # Stream intermediate stages as they become available.
    plan = result.get("plan") if isinstance(result, dict) else None
    if plan:
        _print_section("STAGE 4a - plan", plan)
        if isinstance(plan, dict):
            steps = plan.get("steps") or plan.get("plan_steps")
            if steps:
                print(f"  -> {len(steps)} planned step(s): "
                      + ", ".join(str(s.get('id') or s.get('name') or s)[:40] for s in steps[:5]))

    analyses = result.get("analyses") if isinstance(result, dict) else None
    if analyses:
        _print_section("STAGE 4b - analyses", analyses)
        if isinstance(analyses, list):
            for i, a in enumerate(analyses[:5]):
                label = (a.get("name") or a.get("title") or a.get("step_id")
                         or f"analysis#{i}") if isinstance(a, dict) else f"analysis#{i}"
                print(f"  -> analysis {i+1}: {label}")

    recs = result.get("purchase_recs") if isinstance(result, dict) else None
    if recs:
        _print_section("STAGE 4c - purchase_recs", recs)
        if isinstance(recs, list):
            print(f"  -> {len(recs)} purchase recommendation(s)")

    final = result.get("final_report") if isinstance(result, dict) else None
    if final:
        _print_section("STAGE 4d - final_report (preview)",
                       _short_summary(final, max_chars=400))
    return result


def _stage_persist_outputs(result: Dict[str, Any]) -> None:
    """Stage 5: write the final report and raw trace to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    final_report = (result or {}).get("final_report") or ""
    if not final_report:
        final_report = (
            "# Inventory Risk Report\n\n"
            "_No LLM was available; the workflow ran in structural-only "
            "mode. Re-run with a valid API key to populate this report._\n"
        )
    REPORT_PATH.write_text(final_report, encoding="utf-8")
    print(f"  [ok] wrote report -> {REPORT_PATH}")

    # Strip non-serializable objects (e.g. async handles) before dumping.
    safe: Dict[str, Any] = {}
    for k, v in (result or {}).items():
        try:
            json.dumps(v, default=str)
            safe[k] = v
        except Exception:
            safe[k] = repr(v)
    TRACE_PATH.write_text(json.dumps(safe, ensure_ascii=False, indent=2, default=str),
                          encoding="utf-8")
    print(f"  [ok] wrote trace  -> {TRACE_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> int:
    _print_banner()

    pool = None
    wf = None
    result: Optional[Dict[str, Any]] = None

    try:
        _print_stage(1, "Initialize database pool",
                     "macs_pkg.erp.db.DatabaseConfig.from_env() + DatabasePool.open()")
        try:
            pool = await _stage_init_db()
        except Exception as exc:
            print(f"  [warn] could not open DB pool ({exc.__class__.__name__}: {exc})")
            print("         continuing without a live pool (workflow will use mock data).")
            pool = None

        _print_stage(2, "Initialize LLM provider",
                     "macs_pkg.erp.nl2sql.build_default_provider() "
                     "(falls back to _NullProvider if no key)")
        provider = _stage_init_provider()

        _print_stage(3, "Build InventoryRiskWorkflow")
        wf = _stage_build_workflow(provider, pool=pool)

        _print_stage(4, "Run single question", DEFAULT_QUESTION)
        result = await _stage_run_question(wf, DEFAULT_QUESTION)

        _print_stage(5, "Display result & persist outputs",
                     f"report -> {REPORT_PATH}\n"
                     f"trace  -> {TRACE_PATH}")

        if isinstance(result, dict):
            _print_section("summary", {
                "success":     result.get("success"),
                "elapsed_ms":  result.get("elapsed_ms"),
                "error":       result.get("error"),
                "stages": {
                    "plan":          bool(result.get("plan")),
                    "analyses":      len(result.get("analyses") or [])
                                     if isinstance(result.get("analyses"), list)
                                     else bool(result.get("analyses")),
                    "purchase_recs": len(result.get("purchase_recs") or [])
                                     if isinstance(result.get("purchase_recs"), list)
                                     else bool(result.get("purchase_recs")),
                    "final_report":  bool(result.get("final_report")),
                },
            })
        _stage_persist_outputs(result or {})

        if isinstance(result, dict) and result.get("success") is False:
            print()
            print(f"  [fail] workflow returned success=False: {result.get('error')}")
            return 2

        print()
        print(BANNER)
        print("  DEMO COMPLETE")
        print(BANNER)
        return 0

    except Exception as exc:
        print()
        print(BANNER)
        print("  DEMO FAILED")
        print(BANNER)
        print(f"  {exc.__class__.__name__}: {exc}")
        traceback.print_exc()

        # Best-effort: still write whatever trace we have so the user
        # can inspect the failure from disk.
        if result is None:
            result = {
                "question": DEFAULT_QUESTION,
                "plan": None,
                "analyses": None,
                "purchase_recs": None,
                "final_report": None,
                "raw_history": None,
                "elapsed_ms": 0,
                "success": False,
                "error": f"{exc.__class__.__name__}: {exc}",
            }
        try:
            _stage_persist_outputs(result)
        except Exception as inner:  # pragma: no cover - defensive
            print(f"  [warn] could not persist failure trace: {inner}")
        return 1

    finally:
        if pool is not None:
            try:
                await pool.close()
                print("  [ok] database pool closed")
            except Exception as exc:  # pragma: no cover
                print(f"  [warn] error closing pool: {exc}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))