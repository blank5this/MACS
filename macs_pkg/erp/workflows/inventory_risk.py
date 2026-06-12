"""Inventory risk multi-agent workflow (Day 10).

This is the Day-10 deliverable: a multi-agent workflow that takes a
free-form question like *"分析未来 30 天库存风险并给出采购建议"* and
runs it through the four Day-9 templates in hierarchical mode.

Pipeline::

    user question
        ↓
    erp_planner           → {plan: [subtask_1, ...]}
        ↓
    erp_inventory_analyst → {analyses: [low_stock_items...]}
        ↓
    erp_purchase_specialist → {purchase_recs: [supplier×qty×cost...]}
        ↓
    erp_report_writer     → {final_report: markdown}

The workflow wraps the four :class:`AgentTemplate` instances from
:mod:`macs_pkg.erp.agents.templates` and lets :class:`RuntimeEngine`
glue them together with the Hierarchical collaboration mode.

Quickstart::

    import asyncio
    from macs_pkg.erp.workflows import InventoryRiskWorkflow
    from macs_pkg.erp.db import DatabaseConfig, DatabasePool

    async def main():
        pool = DatabasePool(DatabaseConfig.from_env())
        await pool.open()

        wf = InventoryRiskWorkflow(provider=my_provider, pool=pool)
        result = await wf.run("分析未来 30 天库存风险并给出采购建议")
        print(result["final_report"])

        await pool.close()

    asyncio.run(main())
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from ..db.connection import DatabasePool
from macs_pkg.core.agent_template import AgentTemplateRegistry
from macs_pkg.agents.executor import ExecutorAgent
from macs_pkg.agents.planner import PlannerAgent
from macs_pkg.agents.reviewer import ReviewerAgent
from macs_pkg.runtime.engine import RuntimeConfig, RuntimeEngine
from ..agents.templates import (
    ERP_INVENTORY_ANALYST,
    ERP_PLANNER,
    ERP_PURCHASE_SPECIALIST,
    ERP_REPORT_WRITER,
    register_erp_templates,
)

logger = logging.getLogger(__name__)


# ===== Result schema ===============================================

class WorkflowResult(dict):
    """Typed return value for :meth:`InventoryRiskWorkflow.run`.

    Mirrors the plan::

        {
            "question":      str,
            "plan":          dict | None,    # erp_planner output
            "analyses":      dict | None,    # erp_inventory_analyst output
            "purchase_recs": dict | None,    # erp_purchase_specialist output
            "final_report":  str | None,     # erp_report_writer output
            "raw_history":   list,           # full message trace
            "elapsed_ms":    int,
            "success":       bool,
            "error":         str | None,
        }
    """


# ===== Agent factories =============================================

def _build_planner(provider: Any, variables: Dict[str, str]) -> PlannerAgent:
    return ERP_PLANNER.create_agent(
        variables=variables,
        provider=provider,
        overrides={"name": "erp_planner"},
    )


def _build_inventory_analyst(provider: Any, variables: Dict[str, str]) -> ExecutorAgent:
    return ERP_INVENTORY_ANALYST.create_agent(
        variables=variables,
        provider=provider,
        overrides={"name": "erp_inventory_analyst"},
    )


def _build_purchase_specialist(provider: Any, variables: Dict[str, str]) -> ExecutorAgent:
    return ERP_PURCHASE_SPECIALIST.create_agent(
        variables=variables,
        provider=provider,
        overrides={"name": "erp_purchase_specialist"},
    )


def _build_report_writer(provider: Any, variables: Dict[str, str]) -> ReviewerAgent:
    return ERP_REPORT_WRITER.create_agent(
        variables=variables,
        provider=provider,
        overrides={"name": "erp_report_writer"},
    )


# ===== Output parsing helpers ======================================

_JSON_FENCE_RE = None  # lazy compile
import re as _re
_FENCE_RE = _re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", _re.DOTALL)


def _extract_json_block(text: str) -> Optional[dict | list]:
    """Best-effort extraction of a JSON object or array from a string.

    Used to parse the LLM's response into a structured dict. Returns
    None if no valid JSON can be found.
    """
    if not text:
        return None
    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Try fenced ```json ... ```
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Try to find first { ... } or [ ... ] block
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except (json.JSONDecodeError, ValueError):
                pass

    return None


# ===== Workflow ====================================================

class InventoryRiskWorkflow:
    """End-to-end multi-agent inventory-risk + purchase-recommendation flow.

    Args:
        provider: any LLM provider (Claude / MiniMax / etc.) — passed
                  to all 4 agents.
        pool:     a :class:`DatabasePool` (kept for future sub-runs;
                  the 4 agents do their own DB access through the MCP
                  layer once they're wired in Day 11).
        enable_tracing: turn on :class:`ExecutionTracer` for
                         visualising the message flow.
        current_date: the date stamped into every prompt. Defaults
                      to today (ISO-8601).
        project_context: a short description injected into the
                         planner's prompt (default: "MACS ERP Copilot
                         demo").
    """

    def __init__(
        self,
        provider: Any,
        pool: Optional[DatabasePool] = None,
        *,
        enable_tracing: bool = True,
        current_date: Optional[str] = None,
        project_context: str = "MACS ERP Copilot demo",
    ) -> None:
        self.provider = provider
        self.pool = pool

        # Default to today's date (ISO) when not given.
        if current_date is None:
            from datetime import date
            current_date = date.today().isoformat()
        self.current_date = current_date
        self.project_context = project_context

        # Make sure the 4 templates are registered (idempotent).
        register_erp_templates()

        # The runtime is rebuilt per `run()` call so each execution
        # has a clean message history. The tracer and shared memory
        # are opt-in.
        self._enable_tracing = enable_tracing

    # ----- internal: build a fresh RuntimeEngine for one run ------

    def _build_runtime(self) -> RuntimeEngine:
        cfg = RuntimeConfig(
            default_mode="hierarchical",
            enable_tracing=self._enable_tracing,
            enable_shared_memory=False,  # MemPalace optional, skip for now
            log_level="INFO",
            stop_on_error=False,  # let the workflow collect partial output
        )
        runtime = RuntimeEngine(config=cfg)

        # Common variables injected into every template.
        base_vars = {
            "current_date": self.current_date,
            "project_context": self.project_context,
        }

        # 1. Planner
        planner = _build_planner(
            self.provider,
            variables={**base_vars, "question": ""},  # question patched per run
        )

        # 2. Inventory analyst
        analyst = _build_inventory_analyst(
            self.provider,
            variables={
                **base_vars,
                "task_id": "task_inventory_analyst",
                "upstream_context": "",
            },
        )

        # 3. Purchase specialist
        buyer = _build_purchase_specialist(
            self.provider,
            variables={
                **base_vars,
                "task_id": "task_purchase_specialist",
                "upstream_context": "",
            },
        )

        # 4. Report writer
        writer = _build_report_writer(
            self.provider,
            variables={
                **base_vars,
                "task_id": "task_report_writer",
                "upstream_context": "",
            },
        )

        for a in (planner, analyst, buyer, writer):
            runtime.register_agent(a)

        return runtime

    # ----- main entry point ---------------------------------------

    async def run(self, question: str) -> WorkflowResult:
        """Run the full inventory-risk workflow.

        Args:
            question: free-form Chinese/English business question.
                      Example: ``"分析未来 30 天库存风险并给出采购建议"``.

        Returns:
            A :class:`WorkflowResult` dict with the four stage outputs.
            On any error, ``success=False`` and ``error`` is set, but
            partial outputs are still returned.
        """
        import time
        t0 = time.monotonic()

        # Patch the planner's prompt with the actual question.
        # We re-build the planner with a completed variables dict.
        runtime = self._build_runtime()
        planner_agent = runtime.get_agent("erp_planner")
        planner_agent.system_prompt = ERP_PLANNER.render_prompt(
            variables={
                "current_date": self.current_date,
                "project_context": self.project_context,
                "question": question,
            }
        )

        task = {
            "type": "erp_inventory_risk",
            "description": question,
            "context": {
                "current_date": self.current_date,
            },
        }

        try:
            raw_result = await runtime.execute(task, mode="hierarchical")
        except Exception as e:
            logger.exception("InventoryRiskWorkflow.run failed")
            return WorkflowResult(
                question=question,
                plan=None,
                analyses=None,
                purchase_recs=None,
                final_report=None,
                raw_history=[],
                elapsed_ms=int((time.monotonic() - t0) * 1000),
                success=False,
                error=str(e),
            )

        # Parse the raw output into the 4 structured stages.
        plan, analyses, purchase_recs, final_report = _parse_stages(
            raw_result, runtime
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return WorkflowResult(
            question=question,
            plan=plan,
            analyses=analyses,
            purchase_recs=purchase_recs,
            final_report=final_report,
            raw_history=raw_result if isinstance(raw_result, list) else [raw_result],
            elapsed_ms=elapsed_ms,
            success=True,
            error=None,
        )

    # ----- introspection -----------------------------------------

    def list_agents(self) -> List[str]:
        """Names of the 4 agents this workflow will register."""
        return [
            "erp_planner",
            "erp_inventory_analyst",
            "erp_purchase_specialist",
            "erp_report_writer",
        ]


# ===== Stage parsing ===============================================

def _parse_stages(
    raw_result: Any,
    runtime: RuntimeEngine,
) -> tuple[Optional[dict], Optional[dict], Optional[dict], Optional[str]]:
    """Drill into the runtime's outputs and pull out the 4 stages.

    The runtime's ``execute()`` returns the reviewer (final stage)
    output. We need to also pull the planner and executor outputs.
    The cleanest source is the runtime's tracer (if enabled) or the
    agents' own memory buffers.
    """
    # 1. Final report = last agent's output (reviewer).
    final_report: Optional[str] = None
    if isinstance(raw_result, str):
        final_report = raw_result
    elif isinstance(raw_result, dict):
        # Common shapes: {"answer": "..."} / {"result": "..."} / {"output": "..."}
        for key in ("answer", "result", "output", "final_report", "report"):
            v = raw_result.get(key)
            if isinstance(v, str) and v.strip():
                final_report = v
                break
        if final_report is None:
            # Fall back to stringified dict
            final_report = json.dumps(raw_result, ensure_ascii=False, indent=2)
    elif raw_result is not None:
        final_report = str(raw_result)

    # 2. Pull the planners / executors outputs from the agents' memory.
    # Each agent's ``memory`` list contains the messages it sent /
    # received. We look for the last assistant message from each
    # named agent.
    plan = _agent_last_assistant(runtime, "erp_planner")
    analyses = _agent_last_assistant(runtime, "erp_inventory_analyst")
    purchase_recs = _agent_last_assistant(runtime, "erp_purchase_specialist")

    return plan, analyses, purchase_recs, final_report


def _agent_last_assistant(
    runtime: RuntimeEngine, agent_name: str
) -> Optional[dict | str]:
    """Return the parsed last assistant output from an agent's memory.

    Falls back to a string if it can't be parsed as JSON.
    """
    agent = runtime.get_agent(agent_name)
    if agent is None:
        return None
    # Iterate messages in reverse; the last one from this agent is
    # the most recent output.
    for msg in reversed(getattr(agent, "memory", []) or []):
        if msg.sender != agent_name:
            continue
        content = msg.content
        if isinstance(content, str):
            parsed = _extract_json_block(content)
            return parsed if parsed is not None else content
        if isinstance(content, dict):
            # If the content already looks like structured output, return it.
            for key in ("result", "answer", "output"):
                if key in content:
                    v = content[key]
                    if isinstance(v, str):
                        parsed = _extract_json_block(v)
                        return parsed if parsed is not None else v
                    return v
            return content
    return None


# ===== Convenience top-level function =============================

async def run_inventory_risk_analysis(
    question: str,
    provider: Any,
    pool: Optional[DatabasePool] = None,
    *,
    current_date: Optional[str] = None,
) -> WorkflowResult:
    """One-shot helper: build the workflow and run it.

    Example::

        result = await run_inventory_risk_analysis(
            "分析未来 30 天库存风险并给出采购建议",
            provider=my_provider,
        )
        print(result["final_report"])
    """
    wf = InventoryRiskWorkflow(
        provider=provider,
        pool=pool,
        current_date=current_date,
    )
    return await wf.run(question)


__all__ = [
    "InventoryRiskWorkflow",
    "WorkflowResult",
    "run_inventory_risk_analysis",
    "_extract_json_block",
]
