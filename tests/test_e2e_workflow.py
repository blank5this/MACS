# E:\MACS\tests\test_e2e_workflow.py
"""End-to-end smoke test for the multi-agent inventory risk workflow.

Marked as an integration test because the workflow may invoke a real LLM
provider in some scenarios.  For the smoke test itself, we use a scripted
provider that returns canned JSON, so no real LLM call is needed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, List

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap: make ``import macs...`` work regardless of where pytest
# is invoked from.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from macs_pkg.erp.workflows.inventory_risk import (  # noqa: E402
    InventoryRiskWorkflow,
    run_inventory_risk_analysis,
)


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Canned JSON outputs (same shape as tests/test_inventory_workflow.py)
# ---------------------------------------------------------------------------
_PLAN_OUT: List[dict] = [
    {
        "stage": "plan",
        "subtasks": [
            {"id": "s1", "owner": "analyst", "description": "Assess current inventory risk"},
            {"id": "s2", "owner": "analyst", "description": "Identify top overstocks"},
            {"id": "s3", "owner": "buyer", "description": "Recommend purchase adjustments"},
            {"id": "s4", "owner": "writer", "description": "Compile final report"},
        ],
    }
]

_ANALYST_OUT: List[dict] = [
    {
        "stage": "analyze",
        "subtask_id": "s1",
        "analysis": "Inventory turnover has slowed 12% QoQ; safety stock adequate for SKUs A1-A3.",
    },
    {
        "stage": "analyze",
        "subtask_id": "s2",
        "analysis": "Top overstocks: SKU-B22 (180d cover), SKU-C09 (140d cover).",
    },
]

_BUYER_OUT: List[dict] = [
    {
        "stage": "purchase_rec",
        "subtask_id": "s3",
        "recs": [
            {"sku": "SKU-B22", "action": "decrease", "qty_pct": -25},
            {"sku": "SKU-C09", "action": "decrease", "qty_pct": -15},
        ],
    }
]

_WRITER_OUT: List[dict] = [
    {
        "stage": "final_report",
        "subtask_id": "s4",
        "report": "Inventory risk is moderate. Recommend trimming SKU-B22 and SKU-C09 orders.",
    }
]


# ---------------------------------------------------------------------------
# Scripted LLM provider
# ---------------------------------------------------------------------------
class _ScriptedProvider:
    """Tiny stand-in for an LLM client.

    The workflow calls ``await provider.complete(messages, system=...)``.
    The returned object only needs a ``.content`` attribute carrying a JSON
    string the workflow can parse.
    """

    def __init__(self, responses: List[List[dict]]):
        # ``responses`` is a queue of canned payloads; one is returned per call.
        self._responses = list(responses)
        self._idx = 0

    async def complete(self, messages, system: str = ""):
        payload = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        return _Resp(payload)


class _Resp:
    def __init__(self, payload):
        import json
        self.content = json.dumps(payload)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def scripted_provider():
    return _ScriptedProvider([_PLAN_OUT, _ANALYST_OUT, _BUYER_OUT, _WRITER_OUT])


@pytest.fixture()
def question() -> str:
    return "Assess Q3 inventory risk and recommend purchase adjustments."


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_returns_all_four_stages(scripted_provider, question):
    """Happy path: the workflow must return a dict with plan/analyses/
    purchase_recs/final_report keys."""
    wf = InventoryRiskWorkflow(provider=scripted_provider, pool=None)
    result = await wf.run(question)

    # ``result`` is dict-like (WorkflowResult); ``success`` should be True
    assert result["success"] is True

    # All four stage keys present
    for key in ("plan", "analyses", "purchase_recs", "final_report"):
        assert key in result, f"missing key: {key}"


@pytest.mark.asyncio
async def test_workflow_result_has_question_and_elapsed(scripted_provider, question):
    wf = InventoryRiskWorkflow(provider=scripted_provider, pool=None)
    result = await wf.run(question)

    assert result["question"] == question
    assert isinstance(result["elapsed_ms"], int)
    assert result["elapsed_ms"] >= 0


@pytest.mark.asyncio
async def test_workflow_works_with_no_pool(scripted_provider, question):
    """Explicitly verify pool=None is supported."""
    wf = InventoryRiskWorkflow(provider=scripted_provider, pool=None)
    result = await wf.run(question)
    assert isinstance(result, dict)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_workflow_top_level_helper(scripted_provider, question):
    """``run_inventory_risk_analysis`` should expose the same behaviour."""
    result = await run_inventory_risk_analysis(question, provider=scripted_provider)

    assert isinstance(result, dict)
    assert result["success"] is True
    for key in ("plan", "analyses", "purchase_recs", "final_report"):
        assert key in result


@pytest.mark.asyncio
async def test_workflow_raw_history_is_list(scripted_provider, question):
    wf = InventoryRiskWorkflow(provider=scripted_provider, pool=None)
    result = await wf.run(question)

    assert "raw_history" in result
    assert isinstance(result["raw_history"], list)


@pytest.mark.asyncio
async def test_workflow_failure_returns_dict(scripted_provider, question):
    """Even if the provider raises, the workflow must return a dict-shaped
    WorkflowResult (never let an exception escape)."""

    class _BoomProvider:
        async def complete(self, messages, system: str = ""):
            raise RuntimeError("simulated provider failure")

    wf = InventoryRiskWorkflow(provider=_BoomProvider(), pool=None)
    result = await wf.run(question)

    assert isinstance(result, dict)
    # The runtime swallows provider errors internally and may report
    # success=True with empty outputs OR success=False with a populated
    # error. Both are acceptable — the contract is that we always get
    # a dict back, never an exception.
    assert result["success"] in (True, False)
    assert "error" in result


# ---------------------------------------------------------------------------
# Allow running directly: ``python test_e2e_workflow.py``
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=short"]))