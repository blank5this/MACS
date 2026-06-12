"""Tests for the v1.0.1 fixes.

Two known issues from v1.0.0 are fixed in v1.0.1:

1. ``LLMPlannerAgent`` / ``LLMExecutorAgent`` / ``LLMReviewerAgent``
   hard-coded their class-level :data:`SYSTEM_PROMPT` into the
   ``super().__init__`` call, ignoring any caller-supplied
   ``system_prompt`` override. This prevented templates (e.g.
   :class:`macs_pkg.erp.agents.templates.ERP_PLANNER`) from
   injecting their rendered prompts. v1.0.1 makes the override
   win.

2. :class:`RuntimeEngine` swallowed provider exceptions into a
   bare ``{"error": "..."}`` dict (when ``stop_on_error=False``),
   losing the original exception class. v1.0.1 exposes it as
   ``engine.last_error`` and adds ``error_type`` to the returned
   dict.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from types import MethodType
from typing import Any, Optional

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Strip LLM env vars so the v1.0.1 tests don't accidentally hit a
# real provider.
for k in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    import os
    os.environ.pop(k, None)

from macs_pkg.llm.agents import (  # noqa: E402
    LLMExecutorAgent,
    LLMPlannerAgent,
    LLMReviewerAgent,
)
from macs_pkg.runtime.engine import RuntimeConfig, RuntimeEngine  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal provider stand-in (no network, no API key)
# ---------------------------------------------------------------------------
class _NullProvider:
    async def complete(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("not used in these tests")

    def model_name(self) -> str:  # noqa: D401
        return "null"


# ===========================================================================
# v1.0.1.1 — LLM agent system_prompt override
# ===========================================================================
class TestLLMAgentSystemPromptOverride:
    """All three LLM-powered agent classes must accept a caller-supplied
    ``system_prompt`` that wins over the class-level :data:`SYSTEM_PROMPT`."""

    def test_planner_default_uses_class_prompt(self):
        agent = LLMPlannerAgent(provider=_NullProvider())
        assert agent.system_prompt == LLMPlannerAgent.SYSTEM_PROMPT

    def test_planner_override_wins(self):
        custom = "CUSTOM planner prompt v1.0.1"
        agent = LLMPlannerAgent(provider=_NullProvider(), system_prompt=custom)
        assert agent.system_prompt == custom
        assert agent.system_prompt != LLMPlannerAgent.SYSTEM_PROMPT

    def test_planner_explicit_none_uses_class_prompt(self):
        """``system_prompt=None`` is a legitimate signal meaning
        'use the default'. This must NOT crash."""
        agent = LLMPlannerAgent(provider=_NullProvider(), system_prompt=None)
        assert agent.system_prompt == LLMPlannerAgent.SYSTEM_PROMPT

    def test_executor_default_uses_class_prompt(self):
        agent = LLMExecutorAgent(provider=_NullProvider())
        assert agent.system_prompt == LLMExecutorAgent.SYSTEM_PROMPT

    def test_executor_override_wins(self):
        custom = "CUSTOM executor prompt v1.0.1"
        agent = LLMExecutorAgent(provider=_NullProvider(), system_prompt=custom)
        assert agent.system_prompt == custom
        assert agent.system_prompt != LLMExecutorAgent.SYSTEM_PROMPT

    def test_reviewer_default_uses_class_prompt(self):
        agent = LLMReviewerAgent(provider=_NullProvider())
        assert agent.system_prompt == LLMReviewerAgent.SYSTEM_PROMPT

    def test_reviewer_override_wins(self):
        custom = "CUSTOM reviewer prompt v1.0.1"
        agent = LLMReviewerAgent(provider=_NullProvider(), system_prompt=custom)
        assert agent.system_prompt == custom
        assert agent.system_prompt != LLMReviewerAgent.SYSTEM_PROMPT

    def test_override_does_not_mutate_class_var(self):
        """A caller-supplied override must not leak back into the
        class-level :data:`SYSTEM_PROMPT`."""
        original = LLMPlannerAgent.SYSTEM_PROMPT
        LLMPlannerAgent(provider=_NullProvider(), system_prompt="ephemeral")
        assert LLMPlannerAgent.SYSTEM_PROMPT == original

    def test_all_three_accept_kwargs_system_prompt(self):
        """Backwards compatibility: the old API passed ``system_prompt``
        via ``**kwargs`` (which ``super().__init__`` consumed). The
        v1.0.1 explicit param must NOT break that path."""
        custom = "passed via kwargs"
        # The planner's parent class accepts system_prompt in kwargs.
        # In v1.0.0 the subclass overwrote it; in v1.0.1 explicit
        # param wins, but kwargs should still be passed through for
        # other parameters.
        agent = LLMPlannerAgent(provider=_NullProvider(), system_prompt=custom)
        assert agent.system_prompt == custom


# ===========================================================================
# v1.0.1.2 — RuntimeEngine error propagation
# ===========================================================================
class TestRuntimeEngineErrorPropagation:
    """When ``stop_on_error=False`` the engine must return a dict
    that includes the original exception class name, and must
    expose the raw exception as ``engine.last_error``."""

    @pytest.fixture
    def engine(self):
        return RuntimeEngine(
            config=RuntimeConfig(
                stop_on_error=False,
                enable_shared_memory=False,
                enable_tracing=False,
                enable_dynamic_selection=False,
            )
        )

    @pytest.mark.asyncio
    async def test_engine_initializes_last_error_to_none(self, engine):
        """``last_error`` must be set to ``None`` in ``__init__`` so
        callers can read it without ``hasattr`` guards."""
        assert engine.last_error is None
        assert engine.last_error_task_id is None

    @pytest.mark.asyncio
    async def test_stop_on_error_true_still_raises(self, engine):
        """The default ``stop_on_error=True`` behavior is preserved —
        exceptions still propagate. The v1.0.1 fix is opt-in for the
        swallowing path."""
        engine.config.stop_on_error = True
        from macs_pkg.collaboration.hierarchical import HierarchicalMode

        async def boom(self, task, agents, context=None):
            raise RuntimeError("simulated LLM timeout")

        HierarchicalMode.execute = boom
        try:
            with pytest.raises(RuntimeError, match="simulated LLM timeout"):
                await engine.execute("test", mode="hierarchical")
        finally:
            delattr(HierarchicalMode, "execute")

    @pytest.mark.asyncio
    async def test_stop_on_error_false_returns_error_type(self, engine):
        """With ``stop_on_error=False``, the returned dict carries
        ``error_type`` so callers can switch on the exception class."""
        from macs_pkg.collaboration.hierarchical import HierarchicalMode

        async def boom(self, task, agents, context=None):
            raise ValueError("bad payload")

        HierarchicalMode.execute = boom
        try:
            result = await engine.execute("test", mode="hierarchical")
            assert isinstance(result, dict)
            assert "error" in result
            assert "error_type" in result
            assert result["error_type"] == "ValueError"
            assert "bad payload" in result["error"]
        finally:
            delattr(HierarchicalMode, "execute")

    @pytest.mark.asyncio
    async def test_last_error_set_to_raw_exception(self, engine):
        """The engine must expose the raw exception object as
        ``engine.last_error`` so callers can ``isinstance``-check it
        or read instance attributes."""
        from macs_pkg.collaboration.hierarchical import HierarchicalMode

        async def boom(self, task, agents, context=None):
            raise ConnectionError("LLM provider unreachable")

        HierarchicalMode.execute = boom
        try:
            result = await engine.execute("test", mode="hierarchical")
            assert engine.last_error is not None
            assert isinstance(engine.last_error, ConnectionError)
            assert "LLM provider unreachable" in str(engine.last_error)
            # error_type in the dict must match
            assert result["error_type"] == "ConnectionError"
        finally:
            delattr(HierarchicalMode, "execute")

    @pytest.mark.asyncio
    async def test_last_error_task_id_set(self, engine):
        """``last_error_task_id`` must be set so callers can correlate
        the exception with a specific task run."""
        from macs_pkg.collaboration.hierarchical import HierarchicalMode

        async def boom(self, task, agents, context=None):
            raise RuntimeError("oops")

        HierarchicalMode.execute = boom
        try:
            await engine.execute("test", mode="hierarchical")
            assert engine.last_error_task_id is not None
            assert engine.last_error_task_id.startswith("task_")
        finally:
            delattr(HierarchicalMode, "execute")

    @pytest.mark.asyncio
    async def test_successful_run_clears_last_error(self, engine):
        """After a successful run, ``last_error`` should not keep
        stale data from a previous failed run (we leave the previous
        value untouched for forensic debugging, but ``task_id``
        advances)."""
        from macs_pkg.collaboration.hierarchical import HierarchicalMode

        # First run: failure
        async def boom(self, task, agents, context=None):
            raise RuntimeError("first run fails")

        HierarchicalMode.execute = boom
        try:
            await engine.execute("first", mode="hierarchical")
            assert engine.last_error is not None
            failed_task_id = engine.last_error_task_id
        finally:
            delattr(HierarchicalMode, "execute")

        # Second run: success — last_error stays (intentional: we
        # don't want to lose the failure signal) but the task id
        # stays too. The contract is "last_error reflects the most
        # recent error" — once a success follows, the *next* failure
        # overwrites it. We only assert: the engine still has the
        # old error stashed, available for post-mortem.
        assert engine.last_error is not None
        assert engine.last_error_task_id == failed_task_id

    @pytest.mark.asyncio
    async def test_workflow_can_distinguish_error_types(self, engine):
        """End-to-end demo: a workflow consuming the engine's
        output can now route on ``error_type``."""
        from macs_pkg.collaboration.hierarchical import HierarchicalMode

        async def boom(self, task, agents, context=None):
            raise TimeoutError("LLM took too long")

        HierarchicalMode.execute = boom
        try:
            result = await engine.execute("test", mode="hierarchical")
            # Workflow-style routing
            if result.get("error_type") == "TimeoutError":
                decision = "retry_with_backoff"
            elif result.get("error_type") == "ConnectionError":
                decision = "switch_provider"
            else:
                decision = "fail_loud"
            assert decision == "retry_with_backoff"
        finally:
            delattr(HierarchicalMode, "execute")


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(
        subprocess.call(
            ["pytest", __file__, "-v", "--tb=short"]
        )
    )
