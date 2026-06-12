"""Tests for the ERP standalone health module (Day 13).

The health module is the single source of truth for the
``GET /healthz`` endpoint and the ``make erp-check`` CLI. These
tests exercise the individual probes and the orchestrating
:func:`check_health` function in isolation — no Postgres, no LLM
key, no web app.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Strip LLM env vars so the probe has a deterministic "no key" state.
for k in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(k, None)

from macs_pkg.erp.health import (  # noqa: E402
    HealthReport,
    _probe_llm,
    _probe_rag,
    check_health,
    check_health_sync,
)


# ---------------------------------------------------------------------------
# Module shape
# ---------------------------------------------------------------------------
def test_health_report_is_dataclass():
    r = HealthReport(ok=True, elapsed_ms=12)
    assert r.ok is True
    assert r.elapsed_ms == 12
    assert isinstance(r.to_dict(), dict)


def test_module_exports_public_api():
    from macs_pkg.erp import health as h
    assert callable(h.check_health)
    assert callable(h.check_health_sync)
    assert h.HealthReport is HealthReport


# ---------------------------------------------------------------------------
# _probe_llm
# ---------------------------------------------------------------------------
def test_probe_llm_returns_false_with_no_keys():
    for k in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(k, None)
    result = _probe_llm()
    assert result["ok"] is False
    assert result["configured_providers"] == []


def test_probe_llm_detects_minimax_key():
    os.environ["MINIMAX_API_KEY"] = "fake"
    try:
        result = _probe_llm()
        assert result["ok"] is True
        assert "MINIMAX_API_KEY" in result["configured_providers"]
    finally:
        os.environ.pop("MINIMAX_API_KEY", None)


def test_probe_llm_detects_anthropic_key():
    os.environ["ANTHROPIC_API_KEY"] = "fake"
    try:
        result = _probe_llm()
        assert result["ok"] is True
        assert "ANTHROPIC_API_KEY" in result["configured_providers"]
    finally:
        os.environ.pop("ANTHROPIC_API_KEY", None)


def test_probe_llm_lists_all_configured():
    os.environ["MINIMAX_API_KEY"] = "a"
    os.environ["ANTHROPIC_API_KEY"] = "b"
    try:
        result = _probe_llm()
        assert result["ok"] is True
        assert set(result["configured_providers"]) == {
            "MINIMAX_API_KEY", "ANTHROPIC_API_KEY"
        }
    finally:
        os.environ.pop("MINIMAX_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)


# ---------------------------------------------------------------------------
# _probe_rag
# ---------------------------------------------------------------------------
def test_probe_rag_returns_false_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ERP_RAG_DIR", str(tmp_path / "nonexistent"))
    result = _probe_rag()
    assert result["ok"] is False
    assert result["doc_count"] == 0


def test_probe_rag_returns_false_when_dir_empty(tmp_path, monkeypatch):
    empty_dir = tmp_path / "empty_rag"
    empty_dir.mkdir()
    monkeypatch.setenv("ERP_RAG_DIR", str(empty_dir))
    result = _probe_rag()
    assert result["ok"] is False


def test_probe_rag_returns_true_when_index_exists(tmp_path, monkeypatch):
    rag_dir = tmp_path / "good_rag"
    rag_dir.mkdir()
    (rag_dir / "index.json").write_text("{}")
    (rag_dir / "chunks.json").write_text("[]")
    monkeypatch.setenv("ERP_RAG_DIR", str(rag_dir))
    result = _probe_rag()
    assert result["ok"] is True
    assert result["doc_count"] >= 2


# ---------------------------------------------------------------------------
# check_health (async, full)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_health_returns_health_report(monkeypatch):
    """Full check: db ping should fail (no real Postgres) but the
    function must still return a structured HealthReport."""
    monkeypatch.setenv("ERP_RAG_DIR", "/nonexistent")
    report = await check_health(ping_db=True, db_timeout=0.5)
    assert isinstance(report, HealthReport)
    # llm is False (no keys)
    assert report.llm["ok"] is False
    # db is False (no real Postgres)
    assert report.db["ok"] is False
    # rag is False (no index)
    assert report.rag["ok"] is False
    # ok is False because every probe is False
    assert report.ok is False
    assert report.error is None
    assert report.elapsed_ms >= 0


@pytest.mark.asyncio
async def test_check_health_ping_db_false_skips_db(monkeypatch):
    """With ``ping_db=False`` the db probe is a no-op and we just
    report ``{"ok": True, "skipped": True}`` — even without a real
    Postgres."""
    monkeypatch.setenv("ERP_RAG_DIR", "/nonexistent")
    report = await check_health(ping_db=False)
    assert report.db.get("skipped") is True
    assert report.db.get("ok") is True


@pytest.mark.asyncio
async def test_check_health_never_raises(monkeypatch):
    """The function is documented to NEVER raise. Even if a probe
    explodes, the result is a HealthReport with error info."""
    # Patch the rag probe to throw. The orchestrator should still
    # return a structured report, not raise.
    monkeypatch.setattr(
        "macs_pkg.erp.health._probe_rag",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    report = await check_health(ping_db=False)
    assert isinstance(report, HealthReport)
    assert report.ok is False
    # The top-level error is captured
    assert "boom" in (report.error or "")


@pytest.mark.asyncio
async def test_check_health_db_probe_uses_short_timeout(monkeypatch):
    """When ping_db is True but no DB is reachable, the probe should
    return a False result with an error message, NOT block for 30s."""
    monkeypatch.setenv("ERP_RAG_DIR", "/nonexistent")
    # 0.05s ceiling — even a hung DB cannot stall the test.
    report = await check_health(ping_db=True, db_timeout=0.05)
    assert isinstance(report, HealthReport)
    # The DB probe must have failed but completed promptly
    assert report.db["ok"] is False
    assert "error" in report.db


# ---------------------------------------------------------------------------
# check_health_sync
# ---------------------------------------------------------------------------
def test_check_health_sync_runs_event_loop(monkeypatch):
    monkeypatch.setenv("ERP_RAG_DIR", "/nonexistent")
    report = check_health_sync(ping_db=False)
    assert isinstance(report, HealthReport)
    assert report.db.get("skipped") is True


def test_check_health_sync_returns_ok_false_with_no_env(monkeypatch):
    monkeypatch.setenv("ERP_RAG_DIR", "/nonexistent")
    report = check_health_sync(ping_db=False)
    assert report.ok is False
    assert report.llm["ok"] is False
    assert report.rag["ok"] is False


# ---------------------------------------------------------------------------
# to_dict shape (mirrors /healthz response)
# ---------------------------------------------------------------------------
def test_health_report_to_dict_has_expected_keys():
    r = HealthReport(ok=True, elapsed_ms=10)
    d = r.to_dict()
    for k in ("ok", "db", "llm", "rag", "erp_module", "elapsed_ms"):
        assert k in d


# ---------------------------------------------------------------------------
# CLI smoke (make erp-check)
# ---------------------------------------------------------------------------
def test_health_module_is_importable_from_package_root():
    """The makefile does ``from macs_pkg.erp.health import ...``.
    Make sure that import path works."""
    import importlib
    mod = importlib.import_module("macs_pkg.erp.health")
    assert hasattr(mod, "check_health_sync")


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(
        subprocess.call(
            ["pytest", __file__, "-v", "--tb=short"]
        )
    )
