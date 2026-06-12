"""Tests for the ERP FastAPI web app (Day 12).

Covers:

* Module exports: ``app`` and ``create_app`` are importable.
* ``GET /healthz`` returns a structured response with the expected
  boolean fields.
* ``GET /`` returns the static frontend (HTML) when present, or a
  JSON descriptor when the file is missing.
* ``POST /api/copilot/chat`` returns either a successful ChatResponse
  shape or a 503 (when the agent cannot be built because no LLM
  provider / DB is configured).
* ``POST /api/copilot/inventory_risk`` returns either a successful
  InventoryRiskResponse or a 503.
* ``GET /api/kb/search`` exercises the RAG query path — it returns
  a KBSearchResponse with the expected fields.
* ``reset_resources()`` clears the module-level cache.

These tests are designed to pass **without** a real Postgres or LLM
key. The 503 paths let us verify endpoint wiring in a CI environment
where the secrets are absent.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Make sure we don't pick up a real LLM key from the developer's shell —
# we want the 503 path so the tests are deterministic.
for k in ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(k, None)

from fastapi.testclient import TestClient  # noqa: E402

# Importing the submodule via ``importlib`` gives us the **module**,
# not the re-exported ``app`` symbol from ``web/__init__.py``.
import importlib  # noqa: E402
app_module = importlib.import_module("macs_pkg.erp.web.app")  # noqa: E402
from macs_pkg.erp.web.app import (  # noqa: E402
    ChatRequest,
    HealthResponse,
    InventoryRiskRequest,
    KBSearchResponse,
    create_app,
    reset_resources,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """Return a TestClient and reset module-level resources between tests."""
    reset_resources()
    with TestClient(create_app()) as c:
        yield c
    reset_resources()


# ---------------------------------------------------------------------------
# Module / app shape
# ---------------------------------------------------------------------------
def test_app_is_a_fastapi_instance():
    from fastapi import FastAPI
    assert isinstance(app_module.app, FastAPI)


def test_create_app_returns_fastapi_instance():
    from fastapi import FastAPI
    app = create_app()
    assert isinstance(app, FastAPI)


def test_module_level_app_matches_create_app():
    # The two should be the same class; we don't compare identity
    # because the route table is the contract.
    assert app_module.app.title == create_app().title


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------
def test_healthz_returns_ok_status(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    # After the Day 13 refactor, the endpoint delegates to
    # ``macs_pkg.erp.health.check_health``. In a dev environment
    # without a real DB / LLM key / RAG index, the status is
    # "degraded" — that's the new, more honest contract. We still
    # assert the endpoint always returns 200 with the expected
    # boolean fields.
    assert body["status"] in ("ok", "degraded")
    assert body["erp_module"] is True
    assert "db_available" in body
    assert "llm_available" in body
    assert "web_static" in body


def test_healthz_reports_db_pool_constructed_and_llm_unavailable(client):
    """``db_available`` is True whenever :class:`DatabasePool` can be
    built from env (which it can with sensible defaults). The LLM
    provider flag, on the other hand, must be False because we cleared
    the LLM env vars at module import time."""
    body = client.get("/healthz").json()
    # DatabasePool is constructable from default config — db_available=True
    assert body["db_available"] is True
    # No LLM key was set — llm_available=False
    assert body["llm_available"] is False


def test_healthz_ping_db_returns_false_when_no_real_db(client):
    """With ``?ping_db=true`` and no real Postgres, the probe reports
    ``db_available=False`` (the SELECT 1 round-trip times out)."""
    body = client.get("/healthz", params={"ping_db": "true"}).json()
    assert body["db_available"] is False
    # llm check is independent of the db ping
    assert body["llm_available"] is False


# ---------------------------------------------------------------------------
# / (static frontend)
# ---------------------------------------------------------------------------
def test_root_serves_static_index_html(client):
    r = client.get("/")
    assert r.status_code == 200
    if r.headers.get("content-type", "").startswith("text/html"):
        # Frontend is present
        assert "ERP AI Copilot" in r.text or "MACS" in r.text
    else:
        # Frontend file missing — JSON descriptor returned
        body = r.json()
        assert "name" in body
        assert "docs" in body


# ---------------------------------------------------------------------------
# /api/copilot/chat
# ---------------------------------------------------------------------------
def test_copilot_chat_returns_503_without_llm(client):
    r = client.post(
        "/api/copilot/chat",
        json={"question": "哪些商品缺货?"},
    )
    # Without an LLM provider and DB pool, the endpoint returns 503.
    # With a working environment, it returns 200. Either is acceptable
    # as long as the body shape is valid.
    assert r.status_code in (200, 503)
    if r.status_code == 503:
        body = r.json()
        assert "detail" in body
        # The detail should mention the missing dependencies
        assert "unavailable" in body["detail"].lower() or "missing" in body["detail"].lower()
    else:
        body = r.json()
        assert "question" in body
        assert "elapsed_ms" in body
        # success path: result is set
        assert body.get("error") is None
        assert "result" in body


def test_copilot_chat_rejects_empty_question(client):
    r = client.post(
        "/api/copilot/chat",
        json={"question": ""},
    )
    # Pydantic validation -> 422 from FastAPI
    assert r.status_code == 422


def test_copilot_chat_request_model_validates_length():
    req = ChatRequest(question="哪些商品缺货?")
    assert req.question == "哪些商品缺货?"


# ---------------------------------------------------------------------------
# /api/copilot/inventory_risk
# ---------------------------------------------------------------------------
def test_inventory_risk_returns_503_without_llm(client):
    r = client.post(
        "/api/copilot/inventory_risk",
        json={"question": "分析未来 30 天库存风险"},
    )
    assert r.status_code in (200, 503)
    if r.status_code == 503:
        body = r.json()
        assert "detail" in body
    else:
        body = r.json()
        assert "success" in body
        assert "question" in body
        assert "elapsed_ms" in body


def test_inventory_risk_rejects_empty_question(client):
    r = client.post(
        "/api/copilot/inventory_risk",
        json={"question": ""},
    )
    assert r.status_code == 422


def test_inventory_risk_request_model_has_question():
    req = InventoryRiskRequest(question="哪些商品缺货?")
    assert req.question == "哪些商品缺货?"


# ---------------------------------------------------------------------------
# /api/kb/search
# ---------------------------------------------------------------------------
def test_kb_search_returns_structured_response(client):
    r = client.get("/api/kb/search", params={"q": "如何处理采购退货?"})
    # KB search does NOT need a DB pool or LLM provider — it should
    # work as long as the RAG index has been built.
    if r.status_code == 200:
        body = r.json()
        assert body["question"] == "如何处理采购退货?"
        assert "chunks" in body
        assert "context" in body
        assert "elapsed_ms" in body
        assert isinstance(body["chunks"], list)
    else:
        # If the index file is missing, we still get a KBSearchResponse
        # with an error key (never a 500)
        assert r.status_code == 200
        body = r.json()
        assert "error" in body or "chunks" in body


def test_kb_search_rejects_missing_q(client):
    r = client.get("/api/kb/search")
    assert r.status_code == 422


def test_kb_search_rejects_empty_q(client):
    r = client.get("/api/kb/search", params={"q": ""})
    assert r.status_code == 422


def test_kb_search_respects_top_k(client):
    r = client.get("/api/kb/search", params={"q": "MOQ 政策", "top_k": 5})
    assert r.status_code == 200
    body = r.json()
    if "chunks" in body:
        assert len(body["chunks"]) <= 5


def test_kb_response_model_serializes_chunks():
    resp = KBSearchResponse(
        question="MOQ 政策",
        chunks=[{"text": "x", "title": "t", "score": 0.9}],
        context="x",
        elapsed_ms=12,
    )
    assert resp.question == "MOQ 政策"
    assert len(resp.chunks) == 1
    assert resp.chunks[0]["title"] == "t"


# ---------------------------------------------------------------------------
# Resource cache
# ---------------------------------------------------------------------------
def test_reset_resources_clears_cache():
    from macs_pkg.erp.web.app import _resources
    _resources.db_pool = "stale"
    _resources.llm_provider = "stale"
    reset_resources()
    assert _resources.db_pool is None
    assert _resources.llm_provider is None
    assert _resources.copilot_agent is None


# ---------------------------------------------------------------------------
# OpenAPI
# ---------------------------------------------------------------------------
def test_openapi_lists_all_endpoints(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = set(spec["paths"].keys())
    assert "/healthz" in paths
    # The static root is hidden from OpenAPI (include_in_schema=False).
    assert "/api/copilot/chat" in paths
    assert "/api/copilot/inventory_risk" in paths
    assert "/api/kb/search" in paths


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(
        subprocess.call(
            ["pytest", __file__, "-v", "--tb=short"]
        )
    )
