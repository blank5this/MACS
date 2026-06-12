"""FastAPI app exposing the ERP AI Copilot over HTTP.

Endpoints
---------

* ``GET  /healthz``                       — liveness + module presence
* ``GET  /``                              — static frontend
* ``POST /api/copilot/chat``              — single-agent mixed-tools query
* ``POST /api/copilot/inventory_risk``    — multi-agent workflow (Day 10/11)
* ``GET  /api/kb/search?q=…``             — RAG knowledge base lookup

Design notes
------------
* All ERP modules are imported **lazily** inside endpoints so the app
  boots even without Postgres / LLM credentials configured. This
  mirrors the pattern used in ``examples/erp_copilot_multi_agent.py``.
* Resources (DB pool, LLM provider, copilot agent) are cached at
  module level and built on first request. ``reset_resources()`` is
  exposed for tests.
* The DB pool and LLM provider come from env vars by default
  (``POSTGRES_*``, ``MINIMAX_API_KEY`` / ``ANTHROPIC_API_KEY``). When
  the pool cannot connect, endpoints return ``503`` with a clear
  message — the test suite can exercise the routes without a live DB.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="用户问题 (中/英)")


class ChatResponse(BaseModel):
    question: str
    tool: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    elapsed_ms: int = 0
    error: Optional[str] = None


class InventoryRiskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class InventoryRiskResponse(BaseModel):
    question: str
    success: bool
    plan: Optional[Any] = None
    analyses: Optional[Any] = None
    purchase_recs: Optional[Any] = None
    final_report: Optional[str] = None
    elapsed_ms: int = 0
    error: Optional[str] = None


class KBSearchResponse(BaseModel):
    question: str
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    context: str = ""
    elapsed_ms: int = 0
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    erp_module: bool = True
    db_available: bool = False
    llm_available: bool = False
    web_static: bool = INDEX_HTML.exists()


# ---------------------------------------------------------------------------
# Lazy resource cache
# ---------------------------------------------------------------------------
class _ResourceCache:
    """Module-level cache for heavy resources (DB pool, LLM provider)."""

    def __init__(self) -> None:
        self.db_pool: Any = None
        self.db_pool_error: Optional[str] = None
        self.llm_provider: Any = None
        self.llm_provider_error: Optional[str] = None
        self.copilot_agent: Any = None  # ERPCopilotAgent — built lazily
        self.copilot_agent_error: Optional[str] = None

    def reset(self) -> None:
        self.db_pool = None
        self.db_pool_error = None
        self.llm_provider = None
        self.llm_provider_error = None
        self.copilot_agent = None
        self.copilot_agent_error = None

    # ----- DB pool ----------------------------------------------------

    def get_db_pool(self) -> Any:
        """Return a DatabasePool, or ``None`` if it cannot be built.

        The pool tries to connect on first acquisition. We do not want
        a missing Postgres to block module import — so we catch all
        errors and stash the message in ``db_pool_error``.
        """
        if self.db_pool is not None:
            return self.db_pool
        if self.db_pool_error is not None:
            return None
        try:
            from macs_pkg.erp.db import DatabaseConfig, DatabasePool

            cfg = DatabaseConfig.from_env()
            self.db_pool = DatabasePool(cfg)
        except Exception as exc:  # pragma: no cover — env-dependent
            self.db_pool_error = f"{type(exc).__name__}: {exc}"
            logger.warning("DB pool init failed: %s", self.db_pool_error)
            self.db_pool = None
        return self.db_pool

    # ----- LLM provider ----------------------------------------------

    def get_llm_provider(self) -> Any:
        """Return a configured LLM provider or ``None``.

        Order of preference (first env var that exists wins):
        ``MINIMAX_API_KEY`` → ``ANTHROPIC_API_KEY`` → ``OPENAI_API_KEY``.
        We try the matching provider class. If none are configured we
        return ``None`` — endpoints will report a 503.
        """
        if self.llm_provider is not None:
            return self.llm_provider
        if self.llm_provider_error is not None:
            return None
        try:
            self.llm_provider = _build_default_provider()
        except Exception as exc:  # pragma: no cover — env-dependent
            self.llm_provider_error = f"{type(exc).__name__}: {exc}"
            logger.warning("LLM provider init failed: %s", self.llm_provider_error)
            self.llm_provider = None
        return self.llm_provider

    # ----- Copilot agent ---------------------------------------------

    def get_copilot_agent(self) -> Any:
        """Build (and cache) the :class:`ERPCopilotAgent`.

        Requires both a DB pool and an LLM provider. If either is
        missing we return ``None`` and surface the reason via
        ``copilot_agent_error``.
        """
        if self.copilot_agent is not None:
            return self.copilot_agent
        if self.copilot_agent_error is not None:
            return None
        pool = self.get_db_pool()
        provider = self.get_llm_provider()
        if pool is None or provider is None:
            self.copilot_agent_error = (
                f"db_pool={'ok' if pool else 'missing'}, "
                f"provider={'ok' if provider else 'missing'}"
            )
            return None
        try:
            from macs_pkg.erp.agents.copilot_agent import build_copilot_agent
            self.copilot_agent = build_copilot_agent(
                pool=pool, provider=provider
            )
        except Exception as exc:  # pragma: no cover — env-dependent
            self.copilot_agent_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Copilot agent init failed: %s", self.copilot_agent_error)
            self.copilot_agent = None
        return self.copilot_agent


# ---------------------------------------------------------------------------
# LLM provider selection
# ---------------------------------------------------------------------------
def _build_default_provider() -> Any:
    """Pick the first available provider based on env vars.

    Falls back to ``MiniMaxProvider`` (per the plan), then Claude,
    then OpenAI. Returns ``None`` if no key is configured.
    """
    # The actual import path varies by package layout. We import
    # inside the function to keep cold-start fast and tolerate any
    # of the providers being absent.
    if os.getenv("MINIMAX_API_KEY"):
        try:
            from macs_pkg.llm.minimax import MiniMaxProvider
            return MiniMaxProvider()
        except Exception as exc:
            logger.info("MiniMaxProvider unavailable: %s", exc)
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from macs_pkg.llm.claude import ClaudeProvider
            return ClaudeProvider()
        except Exception as exc:
            logger.info("ClaudeProvider unavailable: %s", exc)
    if os.getenv("OPENAI_API_KEY"):
        try:
            from macs_pkg.llm.openai_provider import OpenAIProvider
            return OpenAIProvider()
        except Exception as exc:
            logger.info("OpenAIProvider unavailable: %s", exc)
    return None


# ---------------------------------------------------------------------------
# FastAPI app + endpoint wiring
# ---------------------------------------------------------------------------
_resources = _ResourceCache()


def create_app() -> FastAPI:
    """Build a fresh FastAPI app. Useful for tests."""
    app = FastAPI(
        title="MACS ERP AI Copilot",
        version="1.0.0-erp-copilot",
        description=(
            "HTTP wrapper around the ERP AI Copilot modules. "
            "Exposes single-agent chat, multi-agent inventory-risk "
            "workflow, and a RAG knowledge-base search."
        ),
    )

    @app.get("/healthz", response_model=HealthResponse, tags=["meta"])
    async def healthz(ping_db: bool = False) -> HealthResponse:
        """Liveness + readiness probe.

        Delegates to :func:`macs_pkg.erp.health.check_health` so the
        HTTP probe, the CLI ``make erp-check`` target, and any future
        deployment share a single source of truth.

        Without ``?ping_db=true`` we skip the actual DB round-trip and
        stay cheap (liveness probe). With ``?ping_db=true`` we open a
        1-second connection and report the result — useful for
        readiness probes that want a stronger signal.
        """
        from macs_pkg.erp.health import check_health

        report = await check_health(ping_db=ping_db, db_timeout=1.0)
        # Map the rich HealthReport onto the lean HTTP response shape.
        # The /healthz endpoint has always been a quick boolean check
        # for k8s probes; we keep that contract.
        return HealthResponse(
            status="ok" if report.ok else "degraded",
            db_available=bool(report.db.get("ok")),
            llm_available=bool(report.llm.get("ok")),
        )

    @app.get("/", include_in_schema=False)
    async def root() -> Any:
        if INDEX_HTML.exists():
            return FileResponse(str(INDEX_HTML))
        return JSONResponse(
            {"name": "MACS ERP AI Copilot", "docs": "/docs", "health": "/healthz"}
        )

    @app.post(
        "/api/copilot/chat",
        response_model=ChatResponse,
        tags=["copilot"],
    )
    async def copilot_chat(req: ChatRequest) -> ChatResponse:
        t0 = time.monotonic()
        agent = _resources.get_copilot_agent()
        if agent is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Copilot agent unavailable: "
                    f"{_resources.copilot_agent_error or 'unknown'}. "
                    "Set POSTGRES_* and MINIMAX_API_KEY (or ANTHROPIC_API_KEY) "
                    "to enable this endpoint."
                ),
            )
        try:
            raw = await agent.ask(req.question)
        except Exception as exc:
            logger.exception("copilot_chat failed")
            return ChatResponse(
                question=req.question,
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )
        return ChatResponse(
            question=req.question,
            tool=raw.get("tool"),
            result=raw.get("result"),
            error=raw.get("error"),
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    @app.post(
        "/api/copilot/inventory_risk",
        response_model=InventoryRiskResponse,
        tags=["copilot"],
    )
    async def copilot_inventory_risk(req: InventoryRiskRequest) -> InventoryRiskResponse:
        t0 = time.monotonic()
        provider = _resources.get_llm_provider()
        if provider is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "LLM provider unavailable: "
                    f"{_resources.llm_provider_error or 'unknown'}. "
                    "Set MINIMAX_API_KEY or ANTHROPIC_API_KEY."
                ),
            )
        try:
            from macs_pkg.erp.workflows import (
                InventoryRiskWorkflow,
                run_inventory_risk_analysis,
            )
            pool = _resources.get_db_pool()
            wf = InventoryRiskWorkflow(provider=provider, pool=pool)
            result = await wf.run(req.question)
        except Exception as exc:
            logger.exception("copilot_inventory_risk failed")
            return InventoryRiskResponse(
                question=req.question,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )
        return InventoryRiskResponse(
            question=result.get("question", req.question),
            success=bool(result.get("success", False)),
            plan=result.get("plan"),
            analyses=result.get("analyses"),
            purchase_recs=result.get("purchase_recs"),
            final_report=result.get("final_report"),
            error=result.get("error"),
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    @app.get(
        "/api/kb/search",
        response_model=KBSearchResponse,
        tags=["kb"],
    )
    async def kb_search(
        q: str = Query(..., min_length=1, max_length=500, description="查询问题"),
        top_k: int = Query(3, ge=1, le=20),
    ) -> KBSearchResponse:
        t0 = time.monotonic()
        try:
            from macs_pkg.erp.rag.query import ask_kb
            rag = await ask_kb(q, top_k=top_k)
        except Exception as exc:
            logger.exception("kb_search failed")
            return KBSearchResponse(
                question=q,
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )
        return KBSearchResponse(
            question=q,
            chunks=[c.model_dump() if hasattr(c, "model_dump") else dict(c)
                    for c in rag.chunks],
            context=rag.context,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    return app


# Module-level app for ``uvicorn macs_pkg.erp.web.app:app``
app = create_app()


def reset_resources() -> None:
    """Reset the module-level resource cache. Used by tests."""
    _resources.reset()


__all__ = ["app", "create_app", "reset_resources"]
