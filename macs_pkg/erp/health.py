"""Standalone health check for the ERP AI Copilot.

This module exists for two reasons:

1. **CLI / Makefile reuse** — ``make erp-check`` (and any operator
   script) can call :func:`check_health` without spinning up the
   full FastAPI app, so the readiness probe works the same way from
   a shell as it does from Kubernetes.

2. **Decoupling from the web layer** — health logic lives next to
   the ERP package itself, not buried inside ``macs_pkg.erp.web``.
   Future deployments (gRPC, a different HTTP framework, plain
   cronjob) can all share the same health model.

The check has three independent dimensions:

* ``db``     — can we open a Postgres connection?
* ``llm``    — is at least one LLM provider key configured?
* ``rag``    — does the ERP RAG index exist on disk?

Each dimension can be probed independently. The function is **never
meant to raise** — failures are reported as ``{"ok": False, ...}``
so a single misbehaving subsystem cannot make the whole check
explode.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------
@dataclass
class HealthReport:
    """Structured health check output.

    Mirrors the JSON shape returned by the ``GET /healthz`` endpoint
    on the FastAPI app, so the two stay in lock-step.
    """

    ok: bool
    db: dict[str, Any] = field(default_factory=dict)
    llm: dict[str, Any] = field(default_factory=dict)
    rag: dict[str, Any] = field(default_factory=dict)
    erp_module: bool = True
    elapsed_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------
def _probe_llm() -> dict[str, Any]:
    """Return whether any LLM provider key is configured.

    We deliberately do **not** ping the API here — that would make
    the health check slow and dependent on network reachability. The
    contract is "do we have the credentials to even try?"
    """
    candidates = ("MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")
    configured = [k for k in candidates if os.getenv(k)]
    return {
        "ok": bool(configured),
        "configured_providers": configured,
    }


async def _probe_db(timeout: float = 1.0) -> dict[str, Any]:
    """Try to open a real Postgres connection with a hard timeout.

    Returns ``{"ok": False, "error": "..."}`` on any failure. Never
    raises.
    """
    try:
        from macs_pkg.erp.db import DatabaseConfig, DatabasePool
    except Exception as exc:  # pragma: no cover — env-dependent
        return {"ok": False, "error": f"import failed: {exc}"}

    try:
        cfg = DatabaseConfig.from_env()
        pool = DatabasePool(cfg)

        async with pool.connection() as conn:
            await asyncio.wait_for(
                conn.execute("SELECT 1"), timeout=timeout
            )
        return {
            "ok": True,
            "host": cfg.host,
            "port": cfg.port,
            "dbname": cfg.dbname,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
        }


def _probe_rag() -> dict[str, Any]:
    """Check whether the ERP RAG index has been built on disk.

    The index lives at ``~/.macs/erp_rag/`` by default. We treat
    "index exists" as the signal — the engine itself is lazy and
    cheap to rebuild.
    """
    persist_dir = Path(
        os.getenv("ERP_RAG_DIR") or str(Path.home() / ".macs" / "erp_rag")
    )
    exists = persist_dir.exists() and any(persist_dir.iterdir())
    return {
        "ok": exists,
        "persist_dir": str(persist_dir),
        "doc_count": len(list(persist_dir.glob("**/*.json"))) if exists else 0,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def check_health(
    *,
    ping_db: bool = True,
    db_timeout: float = 1.0,
) -> HealthReport:
    """Run all three probes and return a :class:`HealthReport`.

    Args:
        ping_db:  whether to actually open a DB connection. Set to
                  ``False`` to keep the check fast (liveness probe).
        db_timeout: ceiling in seconds for the DB round-trip.

    Returns:
        A populated :class:`HealthReport`. ``ok`` is True only when
        every dimension that was probed is itself OK. The function
        itself never raises.
    """
    import time

    t0 = time.monotonic()
    try:
        llm = _probe_llm()
        rag = _probe_rag()
        if ping_db:
            db = await _probe_db(timeout=db_timeout)
        else:
            db = {"ok": True, "skipped": True}
        ok = bool(llm.get("ok") and rag.get("ok") and db.get("ok"))
        return HealthReport(
            ok=ok,
            db=db,
            llm=llm,
            rag=rag,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as exc:  # last-resort safety net
        logger.exception("check_health exploded")
        return HealthReport(
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )


def check_health_sync(**kwargs: Any) -> HealthReport:
    """Synchronous wrapper around :func:`check_health`.

    Useful for CLI scripts and ``make`` targets where the caller is
    not already inside an event loop. The keyword arguments are
    forwarded to the async function.
    """
    return asyncio.run(check_health(**kwargs))


__all__ = [
    "HealthReport",
    "check_health",
    "check_health_sync",
]
