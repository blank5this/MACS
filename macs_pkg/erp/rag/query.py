"""Query interface for the ERP RAG knowledge base.

Thin async wrapper around :class:`RAGEngine.search` that returns a typed
``RagResult`` with citations. Use::

    from macs_pkg.erp.rag.query import ask_kb
    result = await ask_kb("如何处理采购退货？", top_k=3)
    for chunk in result.chunks:
        print(chunk["title"], chunk["score"])
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .indexer import build_erp_rag_engine

logger = logging.getLogger(__name__)


# ===== Result model ===============================================

class RagChunk(BaseModel):
    """A single retrieved chunk with metadata and a relevance score."""

    text: str
    title: str = ""
    source_path: str = ""
    rel_path: str = ""
    category: str = ""
    score: float = 0.0


class RagResult(BaseModel):
    """The full result of a KB query."""

    question: str
    chunks: list[RagChunk] = Field(default_factory=list)
    context: str = ""  # concatenated chunk texts for LLM prompts
    elapsed_ms: int = 0

    @property
    def top_chunk(self) -> Optional[RagChunk]:
        return self.chunks[0] if self.chunks else None


# ===== Module-level engine cache (lazy) ===========================

_engine_singleton: dict[str, Any] = {}


async def _get_engine():
    """Return a cached RAG engine, building it on first call."""
    if "engine" not in _engine_singleton:
        _engine_singleton["engine"] = await build_erp_rag_engine()
    return _engine_singleton["engine"]


def reset_engine_cache() -> None:
    """Forget the cached engine. Used by tests and config reloads."""
    _engine_singleton.pop("engine", None)


# ===== Public API =================================================

async def ask_kb(
    question: str,
    top_k: int = 3,
    min_score: float = 0.0,
    engine: Optional[Any] = None,
) -> RagResult:
    """Query the ERP knowledge base and return a :class:`RagResult`.

    Args:
        question: user question in Chinese or English.
        top_k:    number of chunks to retrieve (default 3).
        min_score: drop chunks with score < min_score.
        engine:   optional pre-built :class:`RAGEngine` (skip the cache).

    Returns:
        :class:`RagResult` with ``chunks``, ``context``, and ``elapsed_ms``.
    """
    import time

    if engine is None:
        engine = await _get_engine()

    t0 = time.monotonic()
    raw_results = await engine.search(question, top_k=top_k)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    chunks: list[RagChunk] = []
    for r in raw_results:
        # r is a RetrievedContext (pydantic) with .content/.score/.metadata
        score = float(getattr(r, "score", 0.0) or 0.0)
        if score < min_score:
            continue
        meta = getattr(r, "metadata", None) or {}
        content = getattr(r, "content", None) or getattr(r, "text", None) or ""
        chunks.append(RagChunk(
            text=content,
            title=meta.get("title", "") if isinstance(meta, dict) else "",
            source_path=meta.get("source_path", "") if isinstance(meta, dict) else "",
            rel_path=meta.get("rel_path", "") if isinstance(meta, dict) else "",
            category=meta.get("category", "") if isinstance(meta, dict) else "",
            score=score,
        ))

    context = "\n\n---\n\n".join(c.text for c in chunks)

    return RagResult(
        question=question,
        chunks=chunks,
        context=context,
        elapsed_ms=elapsed_ms,
    )


__all__ = ["RagChunk", "RagResult", "ask_kb", "reset_engine_cache"]
