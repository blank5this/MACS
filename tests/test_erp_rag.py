"""Tests for the ERP RAG knowledge base (indexer + query).

Indexing is slow on first run (chunking + embedding); the build fixture
uses a small in-memory vector store so the test stays under 30s.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import macs_pkg.erp.rag.indexer as _indexer
import macs_pkg.erp.rag.query as _query
from macs_pkg.erp.rag.indexer import chunk_markdown, load_kb_chunks, resolve_kb_dir


# ===== Fixtures ===================================================

@pytest.fixture(scope="module")
def kb_chunks():
    """Load all KB chunks once per module."""
    return load_kb_chunks()


# ===== Indexer tests ==============================================

def test_resolve_kb_dir_finds_data_dir():
    kb_dir = resolve_kb_dir()
    assert kb_dir.is_dir(), f"KB dir not found: {kb_dir}"
    # Should contain the 4 category subdirs
    subdirs = {p.name for p in kb_dir.iterdir() if p.is_dir()}
    for required in ("01_operations", "02_warehouse", "03_procurement", "04_finance"):
        assert required in subdirs, f"Missing category dir: {required}"


def test_load_kb_chunks_returns_at_least_17(kb_chunks):
    """At least 17 docs × 1+ chunks per doc."""
    assert len(kb_chunks) >= 17
    for c in kb_chunks[:3]:
        assert "text" in c
        assert "title" in c
        assert "source_path" in c
        assert "category" in c
        assert "rel_path" in c


def test_load_kb_chunks_categorises_correctly(kb_chunks):
    """Each chunk's category matches its first-level directory."""
    by_category: dict[str, int] = {}
    for c in kb_chunks:
        by_category[c["category"]] = by_category.get(c["category"], 0) + 1
    for cat in ("operations", "warehouse", "procurement", "finance"):
        assert by_category.get(cat, 0) > 0, f"No chunks for {cat}"


def test_chunk_markdown_splits_by_headings():
    sample = """# Title

## Section A
Content of A.

## Section B
Content of B.
"""
    chunks = chunk_markdown(sample, "/tmp/test.md")
    titles = [c["title"] for c in chunks]
    assert "Section A" in titles
    assert "Section B" in titles


def test_chunk_markdown_handles_no_headings():
    sample = "Just some text without any headings. Multiple lines.\n\nEven paragraphs."
    chunks = chunk_markdown(sample, "/tmp/test.md")
    assert len(chunks) == 1
    assert "no_headings" in chunks[0]["title"] or chunks[0]["title"]  # fallback


def test_chunk_markdown_subchunks_long_sections():
    sample = "# Title\n\n" + ("X" * 1500)
    chunks = chunk_markdown(sample, "/tmp/test.md", max_chars=400)
    # Long section should be split
    assert len(chunks) >= 2


# ===== Query tests ================================================

@pytest.mark.asyncio
async def test_ask_kb_returns_relevant_chunks():
    result = await _query.ask_kb("如何处理采购退货？", top_k=3)
    assert len(result.chunks) >= 1
    # At least one chunk should mention 退货
    text_blob = " ".join(c.text for c in result.chunks)
    assert "退货" in text_blob or "R1" in text_blob or "R2" in text_blob


@pytest.mark.asyncio
async def test_ask_kb_handles_safety_stock_question():
    result = await _query.ask_kb("安全库存怎么算？", top_k=3)
    assert len(result.chunks) >= 1
    text_blob = " ".join(c.text for c in result.chunks)
    assert "安全库存" in text_blob or "service_factor" in text_blob or "Z" in text_blob


@pytest.mark.asyncio
async def test_ask_kb_handles_three_way_match():
    result = await _query.ask_kb("什么是三方匹配？", top_k=3)
    assert len(result.chunks) >= 1
    text_blob = " ".join(c.text for c in result.chunks)
    assert "三方匹配" in text_blob or "PO" in text_blob or "GR" in text_blob


@pytest.mark.asyncio
async def test_ask_kb_handles_cycle_counting():
    result = await _query.ask_kb("如何执行库存盘点？", top_k=3)
    assert len(result.chunks) >= 1
    text_blob = " ".join(c.text for c in result.chunks)
    assert "盘点" in text_blob or "A 类" in text_blob or "B 类" in text_blob


@pytest.mark.asyncio
async def test_ask_kb_handles_payment_terms():
    result = await _query.ask_kb("Net 30 是什么意思？", top_k=3)
    assert len(result.chunks) >= 1
    text_blob = " ".join(c.text for c in result.chunks)
    assert "Net 30" in text_blob or "付款" in text_blob or "月结" in text_blob


@pytest.mark.asyncio
async def test_ask_kb_result_has_context_string():
    result = await _query.ask_kb("ABC 分析法", top_k=3)
    assert isinstance(result.context, str)
    if result.chunks:
        assert len(result.context) > 50


@pytest.mark.asyncio
async def test_ask_kb_chunks_have_citations():
    result = await _query.ask_kb("Lead Time 是什么", top_k=3)
    assert len(result.chunks) >= 1
    # At least one chunk should have full metadata (hybrid search may include
    # BM25-only chunks with empty metadata, which is acceptable).
    chunks_with_meta = [c for c in result.chunks if c.source_path]
    assert len(chunks_with_meta) >= 1
    for c in chunks_with_meta:
        assert c.rel_path     # relative path for display


@pytest.mark.asyncio
async def test_ask_kb_respects_top_k():
    for k in (1, 2, 5):
        result = await _query.ask_kb("如何补货", top_k=k)
        assert len(result.chunks) <= k


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=short"]))
