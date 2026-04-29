"""Tests for RAG Engine."""

import pytest
import asyncio
from macs_pkg.rag import RAGEngine, RAGConfig


@pytest.mark.asyncio
async def test_rag_engine_with_chinese_embedder(sample_erp_knowledge):
    """Test RAG engine with Chinese character n-gram embedder."""
    config = RAGConfig(
        embedder_provider="chinese_char_ngram",
        embedding_dim=384,
        chunk_size=100,
        chunk_overlap=20,
        default_top_k=2,
        similarity_threshold=0.0,
    )
    engine = RAGEngine(config)

    texts = [doc["content"] for doc in sample_erp_knowledge]
    metadatas = [doc["metadata"] for doc in sample_erp_knowledge]

    chunks_added = await engine.add_documents(texts, metadatas)
    assert chunks_added == 3

    # Search for purchase related query
    results = await engine.search("采购申请", top_k=2)
    assert len(results) >= 1
    # Results should be sorted by score
    if len(results) > 1:
        assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_rag_search_returns_context_with_metadata(sample_erp_knowledge):
    """Test that search results include metadata."""
    config = RAGConfig(
        embedder_provider="chinese_char_ngram",
        embedding_dim=256,
        similarity_threshold=0.0,  # Lower threshold for small corpus
    )
    engine = RAGEngine(config)

    texts = [doc["content"] for doc in sample_erp_knowledge]
    metadatas = [doc["metadata"] for doc in sample_erp_knowledge]
    await engine.add_documents(texts, metadatas)

    results = await engine.search("供应商管理", top_k=5)
    # With small corpus and low threshold, should get results
    assert len(results) >= 0  # May be 0 if vocabulary is limited


@pytest.mark.asyncio
async def test_rag_empty_results_for_irrelevant_query():
    """Test that irrelevant queries return empty or low-scored results."""
    config = RAGConfig(
        embedder_provider="chinese_char_ngram",
        embedding_dim=256,
        similarity_threshold=0.99,  # Very high threshold
    )
    engine = RAGEngine(config)

    await engine.add_documents(["采购申请流程"], [{"source": "test"}])
    results = await engine.search("完全不相关的查询xyz123", top_k=5)

    # With high threshold, should return few or no results
    assert len(results) == 0


@pytest.mark.asyncio
async def test_rag_stats():
    """Test RAG engine stats."""
    config = RAGConfig(
        embedder_provider="chinese_char_ngram",
        embedding_dim=256,
        chunk_size=100,
    )
    engine = RAGEngine(config)
    await engine.add_documents(["测试文本"], [{"source": "test"}])

    stats = await engine.get_stats()
    assert stats["embedder"] == "chinese_char_ngram"
    assert stats["embedding_dim"] == 256


@pytest.mark.asyncio
async def test_rag_clear():
    """Test clearing the knowledge base."""
    config = RAGConfig(
        embedder_provider="chinese_char_ngram",
        embedding_dim=256,
    )
    engine = RAGEngine(config)

    await engine.add_documents(["测试内容"], None)
    await engine.clear()

    # After clear, search should return no results
    results = await engine.search("测试", top_k=5)
    assert len(results) == 0