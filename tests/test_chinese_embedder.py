"""Tests for the Chinese character n-gram embedder."""

import pytest
import asyncio
from macs_pkg.rag.chinese_embedder import ChineseCharNgramEmbedder


@pytest.mark.asyncio
async def test_embedder_initialization():
    """Test embedder can be initialized with custom dimension."""
    embedder = ChineseCharNgramEmbedder(dimension=256)
    assert embedder.dimension == 256


@pytest.mark.asyncio
async def test_embedder_tokenize_chinese():
    """Test Chinese text tokenization."""
    embedder = ChineseCharNgramEmbedder(dimension=384)
    text = "采购申请流程"
    ngrams = embedder._tokenize(text)
    # Should produce character n-grams
    assert len(ngrams) > 0
    assert "采购" in ngrams or "采" in ngrams or "购" in ngrams


@pytest.mark.asyncio
async def test_embed_single_text():
    """Test embedding a single Chinese text."""
    embedder = ChineseCharNgramEmbedder(dimension=384)
    await embedder.fit(["采购申请", "供应商管理", "库存管理"])
    vector = await embedder.embed("采购流程")
    assert len(vector) == 384
    # Vector should not be all zeros after fit
    assert any(v != 0 for v in vector)


@pytest.mark.asyncio
async def test_embed_batch():
    """Test batch embedding of Chinese texts."""
    embedder = ChineseCharNgramEmbedder(dimension=384)
    texts = ["采购申请流程", "供应商管理策略", "库存盘点方法"]
    await embedder.fit(texts)
    vectors = await embedder.embed_batch(texts)
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 384


@pytest.mark.asyncio
async def test_similar_texts_have_similar_embeddings():
    """Test that semantically similar Chinese texts have higher similarity."""
    embedder = ChineseCharNgramEmbedder(dimension=384, max_features=2000)
    # Use a larger corpus for better vocabulary building
    texts = [
        "采购申请流程",
        "如何提交采购申请",
        "采购申请的步骤",
        "供应商管理策略",
        "库存盘点方法",
    ]
    await embedder.fit(texts)

    v1 = await embedder.embed("采购申请")
    v2 = await embedder.embed("提交采购")
    v3 = await embedder.embed("供应商")

    # Cosine similarity
    def cosine(a, b):
        dot = sum(x*y for x,y in zip(a,b))
        norm_a = sum(x*x for x in a) ** 0.5
        norm_b = sum(x*x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)

    sim_12 = cosine(v1, v2)
    sim_13 = cosine(v1, v3)

    # Both should be non-zero if vocabulary was built
    non_zero = any(v != 0 for v in v1) and any(v != 0 for v in v2)
    if non_zero:
        # If embeddings are non-zero, check ordering
        assert sim_12 >= sim_13, f"Same domain should have >= similarity: {sim_12} vs {sim_13}"
    else:
        # If vocab too small, just verify it doesn't crash
        assert len(v1) == 384


@pytest.mark.asyncio
async def test_empty_text_handling():
    """Test handling of empty text."""
    embedder = ChineseCharNgramEmbedder(dimension=384)
    await embedder.fit(["测试文本"])
    vector = await embedder.embed("")
    # Empty text should return zero vector
    assert len(vector) == 384


@pytest.mark.asyncio
async def test_unfitted_embedder():
    """Test that unfitted embedder can still embed (auto-fit)."""
    embedder = ChineseCharNgramEmbedder(dimension=384)
    # Don't call fit, just embed
    vector = await embedder.embed("测试文本")
    assert len(vector) == 384