# ADR-004: Hybrid retrieval (char-ngram + BM25 + RRF)

- **Status**: Accepted
- **Date**: 2026-04
- **Deciders**: Core team

## Context

For Chinese-language ERP policy documents, pure semantic search (embedding similarity) consistently missed:
- Exact phrases ("MOQ 政策", "R1 无缺陷退货")
- Domain-specific abbreviations
- Numeric thresholds ("5,000元", "30天")

Pure keyword search (BM25) caught those but missed synonyms ("采购" vs "进货", "库存" vs "存货").

## Decision

**Hybrid retrieval**: char-ngram embeddings + BM25 keyword, fused via Reciprocal Rank Fusion (RRF).

```
Score(chunk) = Σ 1 / (k + rank_in_retriever_i)
where k=60 (standard RRF constant)
```

Each retriever votes with its rank; the fusion sums inverse-rank scores.

```python
def rrf_fuse(*result_lists, k=60):
    scores = defaultdict(float)
    for results in result_lists:
        for rank, chunk in enumerate(results, 1):
            scores[chunk.id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])
```

## Why char-ngram (not full-word embeddings)?

- Chinese has no whitespace → word segmentation is required for word-level embeddings (jieba, etc.). This adds latency and segmentation errors.
- char-ngram captures partial-match semantics without segmentation.
- 3-grams of Chinese characters work surprisingly well as features.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| OpenAI text-embedding-3 (semantic only) | Great for English | Extra API cost, latency, may miss Chinese phrases |
| jieba + word2vec | Word-level semantics | Segmentation errors, slower |
| BM25 only | Fast, exact match | Misses synonyms |
| **Hybrid (chosen)** | Catches both | More code, two indexes to maintain |

## Consequences

**Positive:**
- 90%+ recall on Chinese policy questions (manual eval on 30 test queries).
- < 50ms query latency on 25-chunk corpus (would scale to 10K+ with same code).
- No external embedding API → fully offline capable.

**Negative:**
- char-ngram embeddings are weaker than OpenAI ada-002 semantically.
- BM25 index must be rebuilt when documents change.
- Two retrieval paths means two places to debug.

## Verification

```python
async def test_hybrid_recall():
    """A phrase-only query that pure semantic search misses."""
    results = await rag.search("MOQ 政策")
    assert any("MOQ" in r.content for r in results)

async def test_synonym_recall():
    """A synonym query that pure BM25 misses."""
    results = await rag.search("进货")  # synonym for "采购"
    assert any("采购" in r.content for r in results)
```