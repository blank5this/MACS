"""Character n-gram based embedder for Chinese text (offline, no GPU required).

This embedder uses character n-gram TF-IDF to create embeddings that capture
Chinese semantic information without requiring external API or GPU.
"""

from typing import List, Dict, Any, Optional, Union
import re
import math
from collections import Counter

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("chinese_embedder")

from .embedder import Embedder


class ChineseCharNgramEmbedder(Embedder):
    """Chinese character n-gram embedder.

    Uses character n-grams (1-3 chars) with TF-IDF weighting to create
    embeddings that capture Chinese semantic information.

    Advantage: Works offline, no GPU, fast.
    Limitation: Better than random but not as good as transformer-based.
    """

    def __init__(
        self,
        dimension: int = 384,
        ngram_range: tuple = (1, 3),
        min_df: int = 1,
        max_features: int = 5000,
    ):
        """Initialize Chinese char n-gram embedder.

        Args:
            dimension: Embedding dimension (pad/truncate to this).
            ngram_range: N-gram range (1-3 for Chinese).
            min_df: Minimum document frequency for vocabulary.
            max_features: Maximum vocabulary size.
        """
        self._dimension = dimension
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_features = max_features
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._doc_count: int = 0
        self._initialized: bool = False

    @property
    def dimension(self) -> int:
        return self._dimension

    def _tokenize(self, text: str) -> List[str]:
        """Extract character n-grams from Chinese text."""
        # Remove special chars, keep Chinese and alphanum
        text = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\w\s]', ' ', text)
        text = re.sub(r'\s+', '', text)

        ngrams = []
        for i in range(len(text)):
            for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
                if i + n <= len(text):
                    ngram = text[i:i+n]
                    if len(ngram) == n:  # 确保n-gram完整
                        ngrams.append(ngram)
        return ngrams

    def _calculate_idf(self, doc_ngrams: List[List[str]]) -> None:
        """Calculate IDF values for n-grams."""
        df = Counter()
        for ngrams in doc_ngrams:
            unique = set(ngrams)
            for ng in unique:
                df[ng] += 1

        self._idf = {}
        for ng, count in df.items():
            self._idf[ng] = math.log((self._doc_count + 1) / (count + 1))

    def _build_vocab(self, doc_ngrams: List[List[str]]) -> None:
        """Build vocabulary from documents."""
        # Count n-gram frequencies across all docs
        total_counts = Counter()
        for ngrams in doc_ngrams:
            total_counts.update(ngrams)

        # Filter by min_df and take top max_features
        filtered = {ng for ng, count in total_counts.items() if count >= self.min_df}
        sorted_ngrams = sorted(filtered, key=lambda x: total_counts[x], reverse=True)
        self._vocab = {ng: i for i, ng in enumerate(sorted_ngrams[:self.max_features])}

    async def fit(self, texts: List[str]) -> None:
        """Fit the embedder on a corpus of texts (build vocabulary and IDF)."""
        self._doc_count = len(texts)
        doc_ngrams = [self._tokenize(t) for t in texts]
        self._build_vocab(doc_ngrams)
        self._calculate_idf(doc_ngrams)
        self._initialized = True

    async def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        if not self._initialized and len(texts) > 0:
            # Fit on first batch if not initialized
            await self.fit(texts)

        results = []
        for text in texts:
            ngrams = self._tokenize(text)
            if not ngrams:
                results.append([0.0] * self._dimension)
                continue

            # Calculate TF-IDF vector
            tf = Counter(ngrams)
            vector = [0.0] * self._dimension

            for ng, count in tf.items():
                if ng in self._vocab:
                    idx = self._vocab[ng]
                    if idx >= self._dimension:
                        continue  # skip if dimension exceeded
                    tf_val = count / len(ngrams)
                    idf_val = self._idf.get(ng, 0.0)
                    vector[idx] = tf_val * idf_val

            # Truncate or pad to dimension
            if len(vector) > self._dimension:
                vector = vector[:self._dimension]
            elif len(vector) < self._dimension:
                vector = vector + [0.0] * (self._dimension - len(vector))

            # L2 normalize
            norm = math.sqrt(sum(v*v for v in vector))
            if norm > 0:
                vector = [v/norm for v in vector]

            results.append(vector)

        return results


class BM25Embedder(Embedder):
    """BM25-based embedder for Chinese (offline, no GPU).

    Uses BM25 scoring for retrieval - better than raw TF-IDF for search.
    """

    def __init__(
        self,
        dimension: int = 384,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self._dimension = dimension
        self.k1 = k1
        self.b = b
        self._vocab: Dict[str, int] = {}
        self._avgdl: float = 0
        self._doc_count: int = 0
        self._initialized: bool = False

    @property
    def dimension(self) -> int:
        return self._dimension

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for Chinese."""
        import jieba
        text = re.sub(r'[^\u4e00-\u9fff\w]', ' ', text)
        words = jieba.lcut(text)
        return [w for w in words if len(w) > 0]

    def _calculate_avgdl(self, doc_tokens: List[List[str]]) -> None:
        total_len = sum(len(tokens) for tokens in doc_tokens)
        self._avgdl = total_len / len(doc_tokens) if doc_tokens else 0

    async def fit(self, texts: List[str]) -> None:
        """Build vocabulary from corpus."""
        doc_tokens = [self._tokenize(t) for t in texts]
        self._doc_count = len(texts)

        # Build vocab from all unique words
        all_words = set()
        for tokens in doc_tokens:
            all_words.update(tokens)
        self._vocab = {w: i for i, w in enumerate(all_words)}
        self._calculate_avgdl(doc_tokens)
        self._initialized = True

    async def embed(self, text: str) -> List[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._initialized:
            await self.fit(texts)

        results = []
        for text in texts:
            tokens = self._tokenize(text)
            if not tokens:
                results.append([0.0] * self._dimension)
                continue

            tf = Counter(tokens)
            vector = [0.0] * min(len(self._vocab), self._dimension)

            for word, count in tf.items():
                if word in self._vocab and self._vocab[word] < self._dimension:
                    tf_score = (count * (self.k1 + 1)) / (count + self.k1 * (1 - self.b + self.b * len(tokens) / self._avgdl))
                    vector[self._vocab[word]] = tf_score

            # L2 normalize
            norm = math.sqrt(sum(v*v for v in vector))
            if norm > 0:
                vector = [v/norm for v in vector]

            results.append(vector)

        return results


def create_chinese_embedder(
    dimension: int = 384,
    embedder_type: str = "chinese_char_ngram",
    **kwargs,
) -> Embedder:
    """Create a Chinese text embedder.

    Args:
        dimension: Embedding dimension.
        embedder_type: 'chinese_char_ngram' or 'bm25'

    Returns:
        Embedder instance.
    """
    if embedder_type == "chinese_char_ngram":
        return ChineseCharNgramEmbedder(dimension=dimension, **kwargs)
    elif embedder_type == "bm25":
        return BM25Embedder(dimension=dimension, **kwargs)
    else:
        raise ValueError(f"Unknown embedder type: {embedder_type}")