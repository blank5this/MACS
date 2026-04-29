"""RAG Engine - combines embedding, vector store, and retrieval for RAG pipelines."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import asyncio
import re

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("rag_engine")

from .document import Document, DocumentChunker, DocumentProcessor
from .embedder import Embedder, create_embedder, DummyEmbedder
from .vector_store import VectorStore, SearchResult, create_vector_store


# ──────────────────────────────────────────────────────────────────────────────
# BM25 Keyword Indexer (for hybrid search)
# ──────────────────────────────────────────────────────────────────────────────

class BM25Indexer:
    """Lightweight BM25 keyword search index.

    Does not require external dependencies — pure Python implementation.
    Used in hybrid search to complement vector similarity search.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._corpus: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        self._doc_lengths: List[int] = []
        self._avg_doc_length: float = 0.0
        self._vocab: Dict[str, int] = {}  # term -> df (document frequency)
        self._doc_freq: Dict[str, int] = {}  # term -> number of docs containing it
        self._num_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize Chinese text into character n-grams + word unigrams."""
        # Character bigrams for Chinese
        chars = [c for c in text if c.strip()]
        bigrams = [text[i:i+2] for i in range(len(text)-1) if text[i:i+2].strip()]
        # Simple word split (space-delimited, works for both Chinese and English)
        words = text.split()
        return chars + bigrams + words

    def _compute_idf(self, term: str, df: int, n: int) -> float:
        """Compute IDF for a term."""
        # Standard BM25 IDF formula
        return max(0.0, 1.0 - (df / n) + 0.5)

    async def index(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> None:
        """Build BM25 index from texts."""
        self._corpus = texts
        self._metadatas = metadatas or [{}] * len(texts)
        self._num_docs = len(texts)

        if self._num_docs == 0:
            return

        # Compute document frequencies
        for text in texts:
            tokens = self._tokenize(text.lower())
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1
            self._doc_lengths.append(len(tokens))

        self._avg_doc_length = sum(self._doc_lengths) / self._num_docs

        # Build vocab
        self._vocab = {term: df for term, df in self._doc_freq.items()}

    def _bm25_score(self, query_tokens: List[str], doc_idx: int) -> float:
        """Compute BM25 score for a single document."""
        doc_len = self._doc_lengths[doc_idx]
        score = 0.0
        doc_tokens = set(self._tokenize(self._corpus[doc_idx].lower()))

        for token in query_tokens:
            if token not in self._vocab:
                continue
            df = self._doc_freq[token]
            idf = self._compute_idf(token, df, self._num_docs)

            # Term frequency in this doc
            doc_tf = self._tokenize(self._corpus[doc_idx].lower()).count(token)

            # BM25 term frequency saturation
            numerator = doc_tf * (self.k1 + 1)
            denominator = doc_tf + self.k1 * (1 - self.b + self.b * doc_len / (self._avg_doc_length + 1e-8))

            score += idf * numerator / (denominator + 1e-8)

        return score

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the BM25 index.

        Returns:
            List of dicts with 'content', 'score', 'metadata', 'chunk_id'.
        """
        if not self._corpus:
            return []

        query_tokens = self._tokenize(query.lower())
        scores = []

        for i in range(self._num_docs):
            score = self._bm25_score(query_tokens, i)
            scores.append((i, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        seen_content = set()
        for doc_idx, score in scores:
            if score <= 0.0:
                continue
            content = self._corpus[doc_idx]
            # Deduplicate by content
            if content in seen_content:
                continue
            seen_content.add(content)
            results.append({
                "content": content,
                "score": score,
                "metadata": self._metadatas[doc_idx],
                "chunk_id": str(doc_idx),
            })
            if len(results) >= top_k:
                break

        return results


# ──────────────────────────────────────────────────────────────────────────────
# RRF (Reciprocal Rank Fusion) utility
# ──────────────────────────────────────────────────────────────────────────────

def rrf_fuse(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: float = 60.0,
) -> List[Dict[str, Any]]:
    """Fuse ranked results from vector search and BM25 using RRF.

    Reciprocal Rank Fusion formula: score = sum(1 / (k + rank))

    Args:
        vector_results: Results from vector search (sorted by score desc).
        bm25_results: Results from BM25 search (sorted by score desc).
        k: RRF constant (higher = less weight to low-ranked results).

    Returns:
        Combined results re-ranked by RRF score.
    """
    rrf_scores: Dict[str, float] = {}

    for rank, result in enumerate(vector_results):
        chunk_id = result.get("chunk_id", result.get("content", ""))
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    for rank, result in enumerate(bm25_results):
        chunk_id = result.get("chunk_id", result.get("content", ""))
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    # Build result map
    all_results: Dict[str, Dict[str, Any]] = {}
    for result in vector_results:
        chunk_id = result.get("chunk_id", result.get("content", ""))
        all_results[chunk_id] = {**result, "source": "vector"}

    for result in bm25_results:
        chunk_id = result.get("chunk_id", result.get("content", ""))
        if chunk_id not in all_results:
            all_results[chunk_id] = {**result, "source": "bm25"}

    # Sort by RRF score
    fused = sorted(
        [{"chunk_id": cid, "rrf_score": score, **all_results[cid]}
         for cid, score in rrf_scores.items()],
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    return fused


@dataclass
class RAGConfig:
    """Configuration for RAG engine."""
    embedder_provider: str = "dummy"
    vector_store_type: str = "memory"
    embedding_dim: int = 384
    chunk_size: int = 500
    chunk_overlap: int = 50
    default_top_k: int = 5
    similarity_threshold: float = 0.5
    enable_hybrid: bool = False  # Enable hybrid search (vector + BM25 + RRF)

    # Provider-specific settings
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    persist_directory: Optional[str] = None
    collection_name: str = "macs_rag"


@dataclass
class RetrievedContext:
    """Retrieved context with sources."""
    content: str
    score: float
    metadata: Dict[str, Any]
    chunk_id: str
    source: str = "vector"  # "vector", "bm25", or "hybrid"


class RAGEngine:
    """RAG (Retrieval Augmented Generation) Engine.

    Provides:
    - Document ingestion and chunking
    - Embedding generation
    - Vector storage and similarity search
    - Context retrieval and augmentation
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedder: Optional[Embedder] = None,
        vector_store: Optional[VectorStore] = None,
        chunker: Optional[DocumentChunker] = None,
    ):
        """Initialize RAG engine.

        Args:
            config: RAG configuration.
            embedder: Custom embedder (overrides config).
            vector_store: Custom vector store (overrides config).
            chunker: Custom document chunker.
        """
        self.config = config or RAGConfig()

        # Initialize components
        self._embedder = embedder or create_embedder(
            provider=self.config.embedder_provider,
            api_key=self.config.api_key,
            model_name=self.config.model_name,
            dimension=self.config.embedding_dim,
        )
        self._vector_store = vector_store or create_vector_store(
            store_type=self.config.vector_store_type,
            embedding_dim=self.config.embedding_dim,
            persist_directory=self.config.persist_directory,
            collection_name=self.config.collection_name,
        )
        self._chunker = chunker or DocumentChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self._processor = DocumentProcessor(chunker=self._chunker)
        self._bm25_indexer: Optional[BM25Indexer] = None
        self._bm25_chunks: List[str] = []

    @property
    def embedder(self) -> Embedder:
        """Get the embedder."""
        return self._embedder

    @property
    def vector_store(self) -> VectorStore:
        """Get the vector store."""
        return self._vector_store

    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        process: bool = True,
    ) -> int:
        """Add documents to the knowledge base.

        Args:
            texts: List of text documents.
            metadatas: Optional metadata for each document.
            process: Whether to chunk the documents.

        Returns:
            Number of chunks added.
        """
        if process:
            # Chunk documents
            chunks = self._processor.process_batch(texts, metadatas)
            chunk_texts = [c.content for c in chunks]
            chunk_metas = [c.metadata for c in chunks]
        else:
            chunk_texts = texts
            chunk_metas = metadatas or [{}] * len(texts)

        if not chunk_texts:
            return 0

        # Generate embeddings
        logger.info(f"Embedding {len(chunk_texts)} chunks...")
        embeddings = await self._embedder.embed_batch(chunk_texts)

        # Add to vector store
        ids = await self._vector_store.add_texts(
            texts=chunk_texts,
            metadatas=chunk_metas,
            embeddings=embeddings,
        )

        # Build BM25 index if hybrid search is enabled
        if self.config.enable_hybrid:
            self._bm25_chunks.extend(chunk_texts)
            self._bm25_indexer = BM25Indexer()
            await self._bm25_indexer.index(self._bm25_chunks, self._vector_store._metadatas if hasattr(self._vector_store, '_metadatas') else None)

        logger.info(f"Added {len(ids)} chunks to vector store")
        return len(ids)

    async def add_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        process: bool = True,
    ) -> int:
        """Add a single document.

        Args:
            text: Text document.
            metadata: Document metadata.
            process: Whether to chunk the document.

        Returns:
            Number of chunks added.
        """
        return await self.add_documents([text], [metadata] if metadata else None, process)

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[RetrievedContext]:
        """Search for relevant context.

        When enable_hybrid=True, combines vector search with BM25 keyword
        search using Reciprocal Rank Fusion (RRF) for better Chinese retrieval.

        Args:
            query: Search query.
            top_k: Number of results (uses config default if not provided).
            filter_func: Optional filter function for metadata.

        Returns:
            List of RetrievedContext objects.
        """
        top_k = top_k or self.config.default_top_k

        # Generate query embedding
        logger.debug(f"Searching for: {query[:50]}...")
        query_embedding = await self._embedder.embed(query)

        # Search vector store
        vector_results = await self._vector_store.search(
            query=query_embedding,
            top_k=top_k * 2,  # Fetch more for fusion
            filter_func=filter_func,
        )

        # BM25 search (if hybrid enabled and index exists)
        bm25_results: List[Dict[str, Any]] = []
        if self.config.enable_hybrid and self._bm25_indexer is not None:
            bm25_results = await self._bm25_indexer.search(query, top_k=top_k * 2)
            logger.debug(f"BM25 found {len(bm25_results)} results")

        # Hybrid fusion: RRF
        if self.config.enable_hybrid and bm25_results:
            fused = rrf_fuse(
                [
                    {"content": r.content, "score": r.score, "metadata": r.metadata, "chunk_id": r.chunk_id or ""}
                    for r in vector_results
                ],
                bm25_results,
                k=60.0,
            )

            # Normalize RRF scores to 0-1 range
            max_rrf = fused[0]["rrf_score"] if fused else 1.0
            contexts = [
                RetrievedContext(
                    content=r["content"],
                    score=r["rrf_score"] / max_rrf,  # Normalize to 0-1
                    metadata=r["metadata"],
                    chunk_id=r["chunk_id"],
                    source="hybrid",
                )
                for r in fused[:top_k]
                if r["rrf_score"] > 0
            ]
        else:
            # Pure vector search
            contexts = [
                RetrievedContext(
                    content=r.content,
                    score=r.score,
                    metadata=r.metadata,
                    chunk_id=r.chunk_id or "",
                    source="vector",
                )
                for r in vector_results
                if r.score >= self.config.similarity_threshold
            ]

        logger.info(f"Found {len(contexts)} relevant contexts (mode={'hybrid' if self.config.enable_hybrid and bm25_results else 'vector'})")
        return contexts

    async def retrieve_and_augment(
        self,
        query: str,
        prompt_template: str = "Context:\n{context}\n\nQuestion: {query}\n\nAnswer:",
        top_k: Optional[int] = None,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> Dict[str, Any]:
        """Retrieve context and augment prompt.

        Args:
            query: User query.
            prompt_template: Template with {context} and {query} placeholders.
            top_k: Number of contexts to retrieve.
            filter_func: Optional metadata filter.

        Returns:
            Dict with 'contexts', 'augmented_prompt', and 'sources'.
        """
        # Retrieve contexts
        contexts = await self.search(query, top_k, filter_func)

        if not contexts:
            return {
                "contexts": [],
                "augmented_prompt": prompt_template.format(
                    context="[No relevant context found]",
                    query=query,
                ),
                "sources": [],
            }

        # Combine context contents
        context_text = "\n---\n".join([
            f"[Source {i+1}] {c.content}"
            for i, c in enumerate(contexts)
        ])

        # Format prompt
        augmented_prompt = prompt_template.format(
            context=context_text,
            query=query,
        )

        return {
            "contexts": contexts,
            "augmented_prompt": augmented_prompt,
            "sources": [
                {
                    "chunk_id": c.chunk_id,
                    "score": c.score,
                    "metadata": c.metadata,
                }
                for c in contexts
            ],
        }

    def format_context_for_prompt(
        self,
        contexts: List[RetrievedContext],
        format_str: str = "Source {i}: {content}",
    ) -> str:
        """Format contexts for inclusion in prompt.

        Args:
            contexts: List of retrieved contexts.
            format_str: Format string with {i} and {content} placeholders.

        Returns:
            Formatted context string.
        """
        if not contexts:
            return ""

        lines = []
        for i, ctx in enumerate(contexts):
            lines.append(format_str.format(i=i + 1, content=ctx.content))

        return "\n".join(lines)

    async def delete_by_metadata(
        self,
        metadata_filter: Dict[str, Any],
    ) -> int:
        """Delete documents matching metadata filter.

        Note: This requires iterating through the store.
        Not all vector stores support efficient metadata filtering.

        Args:
            metadata_filter: Metadata key-value pairs to match.

        Returns:
            Number of documents deleted.
        """
        # Get all docs and filter
        # This is a simplified implementation
        logger.warning("delete_by_metadata may not work efficiently on all stores")
        return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base.

        Returns:
            Dict with stats (depends on vector store implementation).
        """
        return {
            "embedder": self.config.embedder_provider,
            "vector_store": self.config.vector_store_type,
            "embedding_dim": self.config.embedding_dim,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "default_top_k": self.config.default_top_k,
            "similarity_threshold": self.config.similarity_threshold,
        }

    async def clear(self) -> None:
        """Clear all documents from the knowledge base."""
        await self._vector_store.clear()
        logger.info("Knowledge base cleared")


class RAGEnabledExecutor:
    """Mixin to add RAG capability to ExecutorAgent.

    Usage:
        class RAGExecutor(RAGEnabledExecutor, ExecutorAgent):
            pass
    """

    def __init__(self, *args, rag_engine: Optional[RAGEngine] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._rag_engine = rag_engine

    def set_rag_engine(self, rag_engine: RAGEngine) -> None:
        """Set the RAG engine for this executor."""
        self._rag_engine = rag_engine

    async def execute_with_rag(
        self,
        task: Dict[str, Any],
        prompt_template: str = "Based on the following context:\n{context}\n\nTask: {query}\n\nResult:",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Execute a task with RAG augmentation.

        Args:
            task: Task dictionary with 'description' or 'query'.
            prompt_template: Prompt template with {context} and {query}.
            top_k: Number of contexts to retrieve.

        Returns:
            Execution result.
        """
        if self._rag_engine is None:
            logger.warning("RAG engine not set, executing without RAG")
            return await self.execute_subtask(task)

        query = task.get("description", task.get("query", str(task)))

        # Retrieve and augment
        result = await self._rag_engine.retrieve_and_augment(
            query=query,
            prompt_template=prompt_template,
            top_k=top_k,
        )

        # Update task with augmented prompt
        augmented_task = {
            **task,
            "description": result["augmented_prompt"],
            "_rag_contexts": result["contexts"],
            "_rag_sources": result["sources"],
        }

        # Execute
        execution_result = await self.execute_subtask(augmented_task)

        # Add RAG metadata to result
        if isinstance(execution_result, dict):
            execution_result["_rag_used"] = True
            execution_result["_rag_sources"] = result["sources"]

        return execution_result
