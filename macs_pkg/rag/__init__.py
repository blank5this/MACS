"""RAG module for MACS - Retrieval Augmented Generation for AI Agents.

This module provides RAG capabilities for the MACS multi-agent system:

- Document processing and chunking
- Multiple embedding model support (sentence-transformers, OpenAI, MiniMax)
- Vector store implementations (in-memory, Chroma, FAISS)
- RAG engine for retrieval and context augmentation

Usage:
    from macs_pkg.rag import RAGEngine, RAGConfig

    # Create RAG engine
    config = RAGConfig(
        embedder_provider="dummy",  # or "sentence-transformers", "openai", "minimax"
        vector_store_type="memory",  # or "chroma", "faiss"
    )
    rag = RAGEngine(config)

    # Add documents
    await rag.add_documents([
        "MACS is a multi-agent collaboration system.",
        "It supports hierarchical, decentralized, and pipeline modes.",
    ], metadatas=[{"source": "docs"}, {"source": "docs"}])

    # Search
    results = await rag.search("What is MACS?")
    for ctx in results:
        print(f"[{ctx.score:.3f}] {ctx.content}")

    # Retrieve and augment prompt
    result = await rag.retrieve_and_augment(
        query="How does MACS work?",
        prompt_template="Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    )
    print(result["augmented_prompt"])
"""

from .document import Document, DocumentChunker, DocumentProcessor
from .embedder import (
    Embedder,
    DummyEmbedder,
    SentenceTransformerEmbedder,
    OpenAIEmbedder,
    MiniMaxEmbedder,
    create_embedder,
)
from .vector_store import (
    VectorStore,
    SearchResult,
    InMemoryVectorStore,
    ChromaVectorStore,
    FAISSVectorStore,
    create_vector_store,
)
from .rag_engine import (
    RAGConfig,
    RetrievedContext,
    RAGEngine,
    RAGEnabledExecutor,
)

__all__ = [
    # Document processing
    "Document",
    "DocumentChunker",
    "DocumentProcessor",
    # Embedders
    "Embedder",
    "DummyEmbedder",
    "SentenceTransformerEmbedder",
    "OpenAIEmbedder",
    "MiniMaxEmbedder",
    "create_embedder",
    # Vector stores
    "VectorStore",
    "SearchResult",
    "InMemoryVectorStore",
    "ChromaVectorStore",
    "FAISSVectorStore",
    "create_vector_store",
    # RAG engine
    "RAGConfig",
    "RetrievedContext",
    "RAGEngine",
    "RAGEnabledExecutor",
]
