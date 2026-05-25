"""RAG Adapter - Bridge MACS RAGEngine to LangChain Retriever.

This module provides adapters to use MACS's RAGEngine as a LangChain
Retriever, enabling seamless integration with LangChain's RAG chains
and Agent frameworks.

Usage:
    from macs_pkg.langchain.rag_adapter import RAGEngineRetriever
    from macs_pkg.rag import RAGEngine

    # Create RAG engine
    rag_engine = RAGEngine(config)

    # Convert to LangChain retriever
    retriever = RAGEngineRetriever(rag_engine, top_k=5)

    # Use with LCEL RAG chain
    chain = prompt | retriever | chat_model | output_parser
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import asyncio

# LangChain imports
_LC_ERROR: Optional[str] = None
_LC_AVAILABLE = False

try:
    from langchain_core.documents import Document as LCDocument
    from langchain_core.vectorstores import VectorStore, Retriever
    _LC_AVAILABLE = True
except (ImportError, OSError) as e:
    LCDocument = None  # type: ignore
    VectorStore = None  # type: ignore
    Retriever = None  # type: ignore
    _LC_ERROR = str(e)

if not _LC_AVAILABLE:
    import warnings
    warnings.warn(
        f"langchain-core unavailable ({_LC_ERROR}). "
        "RAG adapter will work in fallback mode without LangChain integration.",
        RuntimeWarning,
    )

# MACS imports
from macs_pkg.rag.rag_engine import RAGEngine, RAGConfig
from macs_pkg.rag.document import Document as MACSDocument


# ─── Fallback implementations (when langchain-core unavailable) ───────────────

class _FallbackRetriever:
    """Fallback Retriever when langchain-core is unavailable.

    This provides a minimal interface that can be upgraded to real LangChain
    Retriever once langchain-core is available.
    """

    def __init__(
        self,
        rag_engine: Optional[RAGEngine] = None,
        top_k: int = 5,
        search_type: str = "similarity",
        score_threshold: Optional[float] = None,
        **kwargs: Any,
    ):
        self._rag_engine = rag_engine or RAGEngine()
        self._top_k = top_k
        self._search_type = search_type
        self._score_threshold = score_threshold

    @property
    def rag_engine(self) -> RAGEngine:
        return self._rag_engine

    def get_relevant_documents(self, query: str, run_manager: Optional[Any] = None) -> List[Any]:
        """Synchronous document retrieval."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            future = loop.create_task(self._rag_engine.search(query, top_k=self._top_k))
            results = loop.run_until_complete(future)
        except Exception:
            return []

        return results

    async def aget_relevant_documents(self, query: str, run_manager: Optional[Any] = None) -> List[Any]:
        """Async document retrieval."""
        try:
            results = await self._rag_engine.search(query, top_k=self._top_k)
            return results
        except Exception:
            return []


class _FallbackVectorStore:
    """Fallback VectorStore when langchain-core is unavailable."""

    def __init__(
        self,
        rag_engine: Optional[RAGEngine] = None,
        embedding: Optional[Any] = None,
        **kwargs: Any,
    ):
        self._rag_engine = rag_engine or RAGEngine()
        self._embedding = embedding

    @property
    def embedding(self) -> Optional[Any]:
        return self._embedding

    def add_documents(self, documents: List[Any], **kwargs: Any) -> List[str]:
        texts = [getattr(doc, 'page_content', str(doc)) for doc in documents]
        metadatas = [getattr(doc, 'metadata', {}) for doc in documents]

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            future = loop.create_task(
                self._rag_engine.add_documents(texts, metadatas=metadatas)
            )
            result = loop.run_until_complete(future)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    async def aadd_documents(self, documents: List[Any], **kwargs: Any) -> List[str]:
        texts = [getattr(doc, 'page_content', str(doc)) for doc in documents]
        metadatas = [getattr(doc, 'metadata', {}) for doc in documents]

        try:
            result = await self._rag_engine.add_documents(texts, metadatas=metadatas)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    def delete(self, ids: Optional[List[str]] = None, **kwargs: Any) -> None:
        pass

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Any]:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            future = loop.create_task(self._rag_engine.search(query, top_k=k))
            results = loop.run_until_complete(future)
        except Exception:
            return []

        return results

    async def asimilarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Any]:
        try:
            results = await self._rag_engine.search(query, top_k=k)
            return results
        except Exception:
            return []

    def similarity_search_with_score(self, query: str, k: int = 4, **kwargs: Any) -> List[tuple]:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            future = loop.create_task(self._rag_engine.search(query, top_k=k))
            results = loop.run_until_complete(future)
        except Exception:
            return []

        return [(doc, getattr(doc, "score", 0.0)) for doc in results]


# ─── LangChain-compatible implementations (when langchain-core available) ─────

if _LC_AVAILABLE:
    class RAGEngineRetriever(Retriever):
        """LangChain Retriever implementation backed by MACS RAGEngine.

        This adapter wraps MACS's RAGEngine to implement the LangChain Retriever
        interface, enabling use with LCEL RAG chains and Agent frameworks.

        The RAGEngine provides:
        - Hybrid search (vector + BM25 + RRF)
        - Chinese n-gram embedding support
        - Configurable chunking and retrieval parameters

        Attributes:
            rag_engine: The underlying MACS RAGEngine instance.
            top_k: Default number of documents to retrieve.
        """

        def __init__(
            self,
            rag_engine: Optional[RAGEngine] = None,
            top_k: int = 5,
            search_type: str = "similarity",
            score_threshold: Optional[float] = None,
            **kwargs: Any,
        ):
            """Initialize the RAG retriever.

            Args:
                rag_engine: MACS RAGEngine instance. If None, creates a new one.
                top_k: Default number of documents to retrieve.
                search_type: Search type ("similarity", "mmr", "similarity_score_threshold").
                score_threshold: Minimum score threshold for similarity search.
            """
            super().__init__(**kwargs)
            self._rag_engine = rag_engine or RAGEngine()
            self._top_k = top_k
            self._search_type = search_type
            self._score_threshold = score_threshold

        @property
        def rag_engine(self) -> RAGEngine:
            """Get the underlying MACS RAGEngine."""
            return self._rag_engine

        def _convert_to_lc_document(self, doc: MACSDocument) -> LCDocument:
            """Convert MACS Document to LangChain Document.

            Args:
                doc: MACS Document instance.

            Returns:
                LangChain Document with page_content and metadata.
            """
            return LCDocument(
                page_content=doc.content,
                metadata={
                    "chunk_id": getattr(doc, "chunk_id", None),
                    "source": getattr(doc, "source", None),
                    "score": getattr(doc, "score", None),
                    **{k: v for k, v in getattr(doc, "metadata", {}).items()}
                },
            )

        def get_relevant_documents(
            self,
            query: str,
            run_manager: Optional[Any] = None,
        ) -> List[LCDocument]:
            """Synchronous document retrieval.

            This method implements the Retriever interface for synchronous use.

            Args:
                query: The search query.
                run_manager: Optional callback manager for async operations.

            Returns:
                List of relevant LangChain Documents.
            """
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                # Run async search in sync context
                future = loop.create_task(
                    self._rag_engine.search(query, top_k=self._top_k)
                )
                results = loop.run_until_complete(future)
            except Exception as e:
                # Return empty on error
                return []

            return [self._convert_to_lc_document(doc) for doc in results]

        async def aget_relevant_documents(
            self,
            query: str,
            run_manager: Optional[Any] = None,
        ) -> List[LCDocument]:
            """Async document retrieval (primary implementation).

            Args:
                query: The search query.
                run_manager: Optional callback manager.

            Returns:
                List of relevant LangChain Documents.
            """
            try:
                results = await self._rag_engine.search(query, top_k=self._top_k)
                return [self._convert_to_lc_document(doc) for doc in results]
            except Exception as e:
                # Return empty on error
                return []

        def get_relevant_documents_with_score(
            self,
            query: str,
            run_manager: Optional[Any] = None,
        ) -> List[tuple[LCDocument, float]]:
            """Get relevant documents with similarity scores.

            Args:
                query: The search query.
                run_manager: Optional callback manager.

            Returns:
                List of (Document, score) tuples.
            """
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                future = loop.create_task(
                    self._rag_engine.search(query, top_k=self._top_k)
                )
                results = loop.run_until_complete(future)
            except Exception:
                return []

            return [
                (self._convert_to_lc_document(doc), getattr(doc, "score", 0.0))
                for doc in results
            ]

else:
    RAGEngineRetriever = _FallbackRetriever


if _LC_AVAILABLE:
    class RAGEngineVectorStore(VectorStore):
        """LangChain VectorStore implementation backed by MACS RAGEngine.

        This provides a more complete VectorStore interface for cases where
        you need additional VectorStore methods beyond basic retrieval.

        Note: This is a simplified implementation that delegates to RAGEngine.
        For full VectorStore functionality, consider using the RAGEngine's
        built-in vector store support directly.
        """

        def __init__(
            self,
            rag_engine: Optional[RAGEngine] = None,
            embedding: Optional[Any] = None,
            **kwargs: Any,
        ):
            """Initialize the VectorStore.

            Args:
                rag_engine: MACS RAGEngine instance.
                embedding: LangChain embedding function (not used - RAGEngine has its own).
                **kwargs: Additional options.
            """
            super().__init__(**kwargs)
            self._rag_engine = rag_engine or RAGEngine()
            self._embedding = embedding

        @property
        def embedding(self) -> Optional[Any]:
            """Get embedding function (not used in this adapter)."""
            return self._embedding

        def add_documents(
            self,
            documents: List[LCDocument],
            **kwargs: Any,
        ) -> List[str]:
            """Add documents to the vector store.

            Args:
                documents: List of LangChain Documents to add.
                **kwargs: Additional options.

            Returns:
                List of document IDs.
            """
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                future = loop.create_task(
                    self._rag_engine.add_documents(texts, metadatas=metadatas)
                )
                result = loop.run_until_complete(future)
                return result if isinstance(result, list) else []
            except Exception:
                return []

        async def aadd_documents(
            self,
            documents: List[LCDocument],
            **kwargs: Any,
        ) -> List[str]:
            """Async add documents to the vector store.

            Args:
                documents: List of LangChain Documents to add.
                **kwargs: Additional options.

            Returns:
                List of document IDs.
            """
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            try:
                result = await self._rag_engine.add_documents(texts, metadatas=metadatas)
                return result if isinstance(result, list) else []
            except Exception:
                return []

        def delete(self, ids: Optional[List[str]] = None, **kwargs: Any) -> None:
            """Delete documents by ID.

            Args:
                ids: List of document IDs to delete.
                **kwargs: Additional options.
            """
            # RAGEngine may not support delete by ID - this is a no-op fallback
            pass

        def similarity_search(
            self,
            query: str,
            k: int = 4,
            **kwargs: Any,
        ) -> List[LCDocument]:
            """Synchronous similarity search.

            Args:
                query: Search query.
                k: Number of results to return.
                **kwargs: Additional options.

            Returns:
                List of relevant documents.
            """
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                future = loop.create_task(
                    self._rag_engine.search(query, top_k=k)
                )
                results = loop.run_until_complete(future)
            except Exception:
                return []

            return [self._rag_to_lc_document(doc) for doc in results]

        async def asimilarity_search(
            self,
            query: str,
            k: int = 4,
            **kwargs: Any,
        ) -> List[LCDocument]:
            """Async similarity search.

            Args:
                query: Search query.
                k: Number of results to return.
                **kwargs: Additional options.

            Returns:
                List of relevant documents.
            """
            try:
                results = await self._rag_engine.search(query, top_k=k)
                return [self._rag_to_lc_document(doc) for doc in results]
            except Exception:
                return []

        def similarity_search_with_score(
            self,
            query: str,
            k: int = 4,
            **kwargs: Any,
        ) -> List[tuple[LCDocument, float]]:
            """Synchronous similarity search with scores.

            Args:
                query: Search query.
                k: Number of results to return.
                **kwargs: Additional options.

            Returns:
                List of (document, score) tuples.
            """
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                future = loop.create_task(
                    self._rag_engine.search(query, top_k=k)
                )
                results = loop.run_until_complete(future)
            except Exception:
                return []

            return [
                (self._rag_to_lc_document(doc), getattr(doc, "score", 0.0))
                for doc in results
            ]

        def _rag_to_lc_document(self, doc: MACSDocument) -> LCDocument:
            """Convert MACS Document to LangChain Document."""
            return LCDocument(
                page_content=doc.content,
                metadata={
                    "chunk_id": getattr(doc, "chunk_id", None),
                    "source": getattr(doc, "source", None),
                    "score": getattr(doc, "score", None),
                    **{k: v for k, v in getattr(doc, "metadata", {}).items()}
                },
            )

else:
    RAGEngineVectorStore = _FallbackVectorStore


# ─── Convenience functions ────────────────────────────────────────────────────

def create_retriever(
    rag_engine: Optional[RAGEngine] = None,
    top_k: int = 5,
    search_type: str = "similarity",
    **kwargs: Any,
) -> RAGEngineRetriever:
    """Factory function to create a RAG retriever.

    Args:
        rag_engine: MACS RAGEngine instance.
        top_k: Number of documents to retrieve.
        search_type: Search type.
        **kwargs: Additional options.

    Returns:
        Configured RAGEngineRetriever instance.
    """
    return RAGEngineRetriever(
        rag_engine=rag_engine,
        top_k=top_k,
        search_type=search_type,
        **kwargs,
    )


def create_vectorstore(
    rag_engine: Optional[RAGEngine] = None,
    **kwargs: Any,
) -> RAGEngineVectorStore:
    """Factory function to create a RAG vector store.

    Args:
        rag_engine: MACS RAGEngine instance.
        **kwargs: Additional options.

    Returns:
        Configured RAGEngineVectorStore instance.
    """
    return RAGEngineVectorStore(rag_engine=rag_engine, **kwargs)


if __name__ == "__main__":
    print("MACS RAG Adapter - LangChain Retriever backed by MACS RAGEngine")
    print("Usage: RAGEngineRetriever(rag_engine, top_k=5)")