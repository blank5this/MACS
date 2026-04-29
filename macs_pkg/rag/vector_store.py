"""Vector store implementations for RAG - stores and retrieves embeddings."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
import json
import os
import uuid

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("vector_store")


@dataclass
class SearchResult:
    """Represents a search result from vector store."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    chunk_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
            "chunk_id": self.chunk_id,
        }


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add texts to the store.

        Args:
            texts: List of text strings to add.
            metadatas: Optional metadata for each text.
            embeddings: Optional pre-computed embeddings.

        Returns:
            List of IDs for the added texts.
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[SearchResult]:
        """Search for similar texts.

        Args:
            query: Query text or embedding vector.
            top_k: Number of results to return.
            filter_func: Optional function to filter results by metadata.

        Returns:
            List of SearchResult objects.
        """
        pass

    @abstractmethod
    async def delete(self, ids: List[str]) -> None:
        """Delete texts by IDs."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all texts from the store."""
        pass


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store.

    Uses cosine similarity for vector search.
    Suitable for small datasets or testing.
    """

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self._texts: Dict[str, Dict[str, Any]] = {}
        self._embeddings: Dict[str, List[float]] = {}
        self._next_id = 0

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add texts to the in-memory store."""
        import numpy as np

        if embeddings is not None and len(embeddings) != len(texts):
            raise ValueError("Number of embeddings must match number of texts")

        metadatas = metadatas or [{}] * len(texts)
        ids = []

        for i, text in enumerate(texts):
            doc_id = f"doc_{self._next_id}"
            self._next_id += 1

            self._texts[doc_id] = {
                "content": text,
                "metadata": metadatas[i],
            }

            if embeddings is not None:
                self._embeddings[doc_id] = np.array(embeddings[i])
            else:
                # Placeholder - should be provided
                self._embeddings[doc_id] = np.zeros(self.embedding_dim)

            ids.append(doc_id)

        return ids

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[SearchResult]:
        """Search using simple cosine similarity."""
        import numpy as np

        if not self._embeddings:
            return []

        # For string query, use dummy embedding (caller should provide query embedding)
        if isinstance(query, str):
            # Return empty if no query embedding available
            logger.warning("InMemoryVectorStore requires pre-computed query embedding")
            return []

        query_vec = np.array(query)

        results = []
        for doc_id, embedding in self._embeddings.items():
            text_data = self._texts[doc_id]

            # Apply filter if provided
            if filter_func and not filter_func(text_data["metadata"]):
                continue

            # Cosine similarity
            norm_query = np.linalg.norm(query_vec)
            norm_doc = np.linalg.norm(embedding)
            if norm_query == 0 or norm_doc == 0:
                similarity = 0
            else:
                similarity = np.dot(query_vec, embedding) / (norm_query * norm_doc)

            results.append(SearchResult(
                content=text_data["content"],
                metadata=text_data["metadata"],
                score=float(similarity),
                chunk_id=doc_id,
            ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def delete(self, ids: List[str]) -> None:
        """Delete texts by IDs."""
        for doc_id in ids:
            self._texts.pop(doc_id, None)
            self._embeddings.pop(doc_id, None)

    async def clear(self) -> None:
        """Clear all texts."""
        self._texts.clear()
        self._embeddings.clear()


class ChromaVectorStore(VectorStore):
    """Vector store using ChromaDB.

    Persistent vector database with full-text search support.
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "macs_rag",
        embedding_dim: int = 384,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self._client = None
        self._collection = None

    def _get_client(self):
        """Get or create Chroma client."""
        if self._client is not None:
            return self._client

        try:
            import chromadb
            from chromadb.config import Settings

            settings = Settings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False,
            ) if self.persist_directory else Settings()

            self._client = chromadb.PersistentClient(path=self.persist_directory)
            logger.info(f"ChromaDB initialized at {self.persist_directory or 'memory'}")
            return self._client
        except ImportError:
            logger.warning("ChromaDB not installed. Install with: pip install chromadb")
            raise

    def _get_collection(self):
        """Get or create the collection."""
        if self._collection is not None:
            return self._collection

        client = self._get_client()
        self._collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"dimension": self.embedding_dim},
        )
        return self._collection

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add texts to Chroma."""
        collection = self._get_collection()
        metadatas = metadatas or [{}] * len(texts)
        ids = [f"chunk_{uuid.uuid4().hex[:8]}" for _ in texts]

        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

        return ids

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[SearchResult]:
        """Search Chroma collection."""
        collection = self._get_collection()

        # Note: Chroma handles embedding internally if embedder is set
        # For now, search by text (Chroma will use default embedder)
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                dist = dists[i] if i < len(dists) else 0.0

                # Apply filter if provided
                if filter_func and not filter_func(meta):
                    continue

                # Convert distance to similarity score (Chroma uses L2 distance)
                score = 1.0 / (1.0 + dist)

                search_results.append(SearchResult(
                    content=doc,
                    metadata=meta,
                    score=score,
                    chunk_id=results["ids"][0][i] if results.get("ids") else None,
                ))

        return search_results

    async def delete(self, ids: List[str]) -> None:
        """Delete by IDs."""
        collection = self._get_collection()
        collection.delete(ids=ids)

    async def clear(self) -> None:
        """Clear collection."""
        collection = self._get_collection()
        collection.delete(where={})


class FAISSVectorStore(VectorStore):
    """Vector store using FAISS.

    Facebook AI Similarity Search - efficient for large datasets.
    """

    def __init__(
        self,
        embedding_dim: int = 384,
        index_path: Optional[str] = None,
    ):
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self._index = None
        self._texts: Dict[int, Dict[str, Any]] = {}
        self._id_counter = 0

    def _get_index(self):
        """Get or create FAISS index."""
        if self._index is not None:
            return self._index

        try:
            import faiss
            # Use simple L2 index (can be replaced with IVF or HNSW for production)
            self._index = faiss.IndexFlatL2(self.embedding_dim)
            logger.info(f"FAISS index initialized with dim={self.embedding_dim}")
            return self._index
        except ImportError:
            logger.warning("faiss not installed. Install with: pip install faiss-cpu")
            raise

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add texts to FAISS index."""
        import faiss
        import numpy as np

        if embeddings is None:
            raise ValueError("FAISS requires pre-computed embeddings")

        index = self._get_index()
        metadatas = metadatas or [{}] * len(texts)

        # Convert to numpy array
        vectors = np.array(embeddings).astype("float32")

        # Add to index
        start_id = self._id_counter
        index.add(vectors)

        # Store texts and metadata
        for i, text in enumerate(texts):
            self._texts[start_id + i] = {
                "content": text,
                "metadata": metadatas[i],
            }

        self._id_counter += len(texts)

        return [f"faiss_{i}" for i in range(start_id, start_id + len(texts))]

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[SearchResult]:
        """Search FAISS index."""
        import faiss
        import numpy as np

        if isinstance(query, str):
            logger.warning("FAISS requires pre-computed query embedding for search")
            return []

        index = self._get_index()
        query_vec = np.array([query]).astype("float32")

        # Search
        distances, indices = index.search(query_vec, min(top_k * 2, index.ntotal))

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0:
                continue

            text_data = self._texts.get(int(idx))
            if text_data is None:
                continue

            # Apply filter if provided
            if filter_func and not filter_func(text_data["metadata"]):
                continue

            # Convert L2 distance to similarity score
            score = 1.0 / (1.0 + dist)

            results.append(SearchResult(
                content=text_data["content"],
                metadata=text_data["metadata"],
                score=float(score),
                chunk_id=f"faiss_{idx}",
            ))

            if len(results) >= top_k:
                break

        return results

    async def delete(self, ids: List[str]) -> None:
        """FAISS doesn't support efficient deletion - would need index rebuild."""
        logger.warning("FAISS delete not implemented - use rebuild for deletion")

    async def clear(self) -> None:
        """Clear and recreate index."""
        import faiss
        self._index = faiss.IndexFlatL2(self.embedding_dim)
        self._texts.clear()
        self._id_counter = 0


def create_vector_store(
    store_type: str = "memory",
    **kwargs,
) -> VectorStore:
    """Factory function to create a vector store.

    Args:
        store_type: Type of store ('memory', 'chroma', 'faiss').
        **kwargs: Additional arguments for the store.

    Returns:
        VectorStore instance.
    """
    if store_type == "memory":
        return InMemoryVectorStore(embedding_dim=kwargs.get("embedding_dim", 384))
    elif store_type == "chroma":
        return ChromaVectorStore(
            persist_directory=kwargs.get("persist_directory"),
            collection_name=kwargs.get("collection_name", "macs_rag"),
            embedding_dim=kwargs.get("embedding_dim", 384),
        )
    elif store_type == "faiss":
        return FAISSVectorStore(
            embedding_dim=kwargs.get("embedding_dim", 384),
            index_path=kwargs.get("index_path"),
        )
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")
