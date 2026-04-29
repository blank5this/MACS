"""Embedding models for RAG - converts text to vectors."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("embedder")


class Embedder(ABC):
    """Abstract base class for embedding models."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Embed a single text into a vector."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts into vectors."""
        pass


class DummyEmbedder(Embedder):
    """Dummy embedder that returns random vectors.

    Used for testing or when no real embedding model is available.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> List[float]:
        """Return a random vector."""
        import random
        return [random.random() * 2 - 1 for _ in range(self._dimension)]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Return random vectors for each text."""
        return [await self.embed(text) for text in texts]


class SentenceTransformerEmbedder(Embedder):
    """Embedding using sentence-transformers library.

    Supports multilingual models including Chinese.
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        device: Optional[str] = None,
        normalize: bool = True,
    ):
        """Initialize sentence-transformer embedder.

        Args:
            model_name: Name of the sentence-transformers model.
            device: Device to use ('cpu', 'cuda', 'mps').
            normalize: Whether to normalize embeddings to unit length.
        """
        self.model_name = model_name
        self.device = device or self._get_default_device()
        self.normalize = normalize
        self._model = None

    def _get_default_device(self) -> str:
        """Get default device based on availability."""
        import sys
        # Windows 环境下 torch 加载可能有问题，默认用 CPU
        if sys.platform == "win32":
            return "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        except OSError:
            # torch DLL load failed, use CPU
            return "cpu"
        return "cpu"

    def _load_model(self):
        """Lazy load the model."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Loaded embedding model: {self.model_name} on {self.device}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise
        except OSError as e:
            logger.error(f"Failed to load embedding model (OSError): {e}")
            raise

    @property
    def dimension(self) -> int:
        self._load_model()
        if self._model is None:
            return 384  # fallback
        return self._model.get_sentence_embedding_dimension()

    async def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        self._load_model()

        try:
            from sentence_transformers import SentenceTransformer
            import asyncio
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(texts, normalize_embeddings=self.normalize)
            )
            return embeddings.tolist()
        except OSError as e:
            logger.error(f"Embedding failed (torch issue): {e}")
            raise
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise


class OpenAIEmbedder(Embedder):
    """Embedding using OpenAI's API or compatible providers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        base_url: Optional[str] = None,
    ):
        """Initialize OpenAI-compatible embedder.

        Args:
            api_key: API key for the provider.
            model: Embedding model name.
            dimensions: Embedding dimensions (for text-embedding-3).
            base_url: Custom base URL for compatible providers.
        """
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        """Get or create the API client."""
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            return self._client
        except ImportError:
            logger.warning("openai not installed. Install with: pip install openai")
            raise

    @property
    def dimension(self) -> int:
        return self.dimensions

    async def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        client = self._get_client()

        try:
            import asyncio
            response = await asyncio.to_thread(
                client.embeddings.create,
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Embedding API call failed: {e}")
            raise


class MiniMaxEmbedder(Embedder):
    """Embedding using MiniMax API.

    MiniMax supports embeddings through their API.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "embo-01",
        dimensions: int = 1024,
        group_id: Optional[str] = None,
    ):
        """Initialize MiniMax embedder.

        Args:
            api_key: MiniMax API key.
            model: Embedding model name.
            dimensions: Embedding dimensions.
            group_id: MiniMax group ID.
        """
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.group_id = group_id
        self._client = None

    def _get_client(self):
        """Get or create the API client."""
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.minimax.chat/v1",
            )
            return self._client
        except ImportError:
            raise ImportError("openai library required for MiniMax embedder")

    @property
    def dimension(self) -> int:
        return self.dimensions

    async def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts via MiniMax API."""
        client = self._get_client()

        try:
            import asyncio
            response = await asyncio.to_thread(
                client.embeddings.create,
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"MiniMax embedding failed: {e}")
            raise


def create_embedder(
    provider: str = "dummy",
    **kwargs,
) -> Embedder:
    """Factory function to create an embedder.

    Args:
        provider: Provider name ('dummy', 'sentence-transformers', 'openai', 'minimax', 'chinese_char_ngram').
        **kwargs: Additional arguments for the embedder.

    Returns:
        Embedder instance.
    """
    if provider == "dummy":
        return DummyEmbedder(kwargs.get("dimension", 384))
    elif provider == "sentence-transformers":
        return SentenceTransformerEmbedder(
            model_name=kwargs.get("model_name", "paraphrase-multilingual-MiniLM-L12-v2"),
            device=kwargs.get("device"),
        )
    elif provider == "openai":
        return OpenAIEmbedder(
            api_key=kwargs.get("api_key"),
            model=kwargs.get("model", "text-embedding-3-small"),
            dimensions=kwargs.get("dimensions", 1536),
            base_url=kwargs.get("base_url"),
        )
    elif provider == "minimax":
        return MiniMaxEmbedder(
            api_key=kwargs["api_key"],
            model=kwargs.get("model", "embo-01"),
            dimensions=kwargs.get("dimensions", 1024),
            group_id=kwargs.get("group_id"),
        )
    elif provider == "chinese_char_ngram":
        from .chinese_embedder import ChineseCharNgramEmbedder
        return ChineseCharNgramEmbedder(
            dimension=kwargs.get("dimension", 384),
            ngram_range=kwargs.get("ngram_range", (1, 3)),
            min_df=kwargs.get("min_df", 1),
            max_features=kwargs.get("max_features", 5000),
        )
    elif provider == "bm25":
        from .chinese_embedder import BM25Embedder
        return BM25Embedder(
            dimension=kwargs.get("dimension", 384),
            k1=kwargs.get("k1", 1.5),
            b=kwargs.get("b", 0.75),
        )
    else:
        raise ValueError(f"Unknown embedder provider: {provider}")
