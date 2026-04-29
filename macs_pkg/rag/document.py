"""Document processing for RAG - chunking and metadata management."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import re


@dataclass
class Document:
    """Represents a document for RAG.

    Attributes:
        content: The text content of the document.
        metadata: Metadata associated with the document (source, page, etc.).
        chunk_id: Unique identifier for this chunk.
        embedding: Optional pre-computed embedding vector.
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: Optional[str] = None
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.chunk_id is None:
            import uuid
            self.chunk_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "metadata": self.metadata,
            "chunk_id": self.chunk_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        return cls(
            content=data["content"],
            metadata=data.get("metadata", {}),
            chunk_id=data.get("chunk_id"),
        )


class DocumentChunker:
    """Splits documents into chunks for embedding.

    Supports multiple chunking strategies:
    - Fixed size (by characters or tokens)
    - Sentence-based
    - Paragraph-based
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n",
    ):
        """Initialize chunker.

        Args:
            chunk_size: Target size for each chunk (in characters).
            chunk_overlap: Number of overlapping characters between chunks.
            separator: Separator to use for splitting.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Split text into chunks.

        Args:
            text: Text to chunk.
            metadata: Metadata to attach to each chunk.

        Returns:
            List of Document objects.
        """
        if not text or not text.strip():
            return []

        chunks = []
        metadata = metadata or {}

        # Simple character-based chunking with overlap
        start = 0
        chunk_num = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence-ending punctuation
                for sep in ["。", "！", "？", ".", "!", "?"]:
                    last_sep = chunk_text.rfind(sep)
                    if last_sep > self.chunk_size // 2:
                        chunk_text = chunk_text[:last_sep + 1]
                        end = start + len(chunk_text)
                        break

            chunk = Document(
                content=chunk_text.strip(),
                metadata={
                    **metadata,
                    "chunk_index": chunk_num,
                    "start_char": start,
                    "end_char": end,
                },
            )
            chunks.append(chunk)

            # Move start position (with overlap)
            start = end - self.chunk_overlap
            if start >= len(text) - self.chunk_overlap:
                break
            chunk_num += 1

        return chunks

    def chunk_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Document]:
        """Chunk multiple documents.

        Args:
            texts: List of text documents.
            metadatas: Optional list of metadata dicts for each document.

        Returns:
            List of all chunks from all documents.
        """
        metadatas = metadatas or [{}] * len(texts)
        all_chunks = []

        for i, text in enumerate(texts):
            chunks = self.chunk_text(text, metadatas[i])
            all_chunks.extend(chunks)

        return all_chunks


class DocumentProcessor:
    """Processes raw documents into chunks ready for embedding.

    Supports:
    - Text cleaning and normalization
    - Metadata extraction
    - Chunking
    """

    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        clean_func: Optional[Callable[[str], str]] = None,
    ):
        self.chunker = chunker or DocumentChunker()
        self.clean_func = clean_func or self._default_clean

    @staticmethod
    def _default_clean(text: str) -> str:
        """Default text cleaning function."""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove special characters but keep Chinese, English, numbers, punctuation
        text = re.sub(r"[^\w\s\u4e00-\u9fff。，、；：？！""''【】（）.,!?\"'()]", "", text)
        return text.strip()

    def process(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        clean: bool = True,
    ) -> List[Document]:
        """Process a single document.

        Args:
            text: Raw text content.
            metadata: Document metadata.
            clean: Whether to clean the text.

        Returns:
            List of chunked documents.
        """
        if clean:
            text = self.clean_func(text)

        return self.chunker.chunk_text(text, metadata)

    def process_batch(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        clean: bool = True,
    ) -> List[Document]:
        """Process multiple documents.

        Args:
            texts: List of raw text contents.
            metadatas: Optional list of metadata dicts.
            clean: Whether to clean the texts.

        Returns:
            List of all chunked documents.
        """
        metadatas = metadatas or [{}] * len(texts)
        all_chunks = []

        for text, metadata in zip(texts, metadatas):
            if clean:
                text = self.clean_func(text)
            chunks = self.chunker.chunk_text(text, metadata)
            all_chunks.extend(chunks)

        return all_chunks
