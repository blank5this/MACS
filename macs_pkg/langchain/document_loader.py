"""LangChain Document Loader for MACS.

This module provides document loading capabilities using LangChain's
DocumentLoader components. It supports multiple file formats with
fallback handling for optional dependencies.

Supported Formats:
    - Text files (.txt, .md) - always available
    - CSV files (.csv) - always available
    - PDF files (.pdf) - requires PyPDF2 or pdfplumber

Extension Guide:
    To add support for new formats, follow this pattern:

    1. Create a new loader class that inherits from BaseFormatLoader
    2. Implement the load() method to return List[Document]
    3. Add the extension to SUPPORTED_EXTENSIONS
    4. Add the loader to FORMAT_LOADERS dict in MultiFormatDocumentLoader

    Example for adding JSON support:

        class JSONLoader(BaseFormatLoader):
            '''Loader for JSON files.'''
            def load(self, file_path: str) -> List[Document]:
                from langchain_community.document_loaders import JSONLoader
                loader = JSONLoader(file_path, jq_schema=".")
                return loader.load()

    Then add to MultiFormatDocumentLoader:
        FORMAT_LOADERS = {
            ...
            ".json": JSONLoader,
        }

Dependencies:
    Core (always required):
        - langchain-core
        - langchain-community

    Optional:
        - PyPDF2 or pdfplumber (for PDF support)

LangChain Document Format:
    LangChain uses its own Document class with:
        - page_content: str - the text content
        - metadata: Dict[str, Any] - source, page number, etc.

    This is compatible with but separate from MACS's Document class
    in macs_pkg.rag.document.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Type, Dict as DictType
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# LangChain Document Type (imported from langchain_core)
# =============================================================================

try:
    from langchain_core.documents import Document as LangChainDocument
except ImportError:
    logger.warning("langchain-core not installed. LangChain Document unavailable.")
    LangChainDocument = None


# =============================================================================
# Base Loader Interface
# =============================================================================

class BaseFormatLoader(ABC):
    """Abstract base class for format-specific document loaders.

    All format loaders should inherit from this class and implement
    the load() method.

    Attributes:
        encoding: Character encoding to use when reading files.
    """

    def __init__(self, encoding: str = "utf-8"):
        """Initialize the loader.

        Args:
            encoding: Character encoding for file reading. Defaults to utf-8.
        """
        self.encoding = encoding

    @abstractmethod
    def load(self, file_path: str) -> List[LangChainDocument]:
        """Load documents from a file.

        Args:
            file_path: Path to the file to load.

        Returns:
            List of LangChain Document objects.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid.
        """
        pass

    def _validate_file(self, file_path: str) -> None:
        """Validate that the file exists and is readable.

        Args:
            file_path: Path to validate.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if not os.path.isfile(file_path):
            raise ValueError(f"Not a file: {file_path}")


# =============================================================================
# Text Loader (.txt, .md)
# =============================================================================

class TextLoader(BaseFormatLoader):
    """Loader for plain text and Markdown files.

    Uses LangChain's TextLoader to load .txt and .md files.
    TextLoader is part of langchain_community.document_loaders.
    """

    def load(self, file_path: str) -> List[LangChainDocument]:
        """Load a text or Markdown file.

        Args:
            file_path: Path to .txt or .md file.

        Returns:
            List containing one Document with the file's content.
        """
        self._validate_file(file_path)

        try:
            from langchain_community.document_loaders import TextLoader
        except ImportError:
            raise ImportError(
                "langchain-community is required for TextLoader. "
                "Install with: pip install langchain-community"
            )

        loader = TextLoader(file_path, encoding=self.encoding)
        return loader.load()


# =============================================================================
# CSV Loader (.csv)
# =============================================================================

class CSVLoader(BaseFormatLoader):
    """Loader for CSV files.

    Uses LangChain's CSVLoader to load .csv files. Each row becomes
    a separate Document with column names as metadata.

    Example:
        # Given a CSV with columns: name, age, city
        # Creates documents with metadata: {"name": "John", "age": "30", "city": "NYC"}
    """

    def __init__(
        self,
        encoding: str = "utf-8",
        source_column: Optional[str] = None,
        csv_args: Optional[Dict[str, Any]] = None,
    ):
        """Initialize CSV loader.

        Args:
            encoding: Character encoding for file reading.
            source_column: Column to use as source in metadata.
            csv_args: Additional arguments for csv.DictReader.
        """
        super().__init__(encoding)
        self.source_column = source_column
        self.csv_args = csv_args or {}

    def load(self, file_path: str) -> List[LangChainDocument]:
        """Load a CSV file.

        Args:
            file_path: Path to .csv file.

        Returns:
            List of Documents, one per row.
        """
        self._validate_file(file_path)

        try:
            from langchain_community.document_loaders import CSVLoader
        except ImportError:
            raise ImportError(
                "langchain-community is required for CSVLoader. "
                "Install with: pip install langchain-community"
            )

        loader = CSVLoader(
            file_path,
            encoding=self.encoding,
            source_column=self.source_column,
            csv_args=self.csv_args,
        )
        return loader.load()


# =============================================================================
# PDF Loader (.pdf) - Optional
# =============================================================================

class PDFLoader(BaseFormatLoader):
    """Loader for PDF files.

    Uses PyPDF2 or pdfplumber to extract text from PDF files.
    This loader is only available if one of these libraries is installed.

    Installation:
        pip install PyPDF2
        # or
        pip install pdfplumber
    """

    def __init__(self, extract_images: bool = False):
        """Initialize PDF loader.

        Args:
            extract_images: Whether to extract images from PDFs.
                           Only used with pdfplumber backend.
        """
        self.extract_images = extract_images
        self._backend = None

    def load(self, file_path: str) -> List[LangChainDocument]:
        """Load a PDF file.

        Args:
            file_path: Path to .pdf file.

        Returns:
            List of Documents, one per page.
        """
        self._validate_file(file_path)

        # Try PyPDF2 first, then pdfplumber
        if self._backend is None:
            self._backend = self._detect_backend()

        if self._backend == "pypdf":
            return self._load_with_pypdf(file_path)
        elif self._backend == "pdfplumber":
            return self._load_with_pdfplumber(file_path)
        else:
            raise ImportError(
                "PDF support requires PyPDF2 or pdfplumber. "
                "Install with: pip install PyPDF2\n"
                "Or: pip install pdfplumber"
            )

    def _detect_backend(self) -> str:
        """Detect available PDF library.

        Returns:
            'pypdf', 'pdfplumber', or raises ImportError.
        """
        try:
            from pypdf import PdfReader
            return "pypdf"
        except ImportError:
            pass

        try:
            import pdfplumber
            return "pdfplumber"
        except ImportError:
            pass

        raise ImportError(
            "No PDF library found. Install PyPDF2 or pdfplumber."
        )

    def _load_with_pypdf(self, file_path: str) -> List[LangChainDocument]:
        """Load PDF using PyPDF2.

        Args:
            file_path: Path to PDF file.

        Returns:
            List of Documents, one per page.
        """
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        documents = []

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                doc = LangChainDocument(
                    page_content=text,
                    metadata={
                        "source": file_path,
                        "page": page_num + 1,
                        "total_pages": len(reader.pages),
                    },
                )
                documents.append(doc)

        return documents

    def _load_with_pdfplumber(self, file_path: str) -> List[LangChainDocument]:
        """Load PDF using pdfplumber.

        Args:
            file_path: Path to PDF file.

        Returns:
            List of Documents, one per page.
        """
        import pdfplumber

        documents = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    doc = LangChainDocument(
                        page_content=text,
                        metadata={
                            "source": file_path,
                            "page": page_num + 1,
                            "total_pages": len(pdf.pages),
                        },
                    )
                    documents.append(doc)

        return documents


# =============================================================================
# Unstructured Loader - for advanced file types (JSON, HTML, etc.)
# =============================================================================

class UnstructuredLoader(BaseFormatLoader):
    """Loader using Unstructured library for various file formats.

    The Unstructured library supports many formats including:
    - JSON files
    - HTML files
    - Emails (.eml, .msg)
    - PowerPoint (.pptx)
    - Word (.docx)
    - And many more...

    Installation:
        pip install unstructured
    """

    def __init__(
        self,
        mode: str = "single",
        image_output_dir: Optional[str] = None,
    ):
        """Initialize Unstructured loader.

        Args:
            mode: Parsing mode - 'single', 'elements', or 'paged'.
            image_output_dir: Directory to save extracted images.
        """
        super().__init__()
        self.mode = mode
        self.image_output_dir = image_output_dir

    def load(self, file_path: str) -> List[LangChainDocument]:
        """Load document using Unstructured.

        Args:
            file_path: Path to the file.

        Returns:
            List of Documents.
        """
        self._validate_file(file_path)

        try:
            from langchain_community.document_loaders import UnstructuredFileLoader
        except ImportError:
            raise ImportError(
                "UnstructuredFileLoader requires langchain-community. "
                "Also install: pip install unstructured"
            )

        loader = UnstructuredFileLoader(
            file_path,
            mode=self.mode,
            image_output_dir=self.image_output_dir,
        )
        return loader.load()


# =============================================================================
# Multi-Format Document Loader
# =============================================================================

# Supported extensions and their loader classes
SUPPORTED_EXTENSIONS: DictType[str, Type[BaseFormatLoader]] = {
    ".txt": TextLoader,
    ".md": TextLoader,
    ".csv": CSVLoader,
    ".pdf": PDFLoader,
}

# Extension to description mapping
EXTENSION_DESCRIPTIONS: DictType[str, str] = {
    ".txt": "Plain text",
    ".md": "Markdown",
    ".csv": "CSV (Comma-separated values)",
    ".pdf": "PDF (Portable Document Format)",
}


class MultiFormatDocumentLoader:
    """Unified document loader supporting multiple file formats.

    This is the main entry point for loading documents. It automatically
    selects the appropriate loader based on file extension.

    Usage:
        loader = MultiFormatDocumentLoader()

        # Load a single file
        docs = loader.load("document.pdf")

        # Load multiple files
        all_docs = loader.load_batch(["doc1.txt", "doc2.md", "data.csv"])

        # Check if a format is supported
        if loader.is_supported("document.pdf"):
            docs = loader.load("document.pdf")

    Supported Formats:
        See EXTENSION_DESCRIPTIONS for full list.
    """

    def __init__(
        self,
        default_encoding: str = "utf-8",
        pdf_extract_images: bool = False,
    ):
        """Initialize the multi-format loader.

        Args:
            default_encoding: Default encoding for text files.
            pdf_extract_images: Whether to extract images from PDFs.
        """
        self.default_encoding = default_encoding
        self.pdf_extract_images = pdf_extract_images
        self._loaders: DictType[str, BaseFormatLoader] = {}

    def _get_loader(self, file_path: str) -> BaseFormatLoader:
        """Get or create a loader for the given file.

        Args:
            file_path: Path to the file.

        Returns:
            Appropriate loader instance.
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in self._loaders:
            if ext not in SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported file format: {ext}\n"
                    f"Supported formats: {list(SUPPORTED_EXTENSIONS.keys())}"
                )

            loader_class = SUPPORTED_EXTENSIONS[ext]

            # Configure loaders with appropriate settings
            if ext == ".pdf":
                self._loaders[ext] = loader_class(
                    extract_images=self.pdf_extract_images
                )
            elif ext == ".csv":
                self._loaders[ext] = loader_class(encoding=self.default_encoding)
            else:
                self._loaders[ext] = loader_class(encoding=self.default_encoding)

        return self._loaders[ext]

    def load(self, file_path: str) -> List[LangChainDocument]:
        """Load a document from a file.

        Args:
            file_path: Path to the file.

        Returns:
            List of LangChain Documents.
        """
        loader = self._get_loader(file_path)
        return loader.load(file_path)

    def load_batch(
        self,
        file_paths: List[str],
        show_progress: bool = False,
    ) -> List[LangChainDocument]:
        """Load multiple documents.

        Args:
            file_paths: List of file paths to load.
            show_progress: Whether to show a progress bar.

        Returns:
            List of all Documents from all files.
        """
        all_documents = []

        if show_progress:
            try:
                from tqdm import tqdm
                file_paths = tqdm(file_paths, desc="Loading documents")
            except ImportError:
                pass

        for file_path in file_paths:
            try:
                docs = self.load(file_path)
                all_documents.extend(docs)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue

        return all_documents

    def is_supported(self, file_path: str) -> bool:
        """Check if a file format is supported.

        Args:
            file_path: Path to check.

        Returns:
            True if the format is supported.
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def get_supported_formats() -> DictType[str, str]:
        """Get all supported formats with descriptions.

        Returns:
            Dict mapping extensions to descriptions.
        """
        return EXTENSION_DESCRIPTIONS.copy()


# =============================================================================
# Document Converter (MACS <-> LangChain)
# =============================================================================

@dataclass
class LangChainDocumentConverter:
    """Converter between MACS Document and LangChain Document.

    MACS uses its own Document class in macs_pkg.rag.document, while
    LangChain uses langchain_core.documents.Document. This converter
    allows seamless conversion between the two formats.

    Usage:
        converter = LangChainDocumentConverter()

        # Convert LangChain Document to MACS Document
        macs_doc = converter.to_macs(langchain_doc)

        # Convert MACS Document to LangChain Document
        lc_doc = converter.to_langchain(macs_doc)

        # Batch convert
        macs_docs = converter.batch_to_macs(langchain_docs)
    """

    def to_langchain(self, macs_doc: "Document") -> LangChainDocument:
        """Convert a MACS Document to a LangChain Document.

        Args:
            macs_doc: MACS Document object from macs_pkg.rag.document.

        Returns:
            LangChain Document object.
        """
        if LangChainDocument is None:
            raise ImportError("langchain-core is required for conversion")

        return LangChainDocument(
            page_content=macs_doc.content,
            metadata=macs_doc.metadata,
        )

    def to_macs(self, lc_doc: LangChainDocument) -> "Document":
        """Convert a LangChain Document to a MACS Document.

        Args:
            lc_doc: LangChain Document object.

        Returns:
            MACS Document object from macs_pkg.rag.document.
        """
        from macs_pkg.rag.document import Document

        return Document(
            content=lc_doc.page_content,
            metadata=lc_doc.metadata,
        )

    def batch_to_langchain(
        self, macs_docs: List["Document"]
    ) -> List[LangChainDocument]:
        """Convert multiple MACS Documents to LangChain Documents.

        Args:
            macs_docs: List of MACS Document objects.

        Returns:
            List of LangChain Document objects.
        """
        return [self.to_langchain(doc) for doc in macs_docs]

    def batch_to_macs(
        self, lc_docs: List[LangChainDocument]
    ) -> List["Document"]:
        """Convert multiple LangChain Documents to MACS Documents.

        Args:
            lc_docs: List of LangChain Document objects.

        Returns:
            List of MACS Document objects.
        """
        return [self.to_macs(doc) for doc in lc_docs]


# =============================================================================
# Convenience Functions
# =============================================================================

def load_document(file_path: str, **kwargs) -> List[LangChainDocument]:
    """Load a document using the appropriate loader.

    This is a convenience function that creates a MultiFormatDocumentLoader
    and loads the specified file.

    Args:
        file_path: Path to the document file.
        **kwargs: Additional arguments passed to MultiFormatDocumentLoader.

    Returns:
        List of LangChain Documents.
    """
    loader = MultiFormatDocumentLoader(**kwargs)
    return loader.load(file_path)


def load_documents(
    file_paths: List[str],
    **kwargs,
) -> List[LangChainDocument]:
    """Load multiple documents.

    Args:
        file_paths: List of file paths to load.
        **kwargs: Additional arguments passed to MultiFormatDocumentLoader.

    Returns:
        List of all LangChain Documents.
    """
    loader = MultiFormatDocumentLoader(**kwargs)
    return loader.load_batch(file_paths)


# =============================================================================
# Exports
# =============================================================================

DocumentLoader = MultiFormatDocumentLoader  # Alias for backward compatibility

__all__ = [
    # Main loader
    "MultiFormatDocumentLoader",
    "DocumentLoader",  # Alias
    # Individual loaders
    "TextLoader",
    "CSVLoader",
    "PDFLoader",
    "UnstructuredLoader",
    # Converter
    "LangChainDocumentConverter",
    # Convenience functions
    "load_document",
    "load_documents",
    # Constants
    "SUPPORTED_EXTENSIONS",
    "EXTENSION_DESCRIPTIONS",
]
