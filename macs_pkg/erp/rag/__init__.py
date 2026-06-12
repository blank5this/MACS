"""ERP RAG knowledge base: indexer + query interface."""

from .indexer import build_erp_rag_engine, DEFAULT_KB_DIR
from .query import ask_kb

__all__ = [
    "build_erp_rag_engine",
    "DEFAULT_KB_DIR",
    "ask_kb",
]
