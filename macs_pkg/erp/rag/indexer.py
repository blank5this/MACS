"""Build the ERP knowledge base RAG engine from Markdown files.

Walks the ``data/erp_kb/`` directory (4 subdirectories: operations, warehouse,
procurement, finance), reads every ``.md`` file, chunks by Markdown headings,
attaches metadata (``{category, source_path, title}``), and indexes the chunks
into a :class:`RAGEngine`.

Quickstart::

    from macs_pkg.erp.rag.indexer import build_erp_rag_engine
    engine = await build_erp_rag_engine()
    results = await engine.search("如何处理采购退货？", top_k=3)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ===== Path resolution ============================================

# Walk up from this file to find the project root (the dir that contains
# both ``macs_pkg/`` and ``data/``). Falls back to ``./data/erp_kb``.
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT_CANDIDATES = [
    _THIS_DIR.parent.parent.parent,  # macs_pkg/erp/rag/indexer.py -> 3 levels up
    _THIS_DIR.parent.parent,
    Path.cwd(),
]

DEFAULT_KB_DIR: Path = (
    _PROJECT_ROOT_CANDIDATES[0] / "data" / "erp_kb"
)


def resolve_kb_dir(custom: Optional[Path] = None) -> Path:
    """Return the absolute path to the ERP knowledge base directory.

    Args:
        custom: override path; useful for tests.
    """
    if custom is not None:
        return Path(custom).expanduser().resolve()

    for candidate in _PROJECT_ROOT_CANDIDATES:
        kb_dir = candidate / "data" / "erp_kb"
        if kb_dir.is_dir():
            return kb_dir.resolve()

    return DEFAULT_KB_DIR.resolve()


# ===== Markdown chunking ==========================================

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)
_SECTION_BREAK_RE = re.compile(r"\n\s*\n")


def chunk_markdown(
    text: str,
    source_path: str,
    max_chars: int = 800,
) -> list[dict[str, Any]]:
    """Split a Markdown document into chunks keyed by H2/H3 sections.

    Each chunk has:
        * ``text``   — the chunk content (heading + body)
        * ``title``  — the section heading (or filename if none)
        * ``source_path`` — absolute file path
        * ``category``  — first-level directory (operations/warehouse/...)
    """
    chunks: list[dict[str, Any]] = []
    path = Path(source_path)
    category = path.parent.name  # e.g. "01_operations"
    display_category = _display_category(category)

    # Find all H1-H4 headings with their byte offsets
    sections: list[tuple[int, str, str]] = []
    for m in _HEADING_RE.finditer(text):
        level = len(m.group(1))
        title = m.group(2).strip()
        sections.append((m.start(), level, title))
    sections.append((len(text), 0, ""))  # sentinel

    if not sections[:-1]:
        # No headings — treat the whole doc as one chunk
        body = text.strip()
        if body:
            chunks.append({
                "text": f"# {path.stem}\n\n{body}",
                "title": path.stem,
                "source_path": source_path,
                "category": display_category,
            })
        return chunks

    for i in range(len(sections) - 1):
        start, _level, title = sections[i]
        end = sections[i + 1][0]
        body = text[start:end].strip()
        if not body:
            continue
        # Sub-chunk if a single section exceeds max_chars
        if len(body) <= max_chars:
            chunks.append({
                "text": body,
                "title": title,
                "source_path": source_path,
                "category": display_category,
            })
        else:
            # Split by paragraph
            paragraphs = _SECTION_BREAK_RE.split(body)
            current = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(current) + len(para) + 2 > max_chars and current:
                    chunks.append({
                        "text": current,
                        "title": title,
                        "source_path": source_path,
                        "category": display_category,
                    })
                    current = para
                else:
                    current = f"{current}\n\n{para}".strip()
            if current:
                chunks.append({
                    "text": current,
                    "title": title,
                    "source_path": source_path,
                    "category": display_category,
                })

    return chunks


_CATEGORY_DISPLAY = {
    "01_operations": "operations",
    "02_warehouse": "warehouse",
    "03_procurement": "procurement",
    "04_finance": "finance",
}


def _display_category(folder_name: str) -> str:
    return _CATEGORY_DISPLAY.get(folder_name, folder_name)


# ===== KB loading =================================================

def load_kb_chunks(kb_dir: Optional[Path] = None) -> list[dict[str, Any]]:
    """Walk the KB directory and return all chunks with metadata.

    Args:
        kb_dir: override KB directory. Defaults to ``data/erp_kb/``.

    Returns:
        list of dicts with ``text``, ``title``, ``source_path``, ``category``.
    """
    root = resolve_kb_dir(kb_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"ERP KB directory not found: {root}")

    chunks: list[dict[str, Any]] = []
    for md_file in sorted(root.rglob("*.md")):
        rel = md_file.relative_to(root)
        try:
            text = md_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # 不是 UTF-8 才回退到 GBK；明确告警，避免污染向量库却悄无声息
            logger.warning(
                "KB 文件 %s 非 UTF-8，回退到 GBK（errors=replace，可能丢字节）", rel
            )
            text = md_file.read_text(encoding="gbk", errors="replace")
        file_chunks = chunk_markdown(text, str(md_file))
        for c in file_chunks:
            c["rel_path"] = str(rel)
        chunks.extend(file_chunks)

    logger.info("Loaded %d chunks from %s", len(chunks), root)
    return chunks


# ===== RAG engine builder =========================================

async def build_erp_rag_engine(
    kb_dir: Optional[Path] = None,
    persist_dir: Optional[str] = None,
    collection_name: str = "erp_kb_v1",
    use_existing: bool = True,
):
    """Build and return a :class:`RAGEngine` pre-loaded with the ERP KB.

    Args:
        kb_dir: override KB directory (default: ``data/erp_kb/``).
        persist_dir: where to persist the vector store. Defaults to
                    ``~/.macs/erp_rag/``.
        collection_name: vector store collection name.
        use_existing: if True and the vector store already has chunks,
                      skip re-indexing.

    Returns:
        A :class:`RAGEngine` instance.
    """
    from macs_pkg.rag import RAGConfig, RAGEngine  # deferred import

    if persist_dir is None:
        persist_dir = str(Path.home() / ".macs" / "erp_rag")

    config = RAGConfig(
        collection_name=collection_name,
        persist_directory=persist_dir,
        # Keep in-memory vector store; persist to disk
        vector_store_type="memory",
        # Use the offline Chinese char-ngram embedder
        embedder_provider="chinese_char_ngram",
        enable_hybrid=True,
        chunk_size=400,
        chunk_overlap=50,
    )
    engine = RAGEngine(config=config)

    # Try to skip re-indexing if the store is already populated
    if use_existing:
        try:
            existing = await engine._vector_store.count()  # type: ignore[attr-defined]
            if existing and existing > 0:
                logger.info("RAG store already has %d chunks; skipping re-index", existing)
                return engine
        except Exception:
            pass  # first run; collection may not exist yet

    chunks = load_kb_chunks(kb_dir)
    if not chunks:
        raise RuntimeError("No chunks found — is the KB directory populated?")

    texts = [c["text"] for c in chunks]
    metas = [
        {k: v for k, v in c.items() if k != "text"}
        for c in chunks
    ]
    # process=False: chunks are already split by chunk_markdown; we don't
    # want add_documents to re-chunk and lose our metadata.
    added = await engine.add_documents(
        texts=texts, metadatas=metas, process=False
    )
    logger.info("Indexed %d ERP KB chunks (added=%d)", len(chunks), added)
    return engine


__all__ = [
    "DEFAULT_KB_DIR",
    "resolve_kb_dir",
    "chunk_markdown",
    "load_kb_chunks",
    "build_erp_rag_engine",
]
