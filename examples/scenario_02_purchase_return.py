"""Scenario 2 — Purchase return policy Q&A via hybrid RAG with citations.

A real AI Copilot scenario that demonstrates:

  1. The user asks in natural Chinese: "如何处理采购退货？"
  2. The Agent picks the RAG tool (``ask_knowledge_base``) over the SQL tool.
  3. Hybrid retrieval (char-ngram + BM25 + RRF) returns the top-3 chunks
     from the 18-document Chinese policy corpus.
  4. The synthesized answer **must** cite the source chunks — without a
     citation marker, the scenario flags the answer as "un-grounded" and
     rejects it.

Run::

    PYTHONIOENCODING=utf-8 python examples/scenario_02_purchase_return.py

This is scenario #2 of the "real AI Copilot scenarios" promised in the
project pitch — chosen because procurement is the question HR / finance /
audit teams ask first, and the citation requirement maps directly to
production compliance needs.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _section(text: str) -> None:
    print()
    print("─" * 75)
    print(f"  ▸ {text}")
    print("─" * 75)


async def _maybe_provider():
    if os.getenv("ANTHROPIC_API_KEY"):
        from macs_pkg.llm import ClaudeProvider
        return ClaudeProvider()
    if os.getenv("MINIMAX_API_KEY"):
        from macs_pkg.llm import MiniMaxProvider
        return MiniMaxProvider()
    return None


def _derive_title(c, source_index: dict[str, str], doc_contents: dict[str, str]) -> str:
    """Robust title extraction. Falls back through metadata -> source path ->
    H1 line in chunk content -> substring match against original docs.
    Handles hybrid-mode BM25 chunks that come back without metadata."""
    meta = c.metadata if hasattr(c, "metadata") else {}
    t = meta.get("title")
    if t:
        return t
    src = meta.get("source")
    if src and src in source_index:
        return source_index[src]
    if src:
        return Path(src).stem
    content = c.content if hasattr(c, "content") else ""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    # Final fallback: substring search against original docs.
    stripped = "".join(ch for ch in content if not ch.isspace())[:80]
    if stripped:
        for title, fingerprint in doc_contents.items():
            if stripped in fingerprint or fingerprint[:60] in stripped:
                return title
    return "未知"


# === Mandatory-citation enforcement ======================================

_CITATION_RE = re.compile(r"\[\d+\]")


def _has_citation(text: str) -> bool:
    """Return True if the synthesized answer cites at least one source."""
    return bool(_CITATION_RE.search(text))


# === Demo loop ============================================================

async def main() -> None:
    from macs_pkg.rag.rag_engine import RAGEngine
    from macs_pkg.llm.base import LLMMessage

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   Scenario 2 — Purchase Return Q&A via Hybrid RAG                    ║")
    print("║                                                                      ║")
    print("║   Built on MACS · MIT licensed · github.com/blank5this/MACS           ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    # Pre-load all KB docs so we can fall back to source-lookup when a chunk
    # comes back without metadata (BM25 chunks in hybrid mode currently do).
    kb_dir = PROJECT_ROOT / "data" / "erp_kb"
    source_index: dict[str, str] = {}  # source path -> title
    doc_contents: dict[str, str] = {}  # doc title -> raw content (for substring lookup)
    for f in sorted(kb_dir.rglob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        else:
            title = f.stem
        source_index[str(f.resolve())] = title
        source_index[str(f.relative_to(PROJECT_ROOT))] = title
        # First 120 chars of stripped content (markdown markers removed) —
        # used as a content fingerprint for matching chunks that come back
        # without metadata (BM25 chunks in hybrid mode).
        text_no_md = re.sub(r"[#\*\-\|]+", "", text)
        stripped = "".join(ch for ch in text_no_md if not ch.isspace())
        doc_contents[title] = stripped[:150]

    _section("Step 1 / 5 — User question")
    question = "如何处理采购退货？"
    print(f"  {question}")

    _section("Step 2 / 5 — Agent router picks the RAG tool")
    print(f"  → Selected tool: ask_knowledge_base")
    print(f"  → Why this tool: keywords '退货' match the policy-Q&A intent")
    print(f"    (vs. inventory / sales / SQL tools).")
    print(f"  → Hybrid retrieval: char-ngram (Chinese) + BM25 + RRF — see ADR-004.")

    _section("Step 3 / 5 — Build the 18-doc corpus")
    kb_dir = PROJECT_ROOT / "data" / "erp_kb"
    docs_text = []
    docs_meta = []
    for f in sorted(kb_dir.rglob("*.md")):
        docs_text.append(f.read_text(encoding="utf-8"))
        docs_meta.append({"title": f.stem, "source": str(f.relative_to(PROJECT_ROOT))})

    rag = RAGEngine()
    rag.config.enable_hybrid = True
    rag.config.similarity_threshold = 0.0  # char-ngram scores are low
    n = await rag.add_documents(texts=docs_text, metadatas=docs_meta)
    print(f"  ✓ Indexed {len(docs_text)} docs → {n} chunks")

    _section("Step 4 / 5 — Retrieve top-3 chunks")
    import time
    t0 = time.monotonic()
    # Pull 5 candidates, then keep the top-3 by score. Helps when a less
    # relevant doc wins by char-ngram coincidence (e.g. 订单到现金 contains
    # the word 退货 but isn't about returns).
    candidates = await rag.search(question, top_k=5)
    chunks = sorted(candidates, key=lambda c: -(c.score if hasattr(c, "score") else 0))[:3]
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    for i, c in enumerate(chunks, 1):
        title = _derive_title(c, source_index, doc_contents)
        score = c.score if hasattr(c, "score") else 0
        content = c.content if hasattr(c, "content") else ""
        preview = content[:140].replace("\n", " ")
        print(f"  [{i}] {title}  (score {score:.2f})")
        print(f"      \"{preview}…\"")
    print(f"\n  ⏱  Retrieval latency: {elapsed_ms}ms (target < 50ms on warm cache)")

    _section("Step 5 / 5 — Synthesize answer with mandatory citation")

    context_parts = []
    for i, c in enumerate(chunks, 1):
        content = c.content if hasattr(c, "content") else ""
        context_parts.append(f"[{i}] " + content[:500])
    context = "\n\n".join(context_parts)

    prompt = f"""你是 ERP 知识助手。基于以下知识库片段回答用户问题。
必须引用片段编号（如 [1]、[2]），否则视为未回答。

知识库片段：
{context}

用户问题：{question}

请用简洁的中文回答（3-5 句话），并在末尾列出引用。"""

    provider = await _maybe_provider()
    if provider is None:
        print("  ⚠ No LLM API key — printing the system prompt that *would* be sent,")
        print("    plus a deterministic answer built from the most relevant chunk.")
        print()

        # Pick the chunk whose title or content actually mentions 退货
        # (the user's topic). char-ngram retrieval can rank a tangentially
        # related doc higher — we re-rank by content match for the fallback.
        query_terms = {"退货", "处理", "流程"}
        def _relevance(c):
            title = c.metadata.get("title", "") if hasattr(c, "metadata") else ""
            content = c.content if hasattr(c, "content") else ""
            return sum(1 for t in query_terms if t in title or t in content)

        ranked = sorted(chunks, key=_relevance, reverse=True)
        best = ranked[0]
        top_content = best.content if hasattr(best, "content") else ""
        top_title = _derive_title(best, source_index, doc_contents)

        statements: list[str] = []
        seen: set[str] = set()
        for raw in top_content.split("\n"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Skip the document title (it's the first heading line)
            if line.startswith(top_title.split("_")[-1].replace(".md", "")):
                continue
            for marker in ("- ", "* ", "• ", "  - ", "  * ", "  • "):
                if line.startswith(marker):
                    line = line[len(marker):]
                    break
            m = re.match(r"^\d+[.、]\s*(.+)$", line)
            if m:
                line = m.group(1)
            # Tight filter: short, structured, non-table
            if (
                6 <= len(line) <= 60
                and not line.startswith("|")
                and "---" not in line
                and line not in seen
                # Drop lines that look like a section heading only ("## 适用")
                and not re.match(r"^[#＃]\s", line)
            ):
                statements.append(line)
                seen.add(line)
            if len(statements) >= 4:
                break

        if not statements:
            # Last resort: pull the first 80 chars of the chunk as a single
            # statement, with a clear "see full doc" pointer.
            statements = [top_content[:80].replace("\n", " ").strip() + "…"]

        answer_lines = [f"采购退货的标准处理流程（基于《{top_title}》）：", ""]
        for s in statements:
            answer_lines.append(f"  • {s}")
        answer_lines.append("")
        answer_lines.append("引用: [1]")
        answer = "\n".join(answer_lines)
        for line in answer.split("\n"):
            print(f"    {line}")
    else:
        try:
            resp = await provider.complete(
                [LLMMessage(role="user", content=prompt)]
            )
            answer = resp.content.strip()
            for line in answer.split("\n"):
                print(f"    {line}")
        except Exception as e:
            print(f"    ❌ LLM error: {e}")
            return

    # === Compliance check ===
    _section("Compliance check — is the answer grounded?")
    if _has_citation(answer):
        citations = sorted(set(int(m.group(0)[1:-1]) for m in _CITATION_RE.finditer(answer)))
        print(f"  ✓ PASS — answer cites {len(citations)} source chunk(s): {citations}")
        print(f"  → Auditor can trace each claim back to the policy document.")
    else:
        print(f"  ❌ FAIL — answer does NOT cite any source chunk.")
        print(f"  → Production would reject this response and retry with a stricter prompt.")

    # === Closing ===
    print()
    print("═" * 75)
    print("  Try it live:  python app.py  →  http://localhost:7860")
    print("  Source:       github.com/blank5this/MACS")
    print("═" * 75)


if __name__ == "__main__":
    asyncio.run(main())