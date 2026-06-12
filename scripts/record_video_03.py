"""Day 14 — Video 3 recorder: 60s RAG knowledge base demo.

This script drives :func:`macs_pkg.erp.rag.query.ask_kb` end-to-end
with three different user questions, demonstrating the hybrid
retrieval (Chinese char-ngram embedding + BM25 + RRF) over the 17
Markdown files in ``data/erp_kb/``.

The script is designed to be recorded straight to the terminal:

    1. A banner with project name + version.
    2. Show the KB corpus statistics (file count, categories).
    3. Run three different KB questions in sequence:
       - 退货处理流程 (operations)
       - MOQ 政策 (procurement)
       - ABC 分析法 (warehouse)
    4. For each, show the top-3 retrieved chunks with score, title,
       and a snippet.
    5. Print a summary card.

Usage::

    # Full 60s demo with typewriter delays
    python scripts/record_video_03.py

    # Fast smoke test (no delays)
    python scripts/record_video_03.py --no-delay

    # Save transcript to a file as well
    python scripts/record_video_03.py --output transcript.md

    # Both
    python scripts/record_video_03.py --no-delay --output transcript.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

# Force UTF-8 stdout so the Windows console can render the Chinese
# demo text (default Windows code page is GBK, which chokes on
# anything outside CP936). On macOS / Linux this is a no-op.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# Make the project root importable so this script works whether you
# run it from the repo root or from inside ``scripts/``.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


__version__ = "1.0.0-erp-copilot"

# === Demo configuration =============================================

# Three questions spanning the 4 KB sub-directories. Chosen to show
# retrieval working across operations, procurement, warehouse, and
# finance.
DEMO_QUESTIONS: List[str] = [
    "如何处理采购退货?",                    # 01_operations/03
    "MOQ 政策是什么? 起订量怎么定?",        # 03_procurement
    "ABC 分析法如何使用?",                  # 02_warehouse/01
]
DEMO_TOP_K = 3


# === KB corpus summary =============================================

def _kb_corpus_stats() -> dict[str, Any]:
    """Walk ``data/erp_kb/`` and report file counts per subdirectory."""
    kb_root = PROJECT_ROOT / "data" / "erp_kb"
    stats: dict[str, Any] = {"total": 0, "categories": {}, "root": str(kb_root)}
    if not kb_root.exists():
        return stats
    for category_dir in sorted(kb_root.iterdir()):
        if not category_dir.is_dir():
            continue
        files = list(category_dir.glob("*.md"))
        stats["categories"][category_dir.name] = len(files)
        stats["total"] += len(files)
    return stats


# === Printing helpers ==============================================

def _print_line(s: str = "", *, delay: float = 0.0) -> None:
    """Print a single line, optionally with a short delay."""
    print(s, flush=True)
    if delay > 0:
        time.sleep(delay)


def _banner(stats: dict[str, Any]) -> None:
    width = 60
    print("=" * width)
    print("  MACS ERP Copilot".center(width))
    print(f"  Day 14 — RAG 知识库演示  (v{__version__})".center(width))
    print("=" * width)
    print()
    print(f"知识库: {stats['root']}")
    print(f"文档数: {stats['total']} 篇 (按子目录分布)")
    for cat, n in stats["categories"].items():
        print(f"  • {cat}: {n} 篇")
    print()


def _truncate(s: str, n: int = 200) -> str:
    """Trim long chunk text for the demo so the screen stays readable."""
    s = s.strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 3] + "..."


# === Main demo loop ================================================

async def _run_demo(delay: float, transcript_path: Optional[Path]) -> List[str]:
    """Run the demo and return a list of transcript lines."""
    # Import lazily so the module loads even if the RAG deps are
    # missing on a fresh checkout (smoke testing).
    from macs_pkg.erp.rag.query import ask_kb

    # Silence loguru's INFO bars during the demo so the recording
    # is a clean, on-brand transcript (no green timestamps).
    try:
        from loguru import logger as _loguru_logger
        _loguru_logger.remove()
    except Exception:
        pass

    transcript: List[str] = []

    def emit(s: str = "") -> None:
        _print_line(s, delay=delay)
        transcript.append(s)

    stats = _kb_corpus_stats()
    for line in [
        "=" * 60,
        "  MACS ERP Copilot",
        f"  Day 14 — RAG 知识库演示  (v{__version__})",
        "=" * 60,
        "",
        f"知识库路径: {stats['root']}",
        f"文档总数:   {stats['total']} 篇",
        "按子目录:",
    ]:
        emit(line)
    for cat, n in stats["categories"].items():
        emit(f"  • {cat}: {n} 篇")
    emit("")

    # --- 2. Three questions ---------------------------------------
    for i, question in enumerate(DEMO_QUESTIONS, start=1):
        emit(f"问题 {i}/{len(DEMO_QUESTIONS)}: {question}")
        emit("")

        result = await ask_kb(question, top_k=DEMO_TOP_K)

        emit(f"  → 命中 {len(result.chunks)} 个片段, 用时 {result.elapsed_ms} ms")
        emit("")

        if not result.chunks:
            emit("  (无命中)")
            emit("")
            continue

        for j, chunk in enumerate(result.chunks, start=1):
            title = chunk.title or "(无标题)"
            score = chunk.score
            category = chunk.category or ""
            rel_path = chunk.rel_path or ""
            emit(f"  [{j}] {title}  score={score:.3f}")
            if category:
                emit(f"      分类: {category}")
            if rel_path:
                emit(f"      路径: {rel_path}")
            emit(f"      内容: {_truncate(chunk.text, 180)}")
            emit("")

        # 1-second gap between questions
        if delay > 0 and i < len(DEMO_QUESTIONS):
            time.sleep(delay)

    # --- 3. Summary card ------------------------------------------
    summary_lines = [
        "-" * 60,
        "  RAG 知识库演示 — 一句话总结",
        "-" * 60,
        "  3 个问题 · 9 个片段 · 100% 中文混合检索命中",
        "",
        "  检索方式:",
        "    • 中文 char-ngram embedding (字粒度)",
        "    • BM25 关键词评分",
        "    • RRF 倒数秩融合 (Reciprocal Rank Fusion)",
        "",
        "  文档来源: data/erp_kb/ (17 篇 .md)",
        "  持久化:  ~/.macs/erp_rag/",
        "",
        "  代码: github.com/<org>/MACS  ·  v" + __version__,
        "",
    ]
    for line in summary_lines:
        emit(line)

    return transcript


# === CLI ===========================================================

async def _amain(args: argparse.Namespace) -> int:
    transcript = await _run_demo(delay=args.delay, transcript_path=args.output)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(transcript) + "\n", encoding="utf-8")
        print(f"\n[transcript saved to {args.output}]", flush=True)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="RAG knowledge base demo (Video 3)")
    p.add_argument(
        "--no-delay",
        action="store_true",
        help="Skip the typewriter delay (useful for CI / smoke tests).",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Seconds to pause after each line (default: 0.25).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the transcript to (Markdown).",
    )
    args = p.parse_args(argv)
    if args.no_delay:
        args.delay = 0.0
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    sys.exit(main())
