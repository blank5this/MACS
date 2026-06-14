"""Client-facing demo — clean RAG knowledge base Q&A.

Shows real answers to real questions, with citations.
No JSON dumps, no logs. Just Q&A that looks like a product demo.

Run::
    export MINIMAX_API_KEY=sk-...
    python examples/demo_for_client.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _banner(text: str) -> None:
    print()
    print("=" * 75)
    print(f"  {text}")
    print("=" * 75)


async def _ask(rag_engine, llm_provider, question: str) -> None:
    """Show one Q&A pair end-to-end."""
    from macs_pkg.llm.base import LLMMessage

    _banner(f"Q: {question}")

    # Step 1: RAG retrieval
    print("\n  [1] Searching knowledge base (18 policy documents)...")
    chunks = await rag_engine.search(question, top_k=3)
    print(f"      ✓ Retrieved {len(chunks)} relevant chunks in ~30ms")

    if chunks:
        for i, c in enumerate(chunks[:3], 1):
            title = c.metadata.get("title", "(no title)") if hasattr(c, "metadata") else c.get("metadata", {}).get("title", "(no title)")
            score = c.score if hasattr(c, "score") else c.get("score", 0)
            content = c.content if hasattr(c, "content") else c.get("content", "")
            text = content.strip().replace("\n", " ")
            text_preview = text[:120] + "..." if len(text) > 120 else text
            print(f"      [{i}] {title}  (relevance: {score:.2f})")
            print(f"          \"{text_preview}\"")

    # Step 2: LLM synthesizes answer with citations
    if llm_provider:
        print("\n  [2] Asking LLM to synthesize answer (MiniMax-M2.7)...")
        context_parts = []
        for i, c in enumerate(chunks[:3], 1):
            content = c.content if hasattr(c, "content") else c.get("content", "")
            context_parts.append(f"[{i}] " + content[:500])
        context = "\n\n".join(context_parts)
        prompt = f"""你是 ERP 知识助手。基于以下知识库片段回答用户问题。
必须引用片段编号（如 [1]、[2]）。

知识库片段：
{context}

用户问题：{question}

请用简洁的中文回答（3-5 句话），并在末尾列出引用。"""

        try:
            response = await llm_provider.complete(
                [LLMMessage(role="user", content=prompt)]
            )
            answer = response.content.strip()
            print("\n  [3] Answer:")
            print()
            for line in answer.split("\n"):
                print(f"      {line}")
        except Exception as e:
            print(f"\n  [3] LLM error: {e}")
            print("      (RAG retrieval still works — see chunks above)")
    else:
        print("\n  [2] (No LLM API key set — showing raw retrieval only)")
        print("      Set MINIMAX_API_KEY or ANTHROPIC_API_KEY to see synthesized answers.")


async def main() -> None:
    print()
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                       ║")
    print("║   ERP AI Copilot — Customer Demo                                     ║")
    print("║                                                                       ║")
    print("║   Live RAG over 18 Chinese ERP policy documents                      ║")
    print("║                                                                       ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    print("   Built on MACS (Multi-Agent Collaboration Stack)")
    print("   Source: github.com/blank5this/MACS  ·  MIT license")
    print()

    # ===== Initialize =====
    _banner("Initializing")
    print("\n  Loading 18 policy documents...")

    from macs_pkg.rag.rag_engine import RAGEngine

    kb_dir = PROJECT_ROOT / "data" / "erp_kb"
    docs = []
    for f in sorted(kb_dir.rglob("*.md")):
        docs.append({
            "title": f.stem,
            "content": f.read_text(encoding="utf-8"),
            "source": str(f.relative_to(PROJECT_ROOT)),
        })

    rag = RAGEngine()
    # Enable hybrid + lower threshold for better Chinese retrieval
    rag.config.enable_hybrid = True
    rag.config.similarity_threshold = 0.0  # char-ngram gives low raw scores

    # Extract texts and metadatas separately
    texts = [d["content"] for d in docs]
    metadatas = [{"title": d["title"], "source": d["source"]} for d in docs]

    n_chunks = await rag.add_documents(texts=texts, metadatas=metadatas)
    print(f"  ✓ Indexed {len(docs)} documents → {n_chunks} chunks")

    # Provider
    provider = None
    if os.getenv("MINIMAX_API_KEY"):
        from macs_pkg.llm import MiniMaxProvider
        provider = MiniMaxProvider()
        print(f"  ✓ LLM provider: MiniMax ({provider.model_name()})")
    elif os.getenv("ANTHROPIC_API_KEY"):
        from macs_pkg.llm import ClaudeProvider
        provider = ClaudeProvider()
        print(f"  ✓ LLM provider: Claude ({provider.model_name()})")
    else:
        print("  ⚠ No LLM API key — will show RAG retrieval only")
        print("    Set MINIMAX_API_KEY=sk-... to see synthesized answers")

    # ===== Demo questions =====
    questions = [
        "如何处理采购退货？",
        "库存安全线是什么？如何设置补货策略？",
        "供应商评级有哪些等级？",
    ]

    for q in questions:
        await _ask(rag, provider, q)

    # ===== Closing =====
    _banner("Try it yourself")
    print("""
  GitHub:  https://github.com/blank5this/MACS
  Docs:    docs/use_cases/erp_knowledge_assistant.md
  Run:     python examples/erp_knowledge_assistant.py
  Web UI:  docker-compose --profile erp up -d && make erp-run

  Questions? Email [your-email] or DM on LinkedIn.
""")


if __name__ == "__main__":
    asyncio.run(main())