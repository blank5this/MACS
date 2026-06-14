# Deploy ERP AI Copilot Demo Online — Step by Step

> Goal: Get a clickable URL like `https://huggingface.co/spaces/your-name/macs-erp-copilot` that interviewers can open and try without installing anything.
> Time: ~2 hours for the first deployment.

---

## Why deploy online

For hiring demos, **one URL beats a video**:

| Format | Interviewer effort | Conversion |
|--------|-------------------|------------|
| GitHub repo | Clone, install, run, debug | Low |
| Video | Watch passively, can't interact | Medium |
| **Live URL** | Click, type, see result | High |

Most interviewers spend 5-15 seconds on your portfolio. Make those seconds count.

---

## Option A — Hugging Face Spaces (recommended)

**Why**:
- Free tier (16GB RAM, 2 vCPU)
- Supports Gradio / Streamlit / Docker
- Persistent URL once deployed
- Good for AI/ML demos specifically

### Step 1: Prepare a Gradio wrapper

Create `app.py` at the repo root:

```python
"""Gradio wrapper for the ERP AI Copilot demo.

Run locally:
    pip install gradio
    python app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr

from macs_pkg.llm import MiniMaxProvider, ClaudeProvider
from macs_pkg.rag.rag_engine import RAGEngine
from macs_pkg.llm.base import LLMMessage


# ===== Initialize once at startup =====

KB_DIR = PROJECT_ROOT / "data" / "erp_kb"


async def setup_rag():
    rag = RAGEngine()
    rag.config.enable_hybrid = True
    rag.config.similarity_threshold = 0.0

    docs_text = []
    docs_meta = []
    for f in sorted(KB_DIR.rglob("*.md")):
        docs_text.append(f.read_text(encoding="utf-8"))
        docs_meta.append({"title": f.stem, "source": str(f.relative_to(PROJECT_ROOT))})

    await rag.add_documents(texts=docs_text, metadatas=docs_meta)
    return rag


# Provider selection
provider = None
if os.getenv("ANTHROPIC_API_KEY"):
    provider = ClaudeProvider()
elif os.getenv("MINIMAX_API_KEY"):
    provider = MiniMaxProvider()
else:
    print("⚠ No LLM API key set. Set in HF Spaces → Settings → Variables")


# ===== Demo function =====

rag_engine = None


async def ask(question: str) -> tuple[str, str]:
    """Ask the KB a question. Returns (answer, retrieval_log)."""
    global rag_engine
    if rag_engine is None:
        rag_engine = await setup_rag()

    # Retrieve
    chunks = await rag_engine.search(question, top_k=3)
    retrieval_log = "\n\n".join(
        f"[{i+1}] {c.metadata.get('title', '?')} (score: {c.score:.2f})\n"
        f"    {c.content[:200]}..."
        for i, c in enumerate(chunks)
    )

    if not provider:
        return (
            "⚠ No LLM API key configured. Showing RAG retrieval only.",
            retrieval_log,
        )

    # Synthesize
    context = "\n\n".join(
        f"[{i+1}] " + c.content[:500] for i, c in enumerate(chunks)
    )
    prompt = f"""你是 ERP 知识助手。基于以下知识库片段回答用户问题。
必须引用片段编号（如 [1]、[2]）。

知识库片段：
{context}

用户问题：{question}

请用简洁的中文回答（3-5 句话）。"""

    response = await provider.complete([LLMMessage(role="user", content=prompt)])
    return response.content, retrieval_log


# ===== Gradio UI =====

demo = gr.Interface(
    fn=lambda q: ask_sync(q),
    inputs=gr.Textbox(
        label="Ask a question (Chinese)",
        placeholder="如何处理采购退货？",
        lines=2,
    ),
    outputs=[
        gr.Textbox(label="Answer", lines=8),
        gr.Textbox(label="RAG retrieval (3 chunks)", lines=12),
    ],
    title="ERP AI Copilot Demo",
    description=(
        "An AI assistant for ERP / inventory / procurement questions. "
        "Built on MACS Multi-Agent framework. github.com/blank5this/MACS"
    ),
    examples=[
        ["如何处理采购退货？"],
        ["库存安全线是什么？"],
        ["供应商评级有哪些等级？"],
        ["ABC 分析法是什么？"],
        ["采购审批流程是什么？"],
    ],
)


# Sync wrapper for Gradio
def ask_sync(q):
    import asyncio
    return asyncio.run(ask(q))


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
```

### Step 2: Create requirements for HF Spaces

Create `requirements_hf.txt` (or add to `requirements.txt`):

```
gradio>=4.0
macs-pkg @ git+https://github.com/blank5this/MACS.git
```

### Step 3: Create HF Space

1. Go to https://huggingface.co/new-space
2. Name: `macs-erp-copilot`
3. SDK: **Gradio**
4. Hardware: CPU basic (free)
5. Create

### Step 4: Push code

```bash
# Clone the new space
git clone https://huggingface.co/spaces/your-name/macs-erp-copilot
cd macs-erp-copilot

# Copy your files
cp ../MACS/app.py .
cp ../MACS/requirements.txt .
# Copy KB
cp -r ../MACS/data/erp_kb .

# Add macs_pkg to the space
# Option A: install via git
# Edit requirements.txt to: macs-pkg @ git+https://github.com/blank5this/MACS.git
# Option B: copy macs_pkg/ directory

git add .
git commit -m "Initial deploy"
git push
```

### Step 5: Set API key

1. Go to https://huggingface.co/spaces/your-name/macs-erp-copilot/settings
2. Variables → New secret
   - Name: `MINIMAX_API_KEY`
   - Value: `sk-cp-...`
3. Save → Space will restart

### Step 6: Verify

Visit: `https://huggingface.co/spaces/your-name/macs-erp-copilot`

Should see a Gradio UI with textbox + examples.

---

## Option B — Streamlit Cloud (alternative)

**Why Streamlit**: Simpler than Gradio for data-heavy apps. Free tier is generous.

```python
# streamlit_app.py
import streamlit as st
import asyncio

st.set_page_config(page_title="ERP AI Copilot Demo", page_icon="🤖")
st.title("ERP AI Copilot Demo")
st.markdown("[github.com/blank5this/MACS](https://github.com/blank5this/MACS)")

question = st.text_input("Ask a question (Chinese)", "如何处理采购退货？")

if st.button("Ask"):
    answer, retrieval = asyncio.run(ask(question))
    st.subheader("Answer")
    st.write(answer)
    st.subheader("RAG retrieval")
    st.code(retrieval)
```

Deploy: connect GitHub repo at https://share.streamlit.io → auto-deploys on push.

---

## Option C — Render.com (if you want FastAPI web UI)

**Why**: Uses the existing FastAPI app instead of building a new Gradio/Streamlit frontend.

```bash
# Add to repo root
cat > render.yaml <<EOF
services:
  - type: web
    name: macs-erp-copilot
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn macs_pkg.erp.web.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: MINIMAX_API_KEY
        sync: false
      - key: POSTGRES_HOST
        value: localhost  # Won't work — see PostgreSQL section below
EOF
```

**Caveat**: Render's free tier has no PostgreSQL. You need to either:
- Use external Postgres (Render's managed PostgreSQL, free for 90 days)
- Use SQLite as fallback
- Skip the database features for the online demo (RAG + LLM only work without DB)

**Recommended**: Skip this option for v1. HF Spaces Gradio is faster.

---

## Pre-deploy checklist

Before going live, verify:

- [ ] All 256 tests still pass locally
- [ ] `python examples/demo_for_client.py` works locally
- [ ] API key is set in HF Spaces settings (NOT committed to git)
- [ ] `data/erp_kb/` directory is included in the deploy
- [ ] `app.py` runs without import errors
- [ ] First question answered correctly (test in the live UI)
- [ ] Examples load without errors

---

## After deploy

Add the URL to:
- [ ] `README.md` — replace `[demo](...)` placeholder with live URL
- [ ] `LANDING_PAGE.md` — add "Try it live" link
- [ ] `career/RESUME_PROJECT_HIRING.md` — add URL to bullet points
- [ ] LinkedIn "Featured" section
- [ ] Upwork profile

**Sample bullet point for resume:**
```
• Deployed live demo at huggingface.co/spaces/blank5this/macs-erp-copilot
  (Gradio + FastAPI + 18-doc Chinese KB), enabling interviewer Q&A
  without local setup
```

---

## Common deployment issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: macs_pkg` | Not installed in deploy | Add `macs-pkg @ git+...` to requirements |
| `No LLM API key` | Env var not set | Set in HF Spaces settings |
| `RAG returns 0 chunks` | Similarity threshold too high | Set `rag.config.similarity_threshold = 0.0` |
| `Out of memory` | HF Spaces free tier has 16GB | Use small embedding model; cap conversation history |
| `Slow first response` | Cold start | Add "warming up" log message; first request triggers model load |

---

## Cost

| Service | Free tier | Paid if needed |
|---------|-----------|----------------|
| HF Spaces | 16GB RAM, 2 vCPU, unlimited | $5/mo for more |
| Streamlit Cloud | Unlimited public apps | $20/mo for private |
| Render | 750 hours/mo free | $7/mo for always-on |
| LLM API (MiniMax-M2.7) | Pay per token | ~$0.001 per demo session |
| LLM API (Claude Haiku) | Pay per token | ~$0.003 per demo session |

**Recommendation**: Start with HF Spaces + MiniMax-M2.7 (cheapest). Total monthly cost: ~$0-5.

---

## Time estimate

| Step | Time |
|------|------|
| Write `app.py` (Gradio wrapper) | 30 min |
| Test locally | 10 min |
| Create HF Space + push code | 15 min |
| Set API key + verify | 10 min |
| Add URL to README/Landing/Resume | 15 min |

**Total**: ~80 min for a working live demo.