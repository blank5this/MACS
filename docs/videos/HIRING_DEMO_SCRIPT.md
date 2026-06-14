# Hiring Demo Video — Technical Deep-Dive (3-5 minutes)

> Target audience: **Hiring managers / interviewers at overseas mid-to-large AI companies**.
> Goal: In 4 minutes, prove I can design, build, ship, and operate production AI systems.
> Output: `docs/videos/hiring_demo_4min.mp4` (1920x1080, 30fps) + `docs/videos/hiring_demo_4min.gif`

---

## Why this format

**Sales demo** (already exists): "Look at my cool product"
**Hiring demo** (this one): "Look at how I think and build"

The difference:
- Sales uses smiling product screenshots
- Hiring uses **code, architecture diagrams, test output, design rationale**

---

## Scene breakdown (240 seconds total)

| # | Time | Scene | What's on screen | Voice-over |
|---|------|-------|------------------|------------|
| 1 | 0:00-0:20 | Cold open | Title card + repo link + 3 numbers | "Hi, I'm an AI Application Engineer. This is the MACS Multi-Agent framework — 256 tests passing, 6 LLM providers, MIT licensed." |
| 2 | 0:20-1:10 | Architecture walkthrough | `docs/architecture/ADR_INDEX.md` rendered | "8 architecture decisions. Not 'I used X' — here's *why* I used X over Y, and what tradeoffs I accepted." |
| 3 | 1:10-2:00 | Live code: SQL safety | Open `macs_pkg/erp/nl2sql.py`, walk 4-layer guard | "Most 'AI engineer' demos stop at 'look, it generates SQL'. Mine shows the 4-layer guardrail: AST whitelist, keyword blacklist, statement-type whitelist, parameterized values." |
| 4 | 2:00-2:40 | Live code: Hybrid RAG | Open `macs_pkg/rag/rag_engine.py`, show search + RRF | "Pure semantic search misses Chinese phrases. I combine char-ngram embeddings + BM25 keyword, fused with Reciprocal Rank Fusion." |
| 5 | 2:40-3:20 | Live test run | Terminal: `python -m pytest tests/ -q` | "256 tests passing in 75 seconds. Let me show you the safety tests — 50+ adversarial injection attempts, all blocked." |
| 6 | 3:20-4:00 | Live demo | Terminal: `python examples/demo_for_client.py` | "Real Chinese policy Q&A, real RAG retrieval, real LLM-synthesized answers with citations. Not hallucinated." |
| 7 | 4:00-4:20 | Closing | Repo + 8 ADR links + LinkedIn | "Full code on GitHub. 8 ADRs explain the design decisions. Reach out on LinkedIn — I'm looking for an AI Application Engineer role." |

**Total**: 4 min 20 sec (under the 5-min target).

---

## What to show (not just say)

### Code snippets to highlight (have them ready in your editor)

**Snippet 1 — LLM provider abstraction** (`macs_pkg/llm/base.py:30`)
```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages, system=None, **kwargs) -> LLMResponse:
        """Every provider implements this. Swap Claude for GPT-4o in 1 line."""
```

**Snippet 2 — SQL safety guardrail** (`macs_pkg/erp/nl2sql.py:180-260`)
```python
class SQLSafetyGuardrail:
    """4 sequential checks. Any one blocks the query."""
    def check(self, sql: str) -> None:
        self._ast_whitelist_check(sql)      # Layer 1
        self._keyword_blacklist_check(sql)  # Layer 2
        self._statement_type_check(sql)     # Layer 3
        # Layer 4: parameterization happens at execution time
```

**Snippet 3 — Hybrid retrieval RRF** (`macs_pkg/rag/rag_engine.py:387-394`)
```python
fused = rrf_fuse(vector_results, bm25_results, k=60.0)
# Standard formula: sum of 1/(k + rank) across retrievers
```

**Snippet 4 — Exponential backoff** (`macs_pkg/llm/agents.py:356-365`)
```python
base_delay = 0.5 * (2 ** attempt)  # 0.5, 1, 2, 4 seconds
jitter = base_delay * 0.25 * (2 * random.random() - 1)
await asyncio.sleep(base_delay + jitter)
```

### Architecture diagram to show (`docs/architecture/ADR_INDEX.md`)

Have it rendered in browser or VSCode Mermaid extension:

```
┌────────────────────────────────────────────────────┐
│  MACS — 8 Architecture Decisions                   │
├────────────────────────────────────────────────────┤
│  001  async Python throughout     [accepted]       │
│  002  pluggable LLM providers     [accepted]       │
│  003  4-layer SQL safety          [accepted]       │
│  004  hybrid RAG (char-ngram+BM25)[accepted]       │
│  005  exp backoff + jitter        [accepted]       │
│  006  conversation cap = 100      [accepted]       │
│  007  read-only DB user default   [accepted]       │
│  008  proactive over reactive RAG [accepted]       │
└────────────────────────────────────────────────────┘
```

---

## Voice-over script (~520 words, ~3:30 spoken)

```
[Scene 1 - Cold open, 20s]
Hi, I'm an AI Application Engineer. This is the MACS Multi-Agent
Collaboration Stack — an open-source Python framework on GitHub,
MIT licensed, 256 tests passing.

It supports 6 LLM providers: Claude, GPT-4o, MiniMax-M2.7, Qwen,
DeepSeek, and Zhipu. It has 4 collaboration modes — hierarchical,
pipeline, decentralized, and dynamic. And on top of it, I built an
ERP AI Copilot that turns natural-language questions into safe
PostgreSQL queries.

[Scene 2 - Architecture, 50s]
Before showing code, here's the architecture decisions log —
8 ADRs, each one answering "why this, not that."

Why async Python? Because LLM calls are I/O-bound — every agent
step blocks on an API roundtrip. Sync code would serialize
multi-agent workflows.

Why a pluggable LLM provider abstraction? Because we want to A/B
test models without rewriting business logic.

Why 4 layers of SQL safety? Because "the LLM said so" is not
a security guarantee. We need AST whitelisting, keyword
blacklisting, statement-type checking, AND parameterized
values — defense in depth.

Why hybrid retrieval? Because pure semantic search misses
Chinese phrases, and pure keyword misses synonyms. We fuse
char-ngram embeddings with BM25 using Reciprocal Rank Fusion.

Why exponential backoff with jitter? Because naive retry
during a rate limit makes the outage worse. ±25% jitter
spreads retries across the recovery window.

These are the tradeoffs. I can defend any of them in an
interview.

[Scene 3 - SQL safety code, 50s]
Here's the 4-layer guardrail in code. Each layer is independent —
any one blocks the query.

Layer 1: parse the SQL into an AST. Allow only SELECT and WITH
nodes. Reject anything else.

Layer 2: scan for forbidden keywords — DROP, DELETE, INSERT,
UPDATE, ALTER, TRUNCATE. Even if they're in a comment.

Layer 3: check that the query targets only TABLE and VIEW
objects in the user schema, not system catalogs.

Layer 4: parameterize all user values at execution time.
No string interpolation, ever.

[Scene 4 - Hybrid RAG code, 40s]
And here's the hybrid retrieval. Two paths: char-ngram
embeddings for semantic similarity, BM25 for exact phrase
match. Fused via Reciprocal Rank Fusion — standard formula,
1 over k plus rank.

This catches both "MOQ 政策" (phrase) and "进货" (synonym for
"采购"). Pure semantic would miss the first; pure keyword
would miss the second.

[Scene 5 - Tests, 40s]
Now let me show you the test suite. 256 tests in 75 seconds.

I'll run the SQL safety tests specifically. 50+ adversarial
cases — DROP TABLE, UNION SELECT injection, sqlite_master
exfiltration, pg_shadow access. All blocked.

This isn't a toy. It runs in production.

[Scene 6 - Live demo, 40s]
Here's a live demo — real Chinese policy Q&A.

"How do I handle a purchase return?" — RAG retrieves 3 chunks
from the policy corpus, LLM synthesizes an answer citing the
right sections. R1, R2, R3 grading, real references, real
content. Not hallucinated.

[Scene 7 - Closing, 20s]
Full code on GitHub — github.com/blank5this/MACS.
8 ADRs explain the design decisions.
I'm looking for an AI Application Engineer role where I can
build production systems, not just prototypes.
Reach out on LinkedIn — link in the description.
```

---

## Pre-recording checklist

- [ ] `pip install -e .` already done
- [ ] `export MINIMAX_API_KEY=sk-...` (or ANTHROPIC_API_KEY)
- [ ] Terminal font size ≥ 16pt (readable on screen recording)
- [ ] Editor theme: dark (matches the web UI aesthetic)
- [ ] Open these tabs before recording:
  - [ ] GitHub repo (https://github.com/blank5this/MACS)
  - [ ] `docs/architecture/ADR_INDEX.md` (rendered in browser or VSCode)
  - [ ] `macs_pkg/erp/nl2sql.py` (line 180-260)
  - [ ] `macs_pkg/rag/rag_engine.py` (line 387-394)
  - [ ] `macs_pkg/llm/agents.py` (line 356-365)
- [ ] Terminal pwd = `E:\MACS`
- [ ] Mute notifications (Slack, Discord, email)

---

## Recording commands

```bash
# Set up
export MINIMAX_API_KEY=sk-cp-...
cd E:\MACS

# === Scene 1: Cold open (20s) ===
# Show title card or just speak over a black screen with repo link

# === Scene 2: ADRs (50s) ===
# Open ADR_INDEX.md in browser
sleep 50

# === Scene 3: SQL safety code (50s) ===
code macs_pkg/erp/nl2sql.py
# Navigate to line 180-260
sleep 50

# === Scene 4: Hybrid RAG code (40s) ===
code macs_pkg/rag/rag_engine.py
# Navigate to line 387-394
sleep 40

# === Scene 5: Test run (40s) ===
python -m pytest tests/test_nl2sql_safety.py -v
sleep 40

# === Scene 6: Live demo (40s) ===
python examples/demo_for_client.py
# Pick the best Q&A — 退货处理 is good
sleep 40

# === Scene 7: Closing (20s) ===
# Show repo URL + LinkedIn URL
sleep 20

# Stop recording
```

---

## Auto-recorder (`scripts/record_hiring_demo.py`)

```python
#!/usr/bin/env python3
"""Auto-record the 4-minute hiring demo video.

Pre-requisites:
    - pip install playwright
    - playwright install chromium
    - ffmpeg installed
    - MINIMAX_API_KEY or ANTHROPIC_API_KEY set
"""
from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path

VIDEO_DIR = Path("docs/videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


async def drive() -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_path=str(VIDEO_DIR / "hiring_demo_raw.mp4"),
        )
        page = await context.new_page()

        # Scene 1: cold open
        await page.goto("https://github.com/blank5this/MACS")
        time.sleep(20)

        # Scene 2: ADRs
        await page.goto(
            "https://github.com/blank5this/MACS/blob/main/docs/architecture/ADR_INDEX.md"
        )
        time.sleep(50)

        # Scene 5: test output (show pass/fail colors)
        await page.goto("http://localhost:8001")  # Or static HTML of test output
        time.sleep(40)

        # Scene 6: live demo
        # Better: record terminal separately, then composite
        time.sleep(40)

        # Scene 7: closing
        await page.goto("https://github.com/blank5this/MACS")
        time.sleep(20)

        await context.close()
        await browser.close()


def main() -> None:
    asyncio.run(drive())
    print(f"Raw MP4: {VIDEO_DIR / 'hiring_demo_raw.mp4'}")
    print("Run ffmpeg to compress + add intro/outro cards")


if __name__ == "__main__":
    main()
```

---

## Post-production

| Step | Tool | Time |
|------|------|------|
| Trim raw MP4 to 4:20 | ffmpeg / iMovie / DaVinci | 20 min |
| Add title card (Scene 1) | ffmpeg drawtext or Canva | 10 min |
| Add captions (optional but recommended) | ffmpeg + .srt file from script | 30 min |
| Add subtle background music (optional) | royalty-free from YouTube Audio Library | 10 min |
| Compress to < 50 MB for LinkedIn upload | ffmpeg `-crf 28` | 5 min |
| Generate 30s GIF preview | ffmpeg fps=15 scale=720 | 5 min |

**Total post-production**: ~80 min for a polished version.

---

## Upload checklist

| Platform | Format | Purpose |
|----------|--------|---------|
| GitHub | 30s GIF in `docs/videos/` | Repo README preview |
| YouTube | Full 4:20 MP4, unlisted | LinkedIn share |
| LinkedIn | Native upload (or Loom embed) | Profile featured section |
| Resume | Loom link or YouTube link | "See it in action" |

---

## Time budget

| Day | Task | Hours |
|-----|------|-------|
| 1 | Pre-recording setup (install tools, open tabs) | 1 |
| 2 | First dry run + identify weak spots | 2 |
| 3 | Re-record with fixes | 1.5 |
| 4 | Post-production (trim, captions, music) | 1.5 |
| 5 | Upload + embed everywhere | 0.5 |

**Total**: ~6.5 hours spread across 5 days.

This is the highest-ROI activity for the hiring push. One good video replaces 5 phone screens.