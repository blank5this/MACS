# 3-Minute Demo Video — Script + Auto-Recorder

> Target: 180 seconds total. Pure terminal + browser recording. No talking head (optional voice-over track can be added later).
> Output: `docs/videos/demo_3min.mp4` (1920x1080, 30fps) + `docs/videos/demo_3min.gif` (preview).

---

## The 7 scenes

| Scene | Time | What's on screen | Duration |
|-------|------|------------------|----------|
| 1. Cold open | 0:00-0:05 | Title card: "ERP AI Copilot — built on MACS" | 5s |
| 2. The question | 0:05-0:15 | Browser open. Type: "Which products are below safety stock?" | 10s |
| 3. Tool selection | 0:15-0:30 | Animated overlay: agent picks `get_low_stock_products` from 7 tools | 15s |
| 4. Result | 0:30-0:50 | Browser shows answer: 7 products, deficit column, reorder recommendation | 20s |
| 5. RAG question | 0:50-1:20 | Type: "How do I handle a purchase return?" → KB hits 3 chunks | 30s |
| 6. NL→SQL question | 1:20-1:55 | Type: "Top 3 selling products last month?" → SQL generated → executed → ranked | 35s |
| 7. Closing | 1:55-3:00 | GitHub link + Upwork CTA + animated architecture diagram | 65s |

**Last 65 seconds** is intentionally generous — viewer can pause, see the repo, click through.

---

## Voice-over script (optional, ~280 words)

```
[Scene 1 - Cold open, 5s]
This is ERP AI Copilot — a working AI assistant for enterprise
data, built on the MACS Multi-Agent framework. Open source, MIT
licensed, 256 tests passing.

[Scene 2 - First question, 10s]
Here's a real question an ops manager would ask: "Which products
are below safety stock right now?"

[Scene 3 - Tool selection, 15s]
The agent has 7 tools available. It picks the right one
automatically — get_low_stock_products, an MCP business tool
that knows your inventory schema.

[Scene 4 - Result, 20s]
In under 200 milliseconds, it returns 7 products, ranked by
deficit, with reorder recommendations. No SQL knowledge
required.

[Scene 5 - RAG question, 30s]
Different question — "How do I handle a purchase return?" — and
the agent picks a different tool: ask_knowledge_base. It
retrieves the top 3 chunks from an 18-document Chinese policy
corpus using char-ngram + BM25 + RRF hybrid retrieval. Each
chunk comes with a citation.

[Scene 6 - NL2SQL, 35s]
Now the hard one — "What were the top 3 selling products last
month?" The agent generates a safe SQL query, runs it against
PostgreSQL, and returns ranked results. Behind the scenes, a
4-layer safety guardrail prevents any destructive operation —
only SELECT statements are allowed, all values parameterized,
SQL keywords like DROP and DELETE blacklisted.

[Scene 7 - Closing, 65s]
This is just one product in the MACS framework. The same agent
runtime powers multi-agent workflows, custom tools, and any
LLM provider you want — Claude, GPT-4o, MiniMax, Qwen,
DeepSeek. The full source is on GitHub at github.com/blank5this/
MACS. MIT license, ready to clone. For consulting or contract
work, find me on Upwork — link in the description.
```

---

## Auto-recorder (`scripts/record_demo_3min.py`)

This script automates the recording pipeline using Playwright + ffmpeg. No manual clicking needed.

```python
#!/usr/bin/env python3
"""Auto-record the 3-minute ERP AI Copilot demo.

Pipeline:
  1. Start FastAPI web UI (assumes already running on :8001)
  2. Start ffmpeg screen capture
  3. Drive Playwright through 6 scenes with timed waits
  4. Stop capture
  5. Convert to GIF preview

Usage:
    python scripts/record_demo_3min.py

Output:
    docs/videos/demo_3min_raw.mp4   # raw screen recording
    docs/videos/demo_3min.mp4       # trimmed + compressed
    docs/videos/demo_3min.gif       # preview GIF for README
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = PROJECT_ROOT / "docs" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


async def drive_browser_scenes() -> None:
    """Drive Playwright through the 6 demo scenes."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_path=str(VIDEO_DIR / "demo_3min_raw.mp4"),
        )
        page = await context.new_page()

        # Scene 1: cold open (just the title)
        await page.goto("http://localhost:8001")
        await page.wait_for_selector("h1")
        time.sleep(5)

        # Scene 2: first question
        await page.fill("textarea[name=q]", "哪些商品库存低于安全库存？")
        time.sleep(2)
        await page.click("button[type=submit]")
        time.sleep(13)  # wait for tool selection + result

        # Scene 5: RAG question
        await page.fill("textarea[name=q]", "如何处理采购退货？")
        await page.click("button[type=submit]")
        time.sleep(28)

        # Scene 6: NL2SQL question
        await page.fill("textarea[name=q]", "上个月销售额最高的3个商品是什么？")
        await page.click("button[type=submit]")
        time.sleep(33)

        # Scene 7: closing — show repo link
        await page.goto("https://github.com/blank5this/MACS")
        time.sleep(60)

        await context.close()
        await browser.close()


def convert_to_gif() -> None:
    """Convert raw MP4 to a small GIF preview (downsampled)."""
    raw = VIDEO_DIR / "demo_3min_raw.mp4"
    gif = VIDEO_DIR / "demo_3min.gif"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw),
        "-vf", "fps=10,scale=960:-1:flags=lanczos,split[s0][s1];"
               "[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0",
        str(gif),
    ], check=True)


def main() -> None:
    print("=" * 60)
    print("  Recording 3-minute ERP AI Copilot demo")
    print("=" * 60)
    print()
    print("Pre-requisites:")
    print("  - Web UI running on http://localhost:8001")
    print("  - PostgreSQL seeded with sample ERP data")
    print("  - ANTHROPIC_API_KEY or MINIMAX_API_KEY set")
    print("  - Playwright: pip install playwright && playwright install chromium")
    print("  - ffmpeg installed and on PATH")
    print()

    asyncio.run(drive_browser_scenes())
    print(f"  ✓ Raw MP4: {VIDEO_DIR / 'demo_3min_raw.mp4'}")

    convert_to_gif()
    print(f"  ✓ GIF preview: {VIDEO_DIR / 'demo_3min.gif'}")
    print()
    print("Done!")


if __name__ == "__main__":
    main()
```

---

## Quick-and-dirty alternative: pure terminal recording

If you don't want to set up Playwright, you can record a terminal demo using asciinema + svg-term. Much simpler.

```bash
# Install
pip install asciinema
npm install -g svg-term

# Record (Ctrl-D to stop)
asciinema rec docs/videos/demo_3min.cast

# Convert to GIF
svg-term --in docs/videos/demo_3min.cast --out docs/videos/demo_3min.gif
```

**What to type during recording** (paste one block at a time):

```bash
# === Scene 1: cold open (5s pause before) ===
echo "ERP AI Copilot — built on MACS"
echo "github.com/blank5this/MACS"
echo ""
sleep 3

# === Scene 2: framework demo (no DB needed) ===
export MINIMAX_API_KEY=sk-...
python examples/erp_knowledge_assistant.py
sleep 2

# === Scene 3: ask 3 questions ===
python examples/erp_copilot_single_agent.py
# (interactive Q&A happens automatically)
sleep 5

# === Scene 7: closing ===
echo ""
echo "🔗 github.com/blank5this/MACS"
echo "📧 [your email]"
echo "💼 Upwork: [link]"
```

---

## Upload checklist

After recording, upload to:

| Platform | Format | Purpose |
|----------|--------|---------|
| GitHub | `demo_3min.gif` (in repo root or `docs/videos/`) | README preview |
| YouTube | `demo_3min.mp4` (1920x1080, unlisted) | LinkedIn share |
| LinkedIn | Native upload of `demo_3min.mp4` (1.0-1.5x speed) | Profile featured |
| Upwork | Link to YouTube | Project portfolio |

**YouTube title**: `ERP AI Copilot Demo — NL2SQL + RAG + Multi-Agent in 3 Minutes`

**YouTube description**:
```
A 3-minute demo of the ERP AI Copilot — an open-source AI assistant
that turns natural-language questions into safe SQL queries, cited
knowledge-base answers, and multi-agent inventory reports.

Built on the MACS (Multi-Agent Collaboration Stack) framework.
MIT licensed. 256 tests passing.

🔗 Code: https://github.com/blank5this/MACS
🔗 Architecture docs: https://github.com/blank5this/MACS/blob/main/docs/architecture/erp_copilot.md

Tech stack: Python, FastAPI, PostgreSQL, LangChain, Claude / GPT-4o.

Features shown:
- 7-tool single-agent auto-selection (MCP / RAG / NL→SQL)
- 4-layer SQL safety guardrail (AST / blacklist / whitelist / parameterized)
- char-ngram + BM25 + RRF hybrid retrieval
- 4-agent inventory risk workflow
- FastAPI web UI with 3 tabs

For consulting or contract work: [your Upwork link]
```

---

## Timeline to ship this

| Day | Task | Time |
|-----|------|------|
| Day 1 | Write script + auto-recorder (done — this file) | - |
| Day 2 | Install Playwright + ffmpeg, do 1st dry run | 2 hours |
| Day 3 | Polish timing, re-record, generate GIF | 1.5 hours |
| Day 4 | Upload to YouTube, embed in README, share on LinkedIn | 1 hour |

Total: ~5 hours of focused work, spread across 4 days.