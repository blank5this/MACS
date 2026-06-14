# 3-Minute Demo Video — Final Script + Auto-Recorder

> **Target**: 180 seconds total. One-click recording via Playwright + ffmpeg.
> **Output**: `docs/videos/demo_3min.mp4` (1920×1080) + `docs/videos/demo_3min.gif` (preview).
> **Fallback**: `scripts/record_demo_ascii.sh` for zero-install terminal recording via asciinema.

---

## Why this matters for hiring

A 3-minute video that *actually shows the product working* beats any README. The video answers the interviewer's two questions in the first 60 seconds:

1. **Does it work?** → Yes, here it answering 3 real questions
2. **Is it real code or a wrapper?** → Yes, GitHub link at the end

---

## The 6 scenes

| # | Time | What's on screen | Why it's there |
|---|------|------------------|----------------|
| 1 | 0:00–0:05 | Title card: "ERP AI Copilot — built on MACS" | Hook + brand |
| 2 | 0:05–0:25 | Browser tab "📚 政策问答" — type "哪些商品库存低于安全库存？" → answer appears with [1] [2] citations | **RAG in action** — the strongest "this is real" signal |
| 3 | 0:25–0:55 | Type "如何处理采购退货？" → 3 KB chunks → cited answer | **Policy Q&A** — proves it knows Chinese policies |
| 4 | 0:55–1:25 | Tab "📊 Text2SQL" — type "上个月销售额最高的 3 个商品是什么？" → SQL appears → 3 rows | **NL→SQL** — proves it can hit a real DB |
| 5 | 1:25–1:50 | Type "DROP TABLE products" → BLOCKED error in red | **Safety guardrail** — the differentiator |
| 6 | 1:50–3:00 | `github.com/blank5this/MACS` — repo landing page | CTA — viewer can click through |

Total: **180s**. Tune `--smoke` to compress each scene to ~2s for a 15s smoke run.

---

## Recording — the one command

### Prerequisites (one-time)

```bash
# Python deps
pip install playwright
playwright install chromium

# System dep for MP4 + GIF post-processing
# macOS:    brew install ffmpeg
# Linux:    sudo apt install ffmpeg
# Windows:  choco install ffmpeg
```

### Run

```bash
# 1. Start the web UI (separate terminal)
make erp-run   # → http://localhost:8001

# 2. Record (this terminal)
python scripts/record_demo_3min.py
# Output:
#   docs/videos/demo_3min_raw.webm   (Playwright raw)
#   docs/videos/demo_3min.mp4         (libx264, ~30MB)
#   docs/videos/demo_3min.gif         (10fps, downsampled, ~5MB)
```

### Smoke run (15s, no waiting)

```bash
python scripts/record_demo_3min.py --smoke
```

---

## Zero-install fallback — terminal recording

If Playwright/ffmpeg aren't available, use the asciinema fallback:

```bash
brew install asciinema        # or: pip install asciinema
npm install -g svg-term       # optional, for GIF export

bash scripts/record_demo_ascii.sh
# Ctrl-D to stop
# Output: docs/videos/demo_3min.cast   (.gif if svg-term installed)
```

**What this shows**:
- Pure terminal output, no browser
- Real RAG answers via `examples/demo_for_client.py`
- Real Text2SQL via `macs_pkg.erp.demo.run()`
- Looks less polished than the Playwright version, but ships in 5 min

---

## Voice-over script (~280 words, optional)

```
[0:00 - 0:05] Cold open
This is ERP AI Copilot — a working AI assistant for enterprise data,
built on the MACS Multi-Agent framework. Open source, MIT licensed,
256 tests passing.

[0:05 - 0:25] Low-stock question
Here's a real question an ops manager would ask:
"Which products are below safety stock?"
Watch the agent pick the right tool automatically.

[0:25 - 0:55] Purchase return question
Different question — "How do I handle a purchase return?" —
and the agent picks a different tool: ask_knowledge_base.
It retrieves the top 3 chunks from an 18-document Chinese
policy corpus using char-ngram + BM25 + RRF hybrid retrieval.
Each answer must cite the source chunk.

[0:55 - 1:25] NL→SQL
Now the hard one — "Top 3 selling products last month?"
The agent generates a safe SQL query, runs it against the
seeded SQLite database, and returns ranked results.

[1:25 - 1:50] Safety guardrail
What if a user tries something destructive?
"Drop table products" — blocked. Even at the chat layer,
the SQL guardrail rejects anything except SELECT and WITH.
This is the 4-layer safety design — see ADR-003.

[1:50 - 3:00] Closing
This is just one product in the MACS framework. The same
agent runtime powers multi-agent workflows, custom tools,
and any LLM provider — Claude, GPT-4o, MiniMax, Qwen,
DeepSeek. Full source on GitHub at github.com/blank5this/MACS.
For consulting or contract work, find me on Upwork — link
in the description.
```

---

## Upload checklist

After recording, upload to:

| Platform | Format | Purpose |
|----------|--------|---------|
| GitHub | `demo_3min.gif` (in `docs/videos/`) | README preview |
| YouTube | `demo_3min.mp4` (1920×1080, unlisted) | LinkedIn share |
| LinkedIn | Native upload of `demo_3min.mp4` (1.0-1.25× speed) | Profile featured |
| Upwork | Link to YouTube | Project portfolio |

**YouTube title**: `ERP AI Copilot Demo — RAG + Text2SQL + Multi-Agent in 3 Minutes`
**YouTube description**: see `docs/videos/HIRING_DEMO_SCRIPT.md` for the full template.

---

## Why a video AND a live demo?

| Format | Interviewer effort | Conversion |
|--------|-------------------|------------|
| GitHub repo only | Clone, install, run, debug | Low |
| **Live URL** (HF Spaces, see `README_HF.md`) | Click, type, see result | **Highest** |
| 3-min video | Watch passively | Medium-High |
| Live URL + 3-min video | Click the URL **after** watching the video | **Highest combined** |

The video primes the interviewer; the live URL closes the deal.

---

## Timeline to ship this

| Day | Task | Time |
|-----|------|------|
| Day 1 | Run `record_demo_3min.py` once (test the pipeline) | 30 min |
| Day 2 | Polish: re-record with voice-over, splice transitions | 1.5 hours |
| Day 3 | Upload to YouTube, embed in README, share on LinkedIn | 30 min |

**Total**: ~2.5 hours of focused work for a polished demo.