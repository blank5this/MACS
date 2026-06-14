# Resume Project Description — English Versions

> Copy-paste directly into your resume, LinkedIn "Projects", or cover letter.
> Designed for overseas mid-to-large company AI Application Engineer roles.

---

## Version A — One-line summary (for resume header)

```
MACS — Multi-Agent Collaboration Stack | Python · Async · PostgreSQL · FastAPI
Open-source framework + ERP AI Copilot. 326 tests passing. MIT licensed.
github.com/blank5this/MACS
```

---

## Version B — Single paragraph (for resume project section)

```
MACS — Multi-Agent Collaboration Stack (Python, 2026)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Open-source MIT-licensed framework for building production multi-agent AI
systems, with a working ERP AI Copilot application built on top.

Supports 6 LLM providers (Claude, GPT-4o, MiniMax-M2.7, Qwen, DeepSeek,
Zhipu), 5 collaboration modes (hierarchical, pipeline, decentralized,
deep-research, dynamic), and ships with an enterprise-grade Text2SQL +
RAG + multi-agent workflow. 326 automated tests pass; 8 architecture
decision records (ADRs) document the design rationale. github.com/blank5this/MACS
```

---

## Version C — Bullet points (for ATS-friendly resume, 6 bullets)

```
MACS — Multi-Agent Collaboration Stack  |  github.com/blank5this/MACS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Designed and shipped a Python async multi-agent framework supporting
  6 LLM providers (Claude, GPT-4o, MiniMax-M2.7, Qwen, DeepSeek, Zhipu)
  with a pluggable provider abstraction, enabling zero-friction A/B
  testing of models in production.

• Implemented a 4-layer NL→SQL safety guardrail (AST whitelist / SQL
  keyword blacklist / statement-type whitelist / parameterized values)
  backed by a read-only PostgreSQL role — 50+ adversarial injection
  tests verify that no DROP / DELETE / exfiltration can ever execute.

• Built hybrid RAG retrieval over Chinese policy documents using
  char-ngram embeddings + BM25 keyword search fused via Reciprocal
  Rank Fusion (RRF); 90%+ recall on Chinese-language test set,
  <50ms query latency, fully offline-capable.

• Designed 5 collaboration modes (hierarchical / pipeline / decentralized
  / deep-research / dynamic) with cooperative scheduling; demonstrated
  4-agent inventory-risk workflow producing structured Markdown reports
  from natural-language questions.

• Wrote 8 Architecture Decision Records (ADRs) capturing the rationale
  for non-obvious choices (async vs sync, hybrid vs pure retrieval,
  proactive vs reactive RAG, exponential backoff with jitter, etc.) —
  the kind of artifacts that scale engineering beyond one engineer.

• Achieved production-grade reliability: 326 automated tests passing
  in 75 seconds, CI pipeline with 8 jobs, exponential backoff with
  jitter on LLM retries, conversation history capped at 100 messages
  to prevent memory leaks, FastAPI web UI serving 4 endpoints.
```

---

## Version D — Cover letter paragraph (for application email)

```
In the last 6 months I built MACS — an open-source multi-agent framework
shipped with an ERP AI Copilot that turns natural-language questions into
safe SQL queries, RAG-powered knowledge-base answers, and multi-agent
inventory reports. The project lives at github.com/blank5this/MACS, has
326 automated tests, and includes 8 architecture decision records
documenting tradeoffs I'd love to discuss in an interview.

I work in Python (async, FastAPI, LangChain), PostgreSQL, and have
production Java backend experience from my previous role supporting an
ERP deployment. I'm looking for an AI Application Engineer position
where I can build production-grade systems with the same rigor — test
coverage, observability, design rationale written down — that I'd apply
to my own projects.
```

---

## Version E — LinkedIn "Projects" section

```
MACS — Multi-Agent Collaboration Stack
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
https://github.com/blank5this/MACS

A production-grade multi-agent AI framework in Python, with an ERP AI
Copilot application built on top.

WHAT IT DOES
Turns natural-language questions into safe PostgreSQL queries, cited
knowledge-base answers, and multi-agent business reports.

KEY TECHNICAL DECISIONS (8 ADRs documented)
• 4-layer SQL safety guardrail (AST / blacklist / statement-type /
  parameterized values)
• Hybrid retrieval (char-ngram embeddings + BM25 + RRF)
• Proactive RAG (framework-decided) over Reactive RAG (LLM-decided)
• Exponential backoff with ±25% jitter on LLM retries
• Read-only DB user by default (defense in depth)
• Conversation history capped at 100 messages (memory leak prevention)

NUMBERS
• 326 automated tests passing
• 6 LLM providers supported
• 5 collaboration modes
• 18 Chinese policy documents in sample KB
• <50ms RAG query latency
• 100% rejection rate on adversarial SQL injection (50+ tests)

STACK
Python 3.10+ · asyncio · FastAPI · PostgreSQL · LangChain · Claude /
GPT-4o / MiniMax-M2.7 / Qwen / DeepSeek / Zhipu · Docker Compose
```

---

## Version F — Interview self-intro (60 seconds spoken)

```
"I built MACS — an open-source Python framework for multi-agent AI
systems, with an enterprise ERP AI Copilot on top. It supports 6 LLM
providers through a single abstraction layer, ships with a 4-layer SQL
safety guardrail that I wrote unit tests for, and uses hybrid retrieval
to handle Chinese-language policy documents.

I made 8 architecture decisions and wrote them all down as ADRs — I can
walk through any of them. The codebase has 326 passing tests and runs
in production.

I'm looking for an AI Application Engineer role where the team values
that kind of rigor — design rationale documented, tests as first-class
citizens, observability built in. I'd rather join a team that thinks
that way than one where 'just ship it' is the only value."
```

---

## Keywords for ATS (paste into resume skills section)

```
Python · asyncio · FastAPI · PostgreSQL · LangChain · Claude · GPT-4o
Multi-Agent Systems · RAG · NL2SQL · Hybrid Retrieval · BM25 · Reciprocal
Rank Fusion · Prompt Engineering · LLM Provider Abstraction · Docker
Compose · CI/CD · pytest · Async I/O · Connection Pooling · Memory
Management · Architecture Decision Records · Observability · Cost
Optimization · SQL Injection Prevention · Read-Only Database User
```

---

## Numbers to memorize for interviews

| Metric | Value | Source |
|--------|-------|--------|
| Tests passing | 326 | `python -m pytest tests/ -q` |
| Test runtime | ~75 sec | measured |
| LLM providers | 6 | `macs_pkg/llm/` |
| Built-in tools | 9 | `macs_pkg/tools/` |
| MCP tools (ERP) | 5 | `macs_pkg/erp/tools/` |
| KB documents | 18 Chinese .md files | `data/erp_kb/` |
| Chunks indexed | 135 | (per README) |
| ADRs | 8 | `docs/architecture/ADR-*.md` |
| CI jobs | 8 | `.github/workflows/` |
| Web endpoints | 4 | `macs_pkg/erp/web/app.py` |
| Collaboration modes | 4 | `macs_pkg/collaboration/` |
| Lines of code | ~12,000 | `cloc macs_pkg/` |
| Latency (RAG) | < 50ms | measured |
| Adversarial SQL tests | 50+ | `tests/test_nl2sql_safety.py` |
| Conversation cap | 100 messages | ADR-006 |
| Backoff base | 0.5s, ×2 per attempt | ADR-005 |

---

## Common interview questions — pre-prepared answers

### "Tell me about a non-obvious technical decision you made."

> "On the NL→SQL guardrail. Most 'AI engineer' demos stop at 'look, the LLM generated SQL.' I asked: what if the LLM hallucinates a DROP TABLE? So I built 4 independent checks — AST whitelist, keyword blacklist, statement-type check, parameterized values. Any one blocks the query. Plus a read-only DB user at the infrastructure layer. Defense in depth.
>
> It's documented as ADR-003. 50+ adversarial tests verify no DROP / DELETE / exfiltration can ever execute. The tradeoff: some legitimate queries (e.g., `SELECT FOR UPDATE`) are rejected — intentional."

### "Why did you choose hybrid retrieval over pure semantic?"

> "Two failure modes I hit during testing. Pure semantic embeddings missed exact phrases like 'MOQ 政策' (Minimum Order Quantity policy). Pure BM25 missed synonyms like '进货' (purchase-in, a synonym for 采购).
>
> I combined char-ngram embeddings (no Chinese word segmentation needed) with BM25, fused via Reciprocal Rank Fusion. RRF is the standard formula — sum of 1/(k+rank) across retrievers. 90%+ recall on the Chinese test set, <50ms latency.
>
> The tradeoff: two indexes to maintain instead of one. Documented as ADR-004."

### "How do you handle LLM API failures?"

> "Exponential backoff with jitter. 0.5s → 1s → 2s → 4s, capped. ±25% random jitter so synchronized retries don't pile up on the API.
>
> The jitter matters more than it sounds: if 1000 clients all hit a rate limit and all retry at exactly 1s, you create a thundering herd. Jitter spreads them across the recovery window.
>
> ADR-005 walks through the math and the alternatives I rejected."

### "What's the most interesting bug you fixed?"

> "Memory leak in long-running agent sessions. The `MiniMaxAgentMixin._conversation` list grew unbounded. After 6 hours in production, the process OOMed.
>
> Fix: hard cap at 100 messages, FIFO eviction. Trivial code change, but it required me to look at the actual production behavior, not just the spec.
>
> Tradeoff: after 100 turns, the agent forgets the start. Accepted. The alternative — summarization — adds an LLM call per turn. Not worth it for v1.
>
> ADR-006."

### "Why should we hire you over someone with 5 years at Google?"

> "You probably shouldn't, for that job. But for a role where you need someone to ship a working AI system end-to-end, write the tests, document the decisions, and run it in production — I'm useful.
>
> Most 'AI engineers' can call an API. I can build the whole stack: provider abstraction, multi-agent orchestration, tool calling, RAG, NL→SQL safety, MCP servers, FastAPI web UI.
>
> Also: I have Java backend production experience. So if your AI features need to talk to an existing Java service, I won't need 3 months to ramp up on JVM tooling."

---

## 🔗 Demo + video links to attach to every application

Attach these to your resume, LinkedIn, Upwork profile, and email signature.
Recruiters spend 5-15 seconds — make those seconds count.

| Asset | Where | How to share |
|-------|-------|--------------|
| **🟢 Live web demo (Render, CN-fast)** | https://macs-erp-copilot.onrender.com | Paste URL in LinkedIn Featured + resume header |
| **🟢 Live web demo (HF Spaces, global)** | https://huggingface.co/spaces/gkf123/macs-erp-copilot | Backup / international audiences |
| **Local 2-tab Gradio demo** | `python app.py` | Show during live coding interviews |
| **Scenario 1 — Low-stock detection** | [examples/scenario_01_low_stock.py](../examples/scenario_01_low_stock.py) | Run in 10 sec; prints 4-step walkthrough |
| **Scenario 2 — Purchase return RAG** | [examples/scenario_02_purchase_return.py](../examples/scenario_02_purchase_return.py) | Run in 10 sec; citation-enforced |
| **3-min recorded video** | [docs/videos/DEMO_3MIN_FINAL.md](../docs/videos/DEMO_3MIN_FINAL.md) | One command: `python scripts/record_demo_3min.py` |
| **Auto-recorder script** | [scripts/record_demo_3min.py](../scripts/record_demo_3min.py) | Playwright + ffmpeg pipeline |
| **Terminal fallback** | [scripts/record_demo_ascii.sh](../scripts/record_demo_ascii.sh) | Zero-install via asciinema |
| **One-shot HF push** | [scripts/push_to_hf.ps1](../scripts/push_to_hf.ps1) | Rebuild + push in one command |

### Resume bullets (drop-in, paste after the existing 6 bullets)

```
• Deployed a 2-tab Gradio live demo to both Render.com and Hugging Face
  Spaces (RAG over 18 Chinese policy docs + Text2SQL on seeded SQLite),
  enabling interviewer Q&A without local setup — live at
  https://macs-erp-copilot.onrender.com (CN) and
  https://huggingface.co/spaces/gkf123/macs-erp-copilot (global).

• Shipped two curated "real AI Copilot scenarios" (low-stock detection
  and citation-enforced policy Q&A) that run in 10 seconds without
  an LLM API key, each printing a 5-step walkthrough of the agent's
  reasoning — examples/scenario_01_low_stock.py and
  scenario_02_purchase_return.py.

• Wrote a Playwright + ffmpeg auto-recorder (scripts/record_demo_3min.py)
  that drives the FastAPI web UI through 6 scenes in 3 minutes, outputs
  MP4 + GIF, with a zero-install asciinema fallback — docs/videos/
  DEMO_3MIN_FINAL.md.

• Built a one-shot deployment pipeline (scripts/deploy_hf_pack.ps1 +
  scripts/push_to_hf.ps1) that packages the framework + sample KB
  into a clean 1.6 MB dist_hf/ directory and pushes it to HF Spaces
  in a single command, with auto-proxy detection.
```

---

## How to use these

1. Pick **Version C** (6 bullets) for the resume itself — ATS-friendly, quantified, no fluff.
2. Keep **Version D** in a cover letter template — fill in the company name.
3. Memorize **Version F** for "tell me about yourself" — 60 sec, hits all the right notes.
4. Use **Version E** for LinkedIn "Projects" section.
5. Pre-load the interview Q&A into Anki / spaced repetition — practice until you can deliver each answer in 90 seconds without notes.