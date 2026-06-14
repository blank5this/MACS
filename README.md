# MACS — Multi-Agent Collaboration Stack

> **Production-grade Python framework for building multi-agent AI systems.**
> Ships with a working ERP AI Copilot application built on top.
> 256 tests passing · 8 Architecture Decision Records · MIT licensed.

[![Tests](https://img.shields.io/badge/tests-256%20passing-brightgreen.svg)](#-test-results)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## ⚡ Try it in 30 seconds — no install

| What | Where |
|------|-------|
| **Live demo (no setup)** | Deploy one-click to HF Spaces — see [README_HF.md](README_HF.md) |
| **Local 2-tab demo** | `pip install -r requirements_hf.txt && python app.py` → http://localhost:7860 |
| **Scenario 1 — MCP inventory** | `python examples/scenario_01_low_stock.py` |
| **Scenario 2 — RAG with citations** | `python examples/scenario_02_purchase_return.py` |
| **3-min video** | See [docs/videos/DEMO_3MIN_FINAL.md](docs/videos/DEMO_3MIN_FINAL.md) |

---

## What's here

This is not a tutorial repo. It's a **shipping, tested, documented** AI system:

- A reusable multi-agent framework (LLM abstraction, 4 collaboration modes, tool registry, async runtime)
- An enterprise application (ERP AI Copilot) that demonstrates it end-to-end
- 8 Architecture Decision Records explaining the *why* behind the design choices
- 256 automated tests, including 50+ adversarial SQL-injection tests
- CI pipeline with 8 jobs, Docker Compose deployment, FastAPI web UI

**If you're interviewing me**: I can walk through any ADR. The reasoning matters more than the conclusion.

---

## 📊 Numbers

| Metric | Value |
|--------|-------|
| Tests passing | **256** |
| Test runtime | ~75 seconds |
| LLM providers | 6 (Claude · GPT-4o · MiniMax-M2.7 · Qwen · DeepSeek · Zhipu) |
| Built-in tools | 9 |
| MCP tools (ERP) | 5 |
| Collaboration modes | 4 (hierarchical · pipeline · decentralized · dynamic) |
| ADRs | 8 |
| KB documents (sample) | 18 Chinese policy .md files |
| Web endpoints | 4 (FastAPI) |
| CI jobs | 8 |
| Lines of code | ~12,000 |
| License | MIT |

---

## 🏗️ Architecture decisions (the interesting part)

Eight ADRs document non-obvious design choices. **Read these to understand how I think:**

| # | Decision | Why it matters |
|---|----------|----------------|
| [001](docs/architecture/ADR-001-async-python.md) | Async Python throughout | I/O-bound workloads need cooperative scheduling, not threads |
| [002](docs/architecture/ADR-002-llm-provider-abstraction.md) | Pluggable LLM provider abstraction | Swap Claude for GPT-4o in 1 line; test with mocks |
| [003](docs/architecture/ADR-003-sql-safety-guardrail.md) | **4-layer SQL safety guardrail** | AST whitelist + keyword blacklist + statement-type check + parameterized values |
| [004](docs/architecture/ADR-004-hybrid-retrieval.md) | **Hybrid retrieval (char-ngram + BM25 + RRF)** | Pure semantic misses Chinese phrases; pure keyword misses synonyms |
| [005](docs/architecture/ADR-005-self-correction-backoff.md) | Exponential backoff + jitter | ±25% jitter prevents thundering herd on rate limit recovery |
| [006](docs/architecture/ADR-006-conversation-cap.md) | Conversation history cap = 100 messages | Trivial fix for memory leak in long-running sessions |
| [007](docs/architecture/ADR-007-readonly-default.md) | Read-only DB user by default | Defense in depth — even if safety layer fails, DB rejects writes |
| [008](docs/architecture/ADR-008-proactive-rag.md) | Proactive over Reactive RAG | Reliable across all 6 LLM providers; 1 roundtrip vs 2 |

See [ADR_INDEX.md](docs/architecture/ADR_INDEX.md) for the full list.

---

## 🚀 Quickstart

```bash
git clone https://github.com/blank5this/MACS.git
cd MACS
pip install -e .

# Option 1: No DB needed — pure RAG demo
export MINIMAX_API_KEY=sk-...   # or ANTHROPIC_API_KEY
python examples/demo_for_client.py

# Option 2: Full ERP Copilot (PostgreSQL via Docker)
docker-compose --profile erp up -d
make erp-run
# → http://localhost:8001

# Option 3: Run all tests
python -m pytest tests/ -q
# → 256 passed in 75s
```

---

## 🧠 What the ERP AI Copilot actually does

End-to-end, with real examples:

```
You: "Which products are below safety stock?"
  → Agent picks `get_low_stock_products` (MCP tool)
  → Returns 7 products ranked by deficit, with reorder recommendations

You: "How do I handle a purchase return?"
  → Agent picks `ask_knowledge_base` (RAG over 18 Chinese policy docs)
  → Hybrid retrieval (char-ngram + BM25 + RRF), < 50ms
  → Returns 3 cited chunks with policy section references

You: "Top 3 selling products last month?"
  → Agent picks `query_database` (NL→SQL)
  → 4-layer safety guardrail validates the generated SQL
  → Executes on read-only PostgreSQL role
  → Returns ranked results
```

For complex questions like "Analyze inventory risk for next 30 days":

```
Planner (decompose) → Inventory Analyst (velocity + stock)
                   → Purchase Specialist (reorder qty + lead times)
                   → Report Writer (synthesize Markdown report)
```

---

## 🧪 Test coverage highlights

```bash
# Run the safety tests specifically
python -m pytest tests/test_nl2sql_safety.py -v

# Adversarial cases covered:
test_drop_blocked             → "DROP TABLE products"
test_injection_blocked        → "'; DROP TABLE users; --"
test_pg_catalog_blocked       → "SELECT * FROM pg_shadow"
test_pg_read_file_blocked     → "SELECT pg_read_file(...)"
test_union_select_blocked     → "UNION SELECT password FROM users"
# ... 45+ more
```

```bash
# Run the hybrid RAG tests
python -m pytest tests/test_rag_engine.py -v
# Catches both phrase match (BM25) and synonym match (semantic)
```

---

## 📦 Project structure

```
macs_pkg/
├── llm/                 # LLM provider abstraction (6 providers)
├── agents/              # Base / Planner / Executor / Reviewer / Tool agents
├── collaboration/       # 4 collaboration modes
├── rag/                 # Hybrid retrieval (char-ngram + BM25 + RRF)
├── tools/               # 9 built-in tools (calculator, RAG, web search, etc.)
├── erp/                 # Application layer: ERP AI Copilot
│   ├── db/              # PostgreSQL pool, schema, seed
│   ├── tools/           # 5 MCP tools (inventory / sales / procurement)
│   ├── nl2sql.py        # 4-layer safety guardrail
│   ├── rag/             # Knowledge base query
│   ├── agents/          # ERPCopilotAgent with 7 tools
│   ├── workflows/       # Multi-agent inventory risk
│   └── web/             # FastAPI web UI
└── tests/               # 256 tests
```

```
docs/architecture/
├── ADR_INDEX.md
├── ADR-001-async-python.md
├── ADR-002-llm-provider-abstraction.md
├── ADR-003-sql-safety-guardrail.md  # Most interesting for interviews
├── ADR-004-hybrid-retrieval.md       # Most interesting for interviews
├── ADR-005-self-correction-backoff.md
├── ADR-006-conversation-cap.md
├── ADR-007-readonly-default.md
└── ADR-008-proactive-rag.md
```

---

## 🛠️ Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.10+ | Async/await native; rich AI ecosystem |
| Concurrency | asyncio | I/O-bound by nature; see ADR-001 |
| LLM providers | 6 supported | Vendor-agnostic; see ADR-002 |
| Database | PostgreSQL 16 | Async driver (psycopg[async]); production-grade |
| Web | FastAPI | Async-native; auto OpenAPI docs |
| Testing | pytest | 256 tests; 75s runtime |
| Linting | ruff | Fast, opinionated |
| Deployment | Docker Compose | One command to start everything |

---

## 🎬 Demo videos

| Version | Audience | Length | Link |
|---------|----------|--------|------|
| Hiring (technical deep-dive) | Interviewers | 4 min | [script](docs/videos/HIRING_DEMO_SCRIPT.md) |
| Sales (product walkthrough) | Potential clients | 3 min | [script](docs/videos/DEMO_3MIN_SCRIPT.md) |
| **Final 3-min auto-recorder** | Anyone | 3 min | [docs/videos/DEMO_3MIN_FINAL.md](docs/videos/DEMO_3MIN_FINAL.md) + [scripts/record_demo_3min.py](scripts/record_demo_3min.py) |
| Terminal fallback (asciinema) | No-install | 3 min | [scripts/record_demo_ascii.sh](scripts/record_demo_ascii.sh) |
| RAG interactive animation | Anyone | 60s, offline | [docs/demos/03_rag_animation.html](docs/demos/03_rag_animation.html) |

---

## 🎯 Real AI Copilot scenarios

The two scenarios below are the most common questions an ops manager or
procurement lead asks. Both run without an API key (deterministic
fallback) and get richer with an LLM key set.

| Scenario | What it demonstrates | Run |
|----------|----------------------|-----|
| **1. Low-stock detection** | Agent picks `get_low_stock_products` MCP tool, queries seeded SQLite, returns ranked products + reorder recommendations | `python examples/scenario_01_low_stock.py` |
| **2. Purchase return Q&A** | Agent picks `ask_knowledge_base` RAG tool, hybrid retrieval over 18 Chinese policy docs, **citation-enforced** answer | `python examples/scenario_02_purchase_return.py` |

Both scenarios print 5-step walkthroughs designed for hiring demos — show
the interviewer the agent's reasoning at each step, not just the answer.

---

## 🤝 How to engage

- 🐛 Found a bug? Open an issue.
- 💡 Have an idea? Open a discussion.
- 📧 Want to talk AI Application Engineering? DM me on LinkedIn.
- 💼 Hiring me? Check [career/RESUME_PROJECT_HIRING.md](career/RESUME_PROJECT_HIRING.md) for the resume version.

---

## 📄 License

MIT — see [LICENSE](LICENSE).