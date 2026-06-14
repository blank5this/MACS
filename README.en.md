# MACS — Multi-Agent Collaboration Stack
### *Production-grade AI agent framework with a working ERP AI Copilot built on top.*

[![Tests](https://img.shields.io/badge/tests-256%20passing-brightgreen.svg)](#-test-results)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)

> An end-to-end AI agent framework in Python — and a **shipping enterprise AI product** (ERP AI Copilot) you can clone, run, and demo today.

---

## 🎯 What this repo actually ships

This is not a toy. Out of the box, you can run:

### 1. An ERP AI Copilot that answers real business questions

```
You: "Which products are below safety stock?"
AI:  → calls `get_low_stock_products` (MCP tool)
     → returns 7 products with deficit + reorder recommendation

You: "How do I handle a purchase return?"
AI:  → calls `ask_knowledge_base` (RAG)
     → returns 3 cited chunks from the policy KB

You: "What were the top 3 selling products last month?"
AI:  → calls `query_database` (NL→SQL)
     → generates safe SQL, executes on PostgreSQL
     → returns ranked results
```

**Live web UI**: `make erp-run` → http://localhost:8001 (3 tabs)

### 2. A reusable multi-agent framework

- **6 LLM providers** — Claude, GPT-4o, MiniMax-M2.7, Qwen, DeepSeek, Zhipu, Hunyuan
- **4 collaboration modes** — hierarchical, pipeline, decentralized, dynamic
- **9 built-in tools** — calculator, file I/O, HTTP, RAG, web search, code execution, JSON parsing
- **MCP tool server** — register your own tools in 5 lines
- **Agent templates** — batch-create agents with variable interpolation

---

## 📊 Numbers that matter

| Dimension | Count |
|-----------|-------|
| Tests passing | **256** |
| LLM providers | 6 |
| Built-in tools | 9 |
| MCP tools (ERP) | 5 |
| KB documents (ERP) | 18 |
| Collaboration modes | 4 |
| Agent templates | 5 |
| Web endpoints | 4 |
| Demo videos / animations | 3 |
| Python LOC (framework + ERP) | ~12,000 |

---

## 🚀 60-second Quickstart

```bash
git clone https://github.com/blank5this/MACS.git
cd MACS

# Install
pip install -e .

# Option A — Run the RAG knowledge base (no DB needed)
python examples/erp_knowledge_assistant.py

# Option B — Run the full ERP Copilot (needs PostgreSQL)
docker-compose up -d        # PostgreSQL 16 + auto-seed
make erp-run                # FastAPI Web UI on :8001
python examples/erp_copilot_single_agent.py
```

```bash
# Run tests (256 should pass in ~75 seconds)
python -m pytest tests/ -q
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     User Question (Chinese)                  │
└──────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
       ┌─────────────────┐         ┌─────────────────┐
       │  Single Agent   │         │  Multi-Agent    │
       │  7 tools        │         │  4 agents       │
       │  (auto-select)  │         │  (Planner→       │
       │                 │         │   Analyst→       │
       │                 │         │   Buyer→         │
       │                 │         │   Writer)        │
       └────────┬────────┘         └────────┬────────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
       ┌────────────────────────────────────────────┐
       │         Capability Layer                   │
       │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
       │  │  5 MCP   │  │   RAG    │  │  NL→SQL  │  │
       │  │  Tools   │  │  Engine  │  │ + Safety │  │
       │  │(inv/sale/│  │(ngram+   │  │ (4-layer │  │
       │  │ procure) │  │ BM25+RRF)│  │ guardrail│  │
       │  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
       │       │             │             │         │
       │       └──────┬──────┴──────┬──────┘         │
       └──────────────┼─────────────┼────────────────┘
                      ▼             ▼
              ┌─────────────┐  ┌──────────────┐
              │ PostgreSQL  │  │  18 .md KB   │
              │ 5 tables    │  │  (4 sections)│
              │ 1000+ rows  │  │  135 chunks  │
              └─────────────┘  └──────────────┘
                              │
                              ▼
                    FastAPI Web UI (3 tabs)
```

**Detailed architecture**: [docs/architecture/erp_copilot.md](docs/architecture/erp_copilot.md)

---

## 🧠 Why this project exists

Most "AI agent" demos are toys:
- They call OpenAI once and print the result.
- They have no safety guardrails on the SQL they generate.
- They don't show what happens when the LLM hallucinates.
- They can't run in production because they're one big script.

This repo is different. It ships:

| Concern | How it's handled |
|---------|------------------|
| **SQL injection** | 4-layer guardrail (AST whitelist → SQL keyword blacklist → statement-type whitelist → parameterized queries) |
| **Wrong tool chosen** | 4-mode tool routing: LLM-decided → keyword → fallback chain → error |
| **Hallucinated answers** | RAG returns cited chunks; the LLM must quote them |
| **Provider outage** | Pluggable providers with retry + exponential backoff |
| **Slow queries** | Async psycopg connection pool + query timing logs |
| **Memory leaks** | Conversation history capped at 100 messages |
| **Bad retries** | Exponential backoff with ±25% jitter |

---

## 🧩 Use cases

### A — Customer asks about a product in stock

```
Single agent flow:
1. User: "Is SKU-123 in stock?"
2. Agent decides: call `get_product_stock` (MCP tool)
3. Tool queries PostgreSQL: SELECT on_hand FROM inventory WHERE sku = ?
4. Agent formats: "Yes, 47 units in stock. Last restocked 3 days ago."
```

### B — Customer asks about a return policy

```
RAG flow:
1. User: "Can I return a product after 30 days?"
2. Agent decides: call `ask_knowledge_base` (RAG)
3. RAG retrieves top 3 chunks from 18-doc KB via char-ngram + BM25 + RRF
4. Agent synthesizes answer with citations: "[1] Return Policy §3.2 ..."
```

### C — Analyst asks for a sales report

```
Multi-agent flow:
1. User: "Analyze inventory risk for next 30 days"
2. Planner decomposes: 3 sub-tasks
3. Inventory Analyst: queries sales velocity + current stock
4. Purchase Specialist: calculates reorder quantities + supplier lead times
5. Report Writer: synthesizes into Markdown report
6. Output: examples/output/inventory_risk_report.md
```

---

## 📦 Installation

```bash
# Core (just the framework)
pip install -e .

# Full ERP Copilot (adds PostgreSQL, MCP, FastAPI)
pip install -e ".[erp]"
```

---

## 🔌 Adding your own tools

```python
from macs_pkg.tools.base import Tool, ToolSpec

class MyTool(Tool):
    spec = ToolSpec(
        name="my_tool",
        description="Does X to Y",
        inputs={"query": "string"},
        output="dict",
    )

    async def run(self, query: str) -> dict:
        # your logic here
        return {"result": ...}

# Register it
from macs_pkg.tools.registry import ToolRegistry
registry = ToolRegistry.get_instance()
registry.register(MyTool())
```

---

## 🤖 Adding your own LLM provider

```python
from macs_pkg.llm.base import LLMProvider, LLMMessage

class MyProvider(LLMProvider):
    async def complete(self, messages, system=None, **kwargs):
        # call your LLM API
        return LLMResponse(content="...")

# Use it
agent = ERPCopilotAgent(provider=MyProvider(...))
```

---

## 📚 Documentation

- [Quickstart (this file)](#-60-second-quickstart)
- [Architecture](docs/architecture/erp_copilot.md)
- [ERP Copilot use case](docs/use_cases/erp_ai_copilot.md)
- [Multi-agent inventory workflow](docs/use_cases/erp_ai_copilot_multi_agent.md)
- [RAG knowledge base](docs/use_cases/erp_knowledge_assistant.md)
- [CHANGELOG](CHANGELOG.md)
- [v1.0.0 release notes](RELEASE_NOTES_v1.0.0.md)

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome — open an issue first if you're planning a big change.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙋 Who built this

Built by an AI Application Engineer with 1 year of Java backend production experience (ERP domain) + PostgreSQL migration experience. Now focused on AI agent systems for enterprise.

- GitHub: [@blank5this](https://github.com/blank5this)
- Upwork: [profile coming soon]
- LinkedIn: [profile coming soon]

Currently accepting contract work on Upwork for:
- Custom AI agent development
- RAG knowledge base setup
- NL→SQL with safety guardrails
- AI integration into existing Java / Python / PostgreSQL systems