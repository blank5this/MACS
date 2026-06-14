# ERP AI Copilot — Turn Your Business Questions into Answers

> An AI assistant for your ERP / inventory / procurement / sales data.
> Natural language in. Safe SQL + cited answers + risk reports out.

**Built by an AI engineer with real ERP experience. Already running. Open source.**

---

## 🚀 Try it now — 3 ways

| Way | Effort | What you get |
|-----|--------|--------------|
| **🟢 [Live demo on Render](https://macs-erp-copilot.onrender.com)** (China-friendly) | 0 clicks (one URL) | 2-tab Gradio UI: RAG over 18 docs + Text2SQL on seeded SQLite |
| **🟢 [Live demo on HF Spaces](https://huggingface.co/spaces/gkf123/macs-erp-copilot)** (global) | 0 clicks (one URL) | Same 2-tab UI, hosted on Hugging Face |
| Local: `python app.py` | 30 sec (`pip install -r requirements_hf.txt`) | Same 2-tab UI on http://localhost:7860 |
| Two curated scenarios | 0 install, no API key needed | [scenario_01_low_stock.py](examples/scenario_01_low_stock.py) · [scenario_02_purchase_return.py](examples/scenario_02_purchase_return.py) |

---

## The problem

Your team asks questions like:

- *"Which products are about to stock out?"*
- *"What did customer X buy last quarter?"*
- *"What's our return policy for items over $500?"*
- *"Should I reorder SKU-123 now or wait?"*

And your ERP can't answer in plain English. So someone has to write SQL, open a BI dashboard, or read a 30-page policy PDF. That costs you **3-5 hours per question**, and the answers are inconsistent across team members.

---

## The solution

**ERP AI Copilot** — a working AI assistant that:

1. Understands the question in natural language
2. Picks the right tool automatically (database query / MCP business tool / knowledge base)
3. Returns a cited, accurate answer in seconds

```
┌──────────────────────────────────────────────────────────┐
│  User: "Which products are below safety stock right now?" │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  ERPCopilotAgent      │
              │  (LLM with 7 tools)   │
              └───────────┬───────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
    ┌──────────────┐           ┌──────────────┐
    │  PostgreSQL  │           │  MCP Server  │
    │  (your data) │           │  (business   │
    │              │           │   logic)     │
    └──────┬───────┘           └──────┬───────┘
           ▼                          ▼
   ┌─────────────────────────────────────────┐
   │  AI: "7 products are below safety stock. │
   │   Top 3: SKU-A (deficit 23 units),       │
   │   SKU-B (deficit 15 units),              │
   │   SKU-C (deficit 12 units).              │
   │   Recommend reordering SKU-A within      │
   │   48 hours."                             │
   └─────────────────────────────────────────┘
```

---

## 3 capabilities (one product)

### 📊 Text2SQL — ask your database in English

| You ask | AI generates | AI returns |
|---------|--------------|------------|
| "Top 3 selling products last month?" | `SELECT p.name, SUM(s.qty) FROM sales s JOIN products p ...` | Ranked list with revenue |
| "How many purchase orders over $10k pending approval?" | `SELECT COUNT(*) FROM po WHERE amount > 10000 AND status = 'pending'` | Count + list |
| "Average lead time for supplier ACME?" | `SELECT AVG(delivery_days) FROM pos WHERE supplier = 'ACME'` | Number + context |

**Safety built-in:**
- AST whitelist (only SELECT / WITH allowed)
- SQL keyword blacklist (no DROP, DELETE, INSERT, UPDATE, etc.)
- Statement-type whitelist
- All values parameterized (no string interpolation)

### 📚 Knowledge Base — your policies, searchable

Upload PDFs, Markdown, Notion pages, Google Docs. The AI answers questions with citations.

```
Q: "Can a customer return an item after 30 days?"
A: "Per the Return Policy §3.2 [1], items can be returned within 30 days
    of delivery for a full refund. Between 30-60 days, store credit only.
    After 60 days, no returns accepted.

    [1] data/policies/return_policy.md §3.2"
```

**Under the hood:**
- char-ngram + BM25 + RRF hybrid retrieval
- Sub-50ms query latency on 100+ document corpus
- Citations enforced (the LLM must quote retrieved chunks)

### 📈 Inventory Risk Analysis — multi-agent workflow

For complex questions like *"Analyze inventory risk for next 30 days"*, the system spins up 4 specialized agents:

```
Planner          → Decomposes "30-day risk" into 3 sub-tasks
   ↓
Inventory Analyst → Queries sales velocity + current stock
   ↓
Purchase Spec.   → Calculates reorder qty + supplier lead times
   ↓
Report Writer    → Synthesizes into structured Markdown
   ↓
Output: inventory_risk_report.md
```

---

## Who this is for

| If you are... | You get... |
|---------------|------------|
| **An ERP consultant** | A demo you can show clients in 60 seconds |
| **A small manufacturer / retailer** | A self-hosted AI assistant for your ops team |
| **An internal IT team** | A reference architecture for AI-in-ERP |
| **An AI engineer evaluating agent frameworks** | A working, tested, open-source implementation |

---

## What it actually is (not vapor)

| Aspect | Status |
|--------|--------|
| Source code | Open source, MIT license |
| Tests | **256 passing** |
| LLM providers | 6 (Claude, GPT-4o, MiniMax-M2.7, Qwen, DeepSeek, Zhipu, Hunyuan) |
| MCP tools | 5 (inventory / sales / procurement) |
| KB docs (sample) | 18 Chinese policy documents |
| Web UI | FastAPI, 3 tabs, dark theme |
| Deployment | Docker Compose one-liner |
| Demo | 3 videos + 1 interactive animation |

---

## Run it in 60 seconds

```bash
git clone https://github.com/blank5this/MACS
cd MACS
docker-compose up -d        # PostgreSQL + auto-seed
make erp-run                # Web UI on http://localhost:8001
```

Then open the browser. Click the 3 tabs. Ask 3 questions. You'll have a working demo in 5 minutes.

**Or, even faster — no Docker required**:

```bash
pip install -r requirements_hf.txt
python app.py               # → http://localhost:7860  (2 tabs: RAG + Text2SQL)
```

---

## Pricing model

This repo is the **open-source reference implementation**. For consulting / customization:

| Engagement | Scope | Price |
|------------|-------|-------|
| **Setup** | Clone + configure to your schema + deploy | $500-800 |
| **Custom tools** | Add 3-5 business-specific MCP tools | $400-700 per tool batch |
| **Schema adapter** | Map your DB schema to the copilot | $600-1000 |
| **RAG ingest** | Set up your docs / Notion / Drive pipeline | $500-900 |
| **Maintenance** | Bug fixes + LLM updates + new features | $15-22/hr |

For ongoing AI engineering help: **$18-25/hr**.

---

## Why trust me

- **1 year of Java backend production experience** in the ERP domain
- **PostgreSQL migration project** (schema design + data migration + query optimization)
- **Data collection pipeline experience**
- **Built and shipped** this entire repo in production-ready state

Most "AI engineers" can call an LLM API. I can build the **whole stack** — provider abstraction, multi-agent orchestration, tool calling, RAG, NL→SQL safety, MCP servers, FastAPI web UI.

---

## Next steps

**Just curious?** → Clone the repo and try it. It's MIT-licensed.
https://github.com/blank5this/MACS

**Want a custom version for your business?** → Hire me on Upwork (link coming soon) or email [your email].

**Want to learn how it works?** → Read the architecture docs:
- [docs/architecture/erp_copilot.md](docs/architecture/erp_copilot.md)
- [docs/use_cases/erp_ai_copilot.md](docs/use_cases/erp_ai_copilot.md)

---

## FAQ

**Q: Does it work without internet / LLM API?**
A: No, you need an LLM API key (Claude or MiniMax recommended). Local models (Llama, Qwen) also work if you set up an OpenAI-compatible endpoint.

**Q: How long does setup take?**
A: ~30 minutes if you have Docker installed. ~3 hours if you need to set up Postgres manually.

**Q: Can it write to my database?**
A: Default config is **read-only** (enforced by the 4-layer SQL safety guardrail). Writes can be enabled per-tool if you want, but I'd recommend against it for v1.

**Q: What about data privacy?**
A: Everything runs locally. Only your questions go to the LLM provider (Claude API, OpenAI, etc.). Your data never leaves your infrastructure.

**Q: Can it integrate with my existing Java / Python backend?**
A: Yes — the copilot is just a FastAPI service. It can call your existing APIs as MCP tools, or your backend can call the copilot as a microservice.

**Q: What if I don't have PostgreSQL?**
A: The RAG knowledge base works without any database. The MCP tools and NL→SQL need a DB. MySQL / SQLite adapters are on the roadmap.