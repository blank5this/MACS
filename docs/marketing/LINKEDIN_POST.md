---
title: I turned a generic multi-agent framework into a production-ready ERP AI Copilot in 15 days
platform: LinkedIn
target_audience: Overseas AI/ML hiring managers, technical recruiters, AI engineering leads
posting_priority: high
status: draft
---

# I just shipped a 15-day sprint that turned a generic multi-agent framework into a production-ready ERP AI Copilot

I want to share what happened when I stopped building "agent infrastructure" and started shipping an actual product.

Three weeks ago, my repo `MACS` was a Multi-Agent Collaboration framework. It had a runtime, message routing, six LLM providers, a tool registry, and a docker-compose file. It also had zero users, zero demos, and zero story for an interview.

Today it ships as **ERP AI Copilot v1.0.1**: a system that takes a question in plain Chinese like "哪些商品库存低于安全库存?" and returns a structured risk report backed by PostgreSQL, RAG, and four collaborating agents. 22 new files. 168 unit tests passing. 4 CI jobs. Three 60-second demo videos.

Here is what changed in my thinking, and the three technical decisions that made the difference.

## Decision 1: NL to SQL is not enough. NL to SQL with four layers of defense is.

Anyone can wire up an LLM to `psycopg`. The interesting question is what happens when a user types something that looks like a question but is actually an attack.

`macs_pkg/erp/nl2sql.py` runs every generated statement through four gates before it ever touches the database:

1. **AST parse** — the SQL is parsed into an AST. If parsing fails, the statement is rejected. No string matching, no regex.
2. **Blacklist scan** — every AST node is walked. Any reference to `DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`, `ALTER`, `GRANT`, `pg_sleep`, or `information_schema` raises immediately.
3. **Whitelist check** — only statements whose top-level operation is `SELECT` (or `WITH ... SELECT`) pass.
4. **Parameterized execution** — the AST is rebuilt with bound parameters. No f-strings. No string concatenation. No SQL injection surface.

I added 17 dedicated tests for this in `tests/test_nl2sql_safety.py`. Every test has a one-line "what attack are we blocking" docstring. That file is the single thing I am most proud of in this sprint, because it shows I think about failure modes, not happy paths.

## Decision 2: Multi-agent is not a buzzword. It is a context-budget decision.

I tried a single agent first. `ERPCopilotAgent` worked, but the tool list grew to seven tools (five MCP tools, RAG, NL to SQL). The system prompt ballooned past 1,200 tokens. With multi-step planning on top of that, the context window crept toward 4,000 tokens, and the model started missing tool calls.

I split it into four focused agents:

- **Planner** (`ERP_PLANNER`) — turns a user goal into a 3-4 step subtask plan.
- **Inventory Analyst** (`ERP_INVENTORY_ANALYST`) — reads `products` and `inventory` tables, returns risk levels.
- **Purchase Specialist** (`ERP_PURCHASE_SPECIALIST`) — reads `purchase_orders` and `suppliers`, returns pricing trends.
- **Report Writer** (`ERP_REPORT_WRITER`) — receives the previous two outputs, writes a Markdown report, persists it to `examples/output/`.

Each agent owns two to three tools. Each prompt is under 800 tokens. Task success rate jumped from roughly 70% to over 95% in my manual tests. The orchestration lives in `macs_pkg/erp/workflows/inventory_risk.py` and follows a Hierarchical pattern (Planner dispatches, Report Writer aggregates).

The interview answer I now give to "why multi-agent?" is grounded in a number I can defend.

## Decision 3: Hybrid retrieval is not optional for enterprise RAG.

I shipped 18 Chinese-language ERP knowledge documents across four subdirectories (operations, warehouse, procurement, finance). I deliberately did not call an embedding API. Instead I implemented a hybrid retriever in `macs_pkg/erp/rag/`:

- **char-ngram tokenizer** with n in [2, 4] — gives me robust tokenization for Chinese without a tokenizer dependency.
- **BM25 scoring** — classic, predictable, zero-cost.
- **Reciprocal Rank Fusion (RRF)** — merges both rankings into a single top-k list. Default `k=3` to keep context tight.

Top-k is set to 3 by default in `macs_pkg/erp/rag/query.py:69-79`. That is intentional. If your RAG floods the prompt with ten chunks, you have not built a RAG system — you have built an expensive grep.

## The business value side

The point of all this engineering is that a warehouse manager can ask three questions in Chinese and get an answer:

- "分析未来 30 天库存风险并给出采购建议" — runs the four-agent pipeline, writes a Markdown report.
- "哪些供应商涨价最快?" — single agent, Purchase Specialist, structured supplier ranking.
- "如何处理采购退货?" — pure RAG, returns three cited passages from the procurement knowledge base.

There is also a FastAPI Web UI with three tabs (Chat, Multi-agent Report, KB Search) that I built in Day 12 because non-technical colleagues needed to see it without touching Python.

## The reflection that changed my approach

The line I keep coming back to from my own roadmap:

> Stop building MACS as a framework. Build it as an ERP AI Copilot product.
> That one shift in framing is probably worth more to my next offer than another 5,000 lines of agent code.

I used to think the value was in abstractions. Pluggable this, abstract that, six LLM providers behind a unified interface. None of that matters if a hiring manager cannot see what the system does in 60 seconds. Now I lead every interview with a three-minute walk through the Web UI, then drop into architecture, then into failure modes. The order matters.

## The numbers

- **22** new source files
- **168** unit tests passing, **23** integration tests
- **4** CI jobs (lint, unit, integration, ERP-specific)
- **5** PostgreSQL tables seeded with 1000+ rows of synthetic ERP data
- **18** Chinese KB documents, **135** chunks, hybrid retrieval
- **6** LLM providers abstracted (Anthropic, OpenAI, plus MiniMax, Qwen, Zhipu, DeepSeek)
- **5** MCP tools for inventory, sales, procurement
- **3** 60-second demo videos with scripts
- **3** FastAPI Web UI tabs
- **MIT** license

Repo: https://github.com/blank5this/MACS

If you are also building AI applications and want to compare notes — on agent context budgets, on NL to SQL defense layers, on hybrid retrieval without embeddings, on what hiring managers actually ask about multi-agent systems — I would love to connect.

#AI #LLM #RAG #ERP #AIEngineering #MultiAgent #Claude #OpenSource