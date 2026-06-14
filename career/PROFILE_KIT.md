# Profile Kit — Upwork + LinkedIn 文案包

> 直接复制粘贴。所有文案都基于你已有的 MACS + ERP AI Copilot 真实经历。

---

## 1. Upwork 个人简介 (Profile Overview)

**Headline (限 70 字符):**
```
AI Application Engineer | Java Backend | Multi-Agent Systems | RAG
```

字符数: 67 ✓

**Overview (正文, ~3000 字符上限):**

```
I'm an AI Application Engineer who builds production-grade AI systems
on top of solid backend foundations.

Most "AI engineers" only know how to call an LLM API. I build the
whole stack — LLM provider abstraction, multi-agent orchestration,
tool-calling, RAG knowledge bases, NL→SQL translation, MCP tool
servers, and FastAPI web UIs.

WHAT I BUILT (open source, MIT, 350+ tests passing):
• MACS — a Multi-Agent Collaboration Stack with 6 LLM providers
  (Claude, GPT-4o, MiniMax-M2.7, Qwen, DeepSeek, Zhipu, Hunyuan),
  4 collaboration modes (hierarchical / pipeline / decentralized /
  dynamic), and a tool registry with 9 built-in tools.

• ERP AI Copilot — a working enterprise AI product that turns
  natural-language questions into PostgreSQL queries, inventory
  risk reports, and policy-document answers. Built on top of MACS.
  Includes:
  - Text2SQL with 4-layer safety (AST whitelist / blacklist /
    statement-type whitelist / parameterized queries)
  - RAG knowledge base (char-ngram + BM25 + RRF hybrid retrieval)
  - 5 MCP inventory / sales / procurement tools
  - 4-agent collaboration workflow
  - FastAPI web UI (3 tabs)

BACKEND DEPTH (where AI engineers usually fall apart):
• 1 year of Java backend experience with production ERP exposure
• PostgreSQL migration experience (schema design, query optimization)
• Data collection pipelines
• Async Python (asyncio, psycopg, FastAPI)

WHAT I'LL DO FOR YOU:
• Build a custom AI agent for your domain (customer support,
  document Q&A, sales assistant, internal tools)
• Wire up your data sources (Postgres, MySQL, MongoDB, Notion,
  PDFs, Google Drive) into a RAG system
• Build NL→SQL over your database with safety guardrails
• Integrate Claude / GPT-4o / open-source models
• Ship a working FastAPI web UI you can demo to stakeholders

RATE: $18/hr for ongoing work; fixed-price quotes for well-scoped
projects. Negotiable based on project complexity and timeline.

I respond within 4 hours during CN business hours (UTC+8) and
within 12 hours otherwise. I can take on 15-20 hrs/week reliably.
```

---

## 2. Upwork 项目投标模板（5 套可换着用）

### 模板 A — NL→SQL / 数据问答类

```
Hi [Client name],

I read your job post carefully — you need an AI that turns
plain-English questions into safe SQL queries against your
[Shopify / Stripe / Postgres] database.

I've already built and shipped this exact thing as part of an
open-source ERP AI Copilot (NL→SQL with 4-layer safety: AST
whitelist, SQL keyword blacklist, statement-type whitelist,
parameterized queries — see https://github.com/blank5this/MACS).

Quick plan for your project:
1. Schema audit + 5 representative test questions (Day 1)
2. Working Text2SQL over your schema with safety guardrails (Day 3)
3. RAG layer over your existing docs (Day 5)
4. FastAPI web UI for stakeholders to try (Day 7)

Tech stack: Python, FastAPI, PostgreSQL, LangChain, Claude / GPT-4o.
I have Java backend experience, so I can integrate with your
existing services if needed.

Two questions before I send a final quote:
1. How many tables / how complex is the schema?
2. Do you need read-only access, or also writes (INSERT/UPDATE)?

Happy to do a 30-min Zoom to scope this properly.

— [Your name]
```

### 模板 B — RAG / 知识库类

```
Hi [Client name],

Building a RAG knowledge base over your internal docs is exactly
what I do.

Relevant experience:
• Built a RAG engine with char-ngram + BM25 + RRF hybrid retrieval
  over 18 Chinese ERP policy documents (135 chunks)
• Hit < 50ms query latency, 90%+ recall on test set
• Wired into a FastAPI web UI for end users

Open-source reference: https://github.com/blank5this/MACS

For your project, I'd propose:
1. Audit your docs (PDF / Notion / Google Drive / Confluence)
2. Set up ingestion pipeline + chunking strategy
3. Pick the right embedding model (OpenAI ada-002 vs local BGE
   vs Cohere)
4. Build the retrieval + answer-generation pipeline
5. Add citations so users can verify answers
6. Ship a minimal web UI

Can you share:
- Approx. document count and total size
- Are they PDFs, Markdown, Notion pages, or mixed?
- Do you need citations in the answers?

I can start within 24 hours and ship a working MVP within a week.

— [Your name]
```

### 模板 C — 多 Agent 系统类

```
Hi [Client name],

Multi-agent systems are overhyped for 80% of use cases — for the
remaining 20%, they genuinely outperform single-agent setups.

I built and shipped one: a 4-agent inventory-risk workflow
(Planner → Inventory Analyst → Purchase Specialist → Report
Writer) that produces structured business reports from natural
language questions. Open-sourced at https://github.com/blank5this/MACS.

When I'd recommend multi-agent for your project:
- Task requires different expertise areas (analysis + buying + writing)
- Single prompts get too long or unstable
- You want auditable, intermediate outputs

For your [describe their use case], I'd start with a single-agent
prototype first (cheaper, faster), and only escalate to multi-agent
if the single-agent version is hitting clear limits.

Happy to discuss your use case in a 15-min call before sending
a proposal.

— [Your name]
```

### 模板 D — Java + AI 集成类

```
Hi [Client name],

Java + AI integration is where I spend most of my time.

Background:
• 1 year of Java backend production experience (ERP domain)
• PostgreSQL migration project (schema + data + query rewrite)
• Now building AI systems in Python that talk to Java services
  via REST / gRPC / message queues

For your project, I'd suggest:
1. Keep your Java service as the source of truth (it owns the DB
   and business logic)
2. Build a Python AI layer (FastAPI) that:
   - Calls your Java service for authoritative data
   - Adds RAG / NL2SQL / LLM reasoning on top
   - Returns structured JSON to your existing UI
3. Use Claude or GPT-4o (with fallback to MiniMax-M2.7 for cost)

This separation means:
- Your Java code stays untouched
- AI failures don't bring down the core service
- You can swap the LLM without touching business logic

Would love to see your existing Java API contract — can you share
the OpenAPI / Swagger doc or a sample endpoint?

— [Your name]
```

### 模板 E — 通用 / 第一次接触类

```
Hi [Client name],

Saw your project — sounds interesting. Quick intro:

I build production AI systems end-to-end:
- LLM provider abstraction (Claude / GPT-4o / MiniMax / Qwen)
- Multi-agent orchestration
- RAG knowledge bases
- NL→SQL with safety guardrails
- MCP tool servers
- FastAPI web UIs

I also have Java backend + PostgreSQL experience, which helps me
integrate AI features into existing systems without breaking them.

Recent work: shipped an ERP AI Copilot (open-source, MIT license)
that handles real business questions in Chinese — natural language
to SQL, inventory risk analysis, and policy Q&A. 350+ tests passing.

Two things I'd love to know before I quote:
1. What's the user-facing experience? (Web UI / Slack bot / API?)
2. What's the data layer? (Postgres / MySQL / MongoDB / files?)

Happy to do a 20-min Zoom to scope it out.

— [Your name]
```

---

## 3. LinkedIn Profile

### Headline (限 220 字符)
```
AI Application Engineer | Java Backend → Multi-Agent Systems
I build production AI (RAG / NL2SQL / Agents) on top of solid
backend foundations. Open source: github.com/blank5this/MACS
```

字符数: ~190 ✓

### About (限 2600 字符)

```
I'm an AI Application Engineer who builds production AI systems
on top of solid backend foundations.

What I do
━━━━━━━━━
• Design and ship multi-agent systems for real business problems
• Build RAG knowledge bases over enterprise document corpora
• Translate natural language to SQL with safety guardrails
• Integrate LLMs (Claude / GPT-4o / MiniMax-M2.7 / Qwen / DeepSeek)
  into existing Java / Python / PostgreSQL stacks
• Build FastAPI web UIs that stakeholders can actually use

What I built (open source, MIT, 350+ tests passing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MACS — Multi-Agent Collaboration Stack
  → 6 LLM providers, 4 collaboration modes, 9 built-in tools
  → github.com/blank5this/MACS

ERP AI Copilot (built on top of MACS)
  → Text2SQL with 4-layer safety (AST / blacklist / statement
    whitelist / parameterized queries)
  → RAG knowledge base (char-ngram + BM25 + RRF hybrid)
  → 5 MCP inventory / sales / procurement tools
  → 4-agent inventory risk workflow
  → FastAPI web UI with 3 tabs

Background
━━━━━━━━━━
• 1 year of Java backend production experience (ERP domain)
• PostgreSQL migration project (schema + data + query rewrite)
• Data collection pipeline experience
• Now focused on AI application layer

What I can help you with
━━━━━━━━━━━━━━━━━━━━━━━
→ Custom AI agent for your domain
→ RAG over your docs / database
→ NL→SQL with safety
→ AI feature integration into existing Java/Python services
→ FastAPI demo UIs for stakeholder buy-in

Open to contract work, full-time roles, and consulting.
Reach out: [your email] · [your LinkedIn URL]
```

### Featured 板块（5 个展示位）
1. **GitHub: MACS** — https://github.com/blank5this/MACS
2. **ERP AI Copilot Demo** — 录屏链接（待 Phase 1.3 完成）
3. **架构图** — docs/architecture/erp_copilot.md 链接
4. **Blog post / 案例研究** — 写一篇 "How I built an ERP AI Copilot in 14 days" 发布到 dev.to / Medium
5. **Open-source 贡献证明** — GitHub contribution graph 截图

---

## 4. 项目申请 SOP（每天 30 分钟可完成 5 个投标）

```
每天 30 分钟:
1. 登录 Upwork (5 min)
2. 搜索关键词, 按 "newest first" 排序:
   - "AI agent"
   - "LangChain" / "LangGraph"
   - "OpenAI API" / "GPT-4 integration"
   - "RAG" / "vector database" / "embeddings"
   - "Java backend AI"
   - "PostgreSQL AI"
3. 每个项目花 5 分钟:
   - 读完整 description
   - 套用 5 个模板之一（A/B/C/D/E）
   - 把 [Client name] 和 [their use case] 填进去
   - 提一个具体问题（重要 — 让你从模板投标里区分出来）
4. 提交
```

**每日目标**: 5 个高质量投标（不是 20 个低质量）

**追踪表**: 用 Notion / Google Sheet 记录
| 日期 | 项目 | 客户 | 投标金额 | 状态 | 备注 |

---

## 5. 前 10 个客户的话术（针对 LinkedIn 加人）

### 给海外创业公司 CTO

```
Hi [First name],

I'm an AI Application Engineer. I noticed [Company name] is
working on [specific thing from their recent post / product page].

I built a Multi-Agent System (MACS, open-source on GitHub) and an
ERP AI Copilot that turns natural-language questions into safe
PostgreSQL queries + RAG-powered knowledge base answers.

If you're exploring AI features for [their specific product area],
I'd love to chat for 15 minutes about how I might help.

— [Your name]
```

**查找目标** (LinkedIn 搜索):
- "CTO" + "AI" + "startup"
- "Head of Engineering" + "AI"
- "Founder" + "AI agent" / "RAG"

**行业优先级**:
1. B2B SaaS（最容易付费）
2. Fintech（预算大）
3. E-commerce（库存/供应链痛点 = 你的 ERP 经验直接相关）
4. Healthcare（合规要求高 = 你的 SQL 安全设计能讲）

---

## 6. 报价策略

| 项目类型 | 报价 | 工时 |
|---------|------|------|
| NL→SQL MVP（5 表以内） | $500-800 固定价 | 5-7 天 |
| RAG 知识库 MVP（< 100 文档） | $400-700 固定价 | 4-6 天 |
| 多 Agent 工作流 | $800-1500 固定价 | 7-10 天 |
| 集成到现有 Java 服务 | $25-40/hr | 看复杂度 |
| 维护 / 改进 | $15-22/hr | 持续 |

**谈判锚点**: 你的时薪是 $18/hr；客户预算通常比这高 30-50%，他们会砍价，所以**先报高 20%**。

**绝不接的**:
- 单纯 prompt 调优（无技术深度）
- 客户预算 < $200（不划算）
- 客户不提供 API key（你没法 demo）
- 需要你"学习新框架"的项目（你不是来学习的）

---

## 7. 第一周执行清单

- [ ] 注册 Upwork 账号, 提交实名
- [ ] 完善 Upwork profile（用上面的文案）
- [ ] 注册 LinkedIn 个人账号, 完善 profile
- [ ] 设置 Upwork 关键词告警: AI agent / LangChain / RAG / OpenAI / Java backend
- [ ] 提交前 5 个投标（每天 1 个, 第 1 周至少 5 个）
- [ ] LinkedIn 加 20 个海外创业公司 CTO
- [ ] 发 5 个个性化 connection request（用上面的模板）
- [ ] 写第一篇博客 "How I built an ERP AI Copilot in 14 days"
- [ ] 在 IndieHackers / Hacker News 发项目链接