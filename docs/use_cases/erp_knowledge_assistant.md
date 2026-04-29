# Use Case: ERP Knowledge Assistant

> Building an enterprise knowledge base Q&A system with RAG and multi-agent collaboration.

## Problem Statement

Enterprise Resource Planning (ERP) systems contain vast amounts of operational knowledge — policies, procedures, approval workflows, and guidelines. However:

- Employees struggle to find relevant information through deep menu navigation
- IT helpdesks are flooded with repetitive policy questions
- Knowledge exists in scattered documents (manuals, wikis, emails)
- Answers are often outdated or inconsistent across sources

**Goal:** Build an AI-powered assistant that answers employee questions about company policies using RAG over ERP documentation.

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Question                                │
│  "How do I submit a purchase requisition over 10,000 RMB?"     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MACS Runtime (Hierarchical)                   │
│                                                                  │
│  ┌─────────────┐                                                │
│  │   Planner    │ ← Decomposes question into search + answer    │
│  └──────┬──────┘                                                │
│         │ subtasks                                              │
│  ┌──────▼──────┐                                                │
│  │  Executor   │ ← Executes with Proactive RAG retrieval       │
│  └──────┬──────┘                                                │
│         │ results                                               │
│  ┌──────▼──────┐                                                │
│  │  Reviewer   │ ← Validates answer quality                     │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RAG Knowledge Base                               │
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  Procurement    │    │   Supplier      │                     │
│  │  Policy Docs   │    │   Management    │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────┐                   │
│  │   ChineseCharNgramEmbedder (TF-IDF)      │                   │
│  │   384-dim offline embedding (no GPU)     │                   │
│  └────────────────────┬────────────────────┘                   │
│                       │                                          │
│  ┌────────────────────▼────────────────────┐                   │
│  │   InMemoryVectorStore (cosine search)    │                   │
│  └─────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Agent Framework | MACS | Multi-agent with hierarchical mode |
| LLM | MiniMax-M2.7 | Cost-effective, good Chinese |
| Embedding | ChineseCharNgramEmbedder | Offline, no GPU, optimized for Chinese |
| Vector Store | InMemoryVectorStore | Zero infrastructure |
| Deployment | Docker | One-command startup |

---

## Key Implementation Details

### 1. Proactive RAG Pattern

Instead of relying on the LLM to decide when to search (reactive RAG), the Executor proactively searches when it detects ERP-related keywords:

```python
# MiniMaxExecutorAgent._execute_subtask()
erp_keywords = ["采购", "供应商", "库存", "财务", "审批",
                "销售", "订单", "报销", "付款", "管理"]

if any(kw in task_text for kw in erp_keywords):
    rag_result = await rag_tool.execute(query=task_text)
    if rag_result.success:
        rag_context = f"\n\n[RAG检索结果]\n{rag_result.output}\n\n"
        prompt = f"{rag_context}\n请基于上述检索结果回答：\n\n{task_text}"
```

**Advantage:** Stable, predictable, no missed retrievals due to LLM tool-calling failures.

### 2. Hierarchical Agent Collaboration

```
Question → Planner (decompose) → [Executor: RAG search + LLM answer]
                                    ↓
                              [Reviewer: validate completeness]
                                    ↓
                              Final Answer
```

Each agent calls `think()` + `act()` — ensuring LLM is actually invoked.

### 3. Offline Chinese Embedding

```python
config = RAGConfig(
    embedder_provider="chinese_char_ngram",  # Not sentence-transformers!
    embedding_dim=384,
    chunk_size=200,
    chunk_overlap=30,
    similarity_threshold=0.0,  # Low threshold for small corpus
)
```

Uses character n-grams (1-3 chars) + TF-IDF — works offline, no GPU, handles Chinese.

---

## Demo Walkthrough

### Prerequisites

```bash
# Set API key
export MINIMAX_API_KEY=your_key

# Run demo
cd C:\Users\admin\Desktop\macs
python examples/erp_knowledge_assistant.py
```

### Sample Questions and Expected Answers

#### Q1: "员工如何提交采购申请？金额超过1万怎么处理？"

**Expected Answer:**
> 1. 登录ERP系统，点击"采购申请"
> 2. 填写申请单：商品名称、数量、预算金额、预计交付日期
> 3. **金额处理规则：**
>    - < 1万元 → 主管直接审批
>    - ≥ 1万元 → 需财务复核
> 4. 提交后等待审批通知
> 5. 审批通过后，系统自动生成采购订单

#### Q2: "供应商评级有哪些？付款条件是什么？"

**Expected Answer:**
> **供应商评级：**
> - A级：长期合作伙伴
> - B级：合格供应商
> - C级：试用期供应商
>
> **付款条件：**
> - 月结30天
> - 票到付款
> - 预付30%

#### Q3: "库存安全线是什么？如何设置补货策略？"

**Expected Answer:**
> **安全库存预警：**
> 库存低于安全线时系统自动提醒
>
> **补货策略：**
> - 定量补货
> - 定期补货
> - 安全库存补货
>
> **盘点方式：**
> 月度盘点、年度盘点、抽盘
>
> **库位管理：**
> ABC分类管理

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Average response time | ~15 seconds |
| Questions processed | 3/3 (100%) |
| Embedding generation | Offline (~50ms per query) |
| Memory footprint | < 500MB |

---

## Enterprise Deployment Considerations

### Security

- API keys managed via environment variables (not in code)
- Data stays on-premise (RAG knowledge base is local)
- No user query logging by default

### Scalability

- InMemoryVectorStore suitable for < 100K chunks
- For larger scale, swap to Chroma or FAISS
- Docker/K8s deployment for horizontal scaling

### Compliance

- Audit trail via ExecutionTracer (Mermaid sequence diagrams)
- Prometheus metrics for operational visibility
- OpenTelemetry integration for enterprise monitoring

---

## Variations

### 1. Claude-Powered Version

Replace MiniMax with Claude for potentially higher quality:

```python
from macs_pkg.llm import ClaudeProvider, LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent

provider = ClaudeProvider(api_key=os.environ.get("ANTHROPIC_API_KEY"))
planner = LLMPlannerAgent("planner", provider=provider)
executor = LLMExecutorAgent("executor", provider=provider, tool_registry=registry)
reviewer = LLMReviewerAgent("reviewer", provider=provider)
```

### 2. Multi-Tenant Version

Extend to serve multiple departments with separate knowledge bases:

```python
# Per-department RAG engines
procurement_engine = RAGEngine(procurement_config)
finance_engine = RAGEngine(finance_config)
hr_engine = RAGEngine(hr_config)

# Router agent selects engine based on question topic
```

### 3. Hybrid Search Version

Combine vector search with keyword search:

```python
async def hybrid_search(query, top_k=5):
    vector_results = await vector_store.search(query, top_k=top_k*2)
    keyword_results = await keyword_search(query, top_k=top_k)

    # Merge and rerank
    combined = rerank(vector_results, keyword_results)
    return combined[:top_k]
```

---

## Code Location

| Component | File |
|-----------|------|
| ERP Demo | `examples/erp_knowledge_assistant.py` |
| RAG Engine | `macs_pkg/rag/rag_engine.py` |
| Chinese Embedder | `macs_pkg/rag/chinese_embedder.py` |
| LLM Executor (Proactive RAG) | `macs_pkg/llm/agents.py` |
| Hierarchical Mode | `macs_pkg/collaboration/hierarchical.py` |
