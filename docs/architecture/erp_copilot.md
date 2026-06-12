# ERP AI Copilot — 架构文档

> 描述 MACS → ERP AI Copilot 的模块切分、数据流、依赖关系。
> 配套 Mermaid 图可在 GitHub / VS Code Mermaid 扩展 / `make docs` 渲染。

## 顶层模块图

```mermaid
flowchart TB
    subgraph User["用户层"]
        CLI[CLI / Example Scripts]
        WEB[FastAPI Web UI<br/>3 Tab]
        CI[CI / Make Targets]
    end

    subgraph Agent["Agent 层 (macs_pkg/agents/)"]
        CA[ERPCopilotAgent<br/>7 tools · Day 8]
        WF[InventoryRiskWorkflow<br/>4 agents · Day 10-11]
        AT[AgentTemplateRegistry<br/>4 ERP templates · Day 9]
    end

    subgraph Capability["能力层 (macs_pkg/erp/)"]
        MCP[5 MCP Tools<br/>inventory / sales / procurement]
        RAG[RAG Engine<br/>char-ngram + BM25 + RRF]
        NL[NL→SQL Translator<br/>+ 4-Layer Guardrail]
    end

    subgraph Data["数据层"]
        PG[(PostgreSQL 16<br/>5 tables · 1000+ rows)]
        KB[18 篇中文 .md<br/>data/erp_kb/]
    end

    subgraph Core["MACS 核心 (复用)"]
        RT[RuntimeEngine<br/>Hierarchical]
        RE[BaseAgent / Roles]
        LP[6 LLM Providers<br/>Claude / MiniMax / OpenAI...]
    end

    CLI --> CA
    CLI --> WF
    WEB --> CA
    WEB --> WF
    WEB --> RAG
    CI --> CA
    CI --> WF

    CA --> MCP
    CA --> RAG
    CA --> NL
    WF --> AT
    AT --> CA
    AT --> RE

    MCP --> PG
    NL --> PG
    RAG --> KB
    CA --> LP
    WF --> LP
    WF --> RT
```

## 数据流: 单 Agent 查询

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as ERPCopilotAgent
    participant T as ToolAgent
    participant L as LLM Provider
    participant M as MCP Tool
    participant DB as PostgreSQL

    U->>A: "哪些商品库存低于安全线?"
    A->>T: think(question)
    T->>L: select_tool(question, tools=[7])
    L-->>T: tool=get_low_stock_products
    T->>M: get_low_stock_products(threshold=50)
    M->>DB: SELECT ... WHERE on_hand < safety_stock
    DB-->>M: rows
    M-->>T: 2 items
    T-->>A: tool_result
    A-->>U: {"tool": "get_low_stock_products", "result": {...}}
```

## 数据流: 多 Agent 工作流

```mermaid
sequenceDiagram
    participant U as 用户
    participant W as InventoryRiskWorkflow
    participant P as erp_planner
    participant IA as erp_inventory_analyst
    participant PS as erp_purchase_specialist
    participant RW as erp_report_writer
    participant L as LLM Provider

    U->>W: "分析未来 30 天库存风险并给出采购建议"
    W->>P: plan(question)
    P->>L: decompose
    L-->>P: 3 subtasks
    P-->>W: {plan: [s1, s2, s3]}

    par parallel analysts
        W->>IA: analyze(s1)
        IA->>L: think + DB query
        L-->>IA: low_stock_count=2
        IA-->>W: {analyses: [...]}
    end

    W->>PS: recommend(s2)
    PS->>L: think + supplier query + RAG
    L-->>PS: recs
    PS-->>W: {purchase_recs: [...]}

    W->>RW: write_report(s3)
    RW->>L: synthesize
    L-->>RW: markdown
    RW-->>W: {final_report: "..."}

    W-->>U: full WorkflowResult
```

## 数据流: RAG 知识库

```mermaid
flowchart LR
    Q[用户问题] --> EM[Char-Ngram Embedder]
    Q --> BM[BM25 Tokenizer]
    EM --> VEC[(Vector Index<br/>Faiss / in-memory)]
    BM --> INV[(Inverted Index)]
    VEC --> RRF[RRF 融合]
    INV --> RRF
    RRF --> TOP[Top-K Chunks]
    TOP --> CTX[拼接 context]
    CTX --> LLM[LLM 回答]
    LLM --> A[带引用答案]
```

## 依赖矩阵

| 模块 | 依赖 | 被谁依赖 |
|------|------|----------|
| `macs_pkg.erp.db` | `psycopg[binary,pool]` | tools, agents, web, health |
| `macs_pkg.erp.tools` | `db`, `mcp` | agents.copilot, examples |
| `macs_pkg.erp.nl2sql` | `db`, llm provider | agents.copilot, examples |
| `macs_pkg.erp.rag` | `rag.engine`, `data/erp_kb/` | agents.copilot, web, examples |
| `macs_pkg.erp.agents.copilot` | `db`, `tools`, `nl2sql`, `rag`, `core` | workflows, web, examples |
| `macs_pkg.erp.agents.templates` | `core.agent_template` | workflows |
| `macs_pkg.erp.workflows` | `agents.copilot`, `agents.templates`, `core.runtime` | examples, web |
| `macs_pkg.erp.web` | `agents.copilot`, `workflows`, `rag`, `health` | (部署) |
| `macs_pkg.erp.health` | `db`, llm provider, `rag` | web, CLI, k8s |

## 安全边界

```mermaid
flowchart TB
    USER[用户 NL 问题] --> NLS[NL2SQLTranslator]
    NLS --> SQL[候选 SQL]
    SQL --> V1[Layer 1: AST parse<br/>只允许 SELECT]
    V1 --> V2[Layer 2: 关键字黑名单<br/>INSERT/UPDATE/DELETE/DROP/...]
    V2 --> V3[Layer 3: 表/列白名单<br/>与 SCHEMA_DESCRIPTION 校验]
    V3 --> V4[Layer 4: 参数化执行<br/>psycopg parameterized]
    V4 --> DB[(PostgreSQL)]
    V4 -.拒绝.-> ERR[403 Forbidden<br/>返回解释]
```

## 部署拓扑 (docker-compose `--profile erp`)

```mermaid
flowchart LR
    subgraph Host["Host Machine"]
        OP[Operator / 浏览器<br/>:8001]
    end
    subgraph Compose["docker compose --profile erp"]
        PG[postgres:16-alpine<br/>:5432]
        INIT[erp-init<br/>seed · 一次性]
        WEB[erp-web<br/>uvicorn :8000]
    end
    OP -->|HTTP| WEB
    WEB -->|psycopg| PG
    INIT -.seed.-> PG
    PG --- VOL[(pgdata volume)]
```

## 关键设计决策

1. **PostgreSQL 而非 SQLite** — 支持并发写、JSONB、全文检索、materialized
   views. 与生产 ERP 系统同构.
2. **MCP 而非 Function Calling** — 工具层和 Agent 层解耦, 未来可以
   暴露给 IDE / 其他 agent 平台.
3. **Hybrid retrieval (embedding + BM25 + RRF)** — 单一方法在中文短查询
   表现不稳, RRF 融合两种信号.
4. **Hierarchical 而非 Flat** — Planner 先拆解, 4 个 executor 并行,
   Reviewer 收尾. 适合多步业务问题.
5. **Lazy resource** — DB / LLM / RAG 全部 lazy init, 单元测试 0
   外部依赖, 启动不需要任何 key.
6. **Health probe 单一源** — `macs_pkg.erp.health` 同时给 `/healthz`
   和 `make erp-check` 用.

## 文件清单 (按层)

### 数据层
- `macs_pkg/erp/db/connection.py` — `DatabaseConfig` / `DatabasePool`
- `macs_pkg/erp/db/schema.py` — 5 张表 DDL
- `macs_pkg/erp/db/seed.py` — Faker 1000+ 行
- `data/erp_kb/**/*.md` — 18 篇制度文档

### 工具层
- `macs_pkg/erp/tools/inventory_tools.py` — 5 个 async 函数
- `macs_pkg/erp/tools/server.py` — MCP server
- `macs_pkg/erp/nl2sql.py` — Translator + Validator + Executor
- `macs_pkg/erp/rag/indexer.py` + `query.py` — 索引 + 查询

### Agent 层
- `macs_pkg/erp/agents/copilot_agent.py` — 7 工具
- `macs_pkg/erp/agents/templates.py` — 4 模板

### 编排层
- `macs_pkg/erp/workflows/inventory_risk.py`

### 表现层
- `macs_pkg/erp/web/app.py` — FastAPI
- `macs_pkg/erp/web/static/index.html` — 3 Tab UI

### 横切
- `macs_pkg/erp/health.py` — 健康检查 (DB/LLM/RAG)
- `macs_pkg/erp/__init__.py` — 版本号

## 演化路径 (Day 15+ 之后)

| 阶段 | 增加 | 影响模块 |
|------|------|----------|
| 2 周 | 用户认证 + 多租户 | web, db |
| 4 周 | 真实 LLM 微调 (LoRA on ERP corpus) | rag, nl2sql |
| 8 周 | 切出 SaaS (Inventory Copilot, Procurement Copilot) | web, workflows |
| 12 周 | 真实 ERP 对接 (SAP / 用友 / 金蝶) | tools, db |
