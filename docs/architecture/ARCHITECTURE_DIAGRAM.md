# MACS — System Architecture (Mermaid)

This document captures the full system architecture in Mermaid form so it
renders natively on GitHub, in Notion, and in any Markdown viewer that
supports the GFM spec.

## 1. Top-level: User → Mode → Agent → Capability

```mermaid
flowchart TB
    User([User question<br/>via Web UI / API / CLI])

    subgraph Mode["Collaboration mode (5 to pick)"]
        H[Hierarchical<br/>Leader + Executors + Reviewer]
        P[Pipeline<br/>Sequential stage chain]
        D[Decentralized<br/>Propose → vote]
        DR[Deep Research<br/>Planner → parallel → Reviewer]
        DY[Dynamic Selector<br/>Runtime mode picker]
    end

    subgraph Agents["Role agents — all inherit ReactAgent"]
        PL[PlannerAgent<br/>decompose / replan / propose]
        EX[ExecutorAgent<br/>proactive RAG + tool call]
        RV[ReviewerAgent<br/>3-criteria scorer + Citation]
        TA[ToolAgent<br/>LLM-driven tool selection]
    end

    subgraph Caps["Capability layer"]
        LLM[LLM provider<br/>Claude · GPT · DeepSeek · Qwen · Zhipu · Hunyuan]
        RAG[Hybrid RAG<br/>char-ngram TF-IDF + BM25 + RRF]
        SQ[Safe SQL Executor<br/>4-layer guardrail + read-only role]
        MCP[MCP tools x5<br/>inventory · sales · procurement · pricing · velocity]
    end

    DB[(PostgreSQL 16<br/>read-only role)]
    KB[(Knowledge base<br/>18 .md / .pdf chunks)]

    User --> Mode
    Mode --> PL
    Mode --> EX
    Mode --> RV
    Mode --> TA
    PL --> LLM
    EX --> LLM
    EX --> RAG
    EX --> MCP
    EX --> SQ
    RV --> LLM
    TA --> LLM
    RAG --> KB
    SQ --> DB
    MCP --> DB

    classDef mode fill:#fef3c7,stroke:#d97706,color:#000
    classDef agent fill:#dbeafe,stroke:#1d4ed8,color:#000
    classDef cap fill:#dcfce7,stroke:#15803d,color:#000
    class H,P,D,DR,DY mode
    class PL,EX,RV,TA agent
    class LLM,RAG,SQ,MCP cap
```

## 2. ERP AI Copilot request flow

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant W as Web UI<br/>(FastAPI + Gradio)
    participant M as Hierarchical Mode
    participant PL as PlannerAgent
    participant EX as ExecutorAgent
    participant RV as ReviewerAgent
    participant T as ToolAgent
    participant R as Hybrid RAG
    participant S as Safe SQL Executor
    participant DB as PostgreSQL (RO)

    U->>W: "Which products are below safety stock?"
    W->>M: execute(task)
    M->>PL: think(task) → _act_impl dispatch
    PL-->>M: [subtask_1, subtask_2]
    M->>EX: think(subtask_1)
    EX->>T: think("which tool?")
    T-->>EX: get_low_stock_products
    EX->>S: execute_safe_sql(generated)
    S->>DB: SELECT ... LIMIT (RO role)
    DB-->>S: 7 rows
    S-->>EX: {rows, citations}
    EX-->>M: result
    M->>RV: think([results])
    RV-->>M: {approved: True, score: 0.92}
    M-->>W: review_complete
    W-->>U: ranked products + reorder advice
```

## 3. ReactAgent strict think → act lifecycle

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> THINKING: think() called
    THINKING --> IDLE: _think_impl() returns
    IDLE --> ACTING: act() — only if think_called
    ACTING --> IDLE: _act_impl() returns
    THINKING --> Error: think() while THINKING
    ACTING --> Error: act() while ACTING
    Error --> [*]: RuntimeError
```

## 4. Multi-agent workflow: Inventory Risk Analysis

```mermaid
flowchart LR
    Q[User: 哪些商品库存风险最高?]
    P[Planner]
    IA[Inventory Analyst<br/>velocity + stock]
    PA[Purchase Specialist<br/>reorder qty + lead time]
    RW[Report Writer<br/>Markdown synthesis]
    RV[Reviewer<br/>3-criteria scoring]
    OUT[Final report<br/>+ citations + chart]

    Q --> P
    P --> IA
    P --> PA
    IA --> RW
    PA --> RW
    RW --> RV
    RV -->|approved ≥ 0.7| OUT
    RV -->|rejected| P
```

## 5. Safe SQL Executor — 4-layer guardrail

```mermaid
flowchart TB
    A[Generated SQL string]
    A --> B{Layer 1<br/>AST whitelist<br/>only SELECT<br/>no DDL/DML}
    B -->|reject| ER1[Block + log]
    B -->|pass| C{Layer 2<br/>Keyword block<br/>no DROP, UNION<br/>no pg_catalog, pg_*}
    C -->|reject| ER2[Block + log]
    C -->|pass| D{Layer 3<br/>Statement type<br/>SELECT only<br/>auto-LIMIT}
    D -->|reject| ER3[Block + log]
    D -->|pass| E{Layer 4<br/>Read-only DB role<br/>denies writes at DB level}
    E -->|fail| ER4[Block at DB]
    E -->|pass| F[Execute + shape result]
    F --> G[Result dict<br/>+ columns + rowcount + sql_audit]

    classDef pass fill:#dcfce7,stroke:#15803d,color:#000
    classDef fail fill:#fee2e2,stroke:#b91c1c,color:#000
    class A,B,C,D,E,F,G pass
    class ER1,ER2,ER3,ER4 fail
```

## 6. Collaboration mode selector

```mermaid
flowchart TD
    T{Task shape?}
    T -->|Multi-step, needs plan + review| H[Hierarchical]
    T -->|Linear transform pipeline| P[Pipeline]
    T -->|Multiple agents must agree| D[Decentralized]
    T -->|Open-ended research, many sources| DR[Deep Research]
    T -->|Don't know at design time| DY[Dynamic Selector]

    H --> H1[Planner → Executors → Reviewer]
    P --> P1[Stage1 → Stage2 → ...]
    D --> D1[All agents propose, then vote]
    DR --> DR1[Plan → parallel search/synthesize → Reviewer]
    DY --> DY1[Pick mode at runtime via heuristic / LLM]
```
