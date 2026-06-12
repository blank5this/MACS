---
title: 用 Python + FastAPI + PostgreSQL 做一个生产级 ERP AI Copilot (含 RAG / NL→SQL / 多 Agent)
platform: 掘金
target_audience: Python 后端 / AI 应用工程师 / 对 LLM 工程化感兴趣的技术读者
posting_priority: high
status: draft
---

# 用 Python + FastAPI + PostgreSQL 做一个生产级 ERP AI Copilot (含 RAG / NL→SQL / 多 Agent)

> 项目地址: https://github.com/blank5this/MACS  
> 15 天, 22 个新文件, 168 测试, 4 CI jobs, 3 段 60s 视频. 这篇文章挑 3 个最值得讲的点: NL→SQL 4 层防护、多 Agent 编排、混合检索.

---

## 项目结构 (ERP 部分)

```
macs_pkg/erp/
├── db/                     # 数据层
│   ├── connection.py       # DatabasePool (psycopg async)
│   ├── schema.py           # 5 张表 DDL
│   └── seed.py             # Faker 1000+ 行
├── tools/                  # MCP 工具 (stdio / SSE)
│   ├── inventory_tools.py  # 5 个 async 函数
│   └── server.py           # MCPServer 注册
├── nl2sql.py               # NL→SQL + 4 层防护
├── rag/                    # RAG 知识库
│   ├── indexer.py
│   └── query.py            # ask_kb()
├── agents/                 # Agent 模板
│   ├── copilot_agent.py    # 7 工具 ERPCopilotAgent
│   └── templates.py        # 4 ERP AgentTemplate
├── workflows/              # 多 Agent 工作流
│   └── inventory_risk.py   # Planner→Analyst→Buyer→Writer
├── web/                    # FastAPI
│   ├── app.py              # 4 endpoints
│   └── static/index.html   # 3 Tab UI
└── health.py               # 健康检查 (DB/LLM/RAG)
```

---

## 技术深挖 1: NL→SQL 4 层安全防护

LLM 直接生成 SQL 拿来跑数据库, 风险是显而易见的——用户输入"把 products 表删了", 模型礼貌地生成 `DROP TABLE products`, 数据库没了.

`macs_pkg/erp/nl2sql.py` 跑 4 层防护:

```python
# macs_pkg/erp/nl2sql.py (简化版)
import sqlparse
from sqlparse.tokens import Keyword, DML

BLOCKED = {"DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "GRANT"}

def safe_translate(nl_question: str, schema: dict) -> str:
    raw_sql = llm.generate_sql(nl_question, schema)        # 1. LLM 生成
    parsed = sqlparse.parse(raw_sql)                        # 2. AST 解析
    if not parsed or len(parsed) != 1:
        raise UnsafeSQLError("无法解析为单条 SQL")
    
    stmt = parsed[0]
    if stmt.get_type() != "SELECT":                         # 3. 白名单
        raise UnsafeSQLError(f"非 SELECT 语句被拒绝: {stmt.get_type()}")
    
    for token in stmt.flatten():
        if token.ttype is Keyword and token.normalized.upper() in BLOCKED:
            raise UnsafeSQLError(f"命中黑名单: {token.normalized}")  # 4. 黑名单
    
    return bind_parameters(stmt, extracted_params)         # 5. 参数化执行
```

关键点:

- **AST 解析**, 不是字符串匹配——`DRSELECTOP` 这种绕过黑名单的字符串根本进不来
- **黑名单白名单同时上**——黑名单防常见攻击, 白名单保证"只读"
- **参数化绑定**——不拼字符串, 不给 SQL 注入留缝

测试在 `tests/test_nl2sql_safety.py`, 17 个 case, 每个 case 一行 docstring 说明在防什么. 防御编程的范本.

---

## 技术深挖 2: 多 Agent 协作 (Planner→Analyst→Buyer→Writer)

我先做了单 Agent (`ERPCopilotAgent`), 把 7 个工具全塞给它. 跑得起来, 但 prompt 1200 token, 多步任务上下文接近 4000 token, 工具选择准确率从 95% 掉到 70%.

拆 Agent 的代码 (简化版):

```python
# macs_pkg/erp/workflows/inventory_risk.py
from macs_pkg.agents.tool_agent import ToolAgent
from macs_pkg.erp.agents.templates import (
    ERP_PLANNER, ERP_INVENTORY_ANALYST,
    ERP_PURCHASE_SPECIALIST, ERP_REPORT_WRITER,
)

class InventoryRiskWorkflow:
    def __init__(self, llm, db_pool, rag):
        self.planner   = ToolAgent(ERP_PLANNER, llm)
        self.analyst   = ToolAgent(ERP_INVENTORY_ANALYST, llm, tools=[...])
        self.buyer     = ToolAgent(ERP_PURCHASE_SPECIALIST, llm, tools=[...])
        self.writer    = ToolAgent(ERP_REPORT_WRITER, llm)
        self.db = db_pool
        self.rag = rag

    async def run(self, user_goal: str) -> dict:
        # 1. Planner 拆任务
        plan = await self.planner.run({"goal": user_goal})
        
        # 2. Analyst 跑库存分析
        inventory_result = await self.analyst.run({
            "question": plan["inventory_question"]
        })
        
        # 3. Buyer 跑采购分析
        purchase_result = await self.buyer.run({
            "question": plan["purchase_question"]
        })
        
        # 4. Writer 写报告
        report = await self.writer.run({
            "inventory": inventory_result,
            "purchase": purchase_result,
        })
        
        # 5. 落盘
        path = persist_report(report)
        return {"final_report": report, "path": path}
```

设计要点:

- **每个 Agent 2-3 个工具**, prompt < 800 token
- **职责分离**——Analyst 不碰采购, Buyer 不碰库存
- **失败隔离**——Analyst 挂了不影响 Buyer, 排查只看 Analyst 的 trace
- **结果结构化传递**——上一个 Agent 输出 JSON, 下一个 Agent 当输入

---

## 技术深挖 3: RAG 混合检索 (char-ngram + BM25 + RRF)

我没有用 embedding. 原因: 中文 embedding 模型对近义词召回不稳定, 换模型就要重新建索引, 启动成本高.

所以做了**混合检索**:

```python
# macs_pkg/erp/rag/query.py (简化版)
from collections import Counter
import math

def char_ngrams(text: str, n_range=(2, 4)) -> list[str]:
    tokens = []
    for n in n_range:
        for i in range(len(text) - n + 1):
            tokens.append(text[i:i+n])
    return tokens

def bm25_score(query_tokens, doc_tokens, idf, avgdl, k1=1.5, b=0.75):
    score, dl = 0.0, len(doc_tokens)
    for q in query_tokens:
        if q not in idf: continue
        tf = doc_tokens.count(q)
        score += idf[q] * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score

def rrf(rankings, k=60):
    fused = Counter()
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            fused[doc_id] += 1.0 / (k + rank + 1)
    return [doc_id for doc_id, _ in fused.most_common()]

def ask_kb(question: str, kb_index, top_k=3) -> list[dict]:
    q_tokens = char_ngrams(question)
    bm25_ranking = sorted(kb_index.docs, key=lambda d: -bm25_score(q_tokens, ...))
    ngram_ranking = sorted(kb_index.docs, key=lambda d: -ngram_overlap(q_tokens, d))
    final = rrf([bm25_ranking, ngram_ranking])[:top_k]   # 默认 top_k=3
    return [kb_index.docs[doc_id] for doc_id in final]
```

要点:

- **char-ngram (n=2,4)**——中文友好, 不依赖 jieba / 任何分词器
- **BM25**——经典可靠, 零成本, 召回可解释
- **RRF 融合**——Reciprocal Rank Fusion, k=60 是论文默认
- **`top_k=3` 默认**——不灌爆 prompt, 这是工程纪律

跑 18 篇中文 ERP 文档 / 135 chunks, 端到端 200ms 以内. 不需要 GPU, 不需要 API key, CI 也能跑.

---

## 性能数据: 健康检查 + lazy 资源 + 测试金字塔

### 健康检查 (`macs_pkg/erp/health.py`)

3 维探针: DB / LLM / RAG. 单一事实源, 同时给 k8s liveness/readiness 和 CLI 复用.

```python
# macs_pkg/erp/health.py (简化版)
async def probe() -> dict:
    db_ok, db_ms = await probe_db(timeout=1.0)
    llm_ok, llm_ms = await probe_llm(timeout=2.0)
    rag_ok, rag_ms = await probe_rag(timeout=1.0)
    return {
        "db":   {"ok": db_ok, "latency_ms": db_ms},
        "llm":  {"ok": llm_ok, "latency_ms": llm_ms},
        "rag":  {"ok": rag_ok, "latency_ms": rag_ms},
        "ready": db_ok and llm_ok and rag_ok,
    }
```

Web 暴露 `/healthz`, 返回 503 当任一维失败. 避免"LLM 挂了但 Web 还 200"的情况.

### lazy 资源加载

`DatabasePool` / `LLM client` / `RAG index` 都是 lazy init——首次访问才建连接. CI 跑 168 测试时, 没用到 DB 的测试不用启 Postgres, 跑得飞快.

### 测试金字塔

- **非集成 168**——纯函数 / 模板 / 单 Agent, CI 默认跑, < 30s
- **集成 23**——DB / MCP / Web, 标 `@pytest.mark.integration`, CI 单独 job 跑, 需 docker
- **e2e 6**——多 Agent 端到端, 用 `_ScriptedProvider` mock LLM, 0 token 成本

`tests/test_e2e_workflow.py` 第 160 行那个 `_ScriptedProvider` 是测试设计的小亮点——CI 跑端到端, 不调真实 LLM, 不花钱.

---

## 3 段 60s 视频

| # | 主题 | 脚本 |
|---|------|------|
| 1 | 单 Agent 混合工具 — 7 工具自动选择 | [01_single_agent_script.md](https://github.com/blank5this/MACS/blob/main/docs/videos/01_single_agent_script.md) |
| 2 | 多 Agent 协作 — 4 Agent 接力, 4 段产物 | [02_multi_agent_script.md](https://github.com/blank5this/MACS/blob/main/docs/videos/02_multi_agent_script.md) |
| 3 | RAG 知识库 — 18 篇中文文档混合检索 | [03_rag_script.md](https://github.com/blank5this/MACS/blob/main/docs/videos/03_rag_script.md) |

(视频文件位置: 待录, 见 `docs/RECORDING_GUIDE.md`)

---

## 写在最后

AI 应用工程师这个岗位, 招的不是"会调 LangChain 的人", 是"能把业务问题拆成 Agent / RAG / Tool 调用, 还能让它在生产环境跑稳的人".

代码: https://github.com/blank5this/MACS

如果你想跑一下, 一条命令起 Postgres + Web UI:

```bash
make erp-run   # http://localhost:8001
```

觉得有用求个 Star, 提 issue 也欢迎.

## 自检清单

- [ ] 标题包含技术栈关键词 (Python / FastAPI / PostgreSQL / RAG / 多 Agent), 搜索友好
- [ ] 开头 200 字有项目结构 Markdown 树
- [ ] 技术深挖 1 包含 4 层 NL→SQL 防护代码片段
- [ ] 技术深挖 2 包含 Planner→Analyst→Buyer→Writer 完整代码
- [ ] 技术深挖 3 包含 char-ngram + BM25 + RRF 代码
- [ ] 性能数据有具体数字 (168 测试 / 23 集成 / 健康检查 3 维)
- [ ] 结尾有 3 段视频链接占位 + GitHub
- [ ] 代码 / 命令 / 路径全部用 `code` 包裹
- [ ] 字数在 1500-2500 字之间
- [ ] 没有 emoji (Markdown 标题符号除外)