# ERP AI Copilot — 综合用例索引

> 一个文档化的入口, 把 ERP AI Copilot 的 4 个核心用例串成一条完整故事线。
> 覆盖: 单 Agent 混合工具 / 多 Agent 库存风险 / RAG 知识库 / Web UI 演示。

## 一句话定位

**MACS ERP AI Copilot** 是基于 MACS (Multi-Agent Collaboration Stack)
构建的 **企业级 AI 业务助手**, 把自然语言问题映射到 5 个能力维度:

1. **结构化查询** — NL→SQL 安全翻译 + 4 层 SQL 防护
2. **半结构化业务工具** — 5 个 MCP 库存/销售/采购工具
3. **非结构化知识** — 18 篇中文 ERP 制度文档的混合检索 (RAG)
4. **多 Agent 协作** — Planner → Analyst → Buyer → Writer 的库存风险工作流
5. **交互界面** — 3 Tab FastAPI Web UI, 60s 演示就绪

## 顶层架构 (ASCII)

```
                    ┌──────────────────────┐
                    │   用户问题 (中文)     │
                    └──────────┬───────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                              ▼
   ┌────────────────────┐         ┌────────────────────┐
   │  Single Agent       │         │  Multi-Agent        │
   │  ERPCopilotAgent   │         │  Workflow           │
   │  (Day 8)            │         │  (Day 10/11)        │
   │                     │         │                     │
   │  7 tools:           │         │  4 agents:          │
   │  • 5 MCP 工具       │         │  • erp_planner      │
   │  • ask_knowledge    │         │  • erp_inventory    │
   │  • query_database   │         │  • erp_purchase     │
   └────────┬────────────┘         │  • erp_report       │
            │                       └──────────┬──────────┘
            │                                  │
            └──────────────┬───────────────────┘
                           ▼
   ┌──────────────────────────────────────────────────┐
   │              Capability Layer                    │
   │                                                  │
   │  ┌─────────┐  ┌──────────┐  ┌──────────────┐    │
   │  │Postgres │  │  RAG     │  │  KB 18 .md  │    │
   │  │ 5 张表  │  │ Engine   │  │  Operations  │    │
   │  │ 1000+行 │  │ (ngram+  │  │  Warehouse   │    │
   │  │  seed   │  │  BM25+   │  │  Procurement │    │
   │  │         │  │  RRF)    │  │  Finance     │    │
   │  └─────────┘  └──────────┘  └──────────────┘    │
   └──────────────────────────────────────────────────┘
                           │
                           ▼
   ┌──────────────────────────────────────────────────┐
   │           Presentation Layer                     │
   │                                                  │
   │   • 3 Tab Web UI (FastAPI)   ← Day 12          │
   │   • 3 × 60s 演示视频         ← Day 8/11/14     │
   │   • 健康检查 (3 维)          ← Day 13          │
   └──────────────────────────────────────────────────┘
```

## 4 个子用例 (深入链接)

| # | 场景 | 文档 | 代码示例 | 视频 |
|---|------|------|----------|------|
| 1 | **单 Agent 混合工具**: 用户问 "哪些商品库存低于安全线?" → LLM 选 `get_low_stock_products` | [erp_ai_copilot_multi_agent.md](./erp_ai_copilot_multi_agent.md) (ch 2) | [`examples/erp_copilot_single_agent.py`](../../examples/erp_copilot_single_agent.py) | Video 1 |
| 2 | **多 Agent 库存风险**: 一句 "分析未来 30 天库存风险并给出采购建议" → 4 Agent 协作, 4 段产物 | [erp_ai_copilot_multi_agent.md](./erp_ai_copilot_multi_agent.md) | [`examples/erp_copilot_multi_agent.py`](../../examples/erp_copilot_multi_agent.py) | Video 2 |
| 3 | **RAG 知识库问答**: 18 篇 ERP 制度文档 + char-ngram + BM25 + RRF | [erp_knowledge_assistant.md](./erp_knowledge_assistant.md) | [`examples/erp_knowledge_assistant.py`](../../examples/erp_knowledge_assistant.py) | Video 3 |
| 4 | **Web UI 演示**: 3 Tab 浏览器界面, 一键从 chat 到 multi-agent 到 KB search | (本页) | [`macs_pkg/erp/web/app.py`](../../macs_pkg/erp/web/app.py) | (录屏) |

## 15 天交付全景

```
Day  1-3  数据层      → Docker Postgres + 5 表 schema + 1000+ 行 seed
Day  4    MCP 工具    → 5 个 stdio/SSE inventory/sales/procurement 工具
Day  5-6  NL→SQL      → 翻译器 + 4 层 SQL 防护 (whitelist + parse + 黑名单 + 参数化)
Day  7    RAG 知识库  → 18 篇中文 .md 文档 + char-ngram + BM25 + RRF
Day  8    单 Agent    → ERPCopilotAgent 7 工具 (Video 1)
Day  9    领域模板    → 4 个 ERP AgentTemplate 注册到全局注册中心
Day 10-11 多 Agent    → InventoryRiskWorkflow + 端到端 (Video 2)
Day 12    Web UI      → FastAPI 4 endpoints + 3 Tab 静态前端
Day 13    CI 整合     → GitHub Actions + Makefile + health probe
Day 14    文档+视频 3 → 架构图 + 用例索引 + RAG 演示
Day 15    GitHub 重构 → README / CHANGELOG / release v1.0.0-erp-copilot
```

## 快速开始 (TL;DR)

```bash
# 1. 装依赖 + 启 Postgres
pip install -r requirements.txt
docker compose --profile erp up -d postgres erp-init

# 2. 跑 Web UI
make erp-run
# 浏览器打开 http://localhost:8001

# 3. 跑单 Agent 演示 (Video 1)
python examples/erp_copilot_single_agent.py

# 4. 跑多 Agent 演示 (Video 2)
python examples/erp_copilot_multi_agent.py "分析未来 30 天库存风险并给出采购建议"

# 5. 跑 RAG 知识库演示 (Video 3)
python scripts/record_video_03.py --no-delay

# 6. 健康检查
make erp-check

# 7. 跑全部测试
make erp-test
```

## 关键数字 (截至 Day 14)

- **代码**: 22 个新文件 (5 子包 + 5 examples + 4 docs + 4 CI/Makefile + 4 web)
- **测试**: 152 passed (非集成) / 18 errors (需 DB) — 17 个新测试文件
- **知识库**: 18 篇 .md / 4 子目录 / 135 chunks
- **LLM**: Claude Sonnet 4.6 主, MiniMax-M2.7 fallback, 无 key 时 `_NullProvider`
- **Web**: 4 endpoints / 3 Tab / dark theme / 零前端依赖
- **CI**: 4 job (lint / unit / integration / coverage)
- **演示**: 3 × 60s 视频 + 1 套端到端 demo
- **文档**: 3 use cases + 1 架构图 + 1 索引页 + 1 README

## 设计原则

1. **扩展, 不重写** — 100% 复用 `RuntimeEngine` / `AgentTemplateRegistry` /
   `MCPServer` / `RAGEngine` / 6 个 LLM Provider. ERP 是用例, 不是新框架.
2. **单一事实源** — `health.py` 同时被 `/healthz` 端点, `make erp-check`
   CLI 和未来 k8s readiness probe 调用.
3. **Lazy resources** — DB pool / LLM provider / RAG engine 都是首次访问
   才创建, 单元测试 0 依赖.
4. **Tests as docs** — 17 个测试文件即文档, 每个测试名解释一个功能点.
5. **真实可跑** — `make erp-run` 在 docker compose 上 60s 内拉起 DB + Web UI.
   不是 PPT, 是真东西.

## 相关文档

- [架构图 (Mermaid)](../architecture/erp_copilot.md) — 模块 + 数据流
- [Multi-Agent 用例](./erp_ai_copilot_multi_agent.md) — Day 11 深入
- [Knowledge Assistant 用例](./erp_knowledge_assistant.md) — Day 7 RAG 深入
- [Video 1 脚本](../videos/01_single_agent_script.md)
- [Video 2 脚本](../videos/02_multi_agent_script.md)
- [Video 3 脚本](../videos/03_rag_script.md)
