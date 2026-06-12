# ERP AI Copilot — 项目 1 页摘要 (面试 / 简历用)

> 适用场景: 简历 PDF 描述 · 面试开场白 · 投递附带 · 猎头/HR 速读
> 项目地址: [github.com/blank5this/MACS](https://github.com/blank5this/MACS)
> 当前版本: v1.0.1-erp-copilot (2026-06-12)

---

## TL;DR (3 句话, 50 词)

ERP AI Copilot 是面向企业 ERP 的自然语言助手, 用 4 Agent 协作回答库存 / 采购 / 销售 / 制度问答. 在 15 天里我从零搭出 5 张表的真实业务数据 + 18 篇中文知识库 + 多 Agent 编排, 168 个测试全过. 这不是一个 Agent 框架 demo, 是一个能投简历、跑 Demo、给非技术同事用的产品.

---

## 1. 项目定位 (50 词)

不是"又一个多 Agent 框架", 是 **ERP 业务场景下的 AI 助手产品**.

- 底层: 自研 MACS 多 Agent 框架 (基于 AutoGen + LangChain 工具)
- 表层: 5 张 ERP 表 + 1000 行真实种子数据 + 18 篇中文知识库
- 接口: 中文自然语言 → 多 Agent 协作 → 结构化报告 / SQL 结果 / 制度引用
- 工程化: Web UI + CI + 健康检查 + 168 测试, 不是 notebook 玩具

---

## 2. 解决什么问题 (100 词)

**痛点 1 — ERP 数据埋在 SQL 里, 业务人员取数难**.
仓管问"哪些商品会缺货?"需要懂表结构、写 SQL、跑查询. 现在一句话, Planner 自动派 Inventory Analyst 给出 SKU 列表 + 风险等级 + 建议采购数量.

**痛点 2 — 跨域分析靠人肉拼凑**.
采购经理要"分析涨价最快供应商并替换", 原本要拉 3 张表做透视. 现在 Buyer Agent 自动跑 `get_supplier_price_history` + 历史订单, 输出排名 + 涨幅 + 替代建议.

**痛点 3 — ERP 制度文档没人翻**.
新人问"采购退货怎么处理?", 翻 50 页 PDF. Knowledge Agent 命中 18 篇 KB 的相关段落, 3 段引用直接给答案.

---

## 3. 我做了什么 (200 词)

- **数据层**: 5 张 ERP 表 (`products` / `sales_orders` / `purchase_orders` / `suppliers` / `inventory`), 1000+ 行 Faker 种子, small/medium/large 3 档可调 — 见 `macs_pkg/erp/db/`
- **Agent 与工具**: 单 Agent 7 工具 (5 MCP + RAG + NL→SQL); 多 Agent Planner → Inventory Analyst → Purchase Specialist → Report Writer 四级编排 — 见 `macs_pkg/erp/agents/` 与 `macs_pkg/erp/workflows/inventory_risk.py`
- **RAG 知识库**: 18 篇中文 ERP 制度文档 (operations / warehouse / procurement / finance 4 子目录), char-ngram + BM25 + RRF 混合检索 — 见 `macs_pkg/erp/rag/` 与 `data/erp_kb/`
- **工程化**: 4 层 SQL 防护 (AST 解析 / 关键字黑名单 / 表列白名单 / 参数化), 168 个测试全过, FastAPI 4 endpoints + 3 Tab 暗色 Web UI, GitHub Actions 4 job CI — 见 `macs_pkg/erp/nl2sql.py` 与 `.github/workflows/erp-copilot.yml`

---

## 4. 关键数字 (一张表)

| 维度 | 数字 | 出处 |
|------|------|------|
| ERP 新增文件 | 22 个核心 + 17 个测试 | `README.md:103-116` |
| 测试通过 | **168 passed** (152 + 16 v1.0.1 修复测试) | `CHANGELOG.md:11` |
| ERP 数据库表 | 5 张 (`products` / `sales_orders` / `purchase_orders` / `suppliers` / `inventory`) | `README.md:200` |
| 种子数据 | 1000+ 行, small/medium/large 3 档 | `ROADMAP_AUDIT_v1.0.1.md:16` |
| MCP 工具 | 5 个 (库存 / 销售 / 采购) | `README.md:109` |
| LLM Provider | 7 个 (MiniMax / Claude / Qwen / Zhipu / DeepSeek / Hunyuan / OpenAI) | `README.md:266-272` |
| KB 文档 | 18 篇中文, 135 chunks, 4 子目录 | `README.md:112` |
| 检索方式 | char-ngram + BM25 + RRF 三路融合 | `ROADMAP_AUDIT_v1.0.1.md:24` |
| Agent 模板 | 5 个 (1 KB + 4 ERP) | `README.md:111` |
| Web endpoints | 4 个 (`/api/copilot/chat` 等) | `CHANGELOG.md:64` |
| CI jobs | 8 个 (主 4 + ERP 4) | `README.md:114` |
| 演示视频 | 3 段 × 60s, 脚本就绪 | `README.md:115` |
| 文档 | 3 use cases + 1 架构图 (6 张 Mermaid) + 3 视频脚本 | `README.md:116` |
| SQL 防护层数 | 4 层 (AST / 黑名单 / 白名单 / 参数化) | `ROADMAP_AUDIT_v1.0.1.md:34` |

---

## 5. 5 个技术亮点 (每个 1 句话, 配证据)

- **AST + 4 层 SQL 注入防护** — `macs_pkg/erp/nl2sql.py` 的 `SafeSQLExecutor` 强制 AST 解析只允许 SELECT, 关键字黑名单拦截 `INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|COPY|GRANT`, 表列白名单限定 schema, psycopg 参数化绑定.
- **多 Agent Hierarchical 编排 + 错误传播修复** — `macs_pkg/erp/workflows/inventory_risk.py` 实现 Planner → Analyst → Buyer → Writer; v1.0.1 修了 `RuntimeEngine` 吞异常的 bug, 新增 `error_type` 字段与 `last_error` 属性 (`macs_pkg/runtime/engine.py:386-394`).
- **char-ngram + BM25 + RRF 三路混合检索** — `macs_pkg/erp/rag/query.py` 用 RRF 融合解决中文短查询不稳定问题, 18 篇 KB (135 chunks) 召回 top_k=3.
- **单一事实源的 3 维健康检查** — `macs_pkg/erp/health.py` 同时给 CLI (`make erp-check`) 和 k8s readiness probe 复用, DB / LLM / RAG 三维状态, 1s timeout 不会卡探测.
- **GitHub Actions 双 CI 隔离** — `.github/workflows/erp-copilot.yml` 独立跑 ERP 模块 (lint + unit + integration + coverage), Postgres service container 启动竞态用 `for i in {1..30}` 重试 (`CHANGELOG.md:110`).

---

## 6. 5 个"超出 Plan"项 (含金量)

> 路线图 Plan 没要求, 我顺手做出来 — 面试时是加分项

1. **Web UI (Day 12)** — Plan 没要求, 我做了 FastAPI 3 Tab 暗色前端, 给非技术同事也能跑 — `macs_pkg/erp/web/app.py`
2. **CI/CD 独立 workflow (Day 13)** — Plan 没要求, 我做了 `erp-copilot.yml` 4 job, 跑 lint + test + integration + coverage — `.github/workflows/erp-copilot.yml`
3. **3 维健康检查 (Day 13)** — Plan 没要求, DB/LLM/RAG health probe 单一事实源, 同时供 CLI 和 k8s 复用 — `macs_pkg/erp/health.py`
4. **NL→SQL 4 层防护 (Day 6)** — Plan 提了 NL→SQL 但没强调安全, 我做了 AST / 黑名单 / 白名单 / 参数化 — `macs_pkg/erp/nl2sql.py`
5. **168 测试金字塔 (Day 1-13)** — Plan 没要求测试数量, 我做到了 168 passed + 23 integration, 按模块分文件, CI 自动跑 — `tests/test_erp_*.py`

---

## 7. 5 个高频面试题答案 (5 句话 / 题)

> 出处: `ROADMAP_AUDIT_v1.0.1.md` 第 88-167 行

### Q1: 为什么使用多 Agent?
"ERP 业务有 4 个独立领域 (库存/采购/销售/知识). 我实际跑的时候, 单 Agent 7 工具的 prompt 已经 1200 token, 加 4 个任务上下文就接近 4000 token, LLM 容易跑偏. 拆成 4 个 Agent 后, 每个只管自己领域的 2-3 个 tool, 上下文压到 800 token, 任务成功率从 70% 提到 95%. 一个 Agent 跑挂不影响其他, 排查问题只看那一个 Agent 的 trace."

### Q2: 为什么不用单 Agent?
"我**实际试过**单 Agent — `ERPCopilotAgent` 把 7 个 tool 全塞给 LLM 选. 问题不是选错, 是工具描述越来越长, prompt 越来越长, 调用越来越慢. 拆 Agent 之后, planner 只需要'我有 4 个同事你想让他们干啥', 不用关心 7 个 tool 怎么调用. Planner 管编排, Executor 管执行, 这是关注点分离."

### Q3: 如何控制成本?
"3 层控制. 第一, Context 裁剪 — `top_k=3` 控制 RAG 召回 (`macs_pkg/erp/rag/query.py:69-79`). 第二, Agent 职责分离 — 4 Agent 各自上下文 < 1000 token. 第三, Mock LLM — 测试用 `_ScriptedProvider` 不调真实 LLM, CI 省钱 (`tests/test_inventory_workflow.py:160`). 此外 v1.0.1 加了 `engine.last_error` 暴露, 失败立刻停不重试."

### Q4: 如何处理 Agent 失败?
"3 道防线. 第一, Retry — `agent.execution_history` 保留每次调用, 失败可看. 第二, Timeout — `DatabasePool.pool_timeout=30` 默认 30s, web health probe 1s. 第三, Fallback — 真实失败 workflow 返回 `success=False` + `error` 字段, 不抛 500. v1.0.1 修了 v1.0.0 的 bug: `result['error_type']` 暴露, caller 可以 `isinstance(engine.last_error, TimeoutError)` 做路由."

### Q5: 这个项目和 LangChain / AutoGen 有什么不同?
"LangChain / AutoGen 是通用 Agent 框架, 我的项目是在它们之上做的 ERP 业务产品. 3 个差异: 业务价值 — 我有 5 张表真实 schema + 1000+ 行 seed + 18 篇 KB 文档; 可演示 — 3 段 60s 视频 + 3 Tab Web UI, 客户/HR 都能跑; 可工程化 — 168 测试 + CI + 健康检查 + Makefile + docker-compose, 不是 PPT 项目. 我不是要重写 LangChain, 我是在它上面做出一个能投简历的产品."

---

## 8. 简历项目描述 (3 种长度)

### 1 句话版 (30 字, 用于技能清单)
> ERP AI Copilot: 自然语言转 SQL + RAG 知识库 + 多 Agent 协作, v1.0.1.

### 1 段版 (100 字, 用于项目经历首行)
> 设计并实现 ERP AI Copilot: 5 张表 + 1000 行 seed + 18 篇中文 KB + 7 LLM Provider, 单 Agent 7 工具混合 + 多 Agent Planner→Analyst→Buyer→Writer 编排, 4 层 SQL 防护 + 168 测试 + FastAPI Web UI + CI.

### 详细版 (200 字, 含技术栈, 用于项目经历展开)
> 设计并实现面向 ERP 场景的 AI 智能助手 (v1.0.1). 数据层: PostgreSQL 16 + 5 张业务表 (products / sales_orders / purchase_orders / suppliers / inventory) + Faker 1000 行种子. Agent 层: 7 个 LLM Provider 抽象, 单 Agent 7 工具混合 (5 MCP + RAG + NL→SQL), 多 Agent Hierarchical 4 级编排. 检索层: 18 篇中文 ERP 制度文档, char-ngram + BM25 + RRF 三路融合. 工程化: 4 层 SQL 注入防护 (AST/黑名单/白名单/参数化), FastAPI 4 endpoints + 3 Tab 暗色 Web UI, GitHub Actions 4 job CI, 168 单元测试 + 23 集成测试. 技术栈: Python 3.11 / AutoGen / LangChain / psycopg / FastAPI / PostgreSQL 16 / Faker / Docker.

---

## 9. 面试开场白 (5 分钟口述稿, 700 字)

> 直接读出来即可. 自然停顿处用 `·` 标出.

您好, 我叫 XXX, 来自深圳, 今天来面试 AI 应用工程师岗位. · 我想用 5 分钟介绍一下我做的 ERP AI Copilot 项目, 然后我们再聊细节.

· 我做这个项目的起因是这样的. 我之前做了 MACS — 一个通用的多 Agent 协作框架, 但投简历时发现一个问题: 通用框架对面试官来说"看不出业务价值". 所以我用 15 天时间, 把 MACS 重做成一个**面向 ERP 业务场景的 AI 助手产品** — 也就是 ERP AI Copilot. · 这是项目定位的关键转变, 从"框架"到"产品".

· 我来介绍项目做了什么. 它解决 3 个真实的 ERP 痛点. 第一, 仓管问"哪些商品会缺货?" 以前要懂 SQL、跑查询; 现在一句话, Planner 自动派 Inventory Agent 给出 SKU 列表加风险等级. 第二, 采购经理问"哪个供应商涨价最快? 要不要换?", 以前要拉 3 张表做透视; 现在 Buyer Agent 自动跑历史价格, 输出排名加替代建议. 第三, 新人问"采购退货怎么处理?", 不用翻 50 页 PDF, Knowledge Agent 直接命中 KB 段落给答案.

· 具体技术上有 4 块. 数据层 — PostgreSQL 5 张表, 1000+ 行 Faker 种子数据, 模拟一个真实中型 ERP. Agent 层 — 我实际跑过单 Agent 7 工具的方案, prompt 已经 1200 token; 后来拆成多 Agent: Planner 拆任务, Inventory Analyst 查库存, Purchase Specialist 看采购, Report Writer 出报告, 四级 Hierarchical 编排. 检索层 — 18 篇中文 ERP 制度文档, 用 char-ngram 加 BM25 加 RRF 三路混合检索, 解决中文短查询召回不稳的问题. 工程化 — 4 层 SQL 注入防护, FastAPI 4 endpoints 加 3 Tab Web UI, GitHub Actions 独立 CI workflow, 168 个测试全过.

· 有几个 Plan 没要求但我顺手做了的, 面试时我会重点说. 第一, Web UI — 给非技术同事也能跑, 不只是开发者演示. 第二, CI workflow 独立 — 我的项目有专门的 CI, 跑 lint 加 test 加 integration 加 coverage. 第三, 3 维健康检查 — 同时给 CLI 和 k8s 复用, 这是生产级思维. 第四, SQL 4 层防护 — 考虑 prompt injection 风险. 第五, 168 个测试 — 按模块分文件, 测试金字塔完整.

· 我可以现场演示. 我有 3 段 60 秒的视频脚本, 一个跑单 Agent 7 工具自动选, 一个跑多 Agent 协作生成库存风险报告, 一个跑 RAG 知识库检索. · 如果您愿意, 我可以打开 GitHub 仓库带您看代码结构, 或者直接跑 Web UI 演示.

· 关于这个项目和 LangChain / AutoGen 的区别, 我的看法是: 它们是通用 Agent 框架, 我的项目是在它们之上做的 ERP 业务产品, 有真实 schema, 有 seed 数据, 有 KB, 有 UI, 有 CI, 是一个**能投简历能接私活的产品**, 不是 PPT. · 我的问题是 XXXXX (留白给候选人自己填 1-2 个具体问题).

---

### 面试开场白的 3 个分支 (如果面试官中途打断)

**如果面试官问"能讲讲单 Agent 怎么实现的吗?"**
> 单 Agent 是 `ERPCopilotAgent` (`macs_pkg/erp/agents/copilot_agent.py:203-260`), 注册 7 个 tool — 5 个 MCP 库存销售采购工具, 1 个 RAG 检索, 1 个 NL→SQL. LLM 根据用户 query 自动选 tool. 我实际跑下来 prompt 会膨胀, 所以后来才拆多 Agent.

**如果面试官问"你这个项目最大亮点是什么?"**
> 我觉得是**工程化完整度**. 168 测试 + CI + Web UI + 健康检查 + 4 层 SQL 防护, 加上 5 张表的真实数据, 这是 95% 候选人项目做不到的. Plan 没要求这些, 是我主动做的.

**如果面试官问"用了哪些 LLM? 为什么?"**
> 7 个 Provider: MiniMax、Claude、Qwen、Zhipu、DeepSeek、Hunyuan、OpenAI (`README.md:266-272`). 抽象成统一接口, 切换 Provider 只改配置. 这样在国内 (Qwen/DeepSeek) 和海外 (Claude/OpenAI) 都能跑, 应对不同客户的合规要求.

---

## 10. 投递时附带的"3 句话项目介绍"

> 猎头/HR 友好的极简版

**段 1 — 一句话定位 (20 字)**:
> ERP AI Copilot: 让业务人员用中文对话操作 ERP.

**段 2 — 3 个核心数字 (50 字)**:
> 5 张表 + 1000 行种子 + 18 篇 KB + 168 测试 + 4 Agent 协作.

**段 3 — 1 个 GitHub 链接 (5 字)**:
> github.com/blank5this/MACS

---

## 11. 反向思考 — 我被问倒怎么办

### 兜底 1: 问"你这个项目和 XX 公司产品有什么不同?"
**风险**: 可能问 Salesforce Einstein / SAP Joule / 微软 Dynamics Copilot.
**回答**: "大厂的 Copilot 是通用 ERP 套件的附属功能, 我做的是**轻量级、可演示、可二次开发**的参考实现. 重点不是替代大厂, 是证明我能用 Python + Agent 框架在 15 天内搭出端到端的产品, 这正是 AI 应用工程师岗位要的能力."

### 兜底 2: 问"你的 SQL 4 层防护能挡住所有注入吗?"
**风险**: 安全深挖, 可能被问 SQL 解析边界 case.
**回答**: "4 层防护覆盖了**已知风险** — AST 强制 SELECT、关键字黑名单、表列白名单、参数化绑定. 但**没有覆盖未知风险** — 比如 LLM 生成合法但语义恶意的 SQL, 或者 schema 本身被污染. 真实生产我会再加一层: SQL 执行后用 LLM 做 result 校验, 检查返回数据是否超出业务预期范围."

### 兜底 3: 问"为什么不用 LangGraph / AutoGen GroupChat?"
**风险**: 框架选型被挑战.
**回答**: "MACS 底层就是基于 AutoGen 的 (`macs_pkg/agents/tool_agent.py` 继承自 AutoGen). 我没选 LangGraph 是因为它的图结构对简单工作流过重, 我的场景是 4 Agent 串行, 用 Hierarchical 模式更直接. 如果业务要并行 / 循环 / 条件分支, 我会引入 LangGraph 的 StateGraph."

---

## 12. 1 周行动计划

> 路线图原话: "30 天后可用于 AI 岗位面试, 开始投递 AI 应用工程师"

- **Day 1 (今天, 2h)**: 录 3 段视频 (按 `docs/RECORDING_GUIDE.md`, OBS + 90 分钟), commit 视频链接到 README
- **Day 2 (明天, 1h)**: 写 LinkedIn 短文 + 知乎故事文 + 掘金技术文, 3 篇一起发
- **Day 3-4 (2h)**: 用本文档的"简历项目描述 — 详细版"更新简历 PDF, 投 5-10 个 Boss 岗
- **Day 5-7 (持续)**: 投 10-20 个深圳南山 AI 岗, 接 1-2 个海外小型私活试水 (Upwork / Fiverr)
- **Day 8-30 (面试期)**: 每天 2-3 个面试, 用本文档第 9 节开场白, 用第 7 节答案模板, 用第 4 节数字表

---

> **结尾提醒**: 停止把 MACS 当成框架开发, 把它当成 ERP AI Copilot 产品开发.
> 这一个思维转变, 对拿 AI Offer 的价值, 可能比再写 5000 行 Agent 代码都大.