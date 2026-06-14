# 甘凯锋 — AI Application Engineer（优化版）

> **优化原则**：所有"技术名词"用真实项目数据替换；所有"功能描述"用**量化 + 业务影响**替换；"建设中"全部去掉；加 ADR 差异化卖点。

---

## 📋 个人信息

| 项 | 内容 |
|---|---|
| 姓名 | 甘凯锋 |
| 求职方向 | AI Application Engineer / Agent Engineer / AI Backend Engineer |
| 期望地点 | 深圳·南山 |
| 期望薪资 | 15-18K |
| 电话 | 18046830289 |
| 邮箱 | gankaifeng210@gmail.com |
| GitHub | github.com/blank5this/MACS |
| 学历 | 江西水利电力大学 · 计算机科学与技术 · 本科（2021.09 – 2025.06）|
| 英语 | CET-4 |

---

## 🎯 一句话定位

> 独立从 0 到 1 设计并落地 **MACS 多 Agent 协作框架**（6 LLM / 5 协作模式 / 4 角色 Agent / 326 测试 / 8 ADR）和基于它构建的 **ERP AI Copilot**（Text2SQL + 知识库 + 库存风险分析），具备从 Agent 框架、混合 RAG、SQL 安全、Web 部署到监控的完整企业 AI 工程能力。

---

## 🏆 核心亮点（放最前面 — HR 5 秒扫到）

1. ✓ **独立开发 MACS 多智能体协作框架**（326 测试 / 5 协作模式 / 4 角色 Agent / 6 LLM Provider / 8 篇 ADR / ~13K 行核心代码 / MIT 开源）
2. ✓ **基于 MACS 实现 ERP AI Copilot**（Text2SQL + 知识库 + 库存风险分析），**已上线 Render + Hugging Face Spaces**
3. ✓ **4 层 SQL 安全护栏**（AST 白名单 + 关键字黑名单 + 语句类型校验 + 库内只读角色），50+ 对抗注入测试全部拦截
4. ✓ **混合检索 RAG**（char-ngram + BM25 + RRF 融合）+ 强制引用溯源
5. ✓ **5 协作模式**：Hierarchical / Pipeline / Decentralized / Deep Research / Dynamic Selector — 全部基于统一的 `ReactAgent` 强制 think→act 生命周期
6. ✓ **企业 ERP 系统 + MySQL → PostgreSQL 迁移** 实战（300+ 字段适配、14 个业务实体迁移）

---

## 🛠️ 技术栈

**AI / Agent**
- 框架：自研 MACS（Multi-Agent Collaboration Stack）· 5 协作模式 · ReactAgent 严格 think→act 基类
- LLM 接入：Claude · GPT-4o · MiniMax · Qwen · DeepSeek · Zhipu · Hunyuan（6+1 provider，1 行切换）
- 检索：BM25 · char-ngram TF-IDF · RRF 融合 · Citation Graph
- 工程化：指数退避 + jitter · 对话内存 cap · 流式输出 · 单元测试 326 · Adversarial SQL 注入测试 50+

**后端 / 数据**
- Python 3.10+ · asyncio · FastAPI · pytest · ruff · mypy
- Java 11/17 · Spring Boot · Spring Cloud · 多线程
- PostgreSQL 16 · MySQL · Redis · SQLite

**前端 / 部署**
- Gradio · FastAPI 静态页 · React 基础
- Docker · Docker Compose · GitHub Actions CI · Render · Hugging Face Spaces · Prometheus

---

## 🚀 项目经历

### ① ERP AI Copilot — 企业 AI 助手（**已上线**）⭐
**角色：独立开发者**　|　[🟢 在线 Demo](https://macs-erp-copilot.onrender.com)　|　[Github: MACS/erp/](https://github.com/blank5this/MACS)

基于自研多 Agent 框架 MACS 实现的企业 ERP AI 助手。回答"上个月采购金额多少？"这类业务问题，给出**带引用、可审计、可视化**的答案。**已双部署上线**（Render + HF Spaces）。

- **Text2SQL 智能查询** — 自然语言 → SQL，4 层安全护栏（AST 白名单 + 关键字黑名单 + 语句类型校验 + 库内只读角色），50+ 对抗注入测试（`DROP TABLE` / `'; DROP --` / `pg_catalog` / `UNION SELECT` 等）**全部拦截**
- **ERP 知识库** — 18 篇采购 / 库存 / 审批制度文档，混合检索（char-ngram + BM25 + RRF），**强制引用原文段落**到答案中
- **库存风险分析**（多 Agent 工作流）— Planner 拆解 → Inventory Analyst 算速度/库存 → Purchase Specialist 算补货量 → Report Writer 合成 → Reviewer 3 维评分
- **MCP 工具 × 5**（库存 / 销售 / 采购 / 价格 / 周转） · **7 内置工具**（Calculator / Python Exec / File Ops / RAG / Web Search / Formatter）
- **混合 RAG** — char-ngram 解决中文短语字面匹配，BM25 兜底语义，Embedding 可选，RRF 加权融合
- **监控可观测** — Prometheus exporter + EventBus，Token 预算、请求耗时、Tool Calling 失败率

### ② MACS — Multi-Agent Collaboration Stack
**角色：独立开发者**　|　[Github: blank5this/MACS](https://github.com/blank5this/MACS)　|　[8 篇 ADR 架构决策](https://github.com/blank5this/MACS/tree/main/docs/architecture)

通用多智能体协作 Python 框架。**不是用 LangChain 拼的**——是独立设计基类、协作模式、消息路由、记忆系统、RAG、SQL 护栏、Prometheus 监控的生产级框架。

**5 协作模式**（按业务场景选）
- `Hierarchical` — Planner 拆解 + N 个 Executor 并行 + Reviewer 评分（适合 ERP 库存风险分析）
- `Pipeline` — 阶段链式转换（适合 ETL / 数据清洗）
- `Decentralized` — 所有 Agent 并行 propose + 集体 vote（适合多源决策）
- `Deep Research` — 多 query 并发检索 + 综合（适合研究类问题）
- `Dynamic Selector` — 运行时根据任务自动选模式

**4 角色 Agent**（全部继承 `ReactAgent`，强制 `think → act` 生命周期）
- `PlannerAgent` — 任务分解 / replan / propose
- `ExecutorAgent` — 子任务执行，proactive RAG 自动注入 + Tool 调用
- `ReviewerAgent` — 3 维评分（completeness / correctness / relevance）+ Citation Tracker
- `ToolAgent` — LLM 自主选工具 + JSON 容错解析

**6 LLM Provider** — Claude / OpenAI / MiniMax / Qwen / DeepSeek / Zhipu / Hunyuan，统一接口，1 行切换

**核心架构决策**（[ADR 列表](docs/architecture/ADR_INDEX.md)）
- ADR-001 异步 Python — I/O 密集负载用协程不用线程
- ADR-003 **4 层 SQL 安全护栏** — defense in depth
- ADR-004 **混合检索** — 不同检索方法失效模式不同，混合分摊
- ADR-005 退避 + jitter — 防雪崩
- ADR-006 对话 cap=100 — 防内存泄漏
- ADR-007 库内只读 role — defense in depth 第四层
- ADR-008 Proactive RAG — 1 跳 vs 2 跳

**质量**：326 个自动化测试 · CI 全绿 · `pytest` 75s · MIT 开源

### ③ 企业智能数据采集平台
**角色：核心开发**　|　Java · Spring Boot · PostgreSQL · Redis · 多线程

- 接入 **10+ 企业客户**异构数据源，累计采集**数十万级业务单据**
- 利用 AI 自动识别表结构 / 字段关系 / 业务对象，**自动生成采集任务配置**
- 多线程并行采集架构 + 增量同步 + 断点续传 + 异常恢复
- 显著提升采集效率与数据同步稳定性

---

## 💼 工作经历

### 盛世浩淼 · Java 开发工程师 · 2025.09 - 至今

**ERP 业务系统开发**
- 负责企业 ERP 系统需求分析 / 功能设计 / 后端实现
- 涉及**采购管理 · 库存管理 · 财务管理 · 人力资源**4 大模块
- 推动业务流程优化与系统稳定性提升

**MySQL → PostgreSQL 迁移项目**（性能与一致性升级）
- 完成 **300+ 字段**适配、**14 个业务实体**迁移
- 修复 SQL 兼容问题（MySQL 特有语法 → PostgreSQL 标准）
- 优化查询性能，**保障业务平稳切换**（无停机）

**企业数据采集平台**
- 接入 10+ 企业客户，累计采集数十万级业务单据
- AI 自动识别表结构 + 自动生成采集任务
- 多线程并行 + 增量同步 + 断点续传

---

## 🎓 教育背景

**江西水利电力大学** · 计算机科学与技术 · 本科 · 全日制 · 2021.09 - 2025.06

---

## 📌 个人总结

- **AI 转型 + 工程派**：5 年 Java 后端基本盘，半年转型 AI 应用，**不靠调 API 混日子**——能写 SQL 安全护栏、消息总线、Prometheus 监控、对话内存管理、Prompt 容错解析
- **从 0 到 1 落地能力**：独立完成 13,000 行核心代码的 MACS 框架 + ERP AI Copilot 双部署上线
- **架构意识**：8 篇 ADR 记录每个非显然决策的"为什么"（不是"是什么"），可面试深挖
- **协作与落地**：能写代码也能交付，配合产品 / 前端 / 测试推动项目完成

---

## 🔗 关键词（ATS 友好）

`AI Application Engineer` · `Multi-Agent System` · `Agent` · `ReAct` · `RAG` · `Hybrid Retrieval` · `Text2SQL` · `LLM Application` · `Enterprise AI` · `AI Copilot` · `LangChain` · `Workflow` · `ERP` · `FastAPI` · `Python` · `Java` · `Spring Boot` · `PostgreSQL` · `asyncio` · `微服务`
