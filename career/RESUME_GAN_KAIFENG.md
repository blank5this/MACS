# 甘凯锋 — AI Application Engineer

**Multi-Agent Systems · ERP AI · RAG · Java Backend**

📍 深圳·南山 · 🟢 随时到岗 · 📧 你的邮箱 · 📱 你的手机 · 🔗 github.com/blank5this

---

## 🎯 一句话定位

> 独立设计并落地了 **MACS**（多智能体协作框架，6 LLM Provider / 4 角色 Agent / 5 协作模式 / 326 测试）和基于它构建的 **ERP AI Copilot**（Text2SQL + 知识库 + 库存风险分析），具备从框架、Agent、RAG、SQL 安全、Web Demo 到监控的完整企业 AI 工程能力。

---

## 🏆 核心项目（写在简历第一页 — 拿下面试的就是这两个）

### ① ERP AI Copilot · 企业 AI 助手（2026）
**角色：独立开发者**　|　[🟢 在线 Demo](https://macs-erp-copilot.onrender.com)　|　[Github: MACS/erp/](https://github.com/blank5this/MACS)

基于自研多 Agent 框架 MACS 实现的企业 ERP AI 助手。回答"上个月采购金额多少？"这类业务问题，给出**带引用、可审计、可视化**的答案。

| ✓ Text2SQL | 自然语言 → SQL，4 层安全护栏（AST 白名单 + 关键字黑名单 + 语句类型校验 + 库内只读角色），< 2s 返回 |
| ✓ ERP 知识库 | 18 篇制度 PDF/文档 → 混合检索（char-ngram + BM25 + RRF），每个答案强制引用原文段落 |
| ✓ 库存风险分析 | 多 Agent 协作工作流：Planner → Inventory Analyst → Purchase Specialist → Report Writer → Reviewer |
| ✓ Tool Calling | 7 个内置工具 + 5 个 MCP 工具，LLM 自主选工具 + JSON 解析容错 |
| ✓ Hybrid RAG | char-ngram 解决中文短语命中，BM25 解决近义词，RRF 融合 |
| ✓ 监控 | Prometheus exporter + EventBus，生产可观测 |

**已上线**：Render + Hugging Face Spaces 双部署，全球可访问。

### ② MACS · Multi-Agent Collaboration Stack（2026）
**角色：独立开发者**　|　[Github: blank5this/MACS](https://github.com/blank5this/MACS)　|　⭐ Star + Fork

通用多 Agent 协作 Python 框架。对标 LangGraph / AutoGen 的国产可商用方案。
- **5 协作模式**：Hierarchical · Pipeline · Decentralized · Deep Research · Dynamic Selector
- **4 角色 Agent**：Planner · Executor · Reviewer · ToolAgent — 全部继承 `ReactAgent`，强制 `think → act` 生命周期
- **6 LLM Provider**：Claude · GPT-4o · MiniMax-M2.7 · Qwen · DeepSeek · Zhipu · Hunyuan — 1 行切换
- **7 内置工具**：Calculator / Python Exec / File Ops / RAG / Web Search / Formatter
- **326 个自动化测试** · **8 篇 ADR 架构决策记录** · **5 个生产级 ADR** 含 SQL 安全/混合检索/退避策略
- **5,000+ 行核心代码** · MIT 开源

---

## 💼 工作经历

### 高级 Java 后端工程师 · [你上一家公司]（时间）
- 主导 3 个 Spring Cloud 微服务从 0 到 1 上线，平均 QPS 1,200
- 性能优化：核心接口 P99 从 800ms 降至 95ms（缓存 + 异步化 + SQL 索引）
- 团队协作：Code Review / 设计评审 / 故障复盘机制搭建

### Java 后端工程师 · [你更早的公司]（时间）
- 负责 ERP 系统的采购 / 库存模块，PostgreSQL + MyBatis + Redis
- 业务理解：熟悉供应链、采购流程、库存管理（这也是 MACS 选 ERP 场景的原因）

---

## 🛠️ 技术栈

| 维度 | 掌握 |
|---|---|
| **AI/Agent** | 多 Agent 协作 / ReAct / Tool Calling / 5 协作模式 / RAG / Hybrid Retrieval |
| **LLM** | Claude · GPT-4o · MiniMax · Qwen · DeepSeek · Zhipu · Hunyuan 实战 |
| **AI 工程** | Prompt Engineering · 流式输出 · 引用追踪 · LLM-as-Judge · 退避策略 · Token 控制 |
| **RAG** | BM25 · char-ngram · Embedding · RRF 融合 · Citation Graph |
| **后端** | Python 3.10+ · asyncio · FastAPI · Java 11/17 · Spring Boot · Spring Cloud |
| **数据** | PostgreSQL 16 · Redis · SQLite · SQL 安全护栏 · 4 层 Guardrail |
| **前端** | Gradio · FastAPI 静态页 · React 基础（可读能改）|
| **工程** | Docker · Docker Compose · GitHub Actions CI · pytest 326 测试 · Prometheus · Grafana |
| **方法论** | ADR 架构决策 · 单元测试 · 集成测试 · Adversarial Testing（50+ SQL 注入用例） |

---

## 🎓 教育

**本科 · [你的学校] · 软件工程 / 计算机科学与技术 · 时间**

---

## 📌 关键词索引（让 ATS 容易搜到）

`AI Application Engineer` · `Multi-Agent System` · `ReAct` · `Agent` · `RAG` · `Hybrid Retrieval` · `LangChain` · `LLM Application` · `Enterprise AI` · `AI Copilot` · `Text2SQL` · `ERP` · `FastAPI` · `Python` · `Java` · `Spring Boot` · `PostgreSQL` · `Asyncio` · `Microservice`
