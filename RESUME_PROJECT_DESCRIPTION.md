# 简历项目描述 — ERP AI Copilot (3 种长度)

> 项目地址: https://github.com/blank5this/MACS
> 当前版本: v1.0.1-erp-copilot (2026-06-12)
> 技术栈: Python 3.11 · AutoGen · LangChain · psycopg · FastAPI · PostgreSQL 16 · Faker · Docker

---

## 版本 1: 1 句话版 (30 字)

> 用于简历"技能清单"或"项目一行索引"

**ERP AI Copilot**: 自然语言转 SQL + RAG 知识库 + 多 Agent 协作, v1.0.1.

---

## 版本 2: 1 段版 (100 字)

> 用于简历"项目经历"第一行, 让 HR 一眼看懂规模与价值

设计并实现 ERP AI Copilot: 5 张表 + 1000 行 seed + 18 篇中文 KB + 7 LLM Provider, 单 Agent 7 工具混合 + 多 Agent Planner→Analyst→Buyer→Writer 编排, 4 层 SQL 防护 + 168 测试 + FastAPI Web UI + CI.

---

## 版本 3: 详细版 (200 字, 含技术栈)

> 用于简历"项目经历"展开, 给技术面试官看深度

设计并实现面向 ERP 场景的 AI 智能助手 (v1.0.1). 数据层: PostgreSQL 16 + 5 张业务表 (products / sales_orders / purchase_orders / suppliers / inventory) + Faker 1000 行种子. Agent 层: 7 个 LLM Provider 抽象, 单 Agent 7 工具混合 (5 MCP + RAG + NL→SQL), 多 Agent Hierarchical 4 级编排. 检索层: 18 篇中文 ERP 制度文档, char-ngram + BM25 + RRF 三路融合. 工程化: 4 层 SQL 注入防护 (AST/黑名单/白名单/参数化), FastAPI 4 endpoints + 3 Tab 暗色 Web UI, GitHub Actions 4 job CI, 168 单元测试 + 23 集成测试. 技术栈: Python 3.11 / AutoGen / LangChain / psycopg / FastAPI / PostgreSQL 16 / Faker / Docker.

---

## 使用建议

- **Boss 直聘 / 拉勾**: 用版本 1 (1 句话), 配合招聘方 JD 微调关键词
- **LinkedIn / 猎头邮件**: 用版本 2 (1 段), 强调规模与可量化产出
- **简历 PDF 项目经历**: 用版本 3 (详细版), 配项目 GitHub 链接 + 1 张架构图缩略
- **面试开场白**: 不要照抄简历描述, 用 `INTERVIEW_OPENING.md` 的口述稿

---

## 自查清单 (投递前过一遍)

- [ ] 版本 3 里所有数字和当前代码对得上 (168 测试 / 5 表 / 18 KB)
- [ ] 技术栈里出现的库都能在 requirements.txt 找到
- [ ] GitHub 链接能打开, README 首页能看到 ERP AI Copilot 标题
- [ ] 没有用 emoji (HR 系统和 ATS 解析有时会乱码)
- [ ] 没有用"负责 / 参与"这种被动动词 (改用"设计并实现 / 拆解 / 编排 / 修复")
- [ ] 项目时间标注 2026-04 ~ 2026-06 (Day 1 ~ Day 15 节奏)