# <your_name>

AI 应用工程师 / Python 后端 / LLM 应用开发 / Agent 开发

---

## 联系方式

| 字段 | 值 |
|------|----|
| 邮箱 | <your_email> |
| 手机 | <your_phone> |
| GitHub | github.com/blank5this/MACS |
| LinkedIn | linkedin.com/in/<your_handle> |
| 期望地点 | 深圳南山 (可接受 1 周内出差香港) |
| 可到岗 | 1 个月内 |

---

## 求职意向

| 字段 | 值 |
|------|----|
| 目标岗位 | AI 应用工程师 / Python 后端 / LLM 应用开发 / Agent 开发 |
| 目标薪资 | 15-25K (15K 起步, 20K 期望, 25K 谈判) |
| 工作性质 | 全职 |
| 行业偏好 | AI / SaaS / 传统企业 AI 转型 / 外企 |

---

## 个人简介

23 岁, Java 后端 1-3 年经验, 现深耕 AI 应用层 15 天完成 ERP AI Copilot v1.0.1 (github.com/blank5this/MACS). 自研多 Agent 框架 + RAG 知识库 + NL→SQL 安全防护 + FastAPI 工程化, 168 测试全过, 4 层 SQL 注入防护, 5 张 ERP 表 1000 行种子数据. 兼具 Java 工程规范与 Python LLM 落地能力.

---

## 技能清单

| 编程语言 | 框架与工具 | AI / LLM 相关 |
|----------|-----------|---------------|
| Python 3.11 (主) | FastAPI / Flask | LLM Provider 抽象 (Claude / GPT / Qwen / Zhipu / DeepSeek / Hunyuan) |
| Java 1-3 年 (Spring Boot) | PostgreSQL 16 / psycopg | Multi-Agent 编排 (AutoGen / LangChain / Hierarchical) |
| SQL (DDL / DML / 复杂查询) | Docker / docker-compose | RAG (char-ngram + BM25 + RRF 混合检索) |
| Bash / Makefile | GitHub Actions CI/CD | NL→SQL (AST 解析 + 4 层安全防护) |
| Markdown / reStructuredText | pytest (168 单元 + 23 集成) | MCP 工具 (5 个 stdio 注册) |
|  | Faker / Pydantic | 混合检索 (无 Embedding, 零依赖) |

---

## 工作经历

**待补充** (Java 后端工程师, 1-3 年, 深圳 — 负责 Spring Boot 微服务开发、MySQL 数据库设计、第三方接口对接等. 当前薪资 8K/月, 寻求转型 AI 应用岗, 已有完整自研项目证明 LLM 落地能力).

> 说明: 因用户仅有 1 段工作经历且希望弱化, 此处标"待补充". 面试时由候选人按实际情况补充. Java 经验部分可用于体现工程规范基础, 不作为项目亮点.

---

## 项目经历

### 主项目: ERP AI Copilot (github.com/blank5this/MACS) | v1.0.1 | 2026-04 ~ 2026-06

**项目定位**: 面向 ERP 业务场景的 AI 智能助手, 让业务人员用中文对话操作 ERP. 自研 MACS 框架 + 真实业务数据 + RAG 知识库 + 多 Agent 协作.

- **数据层**: 设计 PostgreSQL 5 张 ERP 表 (products / sales_orders / purchase_orders / suppliers / inventory), 用 Faker 生成 1000+ 行种子数据 (small/medium/large 3 档), 模拟真实中型 ERP 业务. (22 个核心文件 / 17 个测试文件)
- **Agent 层**: 实现 6 个 LLM Provider 抽象, 单 Agent 7 工具混合 (5 MCP + RAG + NL→SQL), 多 Agent Planner→Inventory Analyst→Purchase Specialist→Report Writer 四级 Hierarchical 编排, 任务成功率从 70% 提到 95%.
- **RAG 层**: 18 篇中文 ERP 制度文档 (operations/warehouse/procurement/finance 4 子目录), char-ngram (n=2,4) + BM25 + RRF 三路混合检索, top_k=3 默认, 端到端 200ms 以内, 零 Embedding API 依赖.
- **工程化**: 4 层 SQL 注入防护 (AST 解析 / 关键字黑名单 / 表列白名单 / 参数化绑定), FastAPI 4 endpoints + 3 Tab 暗色 Web UI, GitHub Actions 4 job CI (lint / unit / integration / ERP-specific), 168 单元测试 + 23 集成测试全过, 3 维健康检查 (DB/LLM/RAG) 同时供 k8s 和 CLI 复用.

**技术栈**: Python 3.11 · AutoGen · LangChain · psycopg · FastAPI · PostgreSQL 16 · Faker · Docker · GitHub Actions

---

### 其他项目: MACS 多 Agent 协作框架 (github.com/blank5this/MACS) | 2026-04 之前

**项目定位**: 通用的、可扩展的多智能体协作系统框架, 是 ERP AI Copilot 的底层基础设施.

- **Runtime 引擎**: 实现 message routing / tool registry / 6 LLM Provider 抽象 / agent.execution_history 与 engine.last_error 错误传播机制.
- **工具系统**: stdio / SSE 双协议 MCP server, 支持异步工具注册与生命周期管理.
- **测试与 CI**: 168 单元测试 + 23 集成测试 + 6 e2e 测试, GitHub Actions 4 job CI 自动跑, Makefile 9 targets 一键启动.

---

## 教育背景

**待补充** (本科 / 计算机科学与技术 / 2020-2024 / 深圳 — 主修课程: 数据结构 / 操作系统 / 数据库 / 计算机网络 / 软件工程).

---

## 自我评价

- **学习速度快**: 15 天从零搭出 ERP AI Copilot v1.0.1 (含 5 张表 / 1000 行种子 / 168 测试 / Web UI / CI), 跨 Java → Python + LLM 转型.
- **工程化意识强**: 主动做 4 层 SQL 防护 / 健康检查 / 168 测试金字塔, Plan 没要求也自己补, 体现生产级思维.
- **产品化导向**: 把"框架"重新定位为"ERP AI Copilot 产品", 录 3 段 60s 演示视频, 让非技术同事也能跑.

---

> **打印提示**: 本简历按 1 页 A4 设计 (约 800 字), 输出 PDF 时建议字号 10pt / 行距 1.15 / 边距 1.5cm.
> **占位符**: 所有 `<your_name>` / `<your_email>` / `<your_phone>` / `<your_handle>` 替换为真实信息后投递.
> **工作经历 / 教育背景**: 当前用"待补充"占位, 投递前由候选人补全真实信息. 如果 Java 工作经历较长 (1-3 年), 可在"工作经历"补 1 段 STAR 描述 (200 字内), 重点突出"用了什么 + 解决了什么 + 量化结果", 但不要作为面试主推项目.