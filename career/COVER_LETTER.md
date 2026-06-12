# 求职信 — 3 种长度 (按场景选)

> 项目地址: https://github.com/blank5this/MACS
> 当前版本: v1.0.1-erp-copilot
> 期望岗位: AI 应用工程师 / Python 后端 / LLM 应用开发 / Agent 开发
> 期望薪资: 15-25K / 深圳南山 / 1 个月内可到岗

---

## 版本 A: 1 段极简版 (100 字)

**适用场景**: Boss 直聘私聊 / 微信加 HR / 简历附件首页 / 猎头速读

```
您好, 我叫 <your_name>, 深圳南山, 寻 AI 应用工程师岗 (15-25K).

过去 15 天我做了 ERP AI Copilot v1.0.1 (github.com/blank5this/MACS):
5 张 ERP 表 + 1000 行种子 + 18 篇中文 KB + 多 Agent 协作 + 168 测试全过.

技术栈: Python 3.11 + FastAPI + PostgreSQL + AutoGen/LangChain + MCP.

可发 1 页项目摘要 + 3 段 60s 演示视频, 期望 1 周内电话沟通.
```

---

## 版本 B: 3 段标准版 (300 字)

**适用场景**: Boss 直聘公开岗位附言 / 拉勾网投递 / 智联招聘投递

```
您好, 我是 <your_name>, 应聘贵司 [岗位名称] 岗位.

[段 1 — 钩子, 1 句话定位]
我是一名从 Java 后端转型 AI 应用的工程师, 过去 15 天独立完成 ERP AI Copilot v1.0.1 (github.com/blank5this/MACS), 已落地 5 张 ERP 表 + 1000 行种子数据 + 18 篇中文知识库 + 多 Agent 协作 + 4 层 SQL 注入防护 + 168 个测试全过, 项目可直接演示 (Web UI + 3 段 60s 视频).

[段 2 — 项目亮点, 3 个关键数字]
技术栈覆盖 AI 应用工程师核心要求: Python 3.11 + FastAPI + PostgreSQL 16 + AutoGen/LangChain 多 Agent 编排 + RAG 混合检索 (char-ngram + BM25 + RRF, 零 Embedding 依赖) + MCP 工具 (5 个) + GitHub Actions CI/CD (4 job). 我特别在 3 个工程化点上做到位: 第一, NL→SQL 4 层安全防护 (AST 解析 / 关键字黑名单 / 表列白名单 / 参数化绑定); 第二, 3 维健康检查 (DB/LLM/RAG) 同时供 k8s probe 和 CLI 复用; 第三, 测试金字塔分层 (168 单元 + 23 集成 + 6 e2e).

[段 3 — 为什么选贵司 + CTA]
了解到贵司在 [业务方向, 如大模型应用 / AI 中台 / 行业 AI 落地] 有明确布局, 这与我的项目经验高度契合. 我期望 15-25K (按能力定薪), 可 1 个月内到岗. 附件是我的简历 PDF + 1 页项目摘要, 期待您的反馈.
```

---

## 版本 C: 5 段详细版 (600 字)

**适用场景**: 外企 (Microsoft / Google / Salesforce) / 大厂 (腾讯 / 字节 / 华为) 正式招聘流程 / LinkedIn Easy Apply / 猎头邮件正文

```
Subject: AI 应用工程师候选人 <your_name> — ERP AI Copilot v1.0.1 (Python + LLM + Agent + 168 tests)

Dear Hiring Manager,

[段 1 — 开头钩子, 自我介绍 + 投递岗位]
I am writing to apply for the [岗位名称] position at [公司名]. I am a software engineer based in Shenzhen with 1-3 years of Java backend experience, and I have spent the last 15 days intensively building an open-source product, ERP AI Copilot v1.0.1 (github.com/blank5this/MACS), which I believe maps directly to the requirements you listed in your job description.

[段 2 — 项目定位 + 业务价值]
ERP AI Copilot is a production-grade AI assistant for ERP scenarios. It allows non-technical warehouse managers, procurement specialists, and sales analysts to ask questions in plain Chinese ("哪些商品库存低于安全库存?" / "哪些供应商涨价最快?" / "如何处理采购退货?") and receive structured risk reports, supplier rankings, or knowledge citations. The product is engineered, not a notebook toy: 5 PostgreSQL ERP tables seeded with 1000+ rows of synthetic data, 18 Chinese KB documents, a FastAPI Web UI with 3 tabs, GitHub Actions CI with 4 jobs, and 168 unit tests passing.

[段 3 — 技术深度, 3 个亮点]
Three technical decisions I made that may be of interest to your team:

(1) NL→SQL with 4 layers of defense — every LLM-generated statement is parsed into an AST, scanned against a blacklist (DROP/DELETE/UPDATE/INSERT/TRUNCATE/ALTER/GRANT), validated against a SELECT-only whitelist, then executed with bound parameters. 17 dedicated tests in `tests/test_nl2sql_safety.py`, each with a one-line "what attack are we blocking" docstring.

(2) Multi-agent is a context-budget decision, not a buzzword — I tried a single agent first with 7 tools, the prompt ballooned past 1200 tokens and tool selection accuracy dropped. I split into 4 focused agents (Planner / Inventory Analyst / Purchase Specialist / Report Writer), each owning 2-3 tools with prompts under 800 tokens. Task success rate climbed from 70% to 95%.

(3) Hybrid retrieval without embeddings — for Chinese KB documents I implemented char-ngram (n=2,4) + BM25 + RRF fusion. Zero tokenizer dependencies, zero embedding API costs, end-to-end retrieval under 200ms, top_k=3 default to prevent prompt flooding.

[段 4 — 为什么选贵司, 结合 JD]
What attracts me to [公司名] specifically is your [业务方向, 如 large model application platform / enterprise AI transformation / open-source LLM ecosystem]. I see strong overlap with my hands-on experience in: agent orchestration frameworks, RAG system design, LLM provider abstraction (6 providers: Claude / OpenAI / Qwen / Zhipu / DeepSeek / Hunyuan), and production engineering (CI/CD, health checks, parameterized SQL execution). I am particularly interested in [具体业务方向, 如 applying this to multi-tenant SaaS scenarios / extending to multi-modal inputs / building agent evaluation infrastructure].

[段 5 — 期望薪资 + CTA]
Salary expectation: 15-25K RMB (negotiable based on scope and equity), available within 1 month. I would welcome a 30-minute introductory call to walk you through the GitHub repo and a live demo of the Web UI. My resume and a 1-page project summary are attached.

Thank you for your consideration.

Best regards,
<your_name>
<your_email> | <your_phone>
github.com/blank5this/MACS
```

---

## 使用建议

| 投递渠道 | 推荐版本 | 修改重点 |
|----------|---------|----------|
| Boss 直聘私聊 HR | 版本 A | 直接复制开头"您好, 我叫 XXX", 中间段可不改 |
| Boss 直聘公开岗位附言 | 版本 B | 把 `[岗位名称]` 替换为 JD 标题, 段 3 的 `[业务方向]` 替换为 JD 关键词 |
| 拉勾 / 智联 / 前程无忧 | 版本 B | 同上, 在段 1 加 1 句"Java 1-3 年, 转型 AI 应用" |
| LinkedIn Easy Apply | 版本 C | 英文段 1 / 2 / 3 直接用, 段 4 / 5 翻译保持简洁 |
| 猎头邮件正文 | 版本 C | 顶部加"推荐候选人: <your_name>", Subject 用我提供的格式 |
| 外企 (Microsoft / Google) | 版本 C | 全部英文, 项目链接保留 |
| 大厂 (腾讯 / 字节 / 华为) | 版本 C | 段 4 强调"贵司在大模型应用 / Agent 平台的具体布局" |

---

## 反例 (不要这么写)

- "在当今 AI 浪潮下..." — AI 八股, HR 反感
- "我是一个有责任心有担当有热情的工程师" — 三有句式, 毫无信息量
- "期待与贵司一起探索 AI 的无限可能" — 假大空
- 段 1 / 段 3 只写技术栈没数字 — 必须有"168 测试 / 5 张表 / 1000 行"这种可量化产出
- 全文无 GitHub 链接 — 等于没让 HR 验证你的能力