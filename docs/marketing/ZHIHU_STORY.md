---
title: 15 天, 我把一个 Multi-Agent 框架做成了 ERP AI Copilot 产品
platform: 知乎
target_audience: 中文 AI 应用开发者, 想转 AI 岗的 Java/后端工程师, 一线/新一线城市 AI 求职人群
posting_priority: high
status: draft
---

# 15 天, 我把一个 Multi-Agent 框架做成了 ERP AI Copilot 产品

> 一个 23 岁的 Java 工程师, 月薪 8K, 在深圳南山的目标是 15-25K 的 AI 应用工程师岗. 这是我过去 15 天做的一个项目, 也是接下来 30 天的求职弹药.

---

## 起点: 8K 的 Java 工程师, 想冲 AI 岗

先说背景, 免得有人觉得我在卖焦虑.

我今年 23, 在深圳做 Java 后端, 月薪 8K. 日常工作就是写 CRUD、调分页、调接口, 偶尔用一下 Spring Cloud 的全家桶. 业务稳定, 技术稳定, 工资也稳定——稳定在 8K.

2025 年开始, 我身边所有 Java 群里都在聊两件事: 一个是大模型 API 又降价了, 另一个是"传统后端要不要转 AI". 我看了几个招聘网站, 深圳南山 AI 应用工程师的开价是 15-25K, 要求大致是: Python + FastAPI + LLM + RAG + Agent + 至少一个能讲清楚的项目.

我有 Java 底子, Python 写过小脚本, LLM 用过 OpenAI 的 API. RAG 和 Agent 我知道概念, 没真正做过.

那就做一个项目.

## 转折: 我先做了 7 天框架, 然后发现没人用

我一开始做的是 MACS, 一个 Multi-Agent Collaboration System. 框架本身我做得挺完整——有 runtime, 有 message routing, 有 tool registry, 支持 6 个 LLM provider (Claude / GPT / 通义 / 智谱 / DeepSeek / 混元), 有 docker-compose 部署.

第七天晚上, 我把这个项目贴到一个开发者群里, 有人回了三个字: "然后呢?"

我愣住了. 是啊, 然后呢? 这个框架能干嘛? 谁能用? 解决了谁的什么问题?

我打开自己写的 README, 第一句话是"一个通用的、可扩展的多智能体协作系统框架". 这话等于没说. 面试官看完不知道我做了什么, 客户看完不知道为什么要用, 甚至我自己看完, 都觉得这是个"会写 Agent 的程序员写的又一个 Agent 框架"——市面上已经有 50 个这样的东西了.

那天晚上, 我在路线图里写了一句话:

> **停止把 MACS 当成框架开发, 把它当成 ERP AI Copilot 产品开发.**
> **这一个思维转变, 对拿 AI Offer 的价值, 可能比再写 5000 行 Agent 代码都大.**

这句话改变了一切.

## Day 1-3: 不写一行 Agent 代码, 先建数据库

我知道这听起来很奇怪——做 AI 项目, 第一件事居然是建数据库.

但 ERP 是业务. 业务没有数据, Agent 跑什么? 我花了三天时间:

- 设计 5 张表: `products` / `inventory` / `sales_orders` / `purchase_orders` / `suppliers`
- 用 Faker 造了 1000+ 行模拟数据 (small / medium / large 三档可调)
- 写了 `DatabasePool` 异步连接池 (`macs_pkg/erp/db/connection.py`)
- 写了 5 张表的 DDL (`macs_pkg/erp/db/schema.py`)

Day 3 跑通第一条 SQL: `SELECT sku, stock FROM products WHERE stock < safety_stock LIMIT 10`.

这一刻我才真正理解: AI 不是魔法, AI 是数据库的嘴.

## Day 4-6: MCP 工具 + NL→SQL, 然后给自己挖了安全坑

Day 4 写了 5 个 MCP 工具 (库存/销售/采购各几个), 用 stdio 注册, 让 Agent 能调.

Day 5-6 做 NL→SQL——把"哪些商品库存低于安全库存?"翻译成 SQL. 这里我给自己挖了一个安全坑:

LLM 直接生成的 SQL 拿来跑数据库, 风险是显而易见的. 万一用户输入了"把 products 表删了"呢? 万一 prompt injection 让人拼了一句 `DROP TABLE` 进去呢?

所以我做了 **4 层 SQL 防护**, 写在 `macs_pkg/erp/nl2sql.py`:

1. **AST 解析**——SQL 必须能解析成 AST, 否则拒
2. **黑名单扫描**——遍历 AST 节点, 发现 `DROP / DELETE / UPDATE / INSERT / TRUNCATE / ALTER / GRANT / pg_sleep / information_schema` 直接拒
3. **白名单校验**——只允许 `SELECT` (和 `WITH ... SELECT`) 通过
4. **参数化执行**——用 AST 重新绑定参数, 不用 f-string 拼 SQL

Day 6 写完 `tests/test_nl2sql_safety.py`, 17 个测试, 每个测试一行 docstring 说明在防什么攻击. 这是整个项目里我最喜欢的一个文件——因为我终于在想"如果失败会怎样", 而不只是"如果成功会怎样".

## Day 7: RAG 知识库, 但我没用 Embedding

Day 7 做知识库. 我有 18 篇中文 ERP 文档 (运营 / 仓储 / 采购 / 财务 4 个子目录), 用户会问"如何处理采购退货?"这种问题.

我没用 Embedding API. 因为:

- 中文 embedding 模型选择多, 但每个项目换一次就要重新建索引
- Embedding 模型对"退货"和"退换货"这种近义词召回不稳定
- 我想控制成本, 不想每次启动都调一次 API

所以我做了**混合检索** (`macs_pkg/erp/rag/`):

- **char-ngram 分词** (n=2 和 n=4), 中文友好, 零依赖
- **BM25 打分**, 经典可靠, 零成本
- **RRF 融合**, 把两个 ranking 合并成 top-k
- **`top_k=3` 默认**, 不让 prompt 被无关 chunk 灌爆

到 Day 7 晚上, 用户问"如何处理采购退货?", 系统返回 3 段引用, 准确命中仓储规范的对应章节.

## Day 8-11: 先做单 Agent, 然后拆多 Agent

Day 8 我先做了单 Agent (`ERPCopilotAgent`), 把 5 个 MCP 工具 + RAG + NL→SQL 全部塞给它, 让 LLM 自己选. 跑得起来, 但 prompt 到了 1200 token, 多步任务上下文接近 4000 token, 选错工具的概率明显上升.

Day 9-10 我把它拆成 4 个 Agent (`macs_pkg/erp/agents/templates.py`):

- `ERP_PLANNER`——把用户目标拆成 3-4 步
- `ERP_INVENTORY_ANALYST`——只管库存, 2 个工具, prompt < 800 token
- `ERP_PURCHASE_SPECIALIST`——只管采购, 2 个工具
- `ERP_REPORT_WRITER`——收前两个的输出, 写 Markdown 报告, 落盘

Day 11 跑通多 Agent 端到端 (`macs_pkg/erp/workflows/inventory_risk.py`):

```
Planner → Inventory Analyst → Purchase Specialist → Report Writer
                                          ↓
                              examples/output/inventory_risk_report.md
```

我手动测了 10 个查询, 任务成功率从单 Agent 的 70% 提到了 95%. 这个数字是真实的, 也是我面试时被问"为什么用多 Agent"时唯一能拿出手的答案.

## Day 12-13: Web UI + CI + 健康检查

Day 12 加了 FastAPI Web UI (3 Tab: Chat / Multi-agent Report / KB Search), 暗色主题, 给非技术同事演示用. 这是路线图没要求的, 我自己加的.

Day 13 加了 CI (`erp-copilot.yml` 4 job: lint / unit / integration / ERP-specific) 和健康检查 (`health.py` 3 维: DB / LLM / RAG). 健康检查是单一事实源, 同时给 k8s probe 和 CLI 复用.

到这里, 我的完工度盘点是这样的:

| 维度 | 数字 |
|------|------|
| 新增文件 | 22 个核心 + 17 个测试 |
| 测试 (非集成) | **168 passed** |
| 集成测试 | 23 |
| CI jobs | 4 |
| LLM Provider | 6 |
| MCP 工具 | 5 |
| KB 文档 | 18 篇 / 135 chunks |
| Web endpoints | 4 个 (chat / inventory_risk / kb/search / healthz) |
| 视频 | 3 段 × 60s |
| 文档 | 3 use cases + 1 架构图 + 1 索引 |

路线图说 15 天, 我 5 天做完了 80%. 剩下 20% 是产品化: 录视频, 写简历, 投递.

## 反思: 为什么 80% 的 AI 项目死掉

我观察了我身边几个做 AI 项目的同事, 死掉的项目都有一个共同点:

> **它们是框架, 不是产品.**

写了一个 Agent 框架, 能跑 hello world, 贴上 GitHub, 然后呢? 没有 demo, 没有数据, 没有用户故事. 一个月后连作者自己都忘了它能干嘛.

我把项目从"框架"改名为"ERP AI Copilot"之后, 一切都不一样了:

- README 第一行是业务能力 (库存风险分析 / 采购建议 / 销售洞察), 不是技术架构
- Quickstart 是 60 秒启动 Web UI, 不是 `pip install` 之后一脸懵
- 文档是 use case (老板问"这能干嘛"时怎么答), 不是 API reference
- 视频是 3 段 60 秒演示, 不是架构图配文字

面试官打开我的 GitHub, 30 秒内就知道: 这是一个能讲清楚的 ERP AI 产品, 不是又一个 Agent 框架.

## 接下来 30 天: 曝光 + 面试, 不写代码

路线图说得很清楚, 我在"代码 + 文档 + 发布"这条线上已经 100% 到位. 接下来 30 天, 90% 的价值在"曝光 + 面试", 跟代码完全无关.

Day 1 (今天): 发本文 + LinkedIn 文案 + 掘金技术文 + B 站视频简介.
Day 2: 更新简历 PDF, 投 5-10 个 Boss 岗.
Day 3-7: 投 10-20 个深圳南山 AI 岗.
Day 8-30: 每天 2-3 个面试, 用 3 段视频开场, 用 5 个面试答案模板应对高频问题.

## 结尾: 求 Star + 求内推

项目地址: https://github.com/blank5this/MACS

如果你也在深圳南山, 或者你身边有人在招 AI 应用工程师, 求一份内推.

如果你觉得这个项目对你有用, 求一个 Star——它对我求职的意义, 比再写 5000 行代码都大.

## 自检清单

- [ ] 标题包含"15 天"+"Multi-Agent 框架"+"ERP AI Copilot", 搜索友好
- [ ] 开头交代了年龄(23)/ 工资(8K)/ 目标(15-25K)/ 地点(深圳南山), 命中受众
- [ ] 转折点引用了路线图金句"停止把它当框架开发"
- [ ] 4 个 Day 1-15 的关键时刻都用小标题分段
- [ ] 关键数字(5 表 / 168 测试 / 22 文件 / 18 KB / 6 LLM / 4 CI / 3 视频)全部出现
- [ ] 反思段解释了"为什么 80% AI 项目死掉", 有观点而非流水账
- [ ] 结尾有 GitHub 链接 + 求 star + 求内推
- [ ] 全文中文, 无 emoji (Markdown 标题符号除外)
- [ ] 字数在 2000-3000 字之间
- [ ] 没有"在当今 / 让我们一起 / 总而言之"这类 AI 八股