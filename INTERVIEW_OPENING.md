# 面试开场白 — ERP AI Copilot (5 分钟口述稿)

> 适用: AI 应用工程师岗位面试开场
> 字数: ~750 字, 5 分钟读完
> 风格: 口语化, 自然停顿, 不要背稿
> 项目地址: https://github.com/blank5this/MACS

---

## 开场白正文 (直接读)

您好, 我叫 XXX, 来自深圳, 今天来面试 AI 应用工程师岗位. · 我想用 5 分钟介绍一下我做的 ERP AI Copilot 项目, 然后我们再聊细节.

· 我做这个项目的起因是这样的. 我之前做了 MACS — 一个通用的多 Agent 协作框架, 但投简历时发现一个问题: 通用框架对面试官来说"看不出业务价值". 所以我用 15 天时间, 把 MACS 重做成一个**面向 ERP 业务场景的 AI 助手产品** — 也就是 ERP AI Copilot. · 这是项目定位的关键转变, 从"框架"到"产品".

· 我来介绍项目做了什么. 它解决 3 个真实的 ERP 痛点. 第一, 仓管问"哪些商品会缺货?" 以前要懂 SQL、跑查询; 现在一句话, Planner 自动派 Inventory Agent 给出 SKU 列表加风险等级. 第二, 采购经理问"哪个供应商涨价最快? 要不要换?", 以前要拉 3 张表做透视; 现在 Buyer Agent 自动跑历史价格, 输出排名加替代建议. 第三, 新人问"采购退货怎么处理?", 不用翻 50 页 PDF, Knowledge Agent 直接命中 KB 段落给答案.

· 具体技术上有 4 块. 数据层 — PostgreSQL 5 张表, 1000+ 行 Faker 种子数据, 模拟一个真实中型 ERP. Agent 层 — 我实际跑过单 Agent 7 工具的方案, prompt 已经 1200 token; 后来拆成多 Agent: Planner 拆任务, Inventory Analyst 查库存, Purchase Specialist 看采购, Report Writer 出报告, 四级 Hierarchical 编排. 检索层 — 18 篇中文 ERP 制度文档, 用 char-ngram 加 BM25 加 RRF 三路混合检索, 解决中文短查询召回不稳的问题. 工程化 — 4 层 SQL 注入防护, FastAPI 4 endpoints 加 3 Tab Web UI, GitHub Actions 独立 CI workflow, 168 个测试全过.

· 有几个 Plan 没要求但我顺手做了的, 面试时我会重点说. 第一, Web UI — 给非技术同事也能跑, 不只是开发者演示. 第二, CI workflow 独立 — 我的项目有专门的 CI, 跑 lint 加 test 加 integration 加 coverage. 第三, 3 维健康检查 — 同时给 CLI 和 k8s 复用, 这是生产级思维. 第四, SQL 4 层防护 — 考虑 prompt injection 风险. 第五, 168 个测试 — 按模块分文件, 测试金字塔完整.

· 我可以现场演示. 我有 3 段 60 秒的视频脚本, 一个跑单 Agent 7 工具自动选, 一个跑多 Agent 协作生成库存风险报告, 一个跑 RAG 知识库检索. · 如果您愿意, 我可以打开 GitHub 仓库带您看代码结构, 或者直接跑 Web UI 演示.

· 关于这个项目和 LangChain / AutoGen 的区别, 我的看法是: 它们是通用 Agent 框架, 我的项目是在它们之上做的 ERP 业务产品, 有真实 schema, 有 seed 数据, 有 KB, 有 UI, 有 CI, 是一个**能投简历能接私活的产品**, 不是 PPT.

· 我的问题是想了解一下团队目前 AI 应用落地到什么阶段, 以及这个岗位未来 3 个月最希望我解决什么问题. · 谢谢.

---

## 3 个分支 (面试官中途可能问的)

### 分支 A — 如果面试官问"能讲讲单 Agent 怎么实现的吗?"

> 应对时长: 1-2 分钟, 回答完回到主线

单 Agent 是 `ERPCopilotAgent` (`macs_pkg/erp/agents/copilot_agent.py:203-260`), 注册 7 个 tool — 5 个 MCP 库存销售采购工具, 1 个 RAG 检索, 1 个 NL→SQL. LLM 根据用户 query 自动选 tool. 我实际跑下来 prompt 会膨胀, 因为工具描述越来越长, 调用越来越慢, 所以后来才拆多 Agent. · 单 Agent 的优势是实现简单, 缺点是职责不分离, 一个 tool 挂了整体挂. 多 Agent 用 Hierarchical 编排, Planner 只管拆任务, Executor 只管执行.

### 分支 B — 如果面试官问"你这个项目最大亮点是什么?"

> 应对时长: 1 分钟, 然后引导到具体技术深挖

我觉得是**工程化完整度**. 168 测试加 CI 加 Web UI 加健康检查加 4 层 SQL 防护, 加上 5 张表的真实数据, 这是 95% 候选人项目做不到的. Plan 没要求这些, 是我主动做的. · 具体我可以展开讲, 比如健康检查为什么做成单一事实源, 比如 SQL 防护为什么选 AST 解析而不是字符串过滤, 比如测试为什么按模块分 12 个文件. 您想听哪个?

### 分支 C — 如果面试官问"用了哪些 LLM? 为什么?"

> 应对时长: 1 分钟

7 个 Provider: MiniMax、Claude、Qwen、Zhipu、DeepSeek、Hunyuan、OpenAI. 我抽象成统一接口 (`README.md:266-272`), 切换 Provider 只改配置. 这样在国内 (Qwen/DeepSeek/Zhipu) 和海外 (Claude/OpenAI) 都能跑, 应对不同客户的合规要求. · 实际业务跑我用 Claude Sonnet 4 和 Qwen Plus, 因为这两个在中文 ERP 场景下效果和成本平衡最好.

---

## 练习建议

1. **第一遍**: 对着镜子读, 计时 5 分钟, 不要超过 5 分 30 秒
2. **第二遍**: 把"·"换成正常停顿, 不刻意, 自然呼吸
3. **第三遍**: 录视频回放, 检查有没有口头禅 (呃 / 然后 / 就是)
4. **第四遍**: 找一个朋友听, 听完让他用 30 秒复述你的项目, 看他能不能抓到 5 个关键词 (ERP / 多 Agent / RAG / 168 测试 / Web UI)

---

## 自我检查 (面试前 5 分钟过一遍)

- [ ] 我能 30 秒说出项目一句话定位
- [ ] 我能 1 分钟说出 3 个业务痛点 + 对应 Agent
- [ ] 我能 2 分钟说出 4 层技术架构 + 关键数字
- [ ] 我能 1 分钟说出 5 个超出 Plan 项
- [ ] 我能在被问到"和 LangChain 区别"时流畅回答 1 分钟
- [ ] 我能在被问到"最大亮点"时不假大空, 直接说"工程化完整度" + 1 个具体例子