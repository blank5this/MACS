# 面试话术速查 — 甘凯锋

> 围绕 **MACS + ERP AI Copilot** 准备。每题都遵循 STAR 法则（Situation → Task → Action → Result）。

---

## 🟢 5 个高频问题（90% 面试会问）

### 1. 请介绍一下你最近做的项目

**❌ 不要说**：我做了一个多 Agent 框架，集成了 OpenAI API。

**✅ 推荐说（2-3 分钟版）**：

> "我最近在做两个事：
>
> **第一个是 MACS — 一个多 Agent 协作框架**。它解决的问题是让多个 AI 角色（Planner、Executor、Reviewer、Tool Agent）能像团队一样协作。我设计了 5 种协作模式 —— Hierarchical 是传统的领导/执行/审核结构，Pipeline 是流水线的阶段转换，Decentralized 是分布式投票，Deep Research 是面向研究类任务，Dynamic Selector 是在运行时根据任务自动选模式。技术亮点是所有 Agent 都继承自 `ReactAgent` 基类，它强制 `think → act` 生命周期 —— 业务上对应 ReAct 论文的模式，工程上保证不会出现忘记调 think 直接 act 的 bug。326 个自动化测试都过。
>
> **第二个是 ERP AI Copilot**，完全用 MACS 自己搭的。核心是 3 件事：Text2SQL 让用户用自然语言查 ERP 数据，4 层安全护栏防 SQL 注入；ERP 知识库是 18 篇采购/库存/审批制度文档的 RAG，混合检索 + 强制引用；库存风险分析是 Planner 协调多 Agent 的多步推理工作流 —— Planner 把"哪些商品风险最高"拆成几个子任务，让 Inventory Analyst 算速度/库存、让 Purchase Specialist 算补货量、让 Report Writer 合成报告、最后 Reviewer 评分。已上线 Render 和 Hugging Face，双部署。"

---

### 2. 你们的 SQL 安全是怎么做的？

**✅ 推荐说（深挖可展开 5 分钟）**：

> "我做了 **4 层防御**，这在生产环境很重要：
>
> 1. **AST 白名单** —— `ast.parse` 解析 SQL，只允许 `SELECT`，碰到 `INSERT/UPDATE/DELETE/DROP` 直接拒
> 2. **关键字黑名单** —— 拒绝 `pg_catalog`、`pg_read_file`、多语句分隔符、注释符
> 3. **语句类型校验** —— 强制要求有 `FROM`、自动加 `LIMIT` 防止扫全表
> 4. **数据库层只读角色** —— 即使前三层都被绕过，PostgreSQL 的 read-only role 在库内会拒写
>
> 50+ 个对抗测试覆盖：注入、UNION、pg_ 系统表、文件读取、注释绕过，全部通过。
>
> **ADR-003** 把这个写成了架构决策 —— 关键点是 *defense in depth*：单点防御都不够，4 层互不依赖，攻破一层还有下一层。"

---

### 3. 你的 RAG 怎么做？为什么不用纯 Embedding？

**✅ 推荐说**：

> "我用的是 **混合检索**，三路融合：
> - **char-ngram TF-IDF**：捕捉中文短语字面匹配，比如"采购审批流程"
> - **BM25**：捕捉近义词、相关词
> - **Embedding 召回**（可选）：捕捉语义
>
> 三路结果用 **RRF (Reciprocal Rank Fusion)** 融合，每个 chunk 都有三路分数的加权和。
>
> **为什么不用纯 Embedding**？因为中文短查询 + 中文文档 + 业务术语，纯向量很容易在"采购"和"购买"上失配 —— 用户问"采购审批流程"，向量召回会给你"采购付款流程"或"采购合同流程"，而 BM25 会精确命中"采购审批流程"。我把这点写在了 **ADR-004** 里，关键洞察是：**不同检索方法的失效模式不同，混合能把失败模式分摊**。"

---

### 4. 多 Agent 怎么协作的？ReAct 是什么？

**✅ 推荐说**：

> "ReAct 是论文《ReAct: Synergizing Reasoning and Acting in Language Models》的核心思想 —— 推理和行动交替进行。一个 Agent 不是 LLM 一次性输出答案，而是 think（分析）→ act（执行/调工具）→ 观察结果 → 再 think 的循环。
>
> 在 MACS 里，我把这个做成 **基类强制生命周期**：
>
> ```python
> async def think(self, message):
>     # 强制状态检查
>     if self.state == THINKING: raise
>     self.state = THINKING
>     return await self._think_impl(message)
>
> async def act(self, response):
>     # act 必须在 think 后
>     if not self._think_called: raise RuntimeError
>     ...
> ```
>
> 这样 4 个角色 Agent（Planner/Executor/Reviewer/ToolAgent）都不可能写出'忘了 think 直接 act'的 bug。
>
> **5 种协作模式**其实是在 `think → act` 这个单体循环上的团队编排：
> - **Hierarchical**：Planner 先 think，把任务拆成 N 份 act 给 N 个 Executor，每个 Executor 各自 think+act，最后 Reviewer think+act 评分
> - **Pipeline**：上一个 Agent 的 act 结果是下一个 Agent 的 think 输入
> - **Decentralized**：所有 Agent 并行 think（出 proposal），然后集体 vote
> - **Deep Research**：多 query 并发检索 + 综合
> - **Dynamic Selector**：LLM 在运行时挑模式"

---

### 5. 你这个项目和 LangChain / LangGraph 比有什么不同？

**✅ 推荐说**：

> "差异有 3 个：
>
> 1. **范围不同**。LangChain 是 LLM 应用工具箱（PromptTemplate、OutputParser、Retrievers 一大堆），要自己拼。我做的是 **多 Agent 协作模式的内置库** —— 5 种模式是开箱即用的。
> 2. **多 LLM 厂商原生支持**。我做了 6 个 Provider 的统一抽象，1 行切换。LangChain 也有，但它抽象太通用，对中文模型（如智谱、混元、MiniMax）支持参差不齐。
> 3. **生产化更细**。比如 `conversation_cap=100` 防内存泄漏、指数退避 + jitter 防雪崩、ReactAgent 强制生命周期、SQL 4 层护栏 —— 这些是踩坑后专门做的。LangChain 把这些留给用户。
>
> 但说句公道话：如果是做单 Agent + RAG 的简单应用，LangChain 够用，**别用 MACS**。MACS 的价值是当你需要 **多 Agent 协作 + 强工程约束 + 企业级安全** 的时候。"

---

## 🔴 3 个 deep-dive 准备（防止被问倒）

### 6. 项目中遇到的最大技术难点？怎么解决的？

**✅ 推荐说**：

> "两个：
>
> 第一个是 **长会话内存泄漏**。MiniMax API 是 OpenAI 兼容的，我最初把每轮对话都堆在 `_conversation` 列表里，跑 1 小时程序 OOM。
>
> 解决：加了 `MAX_CONVERSATION_LENGTH = 100`，超过时裁掉最早的 — 用 `collections.deque(maxlen=100)`。这个改动只有 5 行，但救了我的服务稳定性。**ADR-006** 记录了这个决策。
>
> 第二个是 **ReAct 循环的思考-执行顺序没人保证**。原来我的 Planner Agent 直接继承 `BaseAgent`，`think()` 和 `act()` 是两个独立抽象方法，调用方必须自己保证先 think 再 act。一次代码 review 我发现 decentralized 模式下有人直接调 act 拿 result —— bug！
>
> 解决：写了 `ReactAgent` 基类，think() 内部设置 `_think_called=True`，act() 进来第一行检查这个 flag，没设置就抛 `RuntimeError`。然后让 4 个角色 Agent 都继承它。**架构断层补上了，bug 类型被消灭在编译期**。"

---

### 7. 怎么评估你这个 Agent 的效果？

**✅ 推荐说**：

> "三层评估：
>
> 1. **自动化测试**：326 个 unit test 覆盖 Agent 生命周期、LLM JSON 解析、SQL 注入、RAG 检索质量。
> 2. **Adversarial 测试**：50+ 个 SQL 注入用例 + 5 个恶意 calculator 输入（`__import__('os')` 等），全部被拒。
> 3. **人评 + LLM-as-Judge**：Reviewer Agent 本身就是 LLM-as-Judge，3 个维度（completeness/correctness/relevance）打 0-1 分。
>
> 实测 ERP 知识助手 3 个真实问题：总耗时 43 秒全部通过（CLAUDE.md 有原始数据）。
>
> **没做的事**：A/B 对比 baseline（用 LangChain 同样需求实现一遍）。这是下一步 —— 但招进来后就能做。"

---

### 8. 你对未来的规划？

**✅ 推荐说**：

> "短期 1 年：进企业 AI 团队，做大模型在企业落地的工程化（Multi-Agent、Tool Calling、SQL 安全、RAG 评估）—— 这些在 MACS 里我已经做过一版完整方案。
>
> 中期 2-3 年：深耕 **Agent Eval** 和 **企业级安全护栏**。现在 LLM 应用最大的痛点不是'能不能跑'，是'生产可不可信'。怎么评估 Agent 行为？怎么在 SQL/工具调用层做硬隔离？怎么让 Agent 输出可审计？这几个方向我已经有 ADR 储备。
>
> 长期：做 **AI Native ERP** —— 不是给 ERP 加 chatbot，而是从 LLM 出发重新设计 ERP 的交互范式。这是更大的事，得有产品思维 + 工程能力的复合背景。"

---

## 🎯 一句话杀手锏（每个回答结尾都可以用）

> "我在 MACS 写了 8 篇 ADR，每个非显然的设计选择都解释了'为什么'，而不只是'是什么'。如果想深挖任何一点，我可以 walk through 任何一篇。"
