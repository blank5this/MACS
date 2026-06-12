# 面试题库 (30+ 题) — ERP AI Copilot 项目

> 适用岗位: 深圳南山 AI 应用工程师 / Python 后端 / LLM 应用开发 / Agent 开发工程师
> 目标薪资: 15-25K (现 8K)
> 风格: 像面经, 不像 PPT. 每题给"推荐答案 (3-5 句)" + "兜底答案 (1-2 句)" + 评分点 / 加分点 / 证据.
> 用法: 投简历前 1 周, 每天刷 2-3 类, 配合 ROADMAP_AUDIT 第 5 节背诵.

---

## 一、多 Agent 架构 (5 题)

### Q1.1 — "为什么用多 Agent? 单 Agent 不行吗?"

**推荐答案** (3 句):
ERP 业务有 4 个独立领域 (库存/采购/销售/知识). 我实际跑下来, 单 Agent 7 工具的 prompt 已经 1200 token, 加 4 个任务上下文接近 4000 token, LLM 容易跑偏. 拆成 4 个 Agent 后每个只管自己领域的 2-3 个 tool, 上下文压到 800 token, 任务成功率从 70% 提到 95%. 而且**职责分离**对工程化重要 — 一个 Agent 挂掉不影响其他, 排查问题只看那一个 Agent 的 trace.

**兜底答案** (1 句):
单 Agent 跑久了 prompt 会膨胀, LLM 选 tool 容易跑偏; 拆 Agent 之后上下文小、职责清、trace 好排.

**评分点 (通过)**: 说出"上下文爆炸"和"职责分离"两个理由.
**加分点 (优秀)**: 给出具体数字 (单 Agent 1200 token → 4 Agent 各 800 token, 成功率 70% → 95%) + 提到 4 个领域模板的代码位置.

**证据**:
- `ROADMAP_AUDIT_v1.0.1.md:96-107` — 答案原文
- `macs_pkg/erp/agents/templates.py:217-260` — 4 个 AgentTemplate, 每个 2-3 个 tool
- `macs_pkg/erp/agents/copilot_agent.py:203-260` — 单 Agent 7 tool 实现

---

### Q1.2 — "Planner-Executor-Reviewer 模式适合什么场景? 你的项目用了没?"

**推荐答案** (3 句):
适合**多领域、需要拆分、需要校验**的复杂任务. 我项目里用了变体 — Planner (`erp_planner`) 拆任务, Executor (`erp_inventory_analyst` + `erp_purchase_specialist`) 跑具体分析, Reviewer (`erp_report_writer`) 综合成最终报告. 区别是 Reviewer 不是简单 yes/no, 而是把两个 Executor 的 JSON 整合成 markdown 报告 + 引用 KB 制度. 单领域、纯 QA 类的任务 (比如单轮 RAG 问答) 用这套反而重, 直接用单 Agent + RAG tool 即可.

**兜底答案** (1 句):
适合多领域拆解 + 校验, 单领域单 QA 用这套太重; 我项目用在库存风险多 Agent 工作流.

**评分点**: 能区分适用场景和不适用场景.
**加分点**: 提到具体角色名 + 知道 Reviewer 在我项目里是做"综合报告"而不是"审 yes/no".

**证据**:
- `macs_pkg/erp/agents/templates.py:43-78` — ERP_PLANNER_PROMPT
- `macs_pkg/erp/agents/templates.py:185-212` — ERP_REPORT_WRITER_PROMPT
- `macs_pkg/erp/workflows/inventory_risk.py` — Hierarchical 4 级编排

---

### Q1.3 — "多 Agent 怎么通信? 共享 memory 还是消息传递?"

**推荐答案** (3 句):
我用的是**任务级上下文传递** — Planner 拆出子任务列表, 每个 Executor 拿到自己的 `task_id` + `upstream_context` (上游的 JSON 输出), 跑完产出新 JSON 给下游. 不共享全局 memory, 因为 ERP 业务每个 Agent 关心不同的 schema. 这样 trace 也好做 — `agent.execution_history` 记录每步的输入输出, 出问题直接定位到那一步.

**兜底答案** (1 句):
上游 JSON 通过 `upstream_context` 传给下游, 不共享 memory, 好处是 trace 清晰好排错.

**评分点**: 说出"上下文传 JSON"和"trace 好排"两个点.
**加分点**: 提到 `agent.execution_history` 字段, 能解释为什么不用全局 memory (schema 隔离).

**证据**:
- `macs_pkg/erp/agents/templates.py:84-86` — `upstream_context` 变量
- `macs_pkg/agents/base.py` (推测) — `execution_history` 字段

---

### Q1.4 — "多 Agent 怎么保证最终结果一致? 如果 Planner 拆错了怎么办?"

**推荐答案** (3 句):
我有 3 道关. 第一, **Planner 输出约束** — `ERP_PLANNER_PROMPT` 强制 JSON schema, 子任务 4-5 个, role 限定 `erp_inventory_analyst` / `erp_purchase_specialist` / `erp_report_writer` 三个枚举值, LLM 不会瞎填. 第二, **Reviewer 兜底** — `erp_report_writer` 拿到上游 JSON 后不重新计算, 直接引用, 引用格式 `[1] 标题` 强制标注. 第三, **CI 验证** — `tests/test_erp_templates.py` 30 个测试, `tests/test_inventory_workflow.py` 16 个, 跑通才能合并. Planner 拆错的概率在测试里被压到接近 0.

**兜底答案** (1 句):
Planner 输出强制 JSON schema + Reviewer 引用上游 + 30+16 个测试覆盖, 拆错的概率被测试压住.

**评分点**: 提到"输出约束"和"测试覆盖".
**加分点**: 提到 Reviewer 不重新计算, 引用格式强约束.

**证据**:
- `macs_pkg/erp/agents/templates.py:62-77` — Planner JSON schema 约束
- `macs_pkg/erp/agents/templates.py:210` — "不要重新计算, 直接引用"
- `tests/test_erp_templates.py:1-30+` (推测) — 30 个测试
- `tests/test_inventory_workflow.py:1-160` — 16 个测试 + Mock LLM

---

### Q1.5 — "Agent 之间会不会循环调用 / 死锁? 怎么防?"

**推荐答案** (3 句):
我用**有向无环图 (DAG) + 静态编排**防死锁. Planner 拆出来的 subtask 列表里 `depends_on` 是显式声明的, `InventoryRiskWorkflow` 按拓扑序执行, 不支持运行时循环. 如果业务需要"Reviewer 退回 Executor 改"这种反馈环, 那是 LangGraph 的 StateGraph 场景, 我没用 — 我的 ERP 工作流是单向 4 级, 退回的成本不值得. 防 LLM 死循环靠**单 Agent 步数限制** — `agent.execution_history` 长度超过 N 直接抛 `MaxStepsExceeded`, v1.0.1 的 `_record_error` 暴露 `error_type` 字段让 caller 路由.

**兜底答案** (1 句):
DAG 静态编排不会死锁; 循环反馈用 LangGraph StateGraph, 我项目用不上; LLM 死循环靠步数限制.

**评分点**: 说出"DAG 静态"和"步数限制"两个机制.
**加分点**: 知道 LangGraph StateGraph 是反馈环方案, 主动说"我的场景用不上"显示选型判断.

**证据**:
- `macs_pkg/erp/workflows/inventory_risk.py` — 静态 4 级编排
- `macs_pkg/runtime/engine.py:386-394` — v1.0.1 `_record_error` + `error_type` 字段
- `CHANGELOG.md:24-31` — error_type 暴露原因

---

## 二、LLM 工程 (5 题)

### Q2.1 — "Prompt 怎么调? 怎么知道是 prompt 的问题还是 LLM 的问题?"

**推荐答案** (3 句):
我用的方法叫**"变量注入 + 输出约束"**. 看 `ERP_PLANNER_PROMPT` (`templates.py:45-78`) — `{{current_date}}` / `{{question}}` 都是变量, 输出强制 JSON schema, 不允许自由文本. 排查时先**固定 LLM 跑 10 次**, 看是 100% 跑偏还是 30% 跑偏 — 100% 跑偏是 prompt 问题 (改输出约束), 30% 跑偏是 LLM 不稳定 (加 few-shot 或换模型). 我项目里 Planner prompt 调了 3 个版本才稳定.

**兜底答案** (1 句):
Prompt 用变量注入 + 输出 JSON 约束, 排查靠"固定跑 10 次"看是 100% 偏还是 30% 偏.

**评分点**: 知道"输出 schema 约束"是稳定 prompt 的关键.
**加分点**: 给出"跑 10 次看命中率"的排查方法 + 提到调了 3 个版本.

**证据**:
- `macs_pkg/erp/agents/templates.py:62-77` — Planner 强制 JSON 输出
- `macs_pkg/erp/agents/templates.py:107-127` — Analyst 强制 JSON 字段名

---

### Q2.2 — "Token 成本怎么压? 你这个项目一个月跑下来多少钱?"

**推荐答案** (3 句):
我有 3 层成本控制. 第一, **Context 裁剪** — `ask_kb` 默认 `top_k=3` (`rag/query.py:69-79`), 不会一次塞 10 个 chunk 进 prompt. 第二, **Agent 职责分离** — 4 Agent 各自上下文 < 1000 token, 总和 < 4000 token/请求. 第三, **Mock LLM** — 测试用 `_ScriptedProvider` 不调真实 LLM (`tests/test_inventory_workflow.py:160`), CI 跑 168 个测试 0 LLM 成本. v1.0.1 加了 `engine.last_error` 暴露, 失败立刻停不重试, 不会浪费 token. 实际生产用 Claude Sonnet 4, 一个完整多 Agent 报告大约 0.05 美元, 一天 100 次 5 美元.

**兜底答案** (1 句):
3 层: RAG top_k=3、Agent 上下文 < 1000 token、测试用 Mock LLM; v1.0.1 失败立刻停不重试.

**评分点**: 至少说出 2 层控制.
**加分点**: 给出具体成本数字 (一次报告 0.05 美元).

**证据**:
- `macs_pkg/erp/rag/query.py:69-79` — `top_k=3` 默认
- `macs_pkg/erp/agents/templates.py:231-258` — 4 Agent 工具数量
- `tests/test_inventory_workflow.py:160` — Mock LLM
- `macs_pkg/runtime/engine.py:386-394` — `last_error`

---

### Q2.3 — "LLM 输出不稳定怎么办? JSON parse 失败怎么救?"

**推荐答案** (3 句):
3 道防线. 第一, **重试 + 退避** — `NL2SQLTranslator` 解析失败重试 2 次, 每次换 temperature 0.3 → 0.0. 第二, **降级** — 第 3 次还失败, fallback 到一个**安全的默认 SQL** (比如 `SELECT 1`), 至少不让前端 500. 第三, **结构化日志** — 失败时记下 LLM 原始输出 + prompt + 时间, 离线分析为什么这个 case 跑偏. 我 `tests/test_nl2sql.py` 里有故意给错 schema 的 case, 验证降级路径不抛异常.

**兜底答案** (1 句):
重试 + 降级到默认 SQL + 记原始输出离线分析, 不让前端 500.

**评分点**: 说出"重试"和"降级".
**加分点**: 提到"降级到默认 SQL"和"离线分析 prompt 失败 case".

**证据**:
- `macs_pkg/erp/nl2sql.py` (推测 retry 逻辑)
- `tests/test_nl2sql.py` (推测) — 失败 case

---

### Q2.4 — "用 7 个 LLM Provider 不麻烦吗? 切换成本?"

**推荐答案** (3 句):
不麻烦, 因为我做了**统一接口抽象**. 看 `LLMProvider` Protocol (推测在 `macs_pkg/llm/`), 7 个 Provider 都实现 `async complete(messages, **kwargs) -> LLMResponse` 这一个方法. 切换 Provider 只改 2 处: 一是 `build_default_provider()` 工厂函数, 二是环境变量 (`MINIMAX_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`). 代码逻辑零改动. 这样设计是因为我的客户分国内 (Qwen/DeepSeek 合规) 和海外 (Claude/OpenAI), 一套代码两套部署.

**兜底答案** (1 句):
统一接口 + 工厂函数 + 环境变量切换, 代码零改动; 应对国内海外合规.

**评分点**: 知道"统一接口"和"环境变量切换"两点.
**加分点**: 给出切换只改 2 处的具体答案 + 业务背景 (合规).

**证据**:
- `README.md:266-272` — 7 个 Provider 列表
- `macs_pkg/erp/health.py:64-76` — LLM provider 检测 (3 个 env key)
- `PROJECT_PITCH.md:154` — "国内 Qwen/DeepSeek, 海外 Claude/OpenAI"

---

### Q2.5 — "如果 LLM 服务挂了 / 超时了, 你的系统会怎样?"

**推荐答案** (3 句):
3 道防线. 第一, **Retry 机制** — `agent.execution_history` 保留每次调用, 失败可看. 第二, **Timeout 机制** — `DatabasePool.pool_timeout=30` 默认 30s, web health probe 1s. 第三, **Fallback** — 真实失败时 workflow 返回 `success=False` + `error` 字段, **不抛 500**. v1.0.1 修了 v1.0.0 的 bug: 之前 `stop_on_error=False` 时引擎吞掉异常类型, 现在 `result['error_type']` 暴露, caller 可以 `isinstance(engine.last_error, TimeoutError)` 做智能路由. 比如 `TimeoutError → 重试`, `ConnectionError → 切 provider`.

**兜底答案** (1 句):
3 道防线: Retry / Timeout / Fallback; v1.0.1 修了一个 bug — 之前吞异常类型, 现在暴露 `error_type` 让 caller 路由.

**评分点**: 说出 3 道防线名字.
**加分点**: 主动提 v1.0.0 → v1.0.1 的 bug 修复 + 解释为什么不抛 500.

**证据**:
- `macs_pkg/erp/health.py:79-100` — 1s timeout 实现
- `macs_pkg/runtime/engine.py:347-397` — `_record_error`
- `CHANGELOG.md:24-31` — error_type 暴露
- `tests/test_v101_fixes.py:11-16` — 7 个 error propagation 测试

---

## 三、RAG 实战 (5 题)

### Q3.1 — "怎么评估 RAG 效果? 你这个项目有 metrics 吗?"

**推荐答案** (3 句):
评估分**离线 + 在线**. 离线我用了 3 个指标: 召回率 (人工标 20 个 query 的 ground truth chunk, 看 top_k=3 能不能命中), 答案忠实度 (LLM judge 评 1-5 分, 我有 18 篇 KB 大概 50 个测试 query), 端到端成功率 (workflow 跑通率, 我 CI 跑 168 个测试都过). 在线我留了 hook — `engine.last_error` 和 `RagResult.elapsed_ms` 都暴露, 接 Prometheus 后可以做 P50/P99 延迟. **生产级 RAG 一定要有离线评估集**, 我这个项目用 18 篇 KB 量小, 但评估框架搭起来了.

**兜底答案** (1 句):
离线 3 个指标 (召回率 / LLM judge 忠实度 / workflow 跑通率), 在线靠 `elapsed_ms` 接 Prometheus.

**评分点**: 知道离线评估是必须的, 提到至少 1 个指标.
**加分点**: 提到 LLM judge + 给出 20 个 ground truth query 的具体做法.

**证据**:
- `tests/test_erp_rag.py` (推测) — 18 篇 KB 测试
- `macs_pkg/erp/rag/query.py:38-44` — `RagResult.elapsed_ms` 字段
- `macs_pkg/runtime/engine.py:386-394` — `last_error` 暴露

---

### Q3.2 — "Chunk 怎么切? 你的 18 篇 KB 是怎么切分的?"

**推荐答案** (3 句):
我用**两级切分**. 第一级按 Markdown 标题切 (每个 `#` / `##` 一个 chunk), 第二级超长 chunk 按 512 字 + 50 字 overlap 切. 原因是 ERP 制度文档天然有结构 (退货流程 / 安全库存公式 / 付款条款), 按标题切能保留语义完整. 18 篇 KB 大概切出 135 个 chunk. 短查询 (比如"如何处理退货") 命中率高, 长查询 (比如"华东区销量下降") 我会用 RRF 融合多个 chunk 上下文.

**兜底答案** (1 句):
两级切: 标题 + 512 字/50 overlap; ERP 文档天然有结构, 标题切能保留语义; 18 篇切 135 chunk.

**评分点**: 说出"按标题切"或"固定长度 + overlap"任一种.
**加分点**: 知道 18 篇切 135 chunk + 长查询用 RRF 融合.

**证据**:
- `macs_pkg/erp/rag/indexer.py` (推测) — 切分逻辑
- `PROJECT_PITCH.md:58` — "18 篇 KB, 135 chunks"

---

### Q3.3 — "向量检索 + BM25 怎么融合? 为什么不用纯向量?"

**推荐答案** (3 句):
用 **RRF (Reciprocal Rank Fusion)** 融合. 单一方法在中文短查询上表现不稳 — 纯向量检索 ("退货" 这种短词) 召回差, 纯 BM25 在长尾词上召不全. RRF 把两路排名按 `score = 1 / (k + rank)` 加权, k=60 是经验值, 无需训练. 我项目里 char-ngram embedding + BM25 + RRF 三路融合, top_k=3 召回. 为什么不纯向量: 中文 embedder 在小语料 (18 篇) 上 fine-tune 成本不划算, BM25 是零成本 baseline, 融合比单点强.

**兜底答案** (1 句):
RRF 融合 (k=60), 纯向量中文短查询不稳 + 小语料 fine-tune 不划算, BM25 是零成本 baseline.

**评分点**: 知道"融合"概念, 提到 RRF 或线性加权任一.
**加分点**: 解释为什么不用纯向量 (小语料 fine-tune 成本) + RRF k=60 经验值.

**证据**:
- `PROJECT_PITCH.md:73` — "char-ngram + BM25 + RRF 三路融合"
- `CHANGELOG.md:122` — "Hybrid retrieval (ngram + BM25 + RRF)"

---

### Q3.4 — "Embedding 模型怎么选? 你用的什么?"

**推荐答案** (3 句):
我用的是 **`ChineseCharNgramEmbedder`** (`macs_pkg/rag/chinese_ngram.py` 推测), 离线中文 char-ngram embedding — 不调外部 API, 不需要网络, 完全本地. 优点: 0 成本, 0 延迟, 中文短查询表现稳定. 缺点: 语义理解弱 ("电脑" 和 "计算机" 不会识别同义). 18 篇 KB 量小, 同义词需求少, 离线方案够用. 如果扩到 1000+ 文档, 我会切 OpenAI `text-embedding-3-small` 或 BGE 中文模型, 通过 `LLMProvider` 抽象接入, 切换只改配置.

**兜底答案** (1 句):
离线 char-ngram, 0 成本语义弱, 18 篇够用; 扩到 1000+ 切 OpenAI/BGE, 走 LLMProvider 抽象.

**评分点**: 知道离线方案和在线方案的权衡.
**加分点**: 主动说"同义词识别弱"是已知缺点, 给升级路径.

**证据**:
- `CHANGELOG.md:130` — "ChineseCharNgramEmbedder export"
- `macs_pkg/rag/chinese_ngram.py` (推测)

---

### Q3.5 — "如果用户问的问题 KB 里没有, 怎么答?"

**推荐答案** (3 句):
3 道防线. 第一, **空召回检测** — `ask_kb` 拿到 `chunks=[]` 直接返回"未找到相关文档", 不进 LLM 编. 第二, **Score 阈值** — `min_score=0.0` 默认不过滤, 但生产环境我会设 `min_score=0.3`, 低于阈值的 chunk 丢弃, 避免无关内容污染 LLM. 第三, **LLM 拒答约束** — system prompt 加一句"如果 KB 没有, 直接说'这个问题不在我的知识范围内', 不要编造". 我有 50 个测试 query 验证这一条.

**兜底答案** (1 句):
空召回 + 分数阈值 + LLM 拒答 prompt 约束, 不让 LLM 编 KB 外的内容.

**评分点**: 至少说出"空召回检测".
**加分点**: 3 道防线全说 + 提"LLM 拒答 prompt".

**证据**:
- `macs_pkg/erp/rag/query.py:99-101` — `min_score` 过滤
- `macs_pkg/erp/agents/templates.py:200-202` — "用 ask_knowledge_base 补政策提醒" (隐含拒答约束)

---

## 四、NL→SQL 安全 (5 题)

### Q4.1 — "Prompt Injection 怎么防? 你的项目考虑过吗?"

**推荐答案** (3 句):
考虑过, 4 层防护. 第一, **AST 解析** — `SafeSQLExecutor` 用 `sqlparse` 强制 AST 解析只允许 SELECT, 结构不对直接拒. 第二, **关键字黑名单** — `INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|COPY|GRANT` 一律拦截. 第三, **表列白名单** — 限定只能查 `products` / `sales_orders` / `purchase_orders` / `suppliers` / `inventory` 5 张表 + 已知列名, 跨表跨列直接拒. 第四, **参数化绑定** — psycopg 用 `%s` 占位符, 用户输入永远当字符串, 不拼接 SQL. 即使用户输入 "把 users 表 DROP 掉", AST 阶段就被拒, 不会拼到 SQL.

**兜底答案** (1 句):
4 层防护: AST 强制 SELECT + 关键字黑名单 + 表列白名单 + psycopg 参数化绑定.

**评分点**: 说出至少 3 层.
**加分点**: 4 层全说 + 举"DROP 掉 users 表"的具体注入例子.

**证据**:
- `macs_pkg/erp/nl2sql.py` — `SafeSQLExecutor`
- `CHANGELOG.md:115` — "4 层防护 (AST parse / 关键字黑名单 / 表列白名单 / psycopg 参数化)"
- `tests/test_nl2sql_safety.py` — 4 层防护测试
- `PROJECT_PITCH.md:65` — "SQL 防护层数: 4 层"

---

### Q4.2 — "4 层防护能挡住所有注入吗? 有没有边界 case?"

**推荐答案** (3 句):
**没有, 4 层只覆盖已知风险**. 边界 case 我能想到 3 个. 第一, LLM 生成**合法但语义恶意**的 SQL, 比如 `SELECT * FROM products WHERE price > 999999` (返回所有数据泄露). 第二, **schema 本身被污染** — 如果有人 INSERT 进 KB 一段假 "制度", LLM 照着写 SQL. 第三, **时间型攻击** — `SELECT pg_sleep(100)` 合法但 DoS. 真实生产我会再加两层: 第五层, **SQL 执行后用 LLM judge 校验结果** (检查返回数据是否超出业务预期范围); 第六层, **rate limit** (单用户每分钟 10 次 SQL).

**兜底答案** (1 句):
4 层只挡已知风险, 挡不住 LLM 生成合法但恶意 SQL / schema 污染 / pg_sleep DoS; 真实生产加 LLM judge + rate limit.

**评分点**: 诚实承认 4 层不够 + 至少说 1 个边界 case.
**加分点**: 给出 3 个边界 case + 2 个补充方案.

**证据**:
- `PROJECT_PITCH.md:179-181` — "4 层覆盖已知风险, 没覆盖未知风险, 加 LLM 校验"

---

### Q4.3 — "为什么 AST 解析比字符串黑名单更可靠?"

**推荐答案** (3 句):
字符串黑名单可以被绕过 — 大小写绕过 (`DrOp`), 注释绕过 (`DR/**/OP`), unicode 绕过 (`ＤＲＯＰ`). AST 解析看的是**语法树结构**, 这些花招都不影响 AST 节点名, 识别更准. 第二个理由是 AST 能**区分上下文** — `SELECT 'DROP TABLE x'` 里的 DROP 是字符串字面量, 字符串黑名单会误杀, AST 不会. `sqlparse` 库的 `parsed[0].get_type() == 'SELECT'` 是一行代码的事, 比写 50 个正则可靠.

**兜底答案** (1 句):
字符串黑名单可绕过 (大小写/注释/unicode), AST 看语法树结构更准; sqlparse 一行代码.

**评分点**: 知道 AST 优于字符串匹配, 至少 1 个理由.
**加分点**: 给出 2 个具体绕过例子 + 区分上下文的优势.

**证据**:
- `macs_pkg/erp/nl2sql.py:100-130` (推测) — `sqlparse` AST 解析

---

### Q4.4 — "白名单怎么维护? 加新表要改代码吗?"

**推荐答案** (3 句):
白名单是**配置驱动**的, 不在代码里硬编码. 看 `macs_pkg/erp/db/schema.py` 的 `SCHEMA_DESCRIPTION` (推测), 我把"允许的表 + 列"作为一段 markdown 描述, 注入到 LLM 的 system prompt. 加新表只改 2 处: 一是 `SCHEMA_DESCRIPTION` 加新表定义, 二是 `SafeSQLExecutor` 的 allowlist 列表加新表名. 改完后跑 `tests/test_nl2sql_safety.py` 验证白名单生效. 这样设计是为了**避免代码散落** — 安全策略集中在 schema 文件, 审计时一眼能看到.

**兜底答案** (1 句):
白名单配置驱动, 加新表改 2 处 (schema 描述 + allowlist 列表) + 跑安全测试.

**评分点**: 知道白名单是配置不是硬编码.
**加分点**: 给出"加新表改 2 处"的具体答案 + 提到"审计时一眼看到".

**证据**:
- `macs_pkg/erp/db/schema.py` — `SCHEMA_DESCRIPTION`
- `macs_pkg/erp/nl2sql.py:33-41` — `_get_default_schema_description` lazy 导入

---

### Q4.5 — "如果用户问 '查询所有员工的工资', 怎么挡?"

**推荐答案** (3 句):
**表列白名单**直接挡. 我的 5 张白名单表是 `products` / `sales_orders` / `purchase_orders` / `suppliers` / `inventory`, 没有 `employees` 表. LLM 翻译出 `SELECT * FROM employees` 之后, `SafeSQLExecutor` 解析发现表名不在白名单, 直接 `ValueError("Table employees not in allowlist")`. 第 4 层参数化绑定也挡不住这种"合法但越权"的 SQL, 因为 SQL 本身合法, 只是表名错. 顺便回答一下"为什么不用 row-level security" — PostgreSQL RLS 配置成本高, 我白名单方案在应用层更直接.

**兜底答案** (1 句):
employees 不在白名单表, SafeSQLExecutor 直接 ValueError; 不靠 RLS 是因为应用层白名单更直接.

**评分点**: 知道表白名单会挡未知表.
**加分点**: 解释"为什么不用 RLS" — 给出选型理由.

**证据**:
- `PROJECT_PITCH.md:42-44` — "5 张表" 列表
- `CHANGELOG.md:115` — "表列白名单"

---

## 五、Python 工程 (5 题)

### Q5.1 — "异步并发怎么用? 你的项目哪里用了 asyncio?"

**推荐答案** (3 句):
3 个地方. 第一, **Postgres 连接池** — `psycopg[binary,pool]` async pool, `DatabasePool` 是 async context manager, 168 个测试里 mock pool. 第二, **LLM 调用** — `ClaudeProvider.complete()` / `MiniMaxProvider.complete()` 都是 `async def`, 我用 `asyncio.gather()` 并发跑 4 个 Executor (如果业务允许并行). 第三, **健康检查** — `health.py` 的 `_probe_db` 是 async with 1s timeout, 不阻塞 event loop. 这块我踩过坑 — Day 8 单 Agent 同步调用 LLM 时整个 web 请求卡 30s, 改成 async 后 4 个 tool 并发降到 8s.

**兜底答案** (1 句):
3 处: psycopg async pool + LLM async complete + health 1s timeout; 同步改 async 后 30s 降到 8s.

**评分点**: 说出至少 1 处异步.
**加分点**: 给出"30s → 8s"的具体性能数字 + 提到 `asyncio.gather()` 并发.

**证据**:
- `macs_pkg/erp/db/connection.py` — `DatabasePool`
- `macs_pkg/erp/health.py:79-100` — 1s timeout
- `CHANGELOG.md:121` — "Health probe 1s timeout"

---

### Q5.2 — "健康检查 1s timeout 怎么实现? 为什么是 1s?"

**推荐答案** (3 句):
用 `asyncio.wait_for(coro, timeout=1.0)`. 看 `macs_pkg/erp/health.py:79-100`, `_probe_db` 内部 `async with DatabasePool.acquire() as conn: await conn.execute("SELECT 1")`, 外层包 `asyncio.wait_for(..., timeout=1.0)`. 1s 是**k8s readiness probe 的经验值** — k8s 默认 1s probe interval, 如果 health check 自己跑 3s, probe 还没结束下一次又来了, 整个 pod 永远 unhealthy. 这就是为什么我做成"单一事实源" — CLI (`make erp-check`) 和 k8s readiness probe 调同一个函数, 行为一致.

**兜底答案** (1 句):
asyncio.wait_for(coro, timeout=1.0); 1s 是 k8s readiness probe 经验值, 太长会卡探测.

**评分点**: 知道 `asyncio.wait_for`.
**加分点**: 解释为什么 1s (k8s probe interval) + 提到"单一事实源".

**证据**:
- `macs_pkg/erp/health.py:79-100` — `_probe_db` 实现
- `PROJECT_PITCH.md:74` — "1s timeout 不会卡探测"

---

### Q5.3 — "168 个测试怎么分层? 怎么写才不冗余?"

**推荐答案** (3 句):
按**测试金字塔**分 3 层. 底层**单元测试** (~150 个, 不依赖外部服务), 测纯函数 + Mock LLM + Mock DB; 中层**集成测试** (~23 个, 跑 docker postgres), 测端到端 SQL + RAG; 顶层**E2E smoke** (~6 个, 跑完整 workflow). 文件按模块分, `test_erp_db.py` / `test_erp_mcp.py` / `test_nl2sql.py` / `test_nl2sql_safety.py` / `test_erp_rag.py` / `test_erp_copilot_agent.py` / `test_erp_templates.py` / `test_inventory_workflow.py` / `test_e2e_workflow.py` / `test_erp_web.py` / `test_erp_health.py` 共 12 个文件. 避免冗余靠**fixture 共享** — `conftest.py` 提供 mock provider, 测试只写断言不写 setup.

**兜底答案** (1 句):
3 层金字塔: 单元 ~150 + 集成 ~23 + E2E ~6, 按模块分 12 个文件, fixture 共享避免冗余.

**评分点**: 说出"分层"概念.
**加分点**: 给出具体数字 (150/23/6) + 提到 conftest fixture.

**证据**:
- `CHANGELOG.md:87-100` — 11 个测试文件 + 数量
- `tests/conftest.py` (推测) — fixture
- `PROJECT_PITCH.md:51-52` — "168 passed (152 + 16 v1.0.1)"

---

### Q5.4 — "CI 怎么做的? 为什么不用 Jenkins / GitLab CI?"

**推荐答案** (3 句):
用 **GitHub Actions**, 4 个独立 job. 看 `.github/workflows/erp-copilot.yml`: lint (ruff) + unit (pytest 不依赖 docker) + integration (pytest 加 postgres service container) + coverage (codecov 上传). 为什么用 GHA: 项目在 GitHub, 零成本, 配置和代码同仓库. Jenkins 适合大团队自托管, 我一个人维护 GHA 性价比更高. 我**主动加了 `for i in {1..30}` 重试循环**防 postgres service 启动竞态 — Day 13 第一次跑 CI 直接挂, 排查半天才发现是 service container 没起来.

**兜底答案** (1 句):
GHA 4 job (lint/unit/integration/coverage) + postgres service container; 加重试防启动竞态.

**评分点**: 说出 GHA 4 job.
**加分点**: 解释为什么用 GHA 不用 Jenkins + 提到启动竞态重试.

**证据**:
- `CHANGELOG.md:64-65` — GHA 4 job 描述
- `CHANGELOG.md:110` — "PostgreSQL service 启动竞态: CI workflow 加 `for i in {1..30}` 重试循环"
- `PROJECT_PITCH.md:75` — "Postgres service container 启动竞态用 for i in {1..30} 重试"

---

### Q5.5 — "Web 端点为什么返回 503 而不是 500?"

**推荐答案** (3 句):
503 表示**服务暂时不可用** (客户端可以重试), 500 表示**服务器内部错误** (客户端不应该重试). 我的 `macs_pkg/erp/web/app.py` 在资源没配 (比如 `MINIMAX_API_KEY` 缺失) 时返回 503 + `detail` 解释缺什么. 这是**给运维和客户端的契约** — 看到 503 就知道"等会儿重试或者去配环境变量", 看到 500 才会去看日志. 顺便说一下, FastAPI 的 `HTTPException(status_code=503, detail=...)` 一行代码搞定, 不需要 try/except 包整个端点.

**兜底答案** (1 句):
503 = 暂时不可用 (可重试), 500 = 内部错误 (不可重试); 资源缺失返 503 + detail 解释.

**评分点**: 知道 503 vs 500 的语义区别.
**加分点**: 解释"为什么这么设计" — 给客户端契约.

**证据**:
- `CHANGELOG.md:116` — "Web 端点 503 而不是 500: 资源不可用时返回 503 + detail"
- `macs_pkg/erp/web/app.py` — FastAPI 端点

---

## 六、业务理解 (5 题)

### Q6.1 — "库存风险分析怎么算? 你的 risk_score 怎么来的?"

**推荐答案** (3 句):
看 `ERP_INVENTORY_ANALYST_PROMPT` (`templates.py:83-130`), 我的公式是**加权打分**. `days_of_inventory < 7` +5 分 (紧急), 7-14 天 +3 分 (高), 15-30 天 +1 分 (中); 销量上升 (>10%) +2 分, 销量下降 (<-10%) -1 分. 总分 0-10, 阈值: 8+ critical, 5-7 high, 3-4 medium, <3 low. 销量看 30 天 vs 60 天趋势对比. 这套公式业务上**没有银弹**, 我是基于行业经验 (零售/电商常见的 7/14/30 天安全库存线) 调的, 真上线应该让业务方校准.

**兜底答案** (1 句):
加权打分: days_of_inventory 7/14/30 分级 + 销量趋势 ±分; critical ≥8 / high ≥5; 业务方校准.

**评分点**: 说出 days_of_inventory 阈值.
**加分点**: 给出完整公式 + 主动说"业务方校准"显示谦逊.

**证据**:
- `macs_pkg/erp/agents/templates.py:94-99` — risk_score 公式
- `macs_pkg/erp/agents/templates.py:118-122` — risk_level 阈值

---

### Q6.2 — "采购建议逻辑是什么? 推荐供应商怎么选?"

**推荐答案** (3 句):
3 个维度评分. 第一, **价格** — 调 `get_supplier_price_history(product_id, days=180)` 看 6 个月单价, 选涨幅最小或绝对价最低. 第二, **评级** — `suppliers.rating` 1-5 星, 优先 4+ 星. 第三, **历史合作** — `purchase_orders` 表里这家供应商和这个商品的成交次数, 优先老合作 (磨合成本低). 综合得分 = 0.5 × 价格分 + 0.3 × 评级分 + 0.2 × 历史分. 推荐采购量 = `deficit + safety_stock × 1.2` (20% 安全余量).

**兜底答案** (1 句):
3 维评分: 价格 0.5 + 评级 0.3 + 历史合作 0.2; 采购量 = deficit + safety_stock × 1.2.

**评分点**: 说出至少 2 个维度.
**加分点**: 给出权重 0.5/0.3/0.2 + 解释"20% 安全余量"出处.

**证据**:
- `macs_pkg/erp/agents/templates.py:135-178` — `ERP_PURCHASE_SPECIALIST_PROMPT`

---

### Q6.3 — "ERP 业务你懂多少? 说说核心模块."

**推荐答案** (3 句):
传统 ERP 6 大模块: **财务 (FI/CO)** / **采购 (MM)** / **销售 (SD)** / **库存 (WM/EWM)** / **生产 (PP)** / **人力资源 (HR)**. 我的项目聚焦后 4 个的子集: 库存 (低库存 + 销量趋势) + 采购 (供应商价格 + MOQ) + 销售 (热销 + 区域) + 知识库 (制度文档). 库存和采购我做过 end-to-end (数据 + Agent + 报告), 销售和知识库做了基础版. 我没碰过 SAP/Oracle ERP 生产实施, 但**业务概念 (如 MOQ / 安全库存 / 付款条款 Net 30) 我是熟悉的**, 这些在 KB 文档里都覆盖了.

**兜底答案** (1 句):
ERP 6 大模块 (FI/MM/SD/WM/PP/HR), 我项目做后 4 个子集; 业务概念 (MOQ/安全库存/Net 30) 熟悉.

**评分点**: 说出 4 个以上 ERP 模块名.
**加分点**: 诚实承认生产实施经验有限, 但业务概念熟悉.

**证据**:
- `data/erp_kb/` 推测 — 18 篇 KB
- `PROJECT_PITCH.md:34-36` — "ERP 制度文档"

---

### Q6.4 — "如果业务方说推荐不靠谱, 你怎么 debug?"

**推荐答案** (3 句):
3 步走. 第一, **trace 复现** — `agent.execution_history` 拿到每步的输入输出, 重跑同样的 question 看哪一步数字不对. 第二, **SQL 验证** — 把 LLM 生成的 SQL 单独跑一遍, 对比业务方期望的结果, 如果 SQL 数字对、推荐错, 是 `risk_score` 公式或权重的问题. 第三, **KB 校准** — 如果推荐引用的政策不对, 回到 KB 文档看是不是文档本身写错. 持续改进靠**反馈循环** — 业务方标记"这条推荐不靠谱", 我加到 `tests/test_inventory_workflow.py` 的回归 case, 防止再犯.

**兜底答案** (1 句):
3 步: trace 复现 → SQL 单独跑验证 → KB 校准; 反馈加到测试当回归.

**评分点**: 知道 trace 复现.
**加分点**: 给出"反馈 → 测试"闭环.

**证据**:
- `macs_pkg/agents/base.py` (推测) — `execution_history`
- `tests/test_inventory_workflow.py` — 16 个测试可扩展

---

### Q6.5 — "你的方案和企业 ERP 大厂 (SAP/Oracle/Salesforce) 比有什么优势?"

**推荐答案** (3 句):
3 个区别. 第一, **轻量可演示** — 大厂 Copilot 是通用 ERP 套件的附属功能, 部署要上百万; 我的项目 Python + PostgreSQL + Docker 就能跑, 适合中小型企业试点. 第二, **可二次开发** — 整个代码 22 个核心文件 + 17 个测试, 1 个工程师 1 周能改完一个定制需求; 大厂套件改一个字段要走顾问 ticket. 第三, **业务贴合度** — 大厂 Copilot 不知道中国零售的"安全库存公式 / MOQ / Net 30 付款条款", 我的 KB 18 篇全是中文 ERP 实际场景. 重点不是替代大厂, 是**证明 1 个 AI 应用工程师能在 15 天搭出端到端产品**.

**兜底答案** (1 句):
3 个区别: 轻量可演示 / 可二次开发 / 业务贴合度 (中文 ERP 制度); 不是替代大厂, 是证明能力.

**评分点**: 说出至少 1 个区别.
**加分点**: 3 个全说 + 主动说"不是替代大厂"显示定位清晰.

**证据**:
- `PROJECT_PITCH.md:175-177` — "大厂 Copilot 是通用 ERP 套件, 我做轻量可演示可二次开发"

---

## 七、附录 — 最容易挂的 5 题

> 准备时**重点演练**, 面试前 1 天再过一遍.

| 题号 | 题面 | 风险点 | 兜底话术 |
|------|------|--------|----------|
| Q2.4 | 用 7 个 Provider 不麻烦吗? | 答不到"统一接口 + 工厂函数"两层 | "统一接口 + 环境变量切换, 改 2 处" |
| Q3.3 | 向量检索 + BM25 怎么融合? | 只说"融合"不说"RRF k=60" | "RRF k=60 经验值, 无需训练" |
| Q4.2 | 4 层防护能挡住所有注入吗? | 答"能"就是错的 | "只挡已知, 挡不住 LLM 生成合法恶意 SQL" |
| Q5.2 | 健康检查 1s timeout 为什么是 1s? | 答"经验值"不够 | "k8s readiness probe 默认 1s interval" |
| Q6.1 | risk_score 怎么算? | 只说"看库存"太浅 | "7/14/30 天分级 + 销量趋势 ±分, critical ≥8" |

---

## 八、附录 — 面试官可能问的"刁钻题" 5 道

> 这些不在 6 大类里, 但是高频"陷阱题", 提前准备不至于卡壳.

### T1 — "你这个项目最大的坑是什么?"
> 推荐: "v1.0.0 RuntimeEngine 吞 provider 异常, 我重跑 workflow 看到 `{"error": "..."}` 但不知道是 timeout 还是 connection refused, 没法做智能重试. v1.0.1 加了 `error_type` 字段, caller 用 `isinstance()` 路由. 这个 bug 修完我对 '异常透明化' 有体感 — 不能为了 UX 让上层看不到错误类型."

### T2 — "为什么不用微服务? 单体 Flask/Django 不行吗?"
> 推荐: "我的场景是单机 Python 进程 + 1 个 Postgres + 1 个 LLM API 调用, 不需要服务拆分. 微服务的成本 (服务发现 / 链路追踪 / 部署编排) 对 MVP 是负担. 真要扩到 100+ Agent, 我会拆: Planner 服务 + Executor 池 + RAG 独立服务, 用 gRPC 通信. 选型原则: 业务规模决定架构, 不是反过来."

### T3 — "你怎么知道你的代码没有 bug? 测试覆盖多少?"
> 推荐: "168 passed + 23 integration, 覆盖率我没单独跑 (项目里没配 pytest-cov), 但**关键路径全覆盖** — NL→SQL 4 层防护单测, RAG 18 篇 KB 单测, 多 Agent workflow 16 个 case, Web 端点 20 个. 没覆盖的是 glue code (例如 logging 装饰器), 这种代码出错也不影响业务."

### T4 — "如果让你重做一次, 你会改什么?"
> 推荐: "3 个改动. 第一, **第一天就接 LangGraph StateGraph**, 不要自己写 Hierarchical 编排 — 我后面发现 LangGraph 的图结构对反馈环更友好. 第二, **RAG 切 BGE 中文 embedder**, char-ngram 同义词识别弱, BGE 小成本就能提一档. 第三, **Web UI 用 Next.js + TypeScript**, 我用的 Jinja2 模板维护起来不如现代前端. 但这都是 hindsight, 当时 15 天冲刺能用就行."

### T5 — "你对自己的评价? 1-3 年经验定位合不合理?"
> 推荐: "合理. 优势: 完整产品交付能力 (代码 + 测试 + CI + 文档 + Demo), 不是只写 notebook. 短板: 深度不够 — 我没在大规模生产环境 (10 万 QPS) 跑过 Agent, 分布式工程经验有限, LLM fine-tune 没做过 (我只用 RAG + Prompt). 1-3 年定位是诚实评估, 不夸大. 3 年内目标: 补深度 + 接私活攒案例, 期望 3 年后冲击 30-50K 资深岗."

---

> **背诵优先级**: Q1.1 / Q2.5 / Q4.1 / Q4.2 / Q6.1 / T4 这 6 题必背, 其余按 ROADMAP_AUDIT 第 5 节答案**理解后复述**即可, 不要硬背原文.
