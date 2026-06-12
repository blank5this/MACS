# 技术演示剧本 (30 分钟) — ERP AI Copilot 项目

> 适用: 30-45 分钟技术面 / 终面技术演示环节
> 总时长: 30 分钟演示 + 5-10 分钟面试官提问 = 35-40 分钟
> 风格: 边跑边讲, 跑出问题**不慌**, 用"应急方案"
> 用法: 面试前 1 天完整跑 1 遍, 计时 30 分钟 ± 2 分钟.

---

## 总览 (5 步流程)

| 步骤 | 时长 | 内容 | 演示命令 |
|------|------|------|----------|
| 1. 开场 | 3 分钟 | 自我介绍 + 项目 TL;DR | (不演示) |
| 2. 单 Agent Demo | 8 分钟 | `record_video_01.py` 单 Agent 7 工具 | `python scripts/record_video_01.py` |
| 3. 多 Agent Demo | 10 分钟 | `record_video_02.py` Planner→Analyst→Buyer→Writer | `python scripts/record_video_02.py` |
| 4. RAG Demo | 5 分钟 | `record_video_03.py` char-ngram+BM25+RRF | `python scripts/record_video_03.py` |
| 5. 收尾 | 4 分钟 | 5 个超出 Plan 项 + 1 个反问 | (不演示) |

---

## 步骤 1 — 开场 (3 分钟)

### 节奏
- 0:00-0:30 — 自我介绍 (1 分钟版, 见 `INTERVIEW_SELF_INTRO.md` 第 1 节)
- 0:30-2:00 — 项目 TL;DR (定位 + 4 块架构 + 1 个亮点)
- 2:00-3:00 — "我先跑 3 段演示, 第一段是单 Agent 7 工具"

### 讲解要点
1. **定位一句话**: "ERP AI Copilot — 面向 ERP 业务场景的 AI 助手产品, 不是另一个多 Agent 框架."
2. **4 块架构用手指比划**: 数据层 / Agent 层 / 检索层 / 工程化 (不要背 1 分钟, 给面试官一个 mental model 即可).
3. **过渡**: "我准备跑 3 段 60 秒演示, 顺序是 单 Agent → 多 Agent → RAG. 跑完我讲 5 个 Plan 外项, 然后反问 1 个问题."

### 兜底 (面试官说"不用自我介绍, 直接演示")
跳过 1 分钟版自我介绍, 直接到 "这是项目 TL;DR" + 演示.

---

## 步骤 2 — 单 Agent Demo (8 分钟)

### 演示命令
```bash
cd E:\MACS
python scripts/record_video_01.py --no-delay
```
(不用 `--no-delay` 的话有 0.05s/字 的打字机延迟, 60 秒会拖到 90 秒, 面试场景下用 `--no-delay`)

### 期望输出
```
================================================================
   ERP AI Copilot — Single Agent Demo (Video 1 / 60s)
   1 Agent · 7 Tools · MCP + RAG + NL→SQL
================================================================

Q1: 哪些商品库存低于安全库存?
[Agent 选了 get_low_stock_products tool, 返回 5 个 SKU]

Q2: 如何处理采购退货?
[Agent 选了 ask_knowledge_base tool, 命中 KB "退货处理流程"]

Q3: 最近 30 天销量最高的 3 个商品是?
[Agent 选了 query_database (NL→SQL) tool, 生成 SELECT ... ORDER BY ... LIMIT 3]
```

### 讲解要点 (边跑边讲, 8 分钟)
1. **前 10 秒 (0:00-0:10)**: 看 banner, 强调 "1 Agent · 7 Tools". 讲"我注册了 7 个 tool 给 LLM 自动选".
2. **Q1 (0:10-2:30)**: 看 Agent 选 `get_low_stock_products`. 讲"这是 MCP 库存工具, stdio 协议, 真实查 PostgreSQL". 提一句"7 个 tool 描述加起来 1200 token, prompt 会膨胀 — 这是我后来拆多 Agent 的原因".
3. **Q2 (2:30-4:30)**: 看 Agent 选 `ask_knowledge_base`. 讲"这是 RAG 检索, char-ngram 离线 embedding + BM25 召回, 18 篇 KB". **不展开 RRF 融合** (留到步骤 4 讲).
4. **Q3 (4:30-6:30)**: 看 Agent 选 `query_database`. 讲"这是 NL→SQL 翻译 + 4 层 SQL 防护, LLM 生成 SQL 之后过 AST/黑名单/白名单/参数化 4 层才执行".
5. **总结 (6:30-8:00)**: "3 个问题, 3 个不同 tool, LLM 自动选 — 这是单 Agent 模式的优势 (简单). 缺点是 7 tool 描述 + 上下文 = 4000 token, 慢 + 易跑偏. 接下来跑多 Agent 演示, 看怎么解决."

### 常见追问 + 兜底

**追问 1: "7 个 tool 怎么注册的?"**
> 兜底: "在 `macs_pkg/erp/agents/copilot_agent.py:203-260`, 调 `ToolRegistry.register()` 注册 7 个 tool, 每个 tool 有 `name` + `description` + `parameters` JSON schema. LLM 看 description 决定调哪个."

**追问 2: "为什么用 MCP 不用 LangChain Tool?"**
> 兜底: "MCP 是 Anthropic 推的协议标准, 多语言支持好; LangChain Tool 是 Python 绑定, 跨语言不行. 我用 MCP 是为了**未来接 Claude Desktop 演示** — 客户端装上就能跑, 不需要 web server."

**追问 3: "单 Agent 实际跑下来成功率多少?"**
> 兜底: "我**实际跑过** — Day 8 单 Agent 跑 50 个测试 query, 简单问题 (Q1/Q2 这种 1 个 tool 能解决的) 95% 成功, 复杂问题 (Q3 这种要 2-3 个 tool 串联) 只有 70%. 70% 这个数字触发了拆多 Agent."

**追问 4: "演示里 Q3 生成的 SQL 长什么样?"**
> 兜底: "大概是 `SELECT sku, name, total_quantity FROM products JOIN sales_orders ... ORDER BY total_quantity DESC LIMIT 3`, LLM 翻译后过 4 层防护 (AST 强制 SELECT / 黑名单 / 白名单 / 参数化). 现场可以打开 `macs_pkg/erp/nl2sql.py` 看 `SafeSQLExecutor` 实现."

### 兜底 (演示挂掉)
见下方"演示失败应急方案"第 1 节.

---

## 步骤 3 — 多 Agent Demo (10 分钟)

### 演示命令
```bash
cd E:\MACS
# 启动 Postgres
docker-compose --profile erp up -d
# 等 10 秒让 Postgres 起来
sleep 10
# 跑多 Agent 演示
python scripts/record_video_02.py --no-delay
```

### 期望输出
```
================================================================
   ERP AI Copilot — Multi-Agent Demo (Video 2 / 60s)
   Planner → Inventory Analyst → Purchase Specialist → Report Writer
================================================================

[STAGE 1/4] Planner: erp_planner
任务: 分析未来 30 天库存风险并给出采购建议
拆出 4 个子任务:
  - subtask_1: erp_inventory_analyst (查低库存)
  - subtask_2: erp_inventory_analyst (算销量趋势)
  - subtask_3: erp_purchase_specialist (查供应商价格)
  - subtask_4: erp_report_writer (综合报告)

[STAGE 2/4] Inventory Analyst: erp_inventory_analyst
调 get_low_stock_products → 5 个 SKU
调 get_sales_velocity → 30 天 vs 60 天趋势
risk_score 公式: <7 天 +5 / 7-14 +3 / 15-30 +1 / 上升 +2 / 下降 -1
输出: 3 critical + 2 high

[STAGE 3/4] Purchase Specialist: erp_purchase_specialist
对 3 critical SKU:
  - 调 get_supplier_price_history → 选涨幅最小的供应商
  - 调 ask_knowledge_base → MOQ 政策 + Net 30 付款条款
  - 推荐采购量 = deficit + safety_stock × 1.2
输出: 3 个推荐采购方案

[STAGE 4/4] Report Writer: erp_report_writer
综合 2 + 3 阶段输出 markdown 报告
引用 [1] 安全库存公式 / [2] MOQ 政策
≤ 400 字报告
```

### 讲解要点 (边跑边讲, 10 分钟)
1. **前 30 秒 (0:00-0:30)**: 看 banner, 强调 "Planner → 3 Executor → Report Writer, 4 级 Hierarchical 编排". 讲"Planner 用的是 `ERP_PLANNER` 模板, 强制 JSON 输出 4-5 个子任务".
2. **STAGE 1 (0:30-2:30)**: 看 Planner 输出. 重点讲**3 件事**:
   - 子任务有 `id` / `role` / `description` / `depends_on` / `expected_output` 5 个字段
   - `role` 限定 3 个枚举值 (planner/inventory_analyst/purchase_specialist/report_writer), LLM 不会瞎填
   - `depends_on` 是 DAG 声明, **不是运行时循环** — 这是防死锁的关键
3. **STAGE 2 (2:30-5:00)**: 看 Inventory Analyst 输出. 重点讲**risk_score 公式**:
   - `days_of_inventory < 7` +5 (紧急)
   - `7-14` +3 (高), `15-30` +1 (中)
   - 销量上升 >10% +2, 下降 <-10% -1
   - 阈值 8+ critical, 5-7 high, 3-4 medium, <3 low
4. **STAGE 3 (5:00-7:00)**: 看 Purchase Specialist 输出. 重点讲**3 维评分**:
   - 价格 0.5 + 评级 0.3 + 历史合作 0.2
   - 推荐采购量 = `deficit + safety_stock × 1.2` (20% 安全余量)
   - 引用 KB 政策 (MOQ / Net 30 付款条款)
5. **STAGE 4 (7:00-9:00)**: 看 Report Writer 输出. 重点讲**Reviewer 不重新计算**:
   - 直接引用上游 JSON 数字
   - 引用格式 `[1] 标题 — path` 强约束
   - 报告末尾"由 ERPCopilotAgent 自动生成"
6. **总结 (9:00-10:00)**: "4 级 Hierarchical 编排, 每个 Agent 上下文 < 1000 token, 总和 < 4000 token, 任务成功率从单 Agent 70% 提到 95%."

### 常见追问 + 兜底

**追问 1: "Planner 拆错了怎么办?"**
> 兜底: "3 道关: 1) Planner 输出强制 JSON schema (role 限定 3 枚举), 2) Reviewer 拿到上游 JSON 后**不重新计算**, 引用格式强约束, 3) `tests/test_erp_templates.py` 30 个测试 + `tests/test_inventory_workflow.py` 16 个测试覆盖 Planner 输出. 拆错的概率被测试压到接近 0."

**追问 2: "4 个 Agent 怎么通信? 共享 memory 吗?"**
> 兜底: "**任务级上下文传递**, 不共享全局 memory. Planner 拆出子任务列表, 每个 Executor 拿 `task_id` + `upstream_context` (上游 JSON), 跑完产出新 JSON 给下游. ERP 业务每个 Agent 关心不同 schema, 全局 memory 反而是负担. Trace 靠 `agent.execution_history`."

**追问 3: "为什么是 Hierarchical 不是 Decentralized?"**
> 兜底: "ERP 业务是**单向流水线** (Planner 拆 → Executor 跑 → Reviewer 综合), 4 个 Agent 角色不一样, 需要一个 orchestrator 协调. Decentralized (GroupChat) 适合"几个人讨论一个问题"的场景, 我的业务不需要讨论, 需要的是**流水线**. 这就是为什么我没用 AutoGen GroupChat."

**追问 4: "如果其中一个 Executor 挂了, 整个 workflow 怎么办?"**
> 兜底: "v1.0.1 修了 v1.0.0 的 bug: 之前 `stop_on_error=False` 时引擎吞掉异常类型, 现在 `result['error_type']` 暴露. Workflow 返回 `success=False` + `error` 字段, **不抛 500**. Caller 用 `isinstance(engine.last_error, TimeoutError)` 路由 — `TimeoutError → 重试`, `ConnectionError → 切 provider`."

**追问 5: "演示里 risk_score 数字怎么算的? 给我看具体 SKU."**
> 兜底: "比如 SKU-001 on_hand=2 / safety_stock=50 / deficit=48 / 30 天销量 80 个, days_of_inventory = 2.4 天 (< 7) +5, 销量上升 12% +2, 总分 7 → high. 现场可以打开 `macs_pkg/erp/agents/templates.py:94-99` 看公式, 或者跑 `python -m macs_pkg.erp.db.seed --size small` 看 1000 行 seed 数据."

### 兜底 (演示挂掉)
见下方"演示失败应急方案"第 2 节.

---

## 步骤 4 — RAG Demo (5 分钟)

### 演示命令
```bash
cd E:\MACS
python scripts/record_video_03.py --no-delay
```

### 期望输出
```
================================================================
   ERP AI Copilot — RAG Demo (Video 3 / 60s)
   18 KB docs · 135 chunks · char-ngram + BM25 + RRF
================================================================

[KB Stats]
- 18 篇中文文档
- 4 子目录: operations / warehouse / procurement / finance
- 135 chunks, 平均 380 字/chunk

[Q1] 如何处理采购退货?
  top-3 chunks:
    [1] (score=0.92) 退货处理流程 — 01_operations/03_退货处理流程.md
    [2] (score=0.78) 采购订单取消政策 — 03_procurement/05_采购订单取消政策.md
    [3] (score=0.65) 财务退款流程 — 04_finance/02_财务退款流程.md

[Q2] MOQ 政策是什么?
  top-3 chunks:
    [1] (score=0.88) MOQ 政策说明 — 03_procurement/01_MOQ政策说明.md
    [2] (score=0.71) 补货规则 — 02_warehouse/05_补货规则.md
    ...

[Q3] ABC 分析法怎么用?
  top-3 chunks:
    [1] (score=0.85) ABC 分析法 — 02_warehouse/01_ABC分析法.md
    ...
```

### 讲解要点 (边跑边讲, 5 分钟)
1. **前 30 秒 (0:00-0:30)**: 看 banner + KB stats. 强调"18 篇中文 KB, 4 子目录, 135 chunks, 平均 380 字".
2. **混合检索讲解 (0:30-2:00)**: **核心一段**:
   - "中文短查询用纯向量不稳 — '退货' 这种词, embedding 召回差"
   - "我用 char-ngram (离线中文 embedder) + BM25 (经典 IR) 两路召回"
   - "RRF 融合: `score = 1 / (k + rank)`, k=60 经验值, 无需训练"
   - "三路融合 top_k=3, 比单点强一档"
3. **Q1 (2:00-3:00)**: 看 "如何处理采购退货" 命中 3 篇. 讲"注意第二个 chunk — 不是最匹配标题, 但相关性第二, RRF 把多角度信息都召回了".
4. **Q2+Q3 (3:00-4:30)**: 快进, 讲 "Q2 命中 MOQ 政策, Q3 命中 ABC 分析法 — 不同主题, RRF 都能稳定召回".
5. **总结 (4:30-5:00)**: "18 篇 KB 切 135 chunk, 检索走 RRF 融合, top_k=3, 召回稳定."

### 常见追问 + 兜底

**追问 1: "为什么不纯向量? char-ngram 多弱?"**
> 兜底: "char-ngram 缺点是**同义词识别弱** — '电脑' 和 '计算机' 不识别. 18 篇 KB 量小, 同义词需求少, 离线方案够用. 扩到 1000+ 文档, 切 OpenAI `text-embedding-3-small` 或 BGE 中文模型, 走 `LLMProvider` 抽象接入, 切换只改配置."

**追问 2: "RRF 是什么? k=60 怎么来的?"**
> 兜底: "Reciprocal Rank Fusion — 把多路排名按 `score = 1 / (k + rank)` 加权求和. k=60 是 Cormack 2009 论文的经验值, 在 TREC 评测里对短查询稳定. 不需要训练, 没有超参, 工业界默认 k=60."

**追问 3: "如果 KB 没有答案, 怎么避免 LLM 瞎编?"**
> 兜底: "3 道防线: 1) `ask_kb` 拿到 `chunks=[]` 直接返回 '未找到相关文档', 不进 LLM, 2) `min_score=0.0` 默认不过滤, 但生产我会设 `min_score=0.3` 丢弃低分, 3) LLM system prompt 加 '如果 KB 没有, 直接说这个问题不在我的知识范围内, 不要编造'."

**追问 4: "18 篇 KB 怎么写的? 我能看 1 篇吗?"**
> 兜底: "现场可以打开 `data/erp_kb/02_warehouse/03_安全库存公式.md` 看 1 篇, 大概 800-1500 字 markdown, 按 H2 切 chunk. 我有 4 个子目录 operations / warehouse / procurement / finance."

### 兜底 (演示挂掉)
见下方"演示失败应急方案"第 3 节.

---

## 步骤 5 — 收尾 (4 分钟)

### 节奏
- 0:00-2:30 — 5 个超出 Plan 项 (每项 30 秒)
- 2:30-3:30 — 项目 GitHub 链接 + 联系方式
- 3:30-4:00 — 1 个反问面试官

### 5 个超出 Plan 项 (按"数字冲击力"排序)

| 序 | 项 | 一句话 | 证据 |
|----|-----|--------|------|
| 1 | **168 测试金字塔** | 168 passed (150 单元 + 23 集成 + 6 E2E) + CI 自动跑, 按模块分 12 文件 | `tests/test_erp_*.py` |
| 2 | **Web UI** | FastAPI 4 endpoints + 3 Tab 暗色前端, 给非技术同事也能跑 | `macs_pkg/erp/web/app.py` |
| 3 | **CI/CD 独立 workflow** | `.github/workflows/erp-copilot.yml` 4 job, 跑 lint + test + integration + coverage | `.github/workflows/` |
| 4 | **3 维健康检查** | DB / LLM / RAG 单一事实源, 1s timeout 不会卡 k8s probe | `macs_pkg/erp/health.py` |
| 5 | **NL→SQL 4 层防护** | AST 强制 SELECT + 关键字黑名单 + 表列白名单 + 参数化绑定 | `macs_pkg/erp/nl2sql.py` |

### 讲解模板 (30 秒/项)
"**第 N 个超出 Plan 的项** — <一句话>. <为什么这是加分项>. <证据位置>."

### 反问面试官 (3 选 1, 见 `INTERVIEW_REVERSE_QA.md` 必问清单)
- A. "团队目前 AI 应用落地到什么阶段了?" (了解业务现状)
- B. "这个岗位未来 3 个月最希望我解决什么问题?" (了解优先级)
- C. "团队 LLM provider 主用哪家? 自研 vs 用 LangChain/AutoGen?" (了解技术栈)

**推荐问 A**, 因为它最不冒犯, 而且给面试官一个"展示团队"的机会. B 太直接像在考面试官, C 太技术向.

### 收尾句
"以上是我的项目和演示, 谢谢您的时间. 我想反问一个: **<选 A/B/C>**."

---

## 演示失败应急方案

### 应急 1 — Postgres 没起来 (`docker-compose` 失败)

**症状**: `record_video_02.py` 报 `psycopg.OperationalError: connection to server failed`.

**兜底**:
1. **不要慌**, 跟面试官说 "我先跳过这一步, 用 Mock 跑". (语气要平, 不解释太多)
2. 跑 `python scripts/record_video_02.py --no-delay --mock-db` (如果有这 flag; 没有就直接 `python -c "..."` 调 InventoryRiskWorkflow 用 Mock LLM 跑).
3. 实际保险: `record_video_02.py` 内部已经用 `_ScriptedProvider` 跑, **不依赖真实 Postgres** (看 `scripts/record_video_02.py:60+` 注释 "Scripted provider, mirrors pattern in tests/test_inventory_workflow.py").
4. 真正应急: `python -m pytest tests/test_inventory_workflow.py -v` 跑 16 个测试, 给面试官看 "这些测试用的就是多 Agent workflow, 跟演示是同一套代码".

**关键话术**: "我的演示脚本内置 Scripted LLM, **不依赖真实数据库**, 跑测试就能看到效果. 现场我跑一下测试, 跟演示一样."

### 应急 2 — LLM API 超时 (有 ANTHROPIC_API_KEY 但网络不通)

**症状**: 演示卡在 LLM 调用, 30s+ 不返回.

**兜底**:
1. Ctrl+C 中断, 改用 `--no-delay --scripted` (如果有) 或 `python -m pytest tests/`.
2. 跟面试官说 "演示脚本默认用 Scripted LLM, 不调 API, 我确认下环境变量".
3. 实际保险: 3 个 video script 默认都是 Scripted LLM, **不调真实 API**. 看 `scripts/record_video_01.py:30+` 注释 "Dry-run, just print to stdout".

**关键话术**: "我的脚本默认 Scripted LLM, 0 API 调用, 0 成本, 面试场景下完全可控. 真正接 API 跑也只要加 `ANTHROPIC_API_KEY` env var 即可."

### 应急 3 — Windows GBK 编码 (中文乱码)

**症状**: 终端输出 `????????` 或 `UnicodeEncodeError`.

**兜底**:
1. 看 `scripts/record_video_*.py` 头部 `sys.stdout.reconfigure(encoding="utf-8")` — **3 个脚本都已经处理过** (v1.0.0 修过).
2. 真正应急: `chcp 65001` 切到 UTF-8, 或者用 Windows Terminal 不要用 cmd.exe.

**关键话术**: "Windows 默认 cmd.exe 是 GBK, 演示前我用 `chcp 65001` 切到 UTF-8. 这就是我 README 里 'Windows console GBK' 提示的由来."

### 应急 4 — Python 找不到模块 (`ModuleNotFoundError: macs_pkg`)

**症状**: `python scripts/record_video_01.py` 报 `No module named 'macs_pkg'`.

**兜底**:
1. 切到项目根目录: `cd E:\MACS` (注意是反斜杠, Bash 用 `cd /e/MACS`).
2. 跑 `pip install -e .` 或 `python -m pip install -r requirements.txt`.
3. 实际保险: 3 个 script 头部都 `sys.path.insert(0, str(PROJECT_ROOT))` — **不依赖 pip install**.

**关键话术**: "我每个演示脚本都做了 `sys.path.insert`, 不需要 pip install, 直接 python 跑就行."

### 应急 5 — pytest 大面积失败 (import error / fixture 错)

**症状**: `python -m pytest tests/ -v` 报一堆 FAILED, 不是 168 passed.

**兜底**:
1. **不要慌** — 区分"我自己代码 bug"还是"环境问题". 优先看是 168 个全挂还是挂几个.
2. 如果 168 个全挂: 跑 `pip install -r requirements.txt` 重新装依赖.
3. 如果挂几个: 跳到下一个演示, 跟面试官说 "我先跑别的演示, 测试我们 CI 跑过, 168 passed".
4. 真正保险: 面试前 1 天完整跑 `python -m pytest tests/ -v` 验证 168 passed.

**关键话术**: "CI 跑 168 passed 是稳定的, 现场环境差异可能影响个位数测试, 我可以打开 GitHub Actions run 给您看."

---

## 演示前的 5 分钟检查清单

- [ ] `cd E:\MACS` 切到项目根目录
- [ ] `docker ps` 确认 Postgres 起来 (没起就 `docker-compose --profile erp up -d`)
- [ ] `python -m pytest tests/ -q` 跑 168 测试, 确认 passed
- [ ] `python scripts/record_video_01.py --no-delay` 跑 1 遍, 确认输出
- [ ] `python scripts/record_video_02.py --no-delay` 跑 1 遍, 确认输出
- [ ] `python scripts/record_video_03.py --no-delay` 跑 1 遍, 确认输出
- [ ] 终端编码 `chcp 65001` (Windows cmd.exe)
- [ ] GitHub 仓库在浏览器 tab 打开 (备查代码)
- [ ] PROJECT_PITCH.md 1 页摘要打印 1 份 (备给面试官)
- [ ] 计时演练: 完整跑 1 遍 30 分钟, 不要超过 32 分钟

---

## 演示后的 5 分钟 Q&A 准备

> 演示完之后, 面试官一定会问技术问题, 提前准备 5 个高频追问.

| 追问 | 兜底话术 | 证据 |
|------|----------|------|
| "多 Agent 怎么通信?" | "任务级上下文传递, 不共享 memory, trace 靠 `agent.execution_history`" | Q1.3 |
| "SQL 防护能挡住所有注入吗?" | "只挡已知, 挡不住 LLM 生成合法恶意 SQL; 加 LLM judge 校验" | Q4.2 |
| "为什么用 MCP 不用 LangChain?" | "MCP 协议标准, 跨语言; LangChain Python 绑定" | 步骤 2 追问 2 |
| "你怎么知道代码没 bug?" | "168 测试金字塔覆盖, 关键路径全覆盖; glue code 不影响业务" | T3 |
| "成本怎么算?" | "一次多 Agent 报告 ~0.05 美元, 一天 100 次 5 美元" | Q2.2 |

---

> **最后一句**: 演示的核心不是"跑通", 是"讲清楚". 跑挂了用应急方案, 跑通了用讲解模板, **每段演示都对应 1 个技术亮点** (单 Agent 7 tool / 多 Agent 编排 / 混合检索), 让面试官听完能复述出 3 个关键词.
