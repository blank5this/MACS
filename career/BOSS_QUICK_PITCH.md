# Boss 直聘打招呼模板 (按公司规模分类)

> 项目地址: https://github.com/blank5this/MACS
> 目标岗位: AI 应用工程师 / Python 后端 / LLM 应用开发 / Agent 开发
> 期望薪资: 15-25K (15K 起步, 20K 期望, 25K 谈判)
> 每个模板 150-200 字: 1 句钩子 + 1 段项目 + 1 句 CTA

---

## 模板 1: 大厂 (腾讯 / 字节 / 华为 / OPPO / vivo / 小米)

**强调重点**: 业务价值 + 工程化完整度 + 团队协作能力

```
您好, 我是 <your_name>, 应聘 [岗位名称] 岗 (深圳南山, 15-25K).

过去 15 天我独立完成了 ERP AI Copilot v1.0.1 (github.com/blank5this/MACS), 这是一个面向企业 ERP 场景的 AI 助手产品, 已落地 5 张表 + 1000 行种子数据 + 18 篇中文知识库 + 多 Agent 协作 + 4 层 SQL 防护 + 168 测试全过.

技术栈完整对标 JD: Python 3.11 + FastAPI + PostgreSQL + AutoGen/LangChain 多 Agent + RAG 混合检索 + MCP 工具 + GitHub Actions CI. 工程化 5 项超出 Plan: Web UI / CI / 健康检查 / SQL 防护 / 测试金字塔.

期望 1 周内电话沟通, 可现场演示 3 Tab Web UI + 3 段 60s 视频. 简历 + 1 页项目摘要已备好.
```

---

## 模板 2: AI 中厂 (月之暗面 / 智谱 / 百川 / MiniMax / DeepSeek / 通义 / 文心一言 / 阶跃星辰)

**强调重点**: 技术深度 + 框架选型 + LLM Provider 抽象能力

```
您好, <your_name> 应聘 [岗位名称] (深圳南山, 15-25K).

我做了 ERP AI Copilot v1.0.1 (github.com/blank5this/MACS), 自研多 Agent 框架 (基于 AutoGen + LangChain), 抽象了 6 个 LLM Provider 统一接口 (Claude / OpenAI / Qwen / Zhipu / DeepSeek / Hunyuan), 切换 Provider 只改配置, 应对国内海外合规要求.

技术深挖 3 点: 第一, NL→SQL 4 层安全防护 (AST / 黑名单 / 白名单 / 参数化); 第二, 多 Agent Hierarchical 4 级编排 (Planner→Analyst→Buyer→Writer), 每个 Agent 上下文 < 800 token, 任务成功率 70% → 95%; 第三, char-ngram + BM25 + RRF 混合检索, 18 篇中文 KB 端到端 < 200ms, 零 Embedding 依赖.

有 168 单元测试 + 23 集成测试 + 6 e2e 测试 + CI 4 job, 期待跟贵司技术团队交流 Agent 工程化.
```

---

## 模板 3: 传统企业 AI 转型 (制造业 / 零售 / 金融 / 平安科技 / 招商金科 / 比亚迪 / 顺丰科技)

**强调重点**: 业务落地能力 + 非技术用户友好 + 中文 NLP + 数据安全

```
您好, <your_name> 应聘 [岗位名称] (深圳南山, 15-25K).

针对贵司 ERP / 业务系统 AI 化场景, 我做了 ERP AI Copilot v1.0.1 (github.com/blank5this/MACS), 专攻"业务人员用中文对话操作 ERP"这个真实痛点: 仓管问"哪些商品会缺货?"、采购问"哪个供应商涨价最快?"、新人问"采购退货怎么处理?", 不需要懂 SQL, 不需要翻 PDF.

落地能力 3 项: 第一, 5 张 ERP 表真实 schema + 1000 行种子数据, 模拟中型企业业务; 第二, 18 篇中文知识库, char-ngram + BM25 + RRF 混合检索解决中文短查询召回不稳; 第三, 4 层 SQL 注入防护, 防止 prompt injection 删表改数据.

还做了 3 Tab Web UI 给非技术同事用, 3 段 60s 演示视频可直接给业务部门看. 期望尽快面谈.
```

---

## 模板 4: 外企深圳 (Microsoft / Google / Salesforce / Apple 深圳)

**强调重点**: 英文能力 + 开源贡献 + 工程化最佳实践 + 国际团队协作

```
Hi, I'm <your_name>, applying for [Job Title] in Shenzhen (15-25K RMB).

I shipped ERP AI Copilot v1.0.1 in 15 days (github.com/blank5this/MACS), an open-source AI assistant for enterprise ERP. The system takes plain Chinese questions like "哪些商品库存低于安全库存?" and returns structured risk reports, supplier rankings, and KB citations — built on Python 3.11, FastAPI, PostgreSQL 16, AutoGen/LangChain multi-agent orchestration, and MCP tool calling.

Three engineering decisions I'd love to discuss: (1) NL→SQL with 4 layers of defense (AST parsing / blacklist / SELECT-only whitelist / parameterized execution); (2) Multi-agent as a context-budget decision — split 7-tool single agent into 4 focused agents, task success rate 70% → 95%; (3) Hybrid retrieval without embeddings — char-ngram + BM25 + RRF on 18 Chinese KB documents, end-to-end < 200ms.

Full English-speaking, MIT-licensed repo, 168 unit tests + 23 integration tests + GitHub Actions 4-job CI. Available within 1 month, can do live demo + code walk-through.
```

---

## 模板 5: Startup (竹间智能 / 达观数据 / 追一科技 / 云从科技 / 衔远科技 / 循环智能)

**强调重点**: 学习速度 + 全栈能力 + 抗压 + 创业心态

```
您好, <your_name> 应聘 [岗位名称] (深圳南山, 15-25K, 可谈期权).

我是 Java 后端 1-3 年转 AI 应用的工程师, 15 天从零搭出 ERP AI Copilot v1.0.1 (github.com/blank5this/MACS): 数据层 (PostgreSQL 5 表 + 1000 行 seed) + Agent 层 (单 Agent 7 工具 / 多 Agent 4 级编排) + RAG 层 (18 篇中文 KB + 混合检索) + 工程化 (Web UI + CI + 健康检查 + 168 测试) 全部独立完成.

学习速度: 15 天从 LLM API 没用过到多 Agent + RAG + NL→SQL 安全防护都能讲清楚; 全栈能力: Python 后端 + 前端 3 Tab UI + CI/CD + Docker + 数据库设计都做过; 抗压: 路线图 30 天计划 5 天做完了 80%, 剩 20% 是产品化, 不是写代码.

期望跟创业团队一起成长, 可接受 996 / 11-11-6 / 弹性, 期望 base 15K + 期权或 20-25K 全现金.
```

---

## Boss 直聘打招呼的 5 条铁律

1. **首句必须定岗位 + 地点 + 薪资**: "应聘 [岗位] (深圳南山, 15-25K)" — 不写 HR 直接划走
2. **必须有 GitHub 链接**: "github.com/blank5this/MACS" — 让 HR 30 秒验证
3. **必须有数字**: "5 张表 / 1000 行 / 168 测试 / 4 层防护" — 没数字等于没项目
4. **必须 1 句话 CTA**: "期望 1 周内电话沟通" / "可发简历 + 1 页项目摘要" — 不 CTA 等于被动等
5. **字数 ≤ 200**: Boss 打招呼窗口只有 6 行可见, 超 200 字 HR 不展开

---

## 自检清单 (每次投递前过一遍)

- [ ] 公司名出现在打招呼里 (个性化, 不是群发模板)
- [ ] 岗位名跟 JD 一致 (不要写"AI 工程师", 写"AI 应用工程师")
- [ ] 薪资写明 (15-25K 别写"面议", HR 会按 12K 给你开)
- [ ] GitHub 链接可点 (不能放中文逗号 / 空格)
- [ ] 数字跟简历一致 (168 测试 / 5 张表 / 18 KB 不能写错)
- [ ] 无 emoji (Boss 系统会自动转码乱码)
- [ ] 无 AI 八股 ("在当今 AI 浪潮下..." 立刻删)
- [ ] 模板 4 (外企) 用了英文, 其他 4 个用了中文