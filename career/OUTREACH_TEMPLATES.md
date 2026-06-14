# 求职信 + 自我介绍 — 3 平台 × 3 长度

> 全部基于 MACS + ERP AI Copilot 项目，**不出现"我熟悉 OpenAI API"** 这种空话，只说**做了什么、解决什么问题、可量化结果**。

---

## 🅰 BOSS 直聘 — 投递信

**适用**：HR 收件箱 / "立即沟通"。HR 看 5 秒，必须第一句抓人。

```
主题：[求职] 甘凯锋 · AI Application Engineer · 6 LLM/5 模式/326 测试的 MACS 多 Agent 框架作者

您好，

我是一个会写代码的 AI 应用工程师，独立开发并开源了 MACS（Multi-Agent
Collaboration Stack）和基于它的 ERP AI Copilot：

· MACS 框架：4 角色 Agent / 5 协作模式 / 6 LLM Provider 抽象 / 326 测试
  https://github.com/blank5this/MACS
· ERP AI Copilot：Text2SQL（4 层 SQL 安全护栏）+ ERP 知识库（混合 RAG）
  + 库存风险分析（多 Agent 工作流）
  🟢 在线：https://macs-erp-copilot.onrender.com

技术栈：Python 3.10+ / asyncio / FastAPI / React 基础 / PostgreSQL /
Java + Spring Boot（之前 5 年）。期望：深圳·南山，15-18k AI 应用工程师
岗位。

附件简历 + GitHub，欢迎随时约面试。

甘凯锋
📱 138-xxxx-xxxx
📧 your.email@example.com
```

---

## 🅱 猎聘 — 投递信

**适用**：猎头邮件 / HR 主动搜索。**关键词密度高**（Agent / RAG / LangChain / LLM），方便 ATS 命中。

```
主题：求职 AI 应用工程师 — Multi-Agent · RAG · Text2SQL 全栈经验

您好，

[硬技能] 6 LLM Provider / 5 Agent 协作模式 / 4 角色 Agent / 326 测试 / 4 层 SQL 安全
[软技能] 独立从 0 到 1 落地 13,000 行核心代码，已 MIT 开源

[项目 1] MACS — Multi-Agent Collaboration Stack
  github.com/blank5this/MACS · 13K 行核心代码
  - 5 协作模式：Hierarchical / Pipeline / Decentralized / Deep Research / Dynamic
  - 4 角色 Agent：Planner / Executor / Reviewer / Tool Agent — 全部继承
    ReactAgent，强制 think→act 生命周期
  - 6 LLM Provider：Claude / GPT-4o / MiniMax / Qwen / DeepSeek / Zhipu / Hunyuan
  - 8 篇架构决策记录（ADR）—— 含 SQL 安全、混合检索、退避策略等
  - 326 个自动化测试，CI 全绿

[项目 2] ERP AI Copilot（基于 MACS 实现）
  🟢 https://macs-erp-copilot.onrender.com
  - Text2SQL：自然语言 → SQL，4 层安全护栏（AST + 关键字 + 语句类型 + 库内只读）
  - ERP 知识库：18 篇采购/库存/审批制度文档，混合 RAG（char-ngram + BM25 + RRF）
  - 库存风险分析：多 Agent 工作流（Planner→Analyst→Specialist→Writer→Reviewer）

[关键词] AI Application Engineer · Multi-Agent · Agent · RAG · Hybrid Retrieval ·
Text2SQL · LangChain · LLM Application · Enterprise AI · AI Copilot · ERP ·
FastAPI · Python · Java · Spring Boot · PostgreSQL · Asyncio

[期望] 深圳·南山 · AI 应用工程师 / Agent 工程师 / AI 后端工程师 · 15-18k · 随时到岗

甘凯锋 · 138-xxxx-xxxx · your.email@example.com
```

---

## 🅲 脉脉 — 站内私信

**适用**：直接找 AI 团队 Leader 或 HR。**短 + 真诚 + 给链接**。

```
[甘凯锋] 您好，看到贵司在招 AI 应用工程师。我刚独立做完一个
Multi-Agent 框架（MACS）+ ERP AI Copilot，已上线，附 2 个链接：

🟢 Demo：https://macs-erp-copilot.onrender.com
⭐ 代码：https://github.com/blank5this/MACS

核心：4 角色 Agent + 5 协作模式 + 6 LLM Provider + 326 测试 + 4 层 SQL
安全护栏 + 混合 RAG。

期望深圳·南山 AI 方向 15-18k，希望可以进一步沟通。
```

---

## 🎤 30 秒自我介绍（电梯版）

> "您好，我叫甘凯锋。我最近半年独立从 0 到 1 做了两个项目：
>
> 一是 **MACS** —— 一个多 Agent 协作框架。设计了 5 种协作模式，让 Planner、Executor、Reviewer、Tool Agent 像团队一样工作。6 家 LLM 一行切换，326 个测试全过。
>
> 二是 **ERP AI Copilot** —— 用 MACS 自己搭的。Text2SQL 让用户问"上个月采购多少"；混合 RAG 让 AI 查采购制度时强制带引用；库存风险是 Planner 协调多 Agent 的多步推理。
>
> 技术栈 Python / asyncio / FastAPI / PostgreSQL，Java 是 5 年后端基本盘。期望深圳·南山 15-18k AI 应用工程师岗位，谢谢。"

---

## 🎤 2 分钟自我介绍（电话 / 视频开场）

> "您好，我叫甘凯锋，深圳本地，5 年 Java 后端基本盘，最近半年转型 AI 应用方向。
>
> **为什么转 AI**：我之前做 ERP 的采购/库存模块，对企业流程熟。但传统 ERP 的人机交互是 90 年代的 —— 填表 + 查报表。我意识到 LLM 能彻底改变这个交互，但需要工程化能力把它变成企业能用的产品。
>
> **做了什么**：
> - **MACS** 框架：13K 行核心代码，4 角色 Agent + 5 协作模式 + 6 LLM 抽象，MIT 开源，326 测试，8 篇 ADR。核心架构决策是 `ReactAgent` 基类强制 think→act 生命周期 —— 防止 Agent 写出'忘了 think 直接 act'的 bug。
> - **ERP AI Copilot**：基于 MACS 实现 3 大功能 —— Text2SQL（4 层 SQL 安全护栏，50+ 注入测试都拒了）、ERP 知识库（18 篇文档的混合 RAG，每个答案带引用）、库存风险分析（多 Agent 协作工作流）。已上线 Render + HF Spaces，全球可访问。
>
> **能力特点**：我是**工程派**。和单纯调 LLM API 不同，我会写 SQL 安全护栏、消息总线、Prometheus 监控、对话内存管理、Prompt 容错解析。这些是企业级 LLM 应用必备，但市面教程里很少提。
>
> **期望**：深圳·南山，AI 应用工程师 / Agent 工程师 / AI 后端工程师方向，15-18k 起步。1 年后希望到 25k+。
>
> 我把 8 篇 ADR 都写得很细，每一篇都是面试可深挖的素材。期待和您聊聊贵司的方向。"

---

## 🎤 5 分钟自我介绍（现场演示场景）

> 在 2 分钟版基础上加 **现场演示**：
>
> "我直接演示一下我做的 ERP AI Copilot。打开 [Render 链接] —— 这是我部署的 2-tab Gradio demo。
>
> 我点 **Tab 1 知识问答**，问：'采购审批流程是什么？' —— 看，这里 0.5 秒内返回，答案后面有 [1][2][3] 引用，悬停能看到原文段落。这是混合 RAG 在工作 —— char-ngram 命中中文短语，BM25 兜底语义。
>
> 切到 **Tab 2 Text2SQL**，问：'上个月采购金额多少？' —— 后端走 4 层护栏：AST 白名单、关键字黑名单、语句类型校验、数据库只读角色。50+ 个对抗测试覆盖 SQL 注入，全部被拒。
>
> 底下的代码是开源的：github.com/blank5this/MACS —— 13K 行核心代码，326 个测试，8 篇架构决策记录（ADR）。
>
> 我最自豪的设计是 `ReactAgent` 基类 —— 它强制 `think → act` 生命周期。`act()` 在 `think()` 之前调用会抛 `RuntimeError`。这一行基类，让 4 个角色 Agent 都不可能写出'忘了 think 直接 act'的 bug —— **bug 类型被消灭在编译期**。
>
> 我的背景：5 年 Java 后端 + Spring Cloud 微服务，主导过 QPS 1200 的核心系统。期望深圳·南山 AI 应用工程师岗位，15-18k。"

---

## 📌 投递时检查清单（每发一份前看）

- [ ] 主题行写了 **岗位名 + 姓名 + 1 个量化亮点**（如 "326 测试"）
- [ ] 第一句就出 **项目 + 链接**，不寒暄
- [ ] 量化结果：326 测试、4 层护栏、6 LLM、5 模式、13K 行
- [ ] 期望薪资 **写明**（15-18k，不要写"面议"）
- [ ] 附了 **GitHub + 在线 Demo** 两个链接
- [ ] 没出现 "熟悉 OpenAI API" 这种空话
- [ ] 没超过 200 字（BOSS）/ 350 字（猎聘）/ 150 字（脉脉）
- [ ] 简历 PDF 已上传附件
