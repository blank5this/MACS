# MACS → ERP AI Copilot 升级路线图 (AI 工程师版)

> **核心心法**: 停止把 MACS 当成框架开发, 把它当成 ERP AI Copilot 产品开发.
> 这一句话对拿 AI Offer 的价值, 可能比再写 5000 行 Agent 代码都大.

---

## 当前项目状态

**项目名称**: MACS (Multi-Agent Collaboration System)

**GitHub**: [https://github.com/blank5this/MACS](https://github.com/blank5this/MACS)

**当前能力**:
- 多 Agent 协作框架
- Tool Registry
- Context 管理
- Message Routing
- 多模型 Provider 抽象 (6 个)
- RAG Tool
- Search Tool
- Python Tool
- Docker 部署

**当前问题**:
- 更像技术框架, 不像业务产品
- 用户价值不明确
- 面试官难以理解业务场景
- 客户不知道为什么要使用

---

## 核心目标

将:

> MACS Framework

升级为:

> **ERP AI Copilot** — 面向企业 ERP 系统的智能助手

---

## 项目定位

### 不再强调
- "Multi-Agent Framework"
- "Agent Runtime"
- "Agent Infrastructure"

### 开始强调
- **ERP AI Copilot**
- 面向企业 ERP 系统的智能助手
- 支持库存分析 / 销售分析 / 采购分析 / ERP 知识库问答 / 自然语言查询 ERP 数据

---

## 项目架构

```
User
  ↓
Planner Agent
  ↓
Inventory Agent  Purchase Agent  Sales Agent  Knowledge Agent
  ↓
Tool Layer
  ↓
ERP Database  RAG Knowledge Base  External APIs
```

---

## 第一阶段 (15 天) — ERP AI Copilot MVP

### 模块 1: ERP 数据层 (PostgreSQL)

**products**:
- id / sku / name / stock / safety_stock

**sales_orders**:
- id / customer / amount / order_date

**purchase_orders**:
- id / supplier / cost / order_date

**suppliers**:
- id / supplier_name / rating

**目标**: 1000+ 行模拟数据

### 模块 2: Text2SQL Agent

支持问题:
- "哪些商品库存低于安全库存?"
- "最近 30 天销量最高商品是什么?"
- "哪个供应商涨价最快?"

执行流程: Natural Language → SQL Generation → Database Query → Result Analysis

### 模块 3: Inventory Agent

**功能**: 库存风险分析
- "哪些 SKU 未来 30 天可能缺货?"
- 输出: SKU 列表 / 风险等级 / 建议采购数量

### 模块 4: Purchase Agent

**功能**: 采购分析
- "最近哪些供应商涨价最快?"
- 输出: 供应商排名 / 涨价幅度 / 建议采购策略

### 模块 5: Sales Agent

**功能**: 销售分析
- "为什么华东地区销量下降?"
- 输出: SKU 分析 / 客户分析 / 时间趋势分析

---

## 第二阶段 (RAG) — 企业知识库

### 建立 ERP 知识库
- ERP 用户手册
- 仓储管理规范
- 财务管理制度
- 采购流程文档

### Knowledge Agent

支持问题:
- "如何处理采购退货?"
- "如何执行库存盘点?"
- "ERP 入库流程是什么?"

流程: Question → Vector Search → Context Retrieval → Answer Generation

---

## 第三阶段 (真正的多 Agent)

### 业务场景

> "分析未来 30 天库存风险并给出采购建议"

执行:
```
Planner Agent
   ↓
Inventory Agent
   ↓
Purchase Agent
   ↓
Report Agent
   ↓
最终报告
```

### 输出内容

库存风险 → 缺货预测 → 采购建议 → 原因分析 → 最终决策报告

---

## GitHub 升级计划

### README 首页

**项目名称**: ERP AI Copilot
**副标题**: Natural Language Interface for ERP Systems

### Features
- Inventory Risk Analysis
- Purchase Recommendation
- Sales Insight
- ERP Knowledge Assistant
- Natural Language SQL Query

### 增加内容
- Architecture Diagram
- Demo GIF / Video
- Use Cases
- Performance Metrics

---

## 面试准备

### 高频问题 1: 为什么使用多 Agent?

**回答**: 复杂 ERP 分析涉及多个业务领域. 拆分 Agent 可以:
- 降低上下文复杂度
- 提升任务成功率
- 降低 Prompt 长度

### 高频问题 2: 为什么不用单 Agent?

**回答**: 单 Agent 处理库存 / 采购 / 销售时容易上下文膨胀. 拆分后:
- 职责更清晰
- Tool 调用更精准
- 结果更稳定

### 高频问题 3: 如何控制成本?

**回答**: Context 裁剪 / Agent 职责分离 / RAG 过滤 / Cache 机制

### 高频问题 4: 如何处理 Agent 失败?

**回答**: Retry 机制 / Timeout 机制 / Fallback Agent / Human Review

---

## Demo 演示脚本

### Demo 1: 库存风险分析
**输入**: "分析未来 30 天库存风险"
**展示**: Inventory Agent 工作流程

### Demo 2: 采购建议
**输入**: "给出未来采购计划"
**展示**: Purchase Agent 分析结果

### Demo 3: 知识库问答
**输入**: "如何执行库存盘点?"
**展示**: RAG 检索过程

### Demo 4: 多 Agent 协作
**输入**: "分析库存风险并生成采购建议"
**展示**: Planner → Inventory → Purchase → Report → 最终报告

---

## 简历项目描述

> ERP AI Copilot (基于自研 MACS 框架)
>
> 设计并实现面向 ERP 场景的多 Agent 智能助手. 构建 Inventory Agent / Purchase Agent / Sales Agent 及 Knowledge Agent. 支持自然语言转 SQL 查询 / RAG 知识库检索 / 多 Agent 协同决策 / 企业数据分析. 通过 Planner Agent 动态编排任务流程, 实现库存风险预测 / 采购建议生成 / 销售洞察分析.

---

## 目标成果

**15 天后**:
- ERP AI Copilot MVP 完成
- GitHub 项目重构完成
- Demo 视频完成
- 架构图完成

**30 天后**:
- 可用于 AI 岗位面试
- 开始投递 AI 应用工程师

**90 天后**:
- 冲击 15K-25K AI 岗位
- 开始尝试海外 Agent 项目接单

**长期目标**:
```
MACS Framework
   ↓
ERP AI Copilot
   ↓
企业 AI 产品
   ↓
海外 SaaS
```

---

> **最重要的一句话**: 停止把 MACS 当成框架开发, 把它当成 ERP AI Copilot 产品开发.
> **这一个思维转变, 对你拿 AI Offer 的价值, 可能比再写 5000 行 Agent 代码都大.**
