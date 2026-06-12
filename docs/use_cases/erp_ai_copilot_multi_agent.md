# Use Case: Multi-Agent Inventory Risk Analysis

> Analyzing 30-day inventory risk and generating purchase recommendations with 4 collaborating agents

## 问题背景

在企业 ERP 运营中,库存风险分析是一项典型的多步骤决策任务。运营经理每周需要回答几个关键问题:哪些 SKU 将在未来 30 天内面临缺货风险?备选供应商有哪些?在考虑交期、单价、最小起订量(MOQ)之后,应该下哪一家的采购单?推荐数量与金额是多少?这些子问题跨越库存、采购、财务三个职能,任何一环遗漏都会让"补货决策"变成一份不完整的 PPT。

传统做法是:运营人员从 ERP 中导出库存与销售预测表,丢给采购;采购再去找供应商询价,反复核对交期;最后由运营助理把数据汇总成周报。整个流程在邮件、Excel、电话之间来回穿梭,通常需要 2-3 天才能完成一轮。一旦中途 SKU 数量或供应商变化,流程就要重做,效率与准确率都难以保障。

更关键的是,这种"分段作业"使得最终报告往往缺乏可追溯性 —— 读者无法快速回答"这条建议来自哪条数据?这个数字是怎么算出来的?"。当企业希望把 ERP Copilot 嵌入到日常工作流中时,必须有一个端到端、可审计、可重放的自动化方案,把"识别风险 → 询价对比 → 起草订单 → 汇总报告"整合为一次调用。

## 解决方案架构

MACS 提供了一个基于 RuntimeEngine 的 **hierarchical 模式多 Agent 工作流**,专门用于库存风险分析。整个流程由 1 个 Planner、2 个 Executor、1 个 Reviewer 协作完成:

```
                +-------------------+
                |   erp_planner     |
                | (PLANNER)         |
                | 接收用户问题       |
                | 输出 3 个子任务     |
                +---------+---------+
                          |
                          v
        +------------------------------+
        |   erp_inventory_analyst      |
        | (EXECUTOR)                   |
        | 查询 ERP: 库存 / 销售预测     |
        | 输出低库存 SKU 列表           |
        +-------------+----------------+
                      |
                      v
        +------------------------------+
        |   erp_purchase_specialist    |
        | (EXECUTOR)                   |
        | 查询供应商、对比单价/交期     |
        | 输出采购建议 (数量 + 金额)    |
        +-------------+----------------+
                      |
                      v
        +-------------------+
        |   erp_report_writer |
        | (REVIEWER)          |
        | 汇总 + 引用 + 审核  |
        | 输出 markdown 报告  |
        +---------+---------+
                  |
                  v
        +-------------------+
        |   WorkflowResult   |
        | plan / analyses /  |
        | purchase_recs /   |
        | final_report       |
        +-------------------+
```

数据流是单向的:Planner 解析用户意图后,生成结构化子任务列表;两位 Executor 顺序执行,前者把分析结果交给后者;Report Writer 在最后整合全部中间产物,生成带引用编号的最终报告,作为整条工作流的唯一对外输出。

## Agent 角色

| Agent | Role | Tools | Output |
| --- | --- | --- | --- |
| `erp_planner` | PLANNER | `parse_intent` | `{"subtasks": [...]}` — 拆解用户问题为 3 个可执行子任务 |
| `erp_inventory_analyst` | EXECUTOR | `query_inventory`, `query_sales_forecast` | `{"low_stock_items": [...]}` — 30 天内可能缺货的 SKU 列表 |
| `erp_purchase_specialist` | EXECUTOR | `query_suppliers`, `compare_price_leadtime` | `{"purchase_recs": [...]}` — 每条低库存 SKU 的供应商推荐 + 数量 + 金额 |
| `erp_report_writer` | REVIEWER | `aggregate_results`, `cite_sources` | `final_report: str` — 200 字左右 markdown 报告,带 `[1]`、`[2]` 引用 |

四个 Agent 的系统提示词(SYSTEM / USER 模板)统一维护在 `macs_pkg.erp.agents.templates` 的 `ERP_TEMPLATES` 字典中,便于跨工作流复用与版本管理。

## 端到端示例

下面以一个真实场景为例,展示 `InventoryRiskWorkflow` 的完整运行轨迹。

**用户输入**:

```text
分析未来 30 天库存风险
```

**Plan 阶段(erp_planner 输出)**:

```python
{
    "subtasks": [
        "查询当前库存与近 30 天销售预测,识别低库存 SKU",
        "为每个低库存 SKU 匹配 2-3 家备选供应商,对比单价与交期",
        "汇总分析结果,生成带引用的最终风险报告"
    ]
}
```

**Analyses 阶段(erp_inventory_analyst 输出)**:

```python
{
    "low_stock_items": [
        {"sku": "WIDGET-001", "on_hand": 120, "forecast_30d": 350, "shortfall": 230},
        {"sku": "GADGET-042", "on_hand":  45, "forecast_30d": 180, "shortfall": 135}
    ]
}
```

**Purchase Recs 阶段(erp_purchase_specialist 输出)**:

```python
{
    "purchase_recs": [
        {"sku": "WIDGET-001", "supplier": "SupplierA", "qty": 250, "unit_price": 120, "total": 30000},
        {"sku": "GADGET-042", "supplier": "SupplierC", "qty": 150, "unit_price": 133, "total": 20000}
    ]
}
```

**Final Report 阶段(erp_report_writer 输出)**:

```markdown
# 30 天库存风险分析报告

经分析,未来 30 天有 2 个 SKU 存在缺货风险:WIDGET-001 与 GADGET-042 [1]。建议立即向 SupplierA 采购 250 件 WIDGET-001(单价 120 元,合计 30,000 元),并向 SupplierC 采购 150 件 GADGET-042(单价 133 元,合计 20,000 元)[2]。本次采购总金额 50,000 元,预计可将断货风险降至 5% 以下。
```

> **引用**: `[1]` 来自 erp_inventory_analyst 的库存与预测数据;`[2]` 来自 erp_purchase_specialist 的供应商对比结果。

最终 `WorkflowResult` 字典包含全部 4 个阶段的产物,既可由前端直接渲染,也可作为审计日志回放整条决策链。

## 代码示例

使用 `InventoryRiskWorkflow` 只需三行核心代码:

```python
from macs_pkg.erp.workflows.inventory_risk import InventoryRiskWorkflow

workflow = InventoryRiskWorkflow(runtime=runtime_engine)  # runtime_engine 来自 RuntimeEngine(mode="hierarchical")
result: WorkflowResult = workflow.run(question="分析未来 30 天库存风险")

print(result["plan"])
print(result["analyses"])
print(result["purchase_recs"])
print(result["final_report"])
```

> 说明:`runtime_engine` 必须以 `mode="hierarchical"` 启动,这样 Planner / Executor / Reviewer 三层角色编排才能生效;若改为 `"flat"` 模式,4 个 Agent 将失去层级调度关系。

## 涉及文件

- `macs_pkg/erp/workflows/inventory_risk.py` — 定义 `InventoryRiskWorkflow`,负责 4 阶段编排与上下文传递
- `macs_pkg/erp/agents/templates.py` — `ERP_TEMPLATES` 字典,4 个 Agent 的 SYSTEM / USER 提示词模板
- `macs_pkg/erp/agents/inventory_analyst.py` — `erp_inventory_analyst` Agent 主体与工具声明
- `macs_pkg/erp/agents/purchase_specialist.py` — `erp_purchase_specialist` Agent 主体与工具声明
- `macs_pkg/erp/agents/report_writer.py` — `erp_report_writer` Agent 主体,负责汇总与引用
- `macs_pkg/erp/agents/planner.py` — `erp_planner` Agent 主体,负责意图解析与子任务拆分
- `macs_pkg/erp/tools/inventory.py` — `query_inventory` / `query_sales_forecast` 工具实现
- `macs_pkg/erp/tools/suppliers.py` — `query_suppliers` / `compare_price_leadtime` 工具实现
- `macs_pkg/erp/schemas.py` — `WorkflowResult`、`PurchaseRec` 等 Pydantic Schema

## 相关用例

- [ERP 知识库助手](./erp_knowledge_assistant.md) — 同一 ERP 域内、单 Agent + RAG 的轻量问答场景,可作为本多 Agent 工作流的前置入口