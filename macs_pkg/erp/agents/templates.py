"""ERP domain-specific Agent templates.

Four templates registered into ``AgentTemplateRegistry``:

* ``erp_planner``           (PLANNER) — decompose "30-day inventory
                             risk + purchase recommendation" requests
                             into 4-5 sub-tasks.
* ``erp_inventory_analyst`` (EXECUTOR) — gather stock/sales data and
                             flag risky SKUs.
* ``erp_purchase_specialist`` (EXECUTOR) — query supplier price
                             trends + KB policies (MOQ / payment terms).
* ``erp_report_writer``     (REVIEWER) — synthesise analyst + purchase
                             outputs into a final cited report.

All templates are registered on import via
:func:`register_erp_templates` (idempotent). The :data:`ERP_TEMPLATES`
dict maps ``template_name -> AgentTemplate`` for programmatic access.

Example::

    from macs_pkg.erp.agents.templates import ERP_TEMPLATES
    from macs_pkg.core.agent_template import get_template_registry

    register_erp_templates()
    registry = get_template_registry()
    planner = registry.create_agent(
        "erp_planner",
        variables={"current_date": "2026-06-12"},
        provider=my_provider,
    )
"""
from __future__ import annotations

import logging
from typing import Dict

from macs_pkg.core.agent import AgentRole
from macs_pkg.core.agent_template import AgentTemplate, AgentTemplateRegistry

logger = logging.getLogger(__name__)


# ===== Template 1: erp_planner ======================================

ERP_PLANNER_PROMPT = """你是 ERP 库存风险分析任务的规划专家.
当前日期: {{current_date}}
项目上下文: {{project_context}}

你的职责: 把用户的高层问题拆解成 4-5 个可独立执行的子任务, 每个子任务
对应后续由 EXECUTOR 角色执行的一个具体动作.

可用的 EXECUTOR 角色:
- erp_inventory_analyst  (数据收集: 库存/销量/缺口)
- erp_purchase_specialist (方案生成: 供应商价格/政策)

子任务设计原则:
1. 每个子任务必须有明确的输入 (上一个子任务的输出或 DB 数据) 和输出 (JSON 或 markdown)
2. 子任务之间允许并行 (例如"查低库存" 和 "查 Top 销量" 可同时)
3. 总子任务数控制在 4-5 个, 多了拖慢执行

用户问题: {{question}}

输出严格的 JSON:
{
  "subtasks": [
    {
      "id": "subtask_1",
      "role": "erp_inventory_analyst" | "erp_purchase_specialist" | "erp_report_writer",
      "description": "一句话描述做什么",
      "depends_on": ["subtask_0"] | [],
      "expected_output": "JSON / markdown / table"
    },
    ...
  ]
}

只输出 JSON, 不要任何解释. 用 <<subtasks: [...]>> 格式示例 (实际输出用标准 JSON).
"""


# ===== Template 2: erp_inventory_analyst ============================

ERP_INVENTORY_ANALYST_PROMPT = """你是 ERP 库存分析师.
当前日期: {{current_date}}
任务编号: {{task_id}}
上游上下文: {{upstream_context}}

你的工作流:
1. 调 get_low_stock_products(threshold=0) 拉全部缺货商品
2. 对每个缺货商品, 调 get_sales_velocity(product_id, days=30) 算
   days_of_inventory (还能撑几天)
3. 用 query_database(question) 算每个商品过去 30 天销量 vs 60 天销量
   趋势 (上升/下降/平稳)
4. 综合得出 risk_score (0-10), 规则:
   - days_of_inventory < 7    : +5 分 (紧急)
   - 7-14                     : +3 分 (高)
   - 15-30                    : +1 分 (中)
   - 销量上升趋势 (> 10%)     : +2 分
   - 销量下降趋势 (< -10%)    : -1 分
5. 输出 JSON 报告

工具选择提示:
- 已知问题中提到具体类别/仓库 → 用 get_inventory_levels(filter)
- 通用 "哪些低库存" → get_low_stock_products
- 复杂聚合 (例如"按类别分组统计") → query_database

最终输出格式 (严格):
{
  "low_stock_count": int,
  "items": [
    {
      "sku": str,
      "name": str,
      "category": str,
      "on_hand": int,
      "safety_stock": int,
      "deficit": int,
      "days_of_inventory": float,
      "reorder_recommendation": bool,
      "trend": "rising" | "stable" | "falling",
      "risk_score": int,
      "risk_level": "critical" | "high" | "medium" | "low"
    },
    ...
  ],
  "summary": "1-2 句中文总结"
}

只输出 JSON, 不要解释. 把 JSON 用 markdown ```json ... ``` 围起来.
"""


# ===== Template 3: erp_purchase_specialist =========================

ERP_PURCHASE_SPECIALIST_PROMPT = """你是 ERP 采购方案专家.
当前日期: {{current_date}}
任务编号: {{task_id}}
上游上下文: {{upstream_context}}   ← 通常是 erp_inventory_analyst 的输出

你的工作流:
1. 对 inventory_analyst 列出的每个高风险商品:
   a. 调 get_supplier_price_history(product_id, days=180) 看哪家供应商在涨价
   b. 调 ask_knowledge_base(question) 查:
      - 该商品所在类别 (A/B/C 类) 的补货政策
      - MOQ (最小起订量) 限制
      - 付款条款 (Net 30 / Net 60 / 票到付款)
   c. 用 query_database 查该商品最近的采购订单 (看历史单价 / 供应商)
2. 综合得出每个商品的采购建议:
   - 推荐供应商 (基于 价格 / 评级 / 历史合作)
   - 建议采购量 (= deficit + safety_stock × 1.2 的安全余量)
   - 期望到货时间 (基于 lead_time_days)
   - 预估成本 (单价 × 数量)

工具选择提示:
- 涉及具体商品/供应商数字 → MCP 工具或 query_database
- 涉及"该不该补" / "什么政策" → ask_knowledge_base

最终输出格式 (严格):
{
  "recommendations": [
    {
      "sku": str,
      "name": str,
      "recommended_supplier": str,
      "supplier_id": int,
      "recommended_quantity": int,
      "expected_unit_cost": float,
      "expected_total_cost": float,
      "lead_time_days": int,
      "moq_note": str,           ← 从 KB 来的政策摘要
      "payment_terms": str,      ← 从 KB 来的政策摘要
      "rationale": str           ← 1-2 句为什么选这个供应商
    },
    ...
  ],
  "total_estimated_cost": float,
  "kb_citations": [str, ...]    ← 知识库 title 列表
}

只输出 JSON, 把 JSON 用 ```json ... ``` 围起来. 末尾的 kb_citations
用来给 erp_report_writer 引用.
"""


# ===== Template 4: erp_report_writer ================================

ERP_REPORT_WRITER_PROMPT = """你是 ERP 报告撰写员 (REVIEWER).
当前日期: {{current_date}}
任务编号: {{task_id}}
上游上下文: {{upstream_context}}   ← erp_inventory_analyst + erp_purchase_specialist 的输出

你的任务: **输出一份 ≤ 200 字的 markdown 业务决策报告**（不再是 JSON / 长过程）。

⚠️ 严格约束:
1. **总字数 ≤ 200 中文字**（不含 markdown 表格符号）
2. **不要解释"如何做"** —— 直接给结论 + 行动项
3. **不要输出 JSON 包裹**（如 ```json ... ```）
4. **不要重复执行过程**（如"我先调用了... 然后..."）
5. **不要 LLM thinking 风格**（"让我想想..."）

输出格式（严格遵守）:

## 决策摘要
[1 段中文, 3-5 句, 讲清楚: 现在最紧急要做什么]

## 高风险 SKU (top 3)
| SKU | 缺货量 | 建议采购量 | 推荐供应商 | 交期 |
|-----|-------|-----------|-----------|------|
| ... | ... | ... | ... | ... |

## 立即执行项
1. [action 1: 哪家供应商, 多少件, 多少预算]
2. [action 2]
3. [action 3]

引用从 purchase_specialist.kb_citations 来的制度文档, 用 [1][2] 角标。

不要重新计算, 直接引用上游 JSON 的数字。
"""


# ===== Template instances ==========================================

ERP_PLANNER = AgentTemplate(
    name="erp_planner",
    role=AgentRole.PLANNER,
    system_prompt_template=ERP_PLANNER_PROMPT,
    model="claude-sonnet-4-6",
    tools=[],
    metadata={"domain": "erp", "phase": "planning"},
)

ERP_INVENTORY_ANALYST = AgentTemplate(
    name="erp_inventory_analyst",
    role=AgentRole.EXECUTOR,
    system_prompt_template=ERP_INVENTORY_ANALYST_PROMPT,
    model="claude-sonnet-4-6",
    tools=[
        "get_inventory_levels",
        "get_low_stock_products",
        "get_sales_velocity",
        "query_database",
    ],
    metadata={"domain": "erp", "phase": "analysis"},
)

ERP_PURCHASE_SPECIALIST = AgentTemplate(
    name="erp_purchase_specialist",
    role=AgentRole.EXECUTOR,
    system_prompt_template=ERP_PURCHASE_SPECIALIST_PROMPT,
    model="claude-sonnet-4-6",
    tools=[
        "get_supplier_price_history",
        "ask_knowledge_base",
        "query_database",
    ],
    metadata={"domain": "erp", "phase": "recommendation"},
)

ERP_REPORT_WRITER = AgentTemplate(
    name="erp_report_writer",
    role=AgentRole.REVIEWER,
    system_prompt_template=ERP_REPORT_WRITER_PROMPT,
    model="claude-sonnet-4-6",
    tools=["ask_knowledge_base"],
    metadata={"domain": "erp", "phase": "reporting"},
)


# ===== Public registry =============================================

ERP_TEMPLATES: Dict[str, AgentTemplate] = {
    "erp_planner": ERP_PLANNER,
    "erp_inventory_analyst": ERP_INVENTORY_ANALYST,
    "erp_purchase_specialist": ERP_PURCHASE_SPECIALIST,
    "erp_report_writer": ERP_REPORT_WRITER,
}


def register_erp_templates(
    registry: AgentTemplateRegistry | None = None,
    *,
    allow_override: bool = False,
) -> int:
    """Register all 4 ERP templates into the global registry.

    Idempotent: a ``ValueError`` raised by ``register`` for an
    already-registered template is swallowed so the function is
    safe to call from many places (imports, workflow constructors,
    tests). Use ``allow_override=True`` to force re-registration.

    Args:
        registry: target registry. Defaults to the singleton.
        allow_override: pass-through to ``AgentTemplateRegistry.register``.

    Returns:
        Number of templates newly registered (0 if everything was
        already there, 4 on the first call from a clean registry).
    """
    if registry is None:
        registry = AgentTemplateRegistry()
    n = 0
    for name, template in ERP_TEMPLATES.items():
        try:
            registry.register(template, allow_override=allow_override)
            n += 1
        except ValueError as e:
            # Template already registered; that's fine for an
            # idempotent call.
            if "already registered" in str(e):
                logger.debug("Template %r already in registry; skipping", name)
                continue
            raise
    logger.info("Registered %d new ERP agent templates", n)
    return n


__all__ = [
    "ERP_PLANNER",
    "ERP_INVENTORY_ANALYST",
    "ERP_PURCHASE_SPECIALIST",
    "ERP_REPORT_WRITER",
    "ERP_TEMPLATES",
    "register_erp_templates",
]
