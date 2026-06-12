# ERP AI Copilot — 15天冲刺计划

> **目标**：将 MACS 从通用多Agent协作框架转型为聚焦业务价值的 **ERP AI Copilot**
> **日期**：2026/06/11 起
> **适用版本**：MACS v0.2.0 → v1.0.0-erp-copilot
> **时间预算**：30 hrs/周（工作日 2h × 5 + 周末 16-20h）

---

## 一、最终交付物

1. 完整 `macs_pkg/erp/` 子包（数据库、NL→SQL、多Agent、RAG、Web UI）
2. 3 段 1 分钟 Demo 视频（库存风险 / 采购建议 / 知识库）
3. 重构后的 GitHub `README.md`，定位为 "ERP AI Copilot"
4. 端到端 CI 通过，PyPI + Docker Hub 自动发布

---

## 二、整体策略

**扩展，不重写**。当前 `E:\MACS` 代码库已经是目标产品的 60-70%：

- ✅ 已有 `AgentTemplateRegistry`（含 `erp_knowledge_expert` 模板）
- ✅ 已有可运行的 `examples/erp_knowledge_assistant.py`
- ✅ 已有完整 `MCP server`（stdio + HTTP/SSE）
- ✅ 已有 `RAGEngine`（中文char-ngram + BM25 + RRF）
- ✅ 已有 `RuntimeEngine` + Hierarchical 协作模式
- ✅ 已有 6 家 LLM Provider（Claude、OpenAI、MiniMax、Qwen、Zhipu、DeepSeek、Hunyuan）
- ✅ 79 个测试通过，CI 矩阵 Python 3.10/3.11/3.12，Docker 多架构

**新增**集中在：
- `macs_pkg/erp/` 子包（业务层）
- `data/erp_kb/` 知识库内容
- `docs/videos/` 演示视频
- 重构 README 和 CHANGELOG

---

## 三、15天详细任务

### Day 1（周一 2h）：项目骨架 + Docker Postgres

**目标**：`macs_pkg/erp/` 目录结构，Postgres 容器跑起来。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/__init__.py` 和子目录 `db/`、`tools/`、`agents/`、`rag/`、`prompts/`、`workflows/`、`web/`
- [ ] 修改 `docker-compose.yml`：新增 `postgres` 服务（postgres:16-alpine，端口 5432，卷 `pgdata`）
- [ ] 新建 `.env.example`：`POSTGRES_DB=erp_copilot`、`POSTGRES_USER=erp`、`POSTGRES_PASSWORD=erp_pass`
- [ ] 修改 `requirements.txt`：增加 `psycopg[binary,pool]>=3.2`、`sqlparse>=0.5`

**验证**：
```bash
docker compose up -d postgres
docker compose exec postgres psql -U erp -d erp_copilot -c "SELECT 1"
```

---

### Day 2（周二 2h）：Schema 定义

**目标**：4 张核心表 + `SCHEMA_DESCRIPTION`（给 NL→SQL 用）。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/db/connection.py`：封装 `psycopg_pool.ConnectionPool`
- [ ] 新建 `macs_pkg/erp/db/schema.py`：5 张表 DDL
- [ ] 新建 `macs_pkg/erp/db/SCHEMA_DESCRIPTION`：用于 prompt 注入

**Schema**：
```sql
-- products
product_id SERIAL PK, sku VARCHAR(32) UNIQUE, name VARCHAR(128),
category VARCHAR(64), unit_price NUMERIC(12,2), safety_stock INT DEFAULT 50

-- suppliers
supplier_id SERIAL PK, name VARCHAR(128), contact_email VARCHAR(128),
rating NUMERIC(3,2), payment_terms VARCHAR(64)

-- purchase_orders
po_id SERIAL PK, supplier_id FK, product_id FK, quantity INT,
unit_cost NUMERIC(12,2), order_date DATE, expected_delivery DATE,
status VARCHAR(16)  -- pending|received|cancelled

-- sales_orders
so_id SERIAL PK, product_id FK, quantity INT, unit_price NUMERIC(12,2),
sale_date DATE, customer_region VARCHAR(32)

-- inventory
product_id PK FK, warehouse_id INT, on_hand INT, last_counted DATE
```

---

### Day 3（周三 2h）：测试数据生成

**目标**：1000+ 条确定性种子数据。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/db/seed.py`：`seed_database(pool, scale="small"|"medium"|"large")`
- [ ] 新建 `scripts/seed_erp_db.py` CLI
- [ ] 新建 `tests/test_erp_db.py`

**参数**：
- small = 300 行/事实表
- medium = 1000 行/事实表
- large = 5000 行/事实表
- 固定 `random.Random(42)` 保证可复现

**验证**：
```bash
python scripts/seed_erp_db.py --scale medium
psql -U erp -d erp_copilot -c "SELECT count(*) FROM sales_orders"  # → 1000
```

---

### Day 4（周六 8h）：MCP 工具层

**目标**：把 ERP 查询暴露为 MCP 工具。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/tools/inventory_tools.py`：5 个 async 函数
  - `get_inventory_levels(product_id=None, category=None)`
  - `get_low_stock_products(threshold=50)`
  - `get_supplier_price_history(product_id, days=180)`
  - `get_top_selling_products(start_date, end_date, limit=10)`
  - `get_sales_velocity(product_id, days=30)`
- [ ] 新建 `macs_pkg/erp/tools/server.py`：`build_erp_mcp_server() -> MCPServer`
- [ ] 新建 `tests/test_erp_mcp.py`

**复用**：`MCPServer`（`macs_pkg/mcp/server.py:55-90` 的装饰器模式）

**验证**：
```bash
python -c "from macs_pkg.erp.tools.server import build_erp_mcp_server; print(list(build_erp_mcp_server()._tools.keys()))"
# → 5 个工具名
```

---

### Day 5（周一 2h）：NL→SQL 核心

**目标**：自然语言转 SQL，严格 JSON 契约。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/nl2sql.py`：
  - `class NLSQLResult(BaseModel)`：`sql`, `explanation`, `params`, `confidence`
  - `class NL2SQLTranslator.translate(question)`
- [ ] 新建 `macs_pkg/erp/prompts/nl2sql_system.txt`：5 个 one-shot 例子
- [ ] 新建 `tests/test_nl2sql.py`：8 个 golden 问题

**Prompt 关键约束**：
- 角色：expert PostgreSQL analyst
- 只输出 JSON
- `SELECT` only
- 必须参数化（`%s` 占位符）
- 禁止 `INSERT/UPDATE/DELETE/DROP/ALTER`

**复用**：`ClaudeProvider`、`MiniMaxProvider`（fallback）

---

### Day 6（周二 2h）：NL→SQL 安全网

**目标**：SQL 验证器 + 安全执行器。

**任务清单**：
- [ ] `SQLValidator`：拒绝非 SELECT、多语句、黑名单关键字
- [ ] `SafeSQLExecutor.execute(question) -> dict`
- [ ] 新建 `tests/test_nl2sql_safety.py`：prompt injection 用例

**安全规则**：
- 黑名单：`INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|COPY|GRANT`
- 拒绝 `;` 后跟第二条语句
- 表/列必须在白名单内
- 用 `sqlparse.parse()` 兜底正则

---

### Day 7（周六 8h）：RAG 知识库

**目标**：把 ERP 操作手册/仓储/采购/财务制度摄入现有 RAG 引擎。

**任务清单**：
- [ ] 新建 `data/erp_kb/01_operations/` 6 篇 md
- [ ] 新建 `data/erp_kb/02_warehouse/` 4 篇 md
- [ ] 新建 `data/erp_kb/03_procurement/` 4 篇 md
- [ ] 新建 `data/erp_kb/04_finance/` 3 篇 md
- [ ] 新建 `macs_pkg/erp/rag/indexer.py`
- [ ] 新建 `macs_pkg/erp/rag/query.py`
- [ ] 新建 `tests/test_erp_rag.py`

**复用**：`RAGEngine`、`ChineseCharNgramEmbedder`、`Citation`

**知识库示例问题**：
- "如何处理采购退货？"
- "如何执行库存盘点？"
- "安全库存计算公式是什么？"
- "三方匹配是什么意思？"

---

### Day 8（周日 8h）：单 Agent 混合工具（Video 1）

**目标**：单 Agent 同时能用 MCP 工具 + RAG + NL→SQL。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/agents/copilot_agent.py`：`ERPCopilotAgent(ToolAgent)`
- [ ] 新建 `macs_pkg/erp/prompts/copilot_system.txt`
- [ ] 新建 `examples/erp_copilot_single_agent.py`
- [ ] 🎥 录制 **Video 1：库存风险分析**（60s）

**复用**：`ToolAgent`（`macs_pkg/agents/tool_agent.py`）、`ToolRegistry`

---

### Day 9（周一 2h）：领域 Agent 模板

**目标**：在 `AgentTemplateRegistry` 注册 4 个 ERP 领域 Agent。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/agents/templates.py`：4 个 `AgentTemplate`
  - `erp_planner`（PLANNER）
  - `erp_inventory_analyst`（EXECUTOR）
  - `erp_purchase_specialist`（EXECUTOR）
  - `erp_report_writer`（REVIEWER）
- [ ] 新建 `tests/test_erp_templates.py`

**复用**：`AgentTemplateRegistry`（`macs_pkg/core/agent_template.py`）

---

### Day 10（周三 2h）：多 Agent 编排

**目标**：把 4 个 Agent 接入 `RuntimeEngine` 走 Hierarchical 模式。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/workflows/inventory_risk.py`：`InventoryRiskWorkflow`
- [ ] 新建 `tests/test_inventory_workflow.py`

**复用**：`RuntimeEngine`、`create_and_register_agents`、Hierarchical 模式

**输出结构**：
```python
{
  "plan": [...],
  "analyses": [...],
  "purchase_recommendations": [...],
  "final_report": "..."
}
```

---

### Day 11（周六 8h）：多 Agent 端到端 + Video 2

**目标**：完整跑通 "分析未来30天库存风险并给出采购建议"。

**任务清单**：
- [ ] 新建 `examples/erp_copilot_multi_agent.py`
- [ ] 新建 `tests/test_e2e_workflow.py`
- [ ] 新建 `docs/use_cases/erp_ai_copilot_multi_agent.md`
- [ ] 🎥 录制 **Video 2：多 Agent 采购建议**（60s）

**输出**：
- `examples/output/inventory_risk_report.md`（生成）
- 完整 trace JSON

---

### Day 12（周一 2h）：轻量 Web UI

**目标**：3 个 Tab 的 Web 界面。

**任务清单**：
- [ ] 新建 `macs_pkg/erp/web/app.py`：FastAPI 应用
  - `POST /api/copilot/chat`
  - `POST /api/copilot/inventory_risk`
  - `GET  /api/kb/search`
  - `GET  /healthz`
- [ ] 新建 `macs_pkg/erp/web/static/index.html`：3 Tab 布局
- [ ] 新建 `tests/test_erp_web.py`
- [ ] 修改 `requirements.txt`：加 `fastapi`、`uvicorn[standard]`

---

### Day 13（周二 2h）：CI 整合

**目标**：ERP 模块进入 CI。

**任务清单**：
- [ ] 修改 `docker-compose.yml`：加 `erp-web` service
- [ ] 新建 `.github/workflows/erp-copilot.yml`
- [ ] 新建 `macs_pkg/erp/health.py`
- [ ] 修改 `Makefile`：加 `make erp-seed`、`make erp-test`、`make erp-run`

---

### Day 14（周六 8h）：录制 Video 3 + 文档定稿

**目标**：完成最后一段视频和完整文档。

**任务清单**：
- [ ] 🎥 录制 3 段视频到 `docs/videos/`：
  - `01_single_agent.mp4`（60s）
  - `02_multi_agent_inventory_risk.mp4`（60s）
  - `03_rag_knowledge_base.mp4`（60s）
- [ ] 新建 `docs/use_cases/erp_ai_copilot.md`
- [ ] 新建 `docs/architecture/erp_copilot.md`：Mermaid 架构图
- [ ] 跑 `make check`（lint + typecheck + test）

---

### Day 15（周日 8h）：GitHub 重构 + 发布

**目标**：把项目定位为 "ERP AI Copilot" 并发布 v1.0.0。

**任务清单**：
- [ ] 大改 `README.md`：
  - 标题改为 "MACS — Multi-Agent Collaboration Stack, now featuring the ERP AI Copilot"
  - 重排版：Overview → Quickstart → ERP Copilot（高亮）→ Architecture → Examples → Contributing
  - 加 badge：CI / Coverage / Docker / PyPI
  - 嵌入 3 段视频
- [ ] 新建 `examples/README.md`
- [ ] 修改 `CHANGELOG.md`：加 v1.0.0 条目
- [ ] 新建 `RELEASE_NOTES_v1.0.0.md`
- [ ] Git tag `v1.0.0-erp-copilot`
- [ ] `make check` 全绿

---

## 四、关键复用清单

| 现有组件 | 路径 | 用法 |
|---|---|---|
| `BaseAgent` / `AgentRole` | `macs_pkg/core/agent.py` | 所有 ERP Agent 继承 |
| `AgentTemplateRegistry` | `macs_pkg/core/agent_template.py` | 注册 4 个 ERP 领域 Agent |
| `PlannerAgent` / `ExecutorAgent` / `ReviewerAgent` | `macs_pkg/agents/` | 多 Agent 工作流主体 |
| `RuntimeEngine` | `macs_pkg/runtime/engine.py` | 多 Agent 编排 |
| `Hierarchical` 协作 | `macs_pkg/collaboration/hierarchical.py` | Planner→Executors→Reviewer |
| `RAGEngine` | `macs_pkg/rag/rag_engine.py` | ERP 知识库底座 |
| `ChineseCharNgramEmbedder` | `macs_pkg/rag/` | 中文文档嵌入 |
| `MCPServer` | `macs_pkg/mcp/server.py` | 5 个 ERP 工具的注册中心 |
| `ClaudeProvider` / `MiniMaxProvider` | `macs_pkg/llm/` | LLM 主力 + 兜底 |
| `examples/erp_knowledge_assistant.py` | `examples/` | 单 Agent RAG 范本 |
| `tests/conftest.py` | `tests/` | fixture 范本 |

---

## 五、风险与缓解

| 风险 | 缓解策略 |
|---|---|
| LLM 不稳定 | 测试用 mock；NL→SQL 设 `temperature=0` |
| Schema 漂移 | 启动时 assert 表结构 |
| 测试隔离 | 每个测试用独立 schema `test_erp_<uuid>` |
| 集成测试慢 | `@pytest.mark.integration` 标记 |
| MiniMax API 限制 | Claude 主用，MiniMax 兜底 |
| Postgres 资源 | dev 用 16-alpine（~50MB） |

---

## 六、端到端验证

```bash
# 1. 启动基础服务
docker compose up -d postgres
make erp-seed  # 跑 scripts/seed_erp_db.py --scale medium

# 2. 单元 + 集成测试
make test
pytest tests/test_erp_*.py -v

# 3. 单 Agent 演示（Video 1）
python examples/erp_copilot_single_agent.py

# 4. 多 Agent 演示（Video 2）
python examples/erp_copilot_multi_agent.py "分析未来30天库存风险并给出采购建议"
cat examples/output/inventory_risk_report.md

# 5. RAG 知识库（Video 3）
python -c "
import asyncio
from macs_pkg.erp.rag.query import ask_kb
print(asyncio.run(ask_kb('如何处理采购退货？')))
"

# 6. Web UI
make erp-run
# 浏览器打开 http://localhost:8000

# 7. 发布
make check
git tag v1.0.0-erp-copilot && git push --tags
```

---

## 七、里程碑验收

| 天数 | 里程碑 |
|---|---|
| Day 3 | 数据库 + 1000+ 测试数据 |
| Day 6 | NL→SQL 端到端可查 |
| Day 10 | 多 Agent 工作流跑通 |
| Day 12 | Web UI 可演示 |
| Day 14 | 3 段 Demo 视频完成 |
| Day 15 | GitHub README 重构 + v1.0.0 发布 |

---

## 八、后续衔接（Day 15 之后）

- **第 2-3 阶段**（30-90天）：技术补强（Python FastAPI、OpenAI/Claude API、MCP、LangGraph、Docker、Nginx）+ 求职投递（深圳南山 AI 岗）
- **第 4 阶段**（90-180天）：Upwork/Freelancer 接单，撰写英文技术文章
- **第 5 阶段**（6-12个月）：SaaS 化（Inventory Copilot / Procurement Copilot / Sales Insight Agent），$9/$19/$49 月费

**关键验收指标（180天）**：
- 15-25k AI 岗 offer
- 或第一笔海外 AI 项目收入
- 12个月内：AI 工程师薪资 20-35k + 可商业化 AI 产品 + 美元收入

---

*本计划最后更新：2026/06/11*
