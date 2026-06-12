# Release Notes — v1.0.0-erp-copilot

> **发布日期**: 2026-06-12
> **Tag**: `v1.0.0-erp-copilot`
> **Commit**: 见 [GitHub releases](https://github.com/blank5this/MACS/releases)
> **Sprint**: 15 天 (2026-05-29 ~ 2026-06-12)

---

## 🎯 一句话

MACS 通用多 Agent 框架正式演进为 **ERP AI Copilot 完整产品**: 把自然语言映射到库存 / 销售 / 采购 / 知识库, 端到端跑通 PostgreSQL + MCP + RAG + 多 Agent 协作 + Web UI + CI.

---

## 🆕 新功能一览

### 1. 单 Agent 混合工具 (Day 8)

```python
from macs_pkg.erp.agents.copilot_agent import build_copilot_agent

agent = build_copilot_agent(pool=pool, provider=claude)
result = await agent.ask("哪些商品库存低于安全线?")
# → LLM 自动选 get_low_stock_products 工具
```

**7 工具**: `get_inventory_levels` / `get_low_stock_products` / `get_supplier_price_history` / `get_top_selling_products` / `get_sales_velocity` / `ask_knowledge_base` / `query_database`.

### 2. 多 Agent 协作 (Day 10-11)

```python
from macs_pkg.erp.workflows import InventoryRiskWorkflow

wf = InventoryRiskWorkflow(provider=claude, pool=pool)
result = await wf.run("分析未来 30 天库存风险并给出采购建议")
# → {plan, analyses, purchase_recs, final_report}
```

**4 Agent 协作**: Planner → Inventory Analyst → Purchase Specialist → Report Writer. 走 `RuntimeEngine` Hierarchical 模式.

### 3. NL→SQL 安全查询 (Day 5-6)

```python
from macs_pkg.erp.nl2sql import NL2SQLTranslator, SafeSQLExecutor

translator = NL2SQLTranslator(provider=claude)
executor = SafeSQLExecutor(pool=pool)
result = await executor.execute("上个月销售最好的 10 个 SKU 是哪些?")
# → {"sql", "rows", "rowcount", "elapsed_ms"}
```

**4 层防护**: AST 强制 SELECT / 关键字黑名单 / 表列白名单 / psycopg 参数化.

### 4. RAG 知识库 (Day 7)

```python
from macs_pkg.erp.rag.query import ask_kb

result = await ask_kb("如何处理采购退货?", top_k=3)
for chunk in result.chunks:
    print(chunk.title, chunk.score, chunk.text)
```

**18 篇中文文档** 跨 4 子目录 (operations / warehouse / procurement / finance), char-ngram + BM25 + RRF 混合检索, 不需要 LLM.

### 5. Web UI (Day 12)

```bash
make erp-run
# 浏览器打开 http://localhost:8001
# 3 Tab: Chat / Multi-agent Report / KB Search
```

**FastAPI + 暗色主题 + 零前端依赖**.

### 6. 健康检查 (Day 13)

```bash
make erp-check
# ok: True/False
# db, llm, rag 三维独立探针
```

**单一事实源** — 同时被 `/healthz` 端点, `make erp-check` CLI 和未来 k8s readiness probe 调用.

### 7. CI 整合 (Day 13)

```bash
.github/workflows/erp-copilot.yml
# 4 job: lint / test-unit / test-integration / coverage
# Postgres 16-alpine service container
# 路径触发: 只在 ERP 相关文件改动时跑
```

---

## 📊 关键数字

| 维度 | 数字 |
|------|------|
| **新增文件** | 22 个核心 + 17 个测试 + 8 个文档 + 9 Makefile targets |
| **代码行数** | ~8,000 行 Python (含 docstring 和测试) |
| **测试用例 (非集成)** | **152 passed** |
| **测试用例 (集成)** | 23 个 (需要 Postgres) |
| **LLM Provider** | 6 个 (MiniMax / Claude / Qwen / Zhipu / DeepSeek / Hunyuan / OpenAI) |
| **MCP 工具** | 5 个 |
| **Agent 模板** | 5 个 (1 KB + 4 ERP) |
| **KB 文档** | 18 篇 (4 子目录, 135 chunks) |
| **Web endpoints** | 4 个 |
| **CI jobs** | 8 个 (4 主 + 4 ERP) |
| **视频** | 3 段 × 60s + 3 旁白稿 |
| **文档** | 3 use cases + 1 架构图 + 1 索引 + 1 examples README |

---

## ⚡ 性能 & 可靠性

- **Lazy resource init**: DB pool / LLM provider / RAG engine 全部首次访问才创建, 单元测试 0 外部依赖
- **Health probe 1s timeout**: DB ping 默认 1s ceiling, 不会卡 k8s readiness probe
- **Web 端点 503 而非 500**: 资源不可用时返回 503 + 解释, 避免暴露内部错误
- **Hybrid retrieval**: char-ngram + BM25 + RRF 融合, 比单一方法更稳定
- **SQL 4 层防护**: AST / 黑名单 / 白名单 / 参数化, 抵御 prompt injection

---

## 🛠️ 升级路径 (从 v0.1.1)

### 不需要迁移步骤

v1.0.0 完全向后兼容 v0.1.1. 所有 MACS 框架 API 保持不变, ERP 模块是**新增**, 不修改任何已有公开 API.

```bash
git pull origin main
git checkout v1.0.0-erp-copilot
pip install -r requirements.txt  # 新增 5 个 ERP 依赖
```

### 想用 ERP Copilot?

```bash
# 启 Postgres
make erp-up

# 设置 LLM key
export ANTHROPIC_API_KEY=your_key

# 跑 example
python examples/erp_copilot_multi_agent.py "分析未来 30 天库存风险"

# 启 Web UI
make erp-run
```

### 想扩展 ERP 模块?

```python
# 1. 加新工具到 macs_pkg/erp/tools/inventory_tools.py
# 2. 注册到 macs_pkg/erp/tools/server.py
# 3. 在 ERPCopilotAgent.TOOL_NAMES 添名
# 4. 写 tests/test_erp_mcp.py 测试
# 5. (可选) 加到 examples/
```

---

## 🐛 已知问题

1. **MCP 集成测试需要 Postgres** — 没有 docker 时 `test_erp_mcp.py` / `test_erp_db.py` / `test_e2e_workflow.py` 报 5 errors. CI 路径不受影响 (有 service container).

2. **Claude LLM Planner 硬编码 SYSTEM_PROMPT** — `LLMPlannerAgent` 用了 class-level 硬编码 prompt, 我们的 `InventoryRiskWorkflow` 在 `run()` 后用 `agent.system_prompt = ...` 覆盖. 这是 MACS 框架本身的限制, 计划在 v1.1 用 `LLMPlannerAgent` 的子类解决.

3. **RuntimeEngine 吞 provider 异常** — `success=True` 可能伴随空 outputs. 建议检查 `result.error` 字段.

4. **Windows console GBK** — 默认 cmd.exe 不能渲染中文标点. 用 `chcp 65001` 或 Windows Terminal / VS Code 终端.

---

## 🙏 致谢

- **MACS 框架** — 15 天前是通用框架, 15 天后是 ERP 业务助手. 框架设计经受住了考验.
- **MCP 协议** — 工具层和 Agent 层解耦, 未来可暴露给 IDE / 其他 Agent 平台.
- **RAGEngine** — char-ngram + BM25 + RRF 混合检索, 中文场景的天作之合.
- **6 个 LLM Provider** — 主力 Claude, 兜底 MiniMax. 没有这个多 Provider 抽象, 测试就得全用 mock.

---

## 📅 路线图 (v1.1+)

| 版本 | 时间 | 重点 |
|------|------|------|
| v1.0.1 | 2026-06-26 | bug 修复, 文档补全 |
| v1.1.0 | 2026-07-15 | 用户认证 + 多租户, Web UI 升级 |
| v1.2.0 | 2026-08-15 | 真实 ERP 对接 (SAP / 用友 / 金蝶) |
| v2.0.0 | 2026-Q4 | 切出 Inventory Copilot / Procurement Copilot SaaS |

---

## 📞 反馈

- 🐛 [GitHub Issues](https://github.com/blank5this/MACS/issues)
- 📖 [docs/use_cases/erp_ai_copilot.md](docs/use_cases/erp_ai_copilot.md)
- 🎥 [docs/videos/](docs/videos/)
- 💼 简历可加: "15 天独立完成 ERP AI Copilot v1.0.0, 端到端 152 测试, 3 段视频"
