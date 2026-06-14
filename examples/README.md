# Examples — 复制粘贴即可运行

> 9 个 example, 覆盖 MACS 框架 + ERP AI Copilot 全场景.
> 所有命令假设你已经在仓库根目录.

## 📋 索引

### 4 个「真实 AI Copilot 场景」(无 API key 也能跑)

| # | 文件 | 场景 | 依赖 |
|---|------|------|------|
| 1 | [`scenario_01_low_stock.py`](./scenario_01_low_stock.py) | 低库存检测 (MCP 工具路由) | 无 |
| 2 | [`scenario_02_purchase_return.py`](./scenario_02_purchase_return.py) | 采购退货政策问答 (RAG + 引用强制) | 无 |
| 3 | [`scenario_03_text2sql.py`](./scenario_03_text2sql.py) | NL→SQL + 4 层 SQL 安全护栏演示 | 无 |
| 4 | [`scenario_04_supplier_perf.py`](./scenario_04_supplier_perf.py) | 供应商评级 + ASCII 可视化排名 | 无 |

### 5 个框架级 example

| # | 文件 | 场景 | 难度 | 依赖 |
|---|------|------|------|------|
| 5 | [`erp_copilot_single_agent.py`](./erp_copilot_single_agent.py) | ERP 单 Agent 混合工具 (Video 1) | ⭐ | LLM key + Postgres |
| 6 | [`erp_copilot_multi_agent.py`](./erp_copilot_multi_agent.py) | ERP 多 Agent 库存风险 (Video 2) | ⭐⭐ | LLM key + Postgres |
| 7 | [`erp_knowledge_assistant.py`](./erp_knowledge_assistant.py) | RAG 知识库问答 (Day 7 原始) | ⭐⭐ | LLM key |
| 8 | [`rag_example.py`](./rag_example.py) | RAG 引擎直接调用 | ⭐ | 无 |
| 9 | [`interview_qa.py`](./interview_qa.py) | 面试问答 demo | ⭐ | LLM key |

## 🚀 5 分钟 Quickstart

### 准备

```bash
# 1. 装依赖
pip install -r requirements.txt

# 2. 启 Postgres + seed
make erp-up

# 3. 设置 LLM key (任选其一)
export MINIMAX_API_KEY=your_minimax_key
# 或
export ANTHROPIC_API_KEY=your_claude_key
# 或
export OPENAI_API_KEY=your_openai_key
```

### Example 1: ERP 单 Agent (Video 1)

```bash
python examples/erp_copilot_single_agent.py
```

**预期输出**: 3 个 demo 问题, 每个都返回 `tool` 名 + `result` 字典 + 用时 ms.

**适用场景**: "我想看一个 LLM 自动选 7 个工具的最小 demo".

---

### Example 2: ERP 多 Agent 工作流 (Video 2) ⭐ 推荐

```bash
python examples/erp_copilot_multi_agent.py "分析未来 30 天库存风险并给出采购建议"
```

**预期输出**:
- Console: 流式 4 段 (plan / analyses / purchase_recs / final_report)
- `examples/output/inventory_risk_report.md`: 最终 Markdown 报告
- `examples/output/inventory_risk_trace.json`: 完整执行 trace

**适用场景**: "我想看 Planner / Analyst / Buyer / Writer 4 个 Agent 怎么协作".

---

### Example 3: RAG 知识库 (原始)

```bash
python examples/erp_knowledge_assistant.py
```

**适用场景**: "我想看 RAG + 多 Agent + 完整时序图 (Mermaid) 是怎么配合的".

---

### Example 4: RAG 直接调用 (无 LLM)

```bash
python examples/rag_example.py
```

**适用场景**: "我不想用 LLM, 只想看 RAG 引擎本身的检索能力". 跟 Video 3 等价, 但更短.

---

### Example 5: 60s 视频录制脚本

```bash
# 视频 1: 单 Agent
python scripts/record_video_01.py --no-delay

# 视频 2: 多 Agent
python scripts/record_video_02.py --no-delay

# 视频 3: RAG (不需要 LLM)
python scripts/record_video_03.py --no-delay
```

**适用场景**: "我想录一段 60s 屏幕录像, 加进 README / 简历 / B 站".

每个 `--no-delay` 跑完都是 1-3 秒. 去掉 flag 跑 60s typewriter 版本用于录屏.

---

## 🧪 跑测试 (跟 example 配对)

```bash
# 仅 ERP (非集成, 152 个, 不需要 docker)
make erp-test

# 跑全部 (含 MACS 框架)
make test

# 单个 example 的对应测试
pytest tests/test_erp_copilot_agent.py -v
pytest tests/test_inventory_workflow.py -v
pytest tests/test_e2e_workflow.py -v
```

---

## 🛠️ 故障排查

### "Connection refused: localhost:5432"

没启 Postgres. 跑 `make erp-up` 或 `docker compose --profile erp up -d postgres`.

### "No LLM key configured"

设置 `MINIMAX_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` 中任意一个.

### "RAG index not found"

```bash
make erp-rag-rebuild
```

### "test_erp_db.py / test_erp_mcp.py 报 error"

这些需要真实 Postgres. CI 上用 `make erp-test` (不带 `ERP_INTEGRATION=1`).

### "UnicodeEncodeError: 'gbk' codec"

Windows console 默认 GBK. 改用 `chcp 65001` 切到 UTF-8, 或用 Windows Terminal / VS Code 内置终端.

---

## 📁 Example ↔ 测试 ↔ 文档 对应表

| Example | 测试 | 用例文档 | 视频 |
|---------|------|----------|------|
| `erp_copilot_single_agent.py` | `test_erp_copilot_agent.py` | `use_cases/erp_ai_copilot.md` | Video 1 |
| `erp_copilot_multi_agent.py` | `test_e2e_workflow.py` + `test_inventory_workflow.py` | `use_cases/erp_ai_copilot_multi_agent.md` | Video 2 |
| `erp_knowledge_assistant.py` | `test_erp_rag.py` | `use_cases/erp_knowledge_assistant.md` | Video 3 |
| `rag_example.py` | `test_erp_rag.py` | (同上) | (录屏) |
| `interview_qa.py` | `test_erp_templates.py` | (无) | (无) |

---

## ➕ 加新 Example

贡献一个新的 example 时, 建议遵循:

1. **顶头 docstring** 写清楚: 这是什么 / 怎么跑 / 期望输出
2. **CLI 参数化** 至少支持 `--no-delay` 和 `--output`
3. **Lazy imports** for heavy deps (LLM, RAG, DB)
4. **No network in smoke mode** (用 `_ScriptedProvider` 或 `_NullProvider`)
5. **加对应测试** 在 `tests/test_*.py` 里
6. **更新本 README 索引表**
