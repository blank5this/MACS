# Release Notes — v1.0.1-erp-copilot

> **发布日期**: 2026-06-12
> **Tag**: `v1.0.1-erp-copilot`
> **Commit**: 见 [GitHub releases](https://github.com/blank5this/MACS/releases)
> **Sprint**: v1.0.0 之后第 1 个补丁 (同日发布)
> **向后兼容**: ✅ 100% 向后兼容 v1.0.0

---

## 🎯 TL;DR

v1.0.1 是 [v1.0.0](https://github.com/blank5this/MACS/releases/tag/v1.0.0-erp-copilot) 的 **bug fix 补丁**: 修复了 2 个代码层面的真问题 (LLM Agent 硬编码 prompt + RuntimeEngine 吞异常), 新增 **16 个测试** 把测试总数从 152 推到 **168 passed**. **无 API 变更**, 升级只需 `git pull` 即可.

---

## 🆕 What's New in v1.0.1

- **🐛 修复 LLMPlannerAgent / LLMExecutorAgent / LLMReviewerAgent 硬编码 SYSTEM_PROMPT**: 3 个 Agent 类在 v1.0.0 通过 `super().__init__(system_prompt=self.SYSTEM_PROMPT)` 写死了类变量, 完全忽略调用方传入的 `system_prompt` 参数. 这导致 `macs_pkg/erp/agents/templates.py` 里的 `ERP_PLANNER` 等模板无法注入渲染好的 prompt — Day 9 只能靠 `agent.system_prompt = ...` 在构造后覆盖, 是 hack. v1.0.1 在 3 个 `__init__` 都加 `system_prompt: Optional[str] = None` 显式参数, caller 优先, 类变量兜底. (文件: `macs_pkg/agents/llm_planner_agent.py`, `macs_pkg/agents/llm_executor_agent.py`, `macs_pkg/agents/llm_reviewer_agent.py`)

- **🐛 修复 RuntimeEngine 吞 provider 异常**: v1.0.0 当 `stop_on_error=False` 时, 引擎返回 `{"error": "..."}` 但**丢失原始 exception 类型**. `TimeoutError` 和 `ConnectionRefusedError` 没法区分, workflow 没法做智能重试. v1.0.1: 返回 dict 多带 `error_type` 字段 (e.g. `"TimeoutError"`), engine 实例多 `last_error: Optional[BaseException]` 和 `last_error_task_id: Optional[str]` 两个属性. (文件: `macs_pkg/runtime/engine.py`)

- **✅ 新增 `tests/test_v101_fixes.py`**: 16 个测试覆盖 2 个修复 (9 个 LLM agent override + 7 个 error propagation). (文件: `tests/test_v101_fixes.py`)

- **✅ 测试总数从 152 推到 168 passed** (+16). (整合所有 `tests/test_*.py`)

- **✅ 100% 向后兼容 v1.0.0**: `stop_on_error=True` 默认行为不变 (抛异常). 新字段是**加**不是**改** (error dict 多了 `error_type` 键, engine 多了 `last_error` 属性).

---

## 🎬 What's New in v1.0.0 (回顾)

v1.0.0 是 **15 天冲刺里程碑**: 从通用多 Agent 框架演进为聚焦业务价值的 **ERP AI Copilot** 完整产品. 关键交付:

- **5 张表 + 1000+ 行 seed 数据** (`macs_pkg/erp/db/`) — Postgres 16, Faker 模拟, 3 档规模 (small/medium/large)
- **5 个 MCP 业务工具** (`macs_pkg/erp/tools/`) — stdio/SSE inventory/sales/procurement
- **NL→SQL + 4 层 SQL 防护** (`macs_pkg/erp/nl2sql.py`) — AST parse / 关键字黑名单 / 表列白名单 / psycopg 参数化
- **RAG 知识库** (`macs_pkg/erp/rag/`) — 18 篇中文 ERP 制度文档, char-ngram + BM25 + RRF 混合检索
- **多 Agent 协作** (`macs_pkg/erp/workflows/inventory_risk.py`) — Planner → Inventory Analyst → Purchase Specialist → Report Writer
- **Web UI** (`macs_pkg/erp/web/`) — FastAPI 4 endpoints + 3 Tab 暗色主题前端
- **CI 整合** (`.github/workflows/erp-copilot.yml`) — 4 job (lint / unit / integration / coverage) + Makefile 9 ERP targets
- **3 段 60s 视频脚本** (`scripts/record_video_*.py` + `docs/videos/`) — 单 Agent / 多 Agent / RAG 演示
- **完整文档** — 3 use cases + 1 架构图 (6 张 Mermaid) + 3 视频旁白稿 + examples README

详细见 [RELEASE_NOTES_v1.0.0.md](RELEASE_NOTES_v1.0.0.md).

---

## 🐛 Bug Fixes (v1.0.1 详细)

### Fix 1: LLM Agent 硬编码 SYSTEM_PROMPT

**问题**:
```python
# v1.0.0 之前 (在 macs_pkg/agents/llm_planner_agent.py)
class LLMPlannerAgent(BaseAgent):
    SYSTEM_PROMPT = "You are a planner..."  # 类变量

    def __init__(self, provider, **kwargs):
        super().__init__(system_prompt=self.SYSTEM_PROMPT, **kwargs)
        # ❌ kwargs 里的 system_prompt 完全被忽略
```

**根因**: `super().__init__(system_prompt=self.SYSTEM_PROMPT)` **位置参数**直接传类变量, kwargs 里的同名参数被覆盖.

**影响**:
- `macs_pkg/erp/agents/templates.py` 里的 `ERP_PLANNER` 模板想注入渲染好的 prompt (含 ERP 业务背景) 失败
- Day 9 只能用 `agent.system_prompt = "..."` 在构造后覆盖 — 这是 hack, 绕过 `__init__` 的设计意图
- 测试 `tests/test_erp_templates.py` 里 30 个测试有 9 个因此加了 `setattr` 兜底

**修复** (v1.0.1):
```python
# v1.0.1 修复后 (在 macs_pkg/agents/llm_planner_agent.py)
class LLMPlannerAgent(BaseAgent):
    SYSTEM_PROMPT = "You are a planner..."

    def __init__(self, provider, system_prompt: Optional[str] = None, **kwargs):
        effective_prompt = system_prompt if system_prompt is not None else self.SYSTEM_PROMPT
        super().__init__(system_prompt=effective_prompt, **kwargs)
        # ✅ caller 传入优先, 类变量兜底
```

**测试**: `tests/test_v101_fixes.py` 9 个 test 验证 caller-supplied prompt 生效 (3 个 Agent × 3 个场景).

---

### Fix 2: RuntimeEngine 吞 provider 异常

**问题**:
```python
# v1.0.0 之前 (在 macs_pkg/runtime/engine.py)
async def execute(self, tasks, stop_on_error=False):
    try:
        result = await self._run_task(task)
    except Exception as e:
        return {"error": str(e), "success": False}
        # ❌ 原始 exception 类型丢失 — TimeoutError vs ConnectionError 一样
```

**影响**:
- Workflow 拿到 `result["error"]` 是字符串, 没法区分 `TimeoutError` (重试) 和 `ConnectionRefusedError` (切 provider)
- v1.0.0 release notes 提到 "建议检查 result.error 字段" — 这是临时方案, 不是工程方案

**修复** (v1.0.1):
```python
# v1.0.1 修复后 (在 macs_pkg/runtime/engine.py)
async def execute(self, tasks, stop_on_error=False):
    try:
        result = await self._run_task(task)
    except Exception as e:
        self.last_error = e
        self.last_error_task_id = task.id
        return {
            "error": str(e),
            "error_type": type(e).__name__,  # ✅ "TimeoutError" / "ConnectionError" / ...
            "task_id": task.id,
            "success": False,
        }

# Caller 现在可以:
if isinstance(engine.last_error, TimeoutError):
    await retry_with_backoff(task)
elif isinstance(engine.last_error, ConnectionError):
    await switch_provider(task)
```

**测试**: `tests/test_v101_fixes.py` 7 个 test 验证 error_type 暴露 + last_error 属性 + 路由决策.

---

## 📦 Installation

### Option 1: PyPI

```bash
pip install macs-pkg==1.0.1
```

### Option 2: Docker

```bash
git clone https://github.com/blank5this/MACS.git
cd MACS
git checkout v1.0.1-erp-copilot
make erp-run
# → Postgres 16 + 自动 seed + Web UI (http://localhost:8001)
```

### Option 3: From Source

```bash
git clone https://github.com/blank5this/MACS.git
cd MACS
git checkout v1.0.1-erp-copilot
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key  # 或 MiniMax_API_KEY / OPENAI_API_KEY
make erp-up
make erp-run
```

---

## 🚀 Quickstart (5 分钟跑起来)

```bash
# 1. 克隆 + 切 tag
git clone https://github.com/blank5this/MACS.git
cd MACS
git checkout v1.0.1-erp-copilot

# 2. 装依赖
pip install -r requirements.txt

# 3. 启 Postgres (docker)
make erp-up

# 4. 设置 LLM key (任选一个)
export ANTHROPIC_API_KEY=sk-ant-...      # Claude (主力)
# export MINIMAX_API_KEY=...             # MiniMax (兜底)
# export OPENAI_API_KEY=sk-...           # OpenAI

# 5. 健康检查
make erp-check
# ok: True/False
# db, llm, rag 三维独立探针

# 6. 跑单 Agent 演示 (对应 Video 1)
python examples/erp_copilot_single_agent.py

# 7. 跑多 Agent 工作流 (对应 Video 2)
python examples/erp_copilot_multi_agent.py "分析未来 30 天库存风险"
# 报告写入 examples/output/inventory_risk_report.md
```

---

## 🛠️ Tech Stack

| 类别 | 技术 | 用途 |
|------|------|------|
| **语言** | Python 3.10+ | 主开发语言, async/await |
| **LLM 框架** | AutoGen + 自研 `macs_pkg` | 协作引擎 + Agent 基类 |
| **LLM Provider** | 6 个 (MiniMax / Claude / Qwen / Zhipu / DeepSeek / Hunyuan / OpenAI) | 多模型抽象, 测试用 mock |
| **数据库** | PostgreSQL 16 + psycopg 3 (async pool) | ERP 5 张表, 1000+ 行 seed |
| **MCP** | stdio / SSE (自研 server) | 5 个 inventory/sales/procurement 工具 |
| **NL→SQL** | LLM 翻译 + sqlparse + AST | 自然语言 → 安全 SQL, 4 层防护 |
| **RAG** | char-ngram + BM25 + RRF | 18 篇中文文档混合检索 |
| **Web** | FastAPI 0.110+ + Uvicorn + 原生 HTML/JS | 3 Tab 暗色主题前端 |
| **MCP 协议** | JSON-RPC over stdio/SSE | 工具层和 Agent 层解耦 |
| **CI/CD** | GitHub Actions | 8 个 job (4 主 + 4 ERP), Postgres service container |
| **容器化** | Docker + docker-compose | postgres / erp-init / erp-web 3 service |
| **测试** | pytest + pytest-asyncio + httpx TestClient | 168 passed + 23 集成 |
| **Lint** | ruff + black | ERP 模块独立 lint target |
| **文档** | Markdown + Mermaid | 6 张架构图 + 3 use cases |

---

## 📊 Project Stats

| 维度 | 数字 |
|------|------|
| **版本** | v1.0.1-erp-copilot |
| **发布日期** | 2026-06-12 |
| **新增文件 (累计)** | 22 个核心 + 17 个测试 (含 1 个 v1.0.1 fix test) |
| **代码行数** | ~8,000 行 Python (含 docstring 和测试) |
| **测试用例 (非集成)** | **168 passed** (v1.0.0: 152 → v1.0.1: 168, +16) |
| **测试用例 (集成)** | 23 个 (需要 Postgres + docker) |
| **LLM Provider** | 6 个 (MiniMax / Claude / Qwen / Zhipu / DeepSeek / Hunyuan / OpenAI) |
| **MCP 工具** | 5 个 (inventory / sales / procurement) |
| **单 Agent 工具** | 7 个 (5 MCP + RAG + NL→SQL) |
| **Agent 模板** | 4 个 ERP (planner / inventory_analyst / purchase_specialist / report_writer) + 1 KB = 5 个 |
| **KB 文档** | 18 篇 (4 子目录, 135 chunks) |
| **数据库表** | 5 张 (products / sales_orders / purchase_orders / suppliers / inventory) |
| **种子数据** | 1000+ 行 (Faker, 3 档规模) |
| **Web endpoints** | 4 个 (chat / inventory_risk / kb/search / healthz) |
| **CI jobs** | 8 个 (4 主 + 4 ERP) |
| **视频** | 3 段 × 60s (脚本就绪, 待录制) |
| **文档** | 3 use cases + 1 架构图 (6 张 Mermaid) + 1 索引 + 3 视频旁白稿 |
| **CHANGELOG 修复** | 2 个 (LLM Agent prompt + RuntimeEngine error) |
| **v1.0.1 patch size** | ~18 KB 代码改动 |

---

## 📚 Documentation

- 🏠 [README.md](README.md) — 项目首页 (ERP 推到顶部, MACS 框架保留底部)
- 🗺️ [MACS_ROADMAP.md](MACS_ROADMAP.md) — 15 天冲刺路线图
- 📋 [ROADMAP_AUDIT_v1.0.1.md](ROADMAP_AUDIT_v1.0.1.md) — 完工度盘点 (超额完成 80%)
- 📖 [CHANGELOG.md](CHANGELOG.md) — 完整变更日志 (v0.1.0 / v0.1.1 / v1.0.0 / v1.0.1)
- 📑 [RELEASE_NOTES_v1.0.0.md](RELEASE_NOTES_v1.0.0.md) — v1.0.0 详细 release notes
- 📖 [docs/use_cases/erp_ai_copilot.md](docs/use_cases/erp_ai_copilot.md) — ERP Copilot 综合索引
- 📖 [docs/use_cases/erp_ai_copilot_multi_agent.md](docs/use_cases/erp_ai_copilot_multi_agent.md) — 多 Agent 库存风险深入
- 📖 [docs/use_cases/erp_knowledge_assistant.md](docs/use_cases/erp_knowledge_assistant.md) — RAG 知识库深入
- 🏗️ [docs/architecture/erp_copilot.md](docs/architecture/erp_copilot.md) — 6 张 Mermaid 架构图 + 依赖矩阵
- 🎬 [docs/videos/01_single_agent_script.md](docs/videos/01_single_agent_script.md) — Video 1 旁白稿
- 🎬 [docs/videos/02_multi_agent_script.md](docs/videos/02_multi_agent_script.md) — Video 2 旁白稿
- 🎬 [docs/videos/03_rag_script.md](docs/videos/03_rag_script.md) — Video 3 旁白稿
- 🎥 [docs/RECORDING_GUIDE.md](docs/RECORDING_GUIDE.md) — OBS 录视频指南
- 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) — 贡献指南
- 🔒 [SECURITY.md](SECURITY.md) — 安全策略
- 📜 [LICENSE](LICENSE) — MIT 许可证

---

## 🔄 Compatibility (与 v1.0.0)

**100% 向后兼容**. v1.0.1 的所有改动都是 **加**, 不是 **改**:

| API | v1.0.0 | v1.0.1 | 兼容性 |
|-----|--------|--------|--------|
| `LLMPlannerAgent.__init__()` | 接 `**kwargs`, 忽略 `system_prompt` | 新增显式 `system_prompt: Optional[str] = None` 参数 | ✅ 旧调用照样工作 (走类变量兜底) |
| `LLMExecutorAgent.__init__()` | 同上 | 同上 | ✅ |
| `LLMReviewerAgent.__init__()` | 同上 | 同上 | ✅ |
| `RuntimeEngine.execute()` 返回值 | `{"error": str, "success": False}` | `{"error": str, "error_type": str, "task_id": str, "success": False}` | ✅ 多了 2 个键, 旧 caller 忽略即可 |
| `RuntimeEngine` 实例属性 | (无) | 新增 `last_error` + `last_error_task_id` | ✅ 新增属性, 不影响已有调用 |
| `stop_on_error=True` 默认行为 | 抛异常 | 抛异常 | ✅ 完全不变 |
| `stop_on_error=False` 默认行为 | 返回 dict, 吞异常类型 | 返回 dict, 暴露 `error_type` | ✅ **优化但兼容** |

**升级步骤**:
```bash
git pull origin main
git checkout v1.0.1-erp-copilot
pip install -r requirements.txt  # 依赖无变化
make erp-test  # 168 passed
```

---

## ⚠️ Known Issues

### 来自 v1.0.0 (未变)

1. **MCP 集成测试需要 docker** — 集成测试 (`test_erp_db.py` / `test_erp_mcp.py` / `test_e2e_workflow.py`) 在没有 docker 的环境报 **5 errors**. CI 路径不受影响 (有 service container). 解决: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:16-alpine`.

2. **Windows console GBK 编码** — 默认 cmd.exe 不能渲染中文标点 (e.g. `→`, `┌`). 解决:
   ```bash
   chcp 65001
   ```
   或用 Windows Terminal / VS Code 终端 / PowerShell. (Day 14 `scripts/record_video_03.py` 已经用 `sys.stdout.reconfigure(encoding="utf-8")` 修过录制脚本.)

### v1.0.1 已知限制

3. **`error_type` 字段不包含 traceback** — 只暴露 `type(e).__name__`, 不暴露 stack. 调试时还需看日志 (`make erp-logs`).

4. **新 `system_prompt` 参数没在 type stub 标 `Optional`** — IDE 智能提示可能看不到默认值. 手动 hint: `agent = LLMPlannerAgent(provider, system_prompt="...")`.

5. **`last_error_task_id` 只记最后一次** — 如果连续多个 task 失败, 旧 error 会被覆盖. 多任务追踪仍需 `execution_history`.

---

## 🤝 Contributing

欢迎 PR! 见 [CONTRIBUTING.md](CONTRIBUTING.md). 提交前请:

```bash
make erp-ci  # = lint + test + check 全跑
```

新功能请按以下顺序:

1. 加代码到 `macs_pkg/erp/<your_module>/`
2. 加测试到 `tests/test_erp_<your_module>.py`
3. 更新 [CHANGELOG.md](CHANGELOG.md)
4. (可选) 加 example 到 `examples/`

---

## 📄 License

[MIT](LICENSE) — 自由使用, 商用友好.

---

## 🙏 Acknowledgments

- **MACS 框架** — 15 天前是通用框架, 15 天后是 ERP 业务助手. 框架设计经受住了考验.
- **MCP 协议** — 工具层和 Agent 层解耦, 未来可暴露给 IDE / 其他 Agent 平台.
- **RAGEngine + char-ngram + BM25 + RRF** — 中文场景的天作之合, 单一方法短查询不稳, RRF 融合稳.
- **6 个 LLM Provider** — 主力 Claude, 兜底 MiniMax. 没有多 Provider 抽象, 测试就得全用 mock.
- **PostgreSQL + psycopg 3 async pool** — async 上下文里最稳的关系型数据库.
- **FastAPI + Uvicorn** — 零前端依赖的 3 Tab Web UI, 60s 演示就绪.

---

## 🔮 What's Next (v1.1.0 Preview)

| 版本 | 计划时间 | 重点 |
|------|----------|------|
| **v1.0.2** | 2026-06-26 | 文档补全 + 视频录制完成 |
| **v1.1.0** | 2026-07-15 | 用户认证 + 多租户 + Web UI 升级 |
| **v1.2.0** | 2026-08-15 | 真实 ERP 对接 (SAP / 用友 / 金蝶) |
| **v2.0.0** | 2026-Q4 | 切出 Inventory Copilot / Procurement Copilot SaaS |

v1.0.1 之后的 **当务之急**:
1. 录 3 段视频 (90 分钟, 按 `docs/RECORDING_GUIDE.md`)
2. 发 LinkedIn / 知乎 / 掘金文案
3. 更新简历 PDF
4. 投递深圳南山 AI 岗

---

## 📞 Feedback

- 🐛 [GitHub Issues](https://github.com/blank5this/MACS/issues)
- 💬 [GitHub Discussions](https://github.com/blank5this/MACS/discussions)
- 📖 [docs/use_cases/erp_ai_copilot.md](docs/use_cases/erp_ai_copilot.md)
- 🎥 [docs/videos/](docs/videos/)
- 💼 简历可加: "15 天独立完成 ERP AI Copilot v1.0.1, 端到端 168 测试, 3 段视频脚本"

---

<div align="center">

**如果觉得有用, 给我们一个 ⭐!** — [github.com/blank5this/MACS](https://github.com/blank5this/MACS)

</div>