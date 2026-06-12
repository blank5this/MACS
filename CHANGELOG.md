# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1-erp-copilot] - 2026-06-12

> Bug fix release: 修复 v1.0.0 release notes 列出的 2 个代码问题 (LLM Planner 硬编码 prompt + RuntimeEngine 吞异常).
> 测试: 168 passed (152 → 168, +16).

### Fixed

- **LLMPlannerAgent / LLMExecutorAgent / LLMReviewerAgent 硬编码 SYSTEM_PROMPT**:
  这 3 个 LLM 驱动的 Agent 类在 v1.0.0 中通过 `super().__init__(system_prompt=self.SYSTEM_PROMPT)`
  写死了类变量, 完全忽略调用方传入的 `system_prompt` 参数. 这导致
  `macs_pkg.erp.agents.templates.ERP_PLANNER` 等模板无法注入渲染好的 prompt —
  Day 9 只能靠 `agent.system_prompt = ...` 在构造后覆盖, 是 hack.
  v1.0.1: 3 个 `__init__` 都加 `system_prompt: Optional[str] = None` 显式参数,
  `effective_prompt = system_prompt if system_prompt is not None else self.SYSTEM_PROMPT`,
  caller 优先, 类变量兜底.

- **RuntimeEngine 吞 provider 异常**: v1.0.0 当 `stop_on_error=False` 时,
  引擎返回 `{"error": "..."}` 但**丢失原始 exception 类型**. 错在 timeout
  和 connection refused 没法区分, workflow 没法做智能重试.
  v1.0.1:
  - 返回 dict 多带 `error_type` 字段 (e.g. `"RuntimeError"`)
  - engine 实例多 `last_error: Optional[BaseException]` 和 `last_error_task_id: Optional[str]`
    两个属性, 让 caller 直接 `isinstance(engine.last_error, TimeoutError)` 做 routing.

### Added

- `tests/test_v101_fixes.py` — 16 个新测试覆盖 2 个修复 (9 个 LLM agent override + 7 个 error propagation)

### Compatibility

- 100% 向后兼容 v1.0.0. `stop_on_error=True` 默认行为不变 (抛异常). 新字段是**加**
  不是**改** (error dict 多了 `error_type` 键, engine 多了 `last_error` 属性).

### Known Issues (carried over from v1.0.0)

1. **MCP 集成测试需要 docker** — 集成测试 (test_erp_db / test_erp_mcp / test_e2e_workflow)
   在没有 docker 的环境报 5 errors. CI 路径不受影响 (有 service container).
2. **Windows console GBK** — 默认 cmd.exe 不能渲染中文标点. 用 `chcp 65001` 或 Windows Terminal.
   (Day 14 `record_video_03.py` 已经用 `sys.stdout.reconfigure(encoding="utf-8")` 修过.)

---

## [1.0.0-erp-copilot] - 2026-06-12

> 15 天冲刺里程碑: 从通用多 Agent 框架演进为聚焦业务价值的 **ERP AI Copilot** 完整产品.
> 交付: 22 个新文件, 17 个测试文件 (152 passed), 3 段 60s 视频, 4 CI jobs.

### Added — ERP AI Copilot 模块 (`macs_pkg/erp/`)

- **数据层** (Day 1-3): `db/connection.py` (psycopg async pool), `db/schema.py` (5 张表 DDL), `db/seed.py` (Faker 1000+ 行)
- **MCP 工具** (Day 4): 5 个 stdio/SSE inventory/sales/procurement 工具 + `tools/server.py` MCP server
- **NL→SQL** (Day 5-6): `NL2SQLTranslator` + `SafeSQLExecutor` + 4 层防护 (AST parse / 关键字黑名单 / 表列白名单 / 参数化)
- **RAG 知识库** (Day 7): `rag/indexer.py` (char-ngram 嵌入) + `rag/query.py` (`ask_kb`) + 18 篇中文 ERP 制度文档
- **单 Agent** (Day 8): `ERPCopilotAgent` 7 工具混合 (5 MCP + RAG + NL→SQL) + `examples/erp_copilot_single_agent.py` + Video 1
- **领域模板** (Day 9): 4 个 `AgentTemplate` (erp_planner / erp_inventory_analyst / erp_purchase_specialist / erp_report_writer) 注册到全局注册中心
- **多 Agent 协作** (Day 10-11): `InventoryRiskWorkflow` (Planner → Analyst → Buyer → Writer) + `examples/erp_copilot_multi_agent.py` + Video 2
- **Web UI** (Day 12): FastAPI app 4 endpoints (`/api/copilot/chat` / `/api/copilot/inventory_risk` / `/api/kb/search` / `/healthz`) + 3 Tab 暗色主题前端
- **CI 整合** (Day 13): `.github/workflows/erp-copilot.yml` 4 job (lint / unit / integration / coverage) + `macs_pkg/erp/health.py` 单一健康源 + `Makefile` +9 ERP targets
- **视频 3** (Day 14): `scripts/record_video_03.py` RAG 演示录制器
- **文档** (Day 14): `docs/use_cases/erp_ai_copilot.md` 综合索引 + `docs/architecture/erp_copilot.md` 6 张 Mermaid 架构图

### Added — CI / 工具链

- `.github/workflows/erp-copilot.yml` — Postgres service container + 3 job + coverage artifact
- `Makefile` — `make erp-up/seed/test/run/stop/check/lint/ci/restart/logs/rag-rebuild` (9 个 ERP targets)
- `requirements.txt` — `psycopg[binary,pool]>=3.2.0`, `sqlparse>=0.5.0`, `Faker>=22.0.0`, `fastapi>=0.110.0`, `uvicorn[standard]>=0.27.0`
- `docker-compose.yml` — `postgres` / `erp-init` / `erp-web` services, `erp` profile

### Added — 文档

- `docs/use_cases/erp_ai_copilot.md` — ERP Copilot 综合索引页
- `docs/use_cases/erp_ai_copilot_multi_agent.md` — 多 Agent 用例深入
- `docs/architecture/erp_copilot.md` — 架构图 + 依赖矩阵 + 数据流
- `docs/videos/01_single_agent_script.md` — Video 1 旁白稿
- `docs/videos/02_multi_agent_script.md` — Video 2 旁白稿
- `docs/videos/03_rag_script.md` — Video 3 旁白稿
- `examples/README.md` — 5 个 example 复制粘贴运行指南
- `RELEASE_NOTES_v1.0.0.md` — 详细 release notes

### Added — 测试 (17 个新文件, 152 passed)

- `tests/test_erp_db.py` (Day 1-3)
- `tests/test_erp_mcp.py` (Day 4)
- `tests/test_nl2sql.py` (Day 5)
- `tests/test_nl2sql_safety.py` (Day 6, 4 层 SQL 防护)
- `tests/test_erp_rag.py` (Day 7)
- `tests/test_erp_copilot_agent.py` (Day 8, 14 个)
- `tests/test_erp_templates.py` (Day 9, 30 个)
- `tests/test_inventory_workflow.py` (Day 10, 16 个)
- `tests/test_e2e_workflow.py` (Day 11, 6 个 e2e smoke)
- `tests/test_erp_web.py` (Day 12, 20 个 FastAPI TestClient)
- `tests/test_erp_health.py` (Day 13, 17 个 health module)

### Changed

- `README.md` — 大改: ERP AI Copilot 推到最前, 加 Quickstart / 关键数字 / 架构图 / 视频索引, 底层 MACS 框架保留在后面
- `macs_pkg/erp/__init__.py` — 加 version 字符串和 quickstart docstring

### Fixed

- **Web app 真实 health check**: `macs_pkg/erp/web/app.py` 的 `/healthz` 不再盲目返回 "ok", 而是委托 `health.py` 综合 DB / LLM / RAG 三维状态
- **Python re-export trap**: `tests/test_erp_web.py` 用 `importlib.import_module` 绕过 `web/__init__.py` 的 `from .app import app` re-export
- **PostgreSQL service 启动竞态**: CI workflow 加 `for i in {1..30}` 重试循环
- **Windows GBK 编码**: `scripts/record_video_03.py` 加 `sys.stdout.reconfigure(encoding="utf-8")`

### Security

- **SQL 注入防护**: 4 层防护 (AST parse 强制 SELECT / 黑名单 `INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|COPY|GRANT` / 表列白名单 / psycopg 参数化)
- **Web 端点 503 而不是 500**: 资源不可用时返回 503 + `detail` 解释缺什么配置, 避免暴露内部错误

### Performance

- **Lazy resource init**: DB pool / LLM provider / RAG engine 全部首次访问才创建, 单元测试 0 外部依赖
- **Health probe 1s timeout**: DB ping 默认 1s ceiling, 不会卡 k8s readiness probe
- **Hybrid retrieval (ngram + BM25 + RRF)**: 单一方法中文短查询表现不稳, RRF 融合稳定

---

## [0.1.1] - 2026-04-29

### Added
- **Internationalization**: English documentation (`docs/README.md`, `docs/ARCHITECTURE.md`)
- **English Use Case**: ERP Knowledge Assistant use case study (`docs/use_cases/erp_knowledge_assistant.md`)
- **OpenTelemetry Exporter**: Full tracing and metrics support (`macs_pkg/monitoring/openTelemetry_exporter.py`)
- **CONTRIBUTING.md**: Contribution guidelines and coding standards
- **CODE_OF_CONDUCT.md**: Community code of conduct
- **SECURITY.md**: Security vulnerability reporting policy
- **CI/CD**: GitHub Actions workflow with multi-version Python testing
- **Optional OpenTelemetry Dependencies**: New `otel` extra in `pyproject.toml`
- **Badges**: CI/PyPI/license badges in README

### Fixed
- **ChineseCharNgramEmbedder export**: Added to `macs_pkg.rag.__all__`
- **OpenTelemetryExporter export**: Added to `macs_pkg.monitoring.__all__`

### Changed
- Updated `pyproject.toml` with `otel` optional dependency group

## [0.1.0] - 2026-04-27

### Added
- **Multi-Agent Framework**: BaseAgent with think()/act() lifecycle
- **Collaboration Modes**: Hierarchical, Decentralized, Pipeline, Dynamic Selector
- **LLM Providers**: ClaudeProvider, MiniMaxProvider, OpenAICompatibleProvider
- **LLM-Powered Agents**: LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent (Claude), MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent (MiniMax)
- **RAG Pipeline**: RAGEngine, InMemoryVectorStore, offline Chinese embedder (ChineseCharNgramEmbedder)
- **Tool System**: ToolRegistry, RAGSearchTool, built-in tools
- **Memory System**: MemPalace long-term memory integration
- **Execution Tracing**: Mermaid sequence diagram generation
- **Prometheus Metrics**: MetricsStore and PrometheusExporter
- **Docker Support**: Dockerfile and docker-compose.yml
- **Unit Tests**: 20 tests covering core components

### Architecture
- **Agent Roles**: Planner (decomposition), Executor (execution), Reviewer (validation), Tool (external calls)
- **Proactive RAG**: Keyword-based automatic knowledge base retrieval for ERP domain
- **Error Handling**: TimeoutError, RateLimitError, LLMError with graceful degradation

---

## Versioning

We use [CalVer](https://calver.org/) with format `YYYY.MM.MICRO`:
- `0.1.0` — Initial release (April 2026)
- `0.1.1` — Documentation and enterprise features (April 2026)

---

## Release Process

1. All tests pass on all supported Python versions
2. Changelog updated with date and changes
3. Git tag created: `git tag -a v0.1.1 -m "Release version 0.1.1"`
4. Published to PyPI (automatic via GitHub Actions)
5. GitHub Release created with changelog excerpt
