# MACS — Multi-Agent Collaboration Stack

### now featuring the **ERP AI Copilot** v1.0.0

[![Tests](https://github.com/blank5this/MACS/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/blank5this/MACS/actions)
[![ERP CI](https://github.com/blank5this/MACS/actions/workflows/erp-copilot.yml/badge.svg?branch=main)](https://github.com/blank5this/MACS/actions)
[![PyPI version](https://img.shields.io/pypi/v/macs_pkg.svg)](https://pypi.org/project/macs_pkg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/macs_pkg.svg)](https://pypi.org/project/macs_pkg/)
[![Downloads](https://img.shields.io/pypi/dm/macs_pkg.svg)](https://pypi.org/project/macs_pkg/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker-compose.yml)

> 一个通用的、可扩展的多智能体协作系统框架。v1.0.0 起内置 **ERP AI Copilot**: 把自然语言映射到库存 / 销售 / 采购 / 知识库, 端到端跑通 PostgreSQL + MCP + RAG + 多 Agent 协作.

---

## ✨ 重点: ERP AI Copilot (v1.0.0)

```
"哪些商品库存低于安全线?"     →  7 工具自动选 (MCP / RAG / NL→SQL)
"分析未来 30 天库存风险"      →  4 Agent 协作 → 4 段结构化报告
"如何处理采购退货?"           →  18 篇中文 KB → 命中 3 段引用

60s 一键起 Web UI, 3 Tab 演示
```

**3 段 60s 视频** (按顺序看效果最佳):

| # | 主题 | 视频 | 旁白稿 |
|---|------|------|--------|
| 1 | **单 Agent 混合工具** — 7 工具自动选择 | [录屏脚本](docs/videos/01_single_agent_script.md) | [script](docs/videos/01_single_agent_script.md) |
| 2 | **多 Agent 协作** — 4 Agent 接力, 4 段产物 | [录屏脚本](docs/videos/02_multi_agent_script.md) | [script](docs/videos/02_multi_agent_script.md) |
| 3 | **RAG 知识库** — 18 篇中文文档混合检索 | [录屏脚本](docs/videos/03_rag_script.md) | [script](docs/videos/03_rag_script.md) |

**5 能力维度**:

1. **结构化查询** — NL→SQL 安全翻译 + 4 层 SQL 防护 (AST / 黑名单 / 白名单 / 参数化)
2. **MCP 业务工具** — 5 个 stdio/SSE inventory / sales / procurement 工具
3. **RAG 知识库** — 18 篇中文 ERP 制度文档, char-ngram + BM25 + RRF 混合检索
4. **多 Agent 协作** — Planner → Inventory Analyst → Purchase Specialist → Report Writer
5. **Web UI** — FastAPI 3 Tab 浏览器界面, dark theme, 60s 演示就绪

**15 天交付**: 数据层 → MCP → NL→SQL → RAG → 单 Agent → 模板 → 工作流 → 端到端 → Web → CI → 视频 → 发布

---

## 🚀 Quickstart (ERP Copilot)

### 1. 装依赖

```bash
git clone https://github.com/blank5this/MACS.git
cd MACS
pip install -r requirements.txt
```

### 2. 一键起 Postgres + Web UI

```bash
# 启 Postgres 16 + 自动 seed + Web UI (http://localhost:8001)
make erp-run

# 健康检查
make erp-check
```

### 3. 跑单 Agent 演示 (Video 1)

```bash
export MINIMAX_API_KEY=your_key  # 或 ANTHROPIC_API_KEY / OPENAI_API_KEY
python examples/erp_copilot_single_agent.py
```

### 4. 跑多 Agent 工作流 (Video 2)

```bash
python examples/erp_copilot_multi_agent.py "分析未来 30 天库存风险并给出采购建议"
# 报告写入 examples/output/inventory_risk_report.md
```

### 5. 跑 RAG 知识库 (Video 3, 不需要 LLM)

```bash
python scripts/record_video_03.py --no-delay
```

### 6. 跑全部 ERP 测试

```bash
make erp-test
# 152 passed, 5 errors (DB-dependent, 需 docker)
```

### 7. 看 3 Tab Web UI

```bash
# 浏览器打开 http://localhost:8001
# 3 Tab: Chat (单 Agent) · Multi-agent Report · KB Search
```

---

## 📊 关键数字 (v1.0.0)

| 维度 | 数字 |
|------|------|
| 新增文件 | 22 个核心 + 17 个测试 |
| 测试 (非集成) | **152 passed** |
| LLM Provider | 6 个 (MiniMax / Claude / Qwen / Zhipu / DeepSeek / Hunyuan / OpenAI) |
| MCP 工具 | 5 个 |
| Agent 模板 | 5 个 (1 KB + 4 ERP) |
| KB 文档 | 18 篇 (4 子目录, 135 chunks) |
| Web endpoints | 4 个 (chat / inventory_risk / kb/search / healthz) |
| CI jobs | 8 个 (4 主 + 4 ERP) |
| 视频 | 3 段 × 60s |
| 文档 | 3 use cases + 1 架构图 + 1 索引 + 3 视频脚本 |

---

## 🏗️ ERP Copilot 架构 (高层)

```
                    用户问题 (中文)
                         │
          ┌──────────────┴──────────────┐
          ▼                              ▼
   ┌──────────────┐              ┌──────────────┐
   │ Single Agent  │              │ Multi-Agent  │
   │ 7 工具        │              │ 4 Agent      │
   │ (Day 8)      │              │ (Day 10/11)  │
   └──────┬───────┘              └──────┬───────┘
          │                              │
          └──────────────┬───────────────┘
                         ▼
   ┌─────────────────────────────────────────┐
   │       Capability Layer                  │
   │  ┌──────┐  ┌──────┐  ┌──────────────┐   │
   │  │  5   │  │ RAG  │  │ 18 KB docs   │   │
   │  │ MCP  │  │Engine│  │ (混合检索)   │   │
   │  │Tools │  │      │  │              │   │
   │  └──┬───┘  └──┬───┘  └──────────────┘   │
   │     │         │                          │
   │     ▼         ▼                          │
   │  PostgreSQL 16  (5 表 · 1000+ 行)         │
   └─────────────────────────────────────────┘
                         │
                         ▼
                FastAPI Web UI (3 Tab)
```

详细架构: [docs/architecture/erp_copilot.md](docs/architecture/erp_copilot.md)

---

## 🗂️ 项目结构 (ERP 部分)

```
macs_pkg/erp/
├── db/                     # Day 1-3  数据层
│   ├── connection.py       # DatabasePool (psycopg async)
│   ├── schema.py           # 5 张表 DDL
│   └── seed.py             # Faker 1000+ 行
├── tools/                  # Day 4    MCP 工具
│   ├── inventory_tools.py  # 5 个 async 函数
│   └── server.py           # MCPServer 注册
├── nl2sql.py               # Day 5-6  NL→SQL + 4 层防护
├── rag/                    # Day 7    RAG 知识库
│   ├── indexer.py
│   └── query.py            # ask_kb()
├── agents/                 # Day 8-9  Agent 模板
│   ├── copilot_agent.py    # 7 工具 ERPCopilotAgent
│   └── templates.py        # 4 ERP AgentTemplate
├── workflows/              # Day 10-11 多 Agent
│   └── inventory_risk.py   # Planner→Analyst→Buyer→Writer
├── web/                    # Day 12   FastAPI
│   ├── app.py              # 4 endpoints
│   └── static/index.html   # 3 Tab UI
└── health.py               # Day 13   健康检查

data/erp_kb/                # 18 篇中文 .md
scripts/
├── seed_erp_db.py
├── record_video_01.py      # 60s 视频 1
├── record_video_02.py      # 60s 视频 2
└── record_video_03.py      # 60s 视频 3
tests/
├── test_erp_db.py          # Day 1-3
├── test_erp_mcp.py         # Day 4
├── test_nl2sql.py          # Day 5
├── test_nl2sql_safety.py   # Day 6
├── test_erp_rag.py         # Day 7
├── test_erp_copilot_agent.py  # Day 8
├── test_erp_templates.py   # Day 9
├── test_inventory_workflow.py # Day 10
├── test_e2e_workflow.py    # Day 11
├── test_erp_web.py         # Day 12
└── test_erp_health.py      # Day 13

.github/workflows/
├── ci.yml                  # 主 CI
├── erp-copilot.yml         # ERP 专用 CI (Day 13)
└── release.yml             # PyPI / Docker Hub 发布
```

---

## 🔧 ERP Copilot 命令一览

```bash
# 启动
make erp-up                # Postgres + seed
make erp-run               # + Web UI
make erp-stop              # 停止

# 开发
make erp-test              # 跑非集成测试 (152 个)
make erp-test ERP_INTEGRATION=1  # 跑全部 (含 DB)
make erp-lint              # ruff macs_pkg/erp/
make erp-check             # CLI health probe
make erp-rag-rebuild       # 重建 RAG 索引
make erp-restart           # 重启 Web
make erp-logs              # 看日志
make erp-ci                # 聚合: lint + test + check
```

---

## 📚 文档

- [docs/use_cases/erp_ai_copilot.md](docs/use_cases/erp_ai_copilot.md) — **综合用例索引** (推荐先看)
- [docs/use_cases/erp_ai_copilot_multi_agent.md](docs/use_cases/erp_ai_copilot_multi_agent.md) — 多 Agent 库存风险深入
- [docs/use_cases/erp_knowledge_assistant.md](docs/use_cases/erp_knowledge_assistant.md) — RAG 知识库深入
- [docs/architecture/erp_copilot.md](docs/architecture/erp_copilot.md) — 架构图 (Mermaid)
- [docs/videos/01_single_agent_script.md](docs/videos/01_single_agent_script.md) — Video 1
- [docs/videos/02_multi_agent_script.md](docs/videos/02_multi_agent_script.md) — Video 2
- [docs/videos/03_rag_script.md](docs/videos/03_rag_script.md) — Video 3
- [CHANGELOG.md](CHANGELOG.md) — 变更日志
- [RELEASE_NOTES_v1.0.0.md](RELEASE_NOTES_v1.0.0.md) — v1.0.0 release notes

---

## 🌐 底层: MACS 通用多 Agent 框架

> 以下是 MACS 框架本身的能力. ERP Copilot 是其上的具体应用.

### 特性

- **通用架构**: 不针对特定场景, 可适应各种应用需求
- **多种协作模式**: 层级式 / 去中心化 / 管道式 / 动态选择
- **模块化设计**: Agent / 协作引擎 / 上下文 / 消息路由独立可扩展
- **基于成熟框架**: AutoGen 协作 + LangChain 工具
- **异步执行**: 全 async, 高并发

### 安装

```bash
pip install -r requirements.txt
# 或最小化
pip install autogen-agentchat langchain langchain-openai pydantic loguru
```

### 支持的 LLM Provider

| Provider | 模型 | API 类型 |
|----------|------|----------|
| **MiniMax** | M2.7 | OpenAI Compatible |
| **Claude** | Sonnet 4 | Anthropic |
| **Qwen** (通义千问) | qwen-plus, qwen-turbo | OpenAI Compatible |
| **Zhipu** (智谱 GLM) | glm-4, glm-3-turbo | OpenAI Compatible |
| **DeepSeek** | deepseek-chat | OpenAI Compatible |
| **Hunyuan** (混元) | hunyuan-turb, hunyuan-plus, hunyuan-pro | Tencent Cloud |
| **OpenAI** | GPT-4o, GPT-4 | OpenAI |

### 内置工具

| 工具 | 功能 |
|------|------|
| `CalculatorTool` | 安全数学计算 |
| `TextFormatterTool` | 文本格式化/统计 |
| `FileReaderTool` / `FileWriterTool` | 文件 I/O |
| `HttpGetTool` | HTTP GET |
| `JsonParserTool` | JSON 解析 |
| `RAGSearchTool` | RAG 检索 |
| `DuckDuckGoSearchTool` | 免费网络搜索 |
| `TavilySearchTool` | AI 增强搜索 |
| `PythonCodeExecutorTool` | 安全 Python 执行 |

### 快速开始 (MACS 本身)

```python
import asyncio
from macs_pkg import create_runtime

async def main():
    runtime = create_runtime(
        agents=[
            {"name": "planner", "role": "planner"},
            {"name": "executor", "role": "executor"},
            {"name": "reviewer", "role": "reviewer"},
        ],
        mode="hierarchical",
    )
    result = await runtime.execute({
        "type": "code_generation",
        "description": "Create a factorial function",
    })
    print(result)

asyncio.run(main())
```

### 协作模式

**层级式 (Hierarchical)**:
```
User → Planner (分解) → [Executor₁, Executor₂, ...] (并行)
                                    ↓
                            Reviewer (审查汇总)
                                    ↓
                              Final Output
```

**去中心化 (Decentralized)**:
```
User → [Agent₁] ↔ [Agent₂] ↔ [Agent₃] (点对点协商)
                  ↓         ↓         ↓
              [投票/共识机制]
                  ↓
              Final Output
```

**管道式 (Pipeline)**:
```
User → Agent₁ → Agent₂ → Agent₃ → Final
        (每步处理后传递给下一步)
```

### 扩展

**自定义 Agent**:
```python
from macs_pkg.core.agent import BaseAgent, AgentRole, Message

class MyAgent(BaseAgent):
    def __init__(self, name):
        super().__init__(name, AgentRole.EXECUTOR)

    async def think(self, message: Message) -> Message:
        pass

    async def act(self, response: Message) -> list:
        pass
```

**自定义协作模式**:
```python
from macs_pkg.collaboration.base import CollaborationMode

class MyMode(CollaborationMode):
    async def execute(self, task, agents, context=None):
        pass

    def select_agents(self, task, available_agents):
        pass
```

### 运行测试

```bash
# 全部
pytest tests/ -v

# 仅 ERP Copilot (非集成)
make erp-test
```

---

## 🤝 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md). 提交 PR 前请:

1. `make erp-ci` 全绿
2. 新功能加测试 (跟 `test_erp_*.py` 风格一致)
3. 更新 [CHANGELOG.md](CHANGELOG.md)

---

## 📄 许可证

MIT — 见 [LICENSE](LICENSE)
