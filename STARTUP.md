# MACS 本地启动指南

> 适用项目路径: `E:\MACS`
> Python 要求: **>= 3.10**（已在 3.14.3 实测通过）

本指南说明如何在本地把 MACS 的两个 demo 跑起来，并验证完整的 Planner → Executor → Reviewer 链路。

---

## 1. 环境要求

| 组件 | 版本 | 备注 |
|------|------|------|
| Python | >= 3.10 | 推荐 3.11 / 3.12 |
| pip | 最新版 | `python -m pip install --upgrade pip` |
| 操作系统 | Windows / macOS / Linux | 本指南以 Windows CMD 为例 |
| 网络 | 可访问 LLM API | 用于真实推理 |

---

## 2. 安装依赖

```bash
cd E:\MACS

# 基础依赖（框架本体 + RAG + FastAPI demo）
pip install -e .
pip install -r requirements.txt
pip install -r requirements-demo.txt
```

如果只想跑不依赖 LLM 的离线 demo（`agent_process_demo.py`），可以跳过 LLM 相关依赖。

---

## 3. 配置 API Key（重要）

**所有真实调用 LLM 的 demo 都需要 `MINIMAX_API_KEY`。**

### 方式 A：环境变量（推荐）

**Windows CMD**:
```cmd
set MINIMAX_API_KEY=<your-key-here>
```

**Windows PowerShell**:
```powershell
$env:MINIMAX_API_KEY = "<your-key-here>"
```

**Linux / macOS / Git Bash**:
```bash
export MINIMAX_API_KEY=<your-key-here>
```

### 方式 B：`.env` 文件

在项目根目录创建 `.env`（已被 `.gitignore` 忽略，不会被提交）:

```
MINIMAX_API_KEY=<your-key-here>
```

> ⚠️ **永远不要**把真实 Key 写进代码、commit 到 git、或贴在聊天/工单里。
> 当前代码已全部改为从环境变量读取。

---

## 4. 启动方式

### 方式 1: FastAPI Demo Server（推荐，支持 HTTP 调用）

```bash
cd E:\MACS
set MINIMAX_API_KEY=<your-key-here>
python demo_server.py
```

服务启动后会看到:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**可访问的端点**:

| URL | 用途 |
|-----|------|
| `http://localhost:8000/health` | 健康检查（含 LLM 连通性测试） |
| `http://localhost:8000/api/v1/modes` | 列出协作模式 |
| `http://localhost:8000/api/v1/execute` | 提交任务（POST） |
| `http://localhost:8000/api/v1/usage/{user}` | 查询 Token 用量 |
| `http://localhost:8000/docs` | **交互式 API 文档（Swagger UI）** |

**测试调用**:

```bash
# 健康检查
curl http://localhost:8000/health

# 提交一个 ERP 问题
curl -X POST http://localhost:8000/api/v1/execute ^
  -H "Content-Type: application/json" ^
  -d "{\"task\": \"员工如何提交采购申请？\", \"mode\": \"hierarchical\", \"use_rag\": true}"
```

典型响应时间: **60~90 秒**（3 个 Agent 各调一次 LLM）。

### 方式 2: 离线流程演示（无需 Key）

```bash
cd E:\MACS
python agent_process_demo.py
```

会逐步打印 Planner → Executor → Reviewer 的协作流程，所有 LLM 调用都是 mock 的（写死的字符串），纯展示用。**适合无网络/无 Key 时演示框架结构**。

### 方式 3: 3-Agent 真实调用（需 Key）

```bash
cd E:\MACS
set MINIMAX_API_KEY=<your-key-here>
python test_3_agent.py
```

会创建 Planner/Executor/Reviewer 三个真实调用 MiniMax-M2.7 的 Agent，串行执行一个简单任务并打印结果。

---

## 5. 端到端验证清单

启动后跑一遍这些命令确认无误:

```bash
# 1. 服务存活
curl http://localhost:8000/health
# → {"status":"healthy","llm_connected":true,...}

# 2. 模式列表
curl http://localhost:8000/api/v1/modes
# → 3 种模式: hierarchical / pipeline / decentralized

# 3. 真实执行 ERP 问答
curl -X POST http://localhost:8000/api/v1/execute ^
  -H "Content-Type: application/json" ^
  -d "{\"task\": \"供应商评级有哪些？付款条件是什么？\"}"
# → status: "success"，result.final_output 含具体答案
```

---

## 6. 常见错误排查

### `RuntimeError: asyncio.run() cannot be called from a running event loop`

**原因**: FastAPI handler 内不能在 async 上下文里调用 `asyncio.run()`。
**修复**: 已修复 — `_build_runtime()` 已改为 async。

### `llm_connected: false`

**原因**: API Key 没设、设错、或网络不通。
**排查**:

```bash
# 1. 确认环境变量已设
echo %MINIMAX_API_KEY%   # Windows CMD
echo $MINIMAX_API_KEY    # Git Bash / Linux

# 2. 确认 Key 可用
python -c "import os; print(len(os.environ.get('MINIMAX_API_KEY', '')))"
# 应该输出 > 50 的数字
```

### `ModuleNotFoundError: No module named 'macs_pkg'`

**原因**: 没在项目根目录运行，或没安装包。
**修复**:

```bash
cd E:\MACS
pip install -e .
```

### `address already in use` （端口 8000 被占用）

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# 或换端口启动
set PORT=8080
python demo_server.py
```

### `There was an error parsing the body` (curl)

**原因**: JSON 里中文引号没转义、或 PowerShell 把 `^` 当成换行符。
**修复**: 把 JSON 写到文件里再 `--data @file.json` 传入，或用 Swagger UI（`/docs`）测试。

---

## 7. 项目结构速览

```
E:\MACS\
├── demo_server.py            # FastAPI Demo Server（HTTP API）
├── agent_process_demo.py     # 离线流程演示（无需 Key）
├── test_3_agent.py           # 3-Agent 真实调用测试
├── macs_pkg/                 # 框架本体
│   ├── agents/               # Planner/Executor/Reviewer/Tool
│   ├── llm/                  # 6 个 LLM Provider 抽象
│   ├── rag/                  # 混合检索 (char-ngram + BM25 + RRF)
│   ├── collaboration/        # 5 种协作模式
│   ├── runtime/              # RuntimeEngine
│   ├── erp/                  # ERP Copilot 业务模块
│   └── utils/                # TokenBudget / Guardrails / SessionMemory
├── examples/                 # 示例脚本
├── tests/                    # 326 个自动化测试
└── docs/architecture/        # 8 篇 ADR（架构决策记录）
```

---

## 8. 下一步

- 想自定义业务场景？→ 改 `demo_server.py` 第 203 行 `DEMO_KNOWLEDGE` 列表，加你自己的知识库内容
- 想换 LLM？→ 改 `demo_server.py` 第 236 行的 model 字符串和 Provider 类
- 想加 API Key 鉴权？→ 设 `API_KEYS=user1:sk-xxx,user2:sk-yyy` 环境变量
- 想部署到云？→ 看 `Dockerfile` + `docker-compose.yml`