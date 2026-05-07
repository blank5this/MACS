# MACS - Multi-Agent Collaboration System

[![Tests](https://github.com/blank5this/MACS/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/blank5this/MACS/actions)
[![PyPI version](https://img.shields.io/pypi/v/macs_pkg.svg)](https://pypi.org/project/macs_pkg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Downloads](https://img.shields.io/pypi/dm/macs_pkg.svg)](https://pypi.org/project/macs_pkg/)

一个通用的、可扩展的多智能体协作系统框架，支持多种协作模式（层级式、去中心化、管道式）。

## 特性

- **通用架构**: 不针对特定场景，可适应各种应用需求
- **多种协作模式**: 支持层级式 Leader-Agent、去中心化协商、管道式处理，以及动态模式选择
- **模块化设计**: Agent、协作引擎、上下文管理、消息路由等模块独立可扩展
- **基于成熟框架**: 以 AutoGen 为协作核心，LangChain 为工具层
- **异步执行**: 全异步架构，支持高并发

## 安装

```bash
pip install -r requirements.txt
```

或者使用 pip 安装：

```bash
pip install autogen-agentchat langchain langchain-openai pydantic loguru
```

## 支持的 LLM Provider

| Provider | 模型 | API 类型 |
|----------|------|----------|
| **MiniMax** | M2.7 | OpenAI Compatible |
| **Claude** | Sonnet 4 | Anthropic |
| **Qwen** (通义千问) | qwen-plus, qwen-turbo | OpenAI Compatible |
| **Zhipu** (智谱 GLM) | glm-4, glm-3-turbo | OpenAI Compatible |
| **DeepSeek** | deepseek-chat | OpenAI Compatible |
| **Hunyuan** (混元) | hunyuan-turb, hunyuan-plus, hunyuan-pro | Tencent Cloud |
| **OpenAI** | GPT-4o, GPT-4 | OpenAI |

### 使用示例

```python
# MiniMax
from macs_pkg.llm import MiniMaxProvider

provider = MiniMaxProvider(api_key="your_key", model="MiniMax-M2.7")

# Qwen (通义千问)
from macs_pkg.llm import QwenProvider

provider = QwenProvider(api_key="your_key", model="qwen-plus")

# Zhipu (智谱)
from macs_pkg.llm import ZhipuProvider

provider = ZhipuProvider(api_key="your_key", model="glm-4")

# Hunyuan (混元) - 腾讯自研大模型
from macs_pkg.llm import HunyuanProvider

# 方式1: 使用混元 API Key (新版)
provider = HunyuanProvider(api_key="your_hunyuan_key", model="hunyuan-turb")

# 方式2: 使用腾讯云 SecretId/SecretKey
provider = HunyuanProvider(
    secret_id="your_secret_id",
    secret_key="your_secret_key",
    model="hunyuan-plus",
)
```

## 内置工具

| 工具 | 功能 |
|------|------|
| `CalculatorTool` | 安全数学计算 |
| `TextFormatterTool` | 文本格式化/统计 |
| `FileReaderTool` | 文件读取 |
| `FileWriterTool` | 文件写入 |
| `HttpGetTool` | HTTP GET 请求 |
| `JsonParserTool` | JSON 解析 |
| `RAGSearchTool` | RAG 知识库检索 |
| `DuckDuckGoSearchTool` | 免费网络搜索 |
| `TavilySearchTool` | AI 增强搜索 |
| `PythonCodeExecutorTool` | 安全 Python 代码执行 |

### 工具使用示例

```python
from macs_pkg.tools import (
    CalculatorTool,
    DuckDuckGoSearchTool,
    PythonCodeExecutorTool,
    create_default_registry,
)

# 创建工具注册表
registry = create_default_registry()

# 添加搜索工具
search_tool = DuckDuckGoSearchTool()
result = await search_tool.run(query="深圳天气", num_results=5)

# 添加代码执行
code_tool = PythonCodeExecutorTool(timeout=30)
result = await code_tool.run(code="print(sum(range(100)))")
```

## 快速开始

### 基本用法

```python
import asyncio
from macs.runtime.engine import create_runtime

async def main():
    # 创建运行时引擎
    runtime = create_runtime(
        agents=[
            {"name": "planner", "role": "planner"},
            {"name": "executor", "role": "executor"},
            {"name": "reviewer", "role": "reviewer"},
        ],
        mode="hierarchical"
    )

    # 执行任务
    result = await runtime.execute({
        "type": "code_generation",
        "description": "Create a factorial function",
    })

    print(result)

asyncio.run(main())
```

### 协作模式

#### 层级式 (Hierarchical)

```
User Input → Planner (分解) → [Executor₁, Executor₂, ...] (并行)
                                       ↓
                               Reviewer (审查汇总)
                                       ↓
                                   Final Output
```

#### 去中心化 (Decentralized)

```
User Input → [Agent₁] ↔ [Agent₂] ↔ [Agent₃] (点对点协商)
                      ↓         ↓         ↓
                   [投票/共识机制]
                      ↓
                  Final Output
```

#### 管道式 (Pipeline)

```
User Input → Agent₁ → Agent₂ → Agent₃ → Final Output
           (每步处理后传递给下一步)
```

## 项目结构

```
macs/
├── core/                      # 核心模块
│   ├── agent.py              # Agent 基类
│   ├── message.py            # 消息协议
│   ├── context.py            # 上下文管理
│   ├── router.py             # 消息路由
│   └── aggregator.py         # 结果聚合
├── collaboration/             # 协作引擎
│   ├── base.py               # 协作模式基类
│   ├── hierarchical.py        # 层级式协作
│   ├── decentralized.py       # 去中心化协作
│   ├── pipeline.py           # 管道式协作
│   └── dynamic_selector.py   # 动态模式选择
├── agents/                    # Agent 实现
│   ├── planner.py            # 规划 Agent
│   ├── executor.py           # 执行 Agent
│   ├── reviewer.py           # 审查 Agent
│   └── tool_agent.py         # 工具 Agent
├── tools/                     # 工具集
├── runtime/                   # 运行时
│   ├── engine.py             # 主引擎
│   └── config.py             # 配置管理
├── examples/                  # 示例
└── tests/                     # 测试
```

## Agent 类型

| 角色 | 描述 |
|------|------|
| **Planner** | 分解复杂任务，创建执行计划 |
| **Executor** | 执行具体的子任务 |
| **Reviewer** | 审核和验证结果 |
| **Tool** | 调用外部工具和函数 |

## 配置

### 运行时配置

```python
from macs.runtime.config import MACSConfig

config = MACSConfig(
    default_model="gpt-4",
    log_level="INFO",
)
```

### 环境变量

```bash
export MACS_LOG_LEVEL=DEBUG
export MACS_DEFAULT_MODEL=gpt-4
```

## 运行测试

```bash
pytest macs/tests/ -v
```

## 示例

参见 `macs/examples/` 目录：

- `simple_chat.py` - 简单对话示例
- `code_generation.py` - 代码生成示例（层级式）
- `research_assistant.py` - 研究助手示例（去中心化）

## 扩展

### 自定义 Agent

```python
from macs.core.agent import BaseAgent, AgentRole, Message

class MyAgent(BaseAgent):
    def __init__(self, name):
        super().__init__(name, AgentRole.EXECUTOR)

    async def think(self, message: Message) -> Message:
        # 处理消息
        pass

    async def act(self, response: Message) -> list:
        # 执行动作
        pass
```

### 自定义协作模式

```python
from macs.collaboration.base import CollaborationMode

class MyMode(CollaborationMode):
    async def execute(self, task, agents, context=None):
        # 自定义协作逻辑
        pass

    def select_agents(self, task, available_agents):
        # 选择合适的 Agent
        pass
```

## 许可证

MIT
