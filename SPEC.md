# MACS 项目规格文档 (SPEC.md)

> 本文档是 MACS 项目的完整规格说明，可用于从零重建项目。
> 与 CLAUDE.md（工作记录）不同，本文档是"设计图纸"。

---

## 1. 项目概览

| 属性 | 值 |
|------|-----|
| 名称 | MACS (Multi-Agent Collaboration System) |
| 类型 | Python 多智能体协作框架 |
| 路径 | `C:\Users\admin\Desktop\macs` |
| Python | >= 3.10 |
| 许可证 | MIT |

### 核心能力

1. **多 Agent 协作** — 支持 hierarchical/decentralized/pipeline/dynamic-selector 四种协作模式
2. **LLM 集成** — 接入 MiniMax、Claude、OpenAI 兼容模型
3. **RAG 知识库** — 离线中文字符 n-gram TF-IDF 嵌入 + 向量检索
4. **工具调用** — Anthropic/OpenAI 格式 Tool Use
5. **记忆系统** — MemPalace 长期记忆
6. **执行追踪** — Mermaid 时序图可视化

---

## 2. 依赖管理

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "macs"
version = "0.1.0"
description = "Multi-Agent Collaboration System"
requires-python = ">=3.10"

dependencies = [
    "autogen-agentchat>=0.2.0",
    "langchain>=0.1.0",
    "langchain-openai>=0.0.5",
    "langchain-community>=0.0.10",
    "pydantic>=2.0",
    "python-dotenv>=1.0.0",
    "loguru>=0.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
]
```

### 直接 pip install

```bash
cd C:\Users\admin\Desktop\macs
pip install -e ".[dev]"
```

---

## 3. 包结构

```
macs_pkg/
├── __init__.py              # 主入口，导出所有公开 API
├── core/                    # 核心抽象
│   ├── agent.py             # BaseAgent, AgentRole, Message, AgentState
│   ├── message.py           # MessageType
│   ├── context.py           # ContextManager, TaskContext
│   ├── router.py            # MessageRouter
│   └── aggregator.py        # ResultAggregator
├── agents/                  # Agent 实现
│   ├── planner.py           # PlannerAgent (任务分解)
│   ├── executor.py          # ExecutorAgent (执行子任务)
│   ├── reviewer.py          # ReviewerAgent (审核结果)
│   └── tool_agent.py        # ToolAgent
├── llm/                     # LLM 提供者
│   ├── base.py              # LLMProvider, LLMMessage, LLMResponse (抽象)
│   ├── claude.py            # ClaudeProvider (Anthropic)
│   ├── openai_compatible.py # OpenAICompatibleProvider, MiniMaxProvider
│   └── agents.py            # LLMPlannerAgent, LLMExecutorAgent,
│                            # LLMReviewerAgent (Claude)
│                            # MiniMaxPlannerAgent, MiniMaxExecutorAgent,
│                            # MiniMaxReviewerAgent (MiniMax)
├── rag/                     # RAG 引擎
│   ├── rag_engine.py        # RAGEngine, RAGConfig, RetrievedContext
│   ├── embedder.py          # Embedder 基类, create_embedder()
│   ├── chinese_embedder.py  # ChineseCharNgramEmbedder (离线 TF-IDF)
│   ├── vector_store.py      # VectorStore, InMemoryVectorStore
│   └── document.py         # Document, DocumentChunker, DocumentProcessor
├── tools/                   # 工具系统
│   ├── base.py             # BaseTool, ToolResult, ToolSpec
│   ├── registry.py          # ToolRegistry
│   ├── rag_tool.py         # RAGSearchTool
│   └── builtin.py          # 内置工具
├── collaboration/           # 协作模式
│   ├── base.py            # CollaborationMode, CollaborationConfig
│   ├── hierarchical.py    # HierarchicalMode (Planner→Executor→Reviewer)
│   ├── decentralized.py   # DecentralizedMode
│   └── pipeline.py       # PipelineMode, ParallelPipelineMode
├── memory/                # 记忆系统
│   ├── agent_memory.py    # AgentMemory
│   └── mempalace_client.py # MemPalace 客户端
├── runtime/                # 运行时引擎
│   ├── engine.py         # RuntimeEngine
│   └── config.py         # RuntimeConfig
├── monitoring/            # 监控
│   └── prometheus_exporter.py
├── messaging/             # 分布式消息
│   └── redis_queue.py
└── utils/
    ├── logger.py          # get_logger()
    └── errors.py          # MACSException, AgentException 等
```

---

## 4. 核心概念

### 4.1 Agent 角色

```python
class AgentRole(Enum):
    PLANNER = "planner"   # 规划 → 分解任务
    EXECUTOR = "executor" # 执行 → 执行子任务
    REVIEWER = "reviewer" # 审查 → 审核结果质量
    TOOL = "tool"         # 工具 → 调用外部工具
```

### 4.2 Agent 生命周期

每个 Agent 实现 `think()` + `act()` 两个阶段：

```
Message → think() → Message → act() → List[Message]
              ↓
         LLM 调用发生在这里（如果配置了 provider）
```

### 4.3 协作模式 — Hierarchical（最常用）

```
User Input → Planner.think() + act() → 分解任务为 subtasks
                                          ↓
                              Executor.think() + act() (并行)
                                          ↓
                              Reviewer.think() + act() → 最终结果
```

### 4.4 RAG 流程

```
文档 → DocumentChunker (200字/块, 30字重叠)
          ↓
     ChineseCharNgramEmbedder (离线 TF-IDF, 无 GPU)
          ↓
     InMemoryVectorStore (余弦相似度)
          ↓
     search(query) → RetrievedContext[]
```

**Proactive RAG**：Executor 检测到 ERP 关键词后主动检索，结果注入 LLM prompt
**Reactive RAG**：LLM 通过 Tool Use 调用 RAG 工具

---

## 5. 关键 API

### 5.1 LLM Provider

```python
# macs_pkg/llm/base.py
@dataclass
class LLMMessage:
    role: str   # "user" | "assistant"
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]   # input_tokens, output_tokens
    tool_calls: List[Dict[str, Any]]
    stop_reason: Optional[str]

class LLMProvider(ABC):
    async def complete(
        messages: List[LLMMessage],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse: ...
```

### 5.2 MiniMax Provider 用法

```python
from macs_pkg.llm import MiniMaxProvider, LLMMessage

provider = MiniMaxProvider(
    api_key="your_key",
    model="MiniMax-M2.7",      # 注意：不是 MiniMax-Text-01
)
response = await provider.complete(
    messages=[LLMMessage(role="user", content="hello")],
    system="You are a helpful assistant.",
    max_tokens=1024,
)
```

### 5.3 Agent 创建

```python
from macs_pkg import (
    PlannerAgent, ExecutorAgent, ReviewerAgent,
    MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent,
)

# 无 LLM（heuristic 降级）
planner = PlannerAgent("planner")

# 有 LLM
planner = MiniMaxPlannerAgent("planner", provider=provider)
executor = MiniMaxExecutorAgent("executor", provider=provider, tool_registry=registry)
reviewer = MiniMaxReviewerAgent("reviewer", provider=provider)
```

### 5.4 RAG Engine 创建

```python
from macs_pkg.rag import RAGEngine, RAGConfig, ChineseCharNgramEmbedder

config = RAGConfig(
    embedder_provider="chinese_char_ngram",  # 离线嵌入器
    vector_store_type="memory",
    embedding_dim=384,
    chunk_size=200,
    chunk_overlap=30,
    default_top_k=3,
    similarity_threshold=0.0,
)
engine = RAGEngine(config)
await engine.add_documents(texts, metadatas)
results = await engine.search("采购申请", top_k=3)
```

### 5.5 RuntimeEngine 执行

```python
from macs_pkg import RuntimeEngine, RuntimeConfig

runtime = RuntimeEngine(RuntimeConfig(
    enable_shared_memory=True,
    enable_tracing=True,
    default_mode="hierarchical",
))
runtime.register_agent(planner)
runtime.register_agent(executor)
runtime.register_agent(reviewer)
result = await runtime.execute(task, mode="hierarchical")
```

---

## 6. 错误处理

```python
# macs_pkg/llm/openai_compatible.py
class LLMError(Exception): pass
class TimeoutError(LLMError): pass      # 超时 → fallback=True
class RateLimitError(LLMError): pass   # 限流 → retry_after=True
```

Executor 处理示例：
```python
except TimeoutError as e:
    return {"error": f"LLM timeout: {e}", "subtask_id": ..., "fallback": True}
except RateLimitError as e:
    return {"error": f"Rate limit: {e}", "subtask_id": ..., "retry_after": True}
except Exception as e:
    logger.error(f"LLM execution failed: {e}")
    return {"error": str(e), "subtask_id": ...}
```

---

## 7. 测试覆盖

```bash
cd C:\Users\admin\Desktop\macs
pytest tests/ -v
```

| 文件 | 测试内容 |
|------|----------|
| `test_chinese_embedder.py` | embedder 初始化、中文分词、单文本/批量嵌入、相似度、空文本、自动 fit |
| `test_rag_engine.py` | RAG 引擎检索、上下文元数据、空结果、统计、清空 |
| `test_planner_agent.py` | 初始化、分解任务、无 LLM 降级、act 发送消息 |
| `test_executor_agent.py` | 初始化、执行计划、结果存储、工具注册 |

共 20 个测试，全部通过。

---

## 8. 运行命令

### 快速验证 API

```bash
python -c "
import asyncio
from macs_pkg.llm import MiniMaxProvider
from macs_pkg.llm.base import LLMMessage

async def test():
    p = MiniMaxProvider(
        api_key='your_key',
        model='MiniMax-M2.7'
    )
    r = await p.complete([LLMMessage(role='user', content='say hi in 5 words')])
    print('OK:', r.content)
asyncio.run(test())
"
```

### ERP 知识助手演示

```bash
cd C:\Users\admin\Desktop\macs
set MINIMAX_API_KEY=your_key
python examples/erp_knowledge_assistant.py
```

---

## 9. 文件实现要点

### 9.1 ChineseCharNgramEmbedder（离线中文嵌入）

- **位置**: `macs_pkg/rag/chinese_embedder.py`
- **原理**: 字符 n-gram (1-3) + TF-IDF 向量化
- **优点**: 完全离线，无需 GPU，支持中文
- **限制**: 依赖词汇表大小，空文本返回零向量

### 9.2 HierarchicalMode 的 think + act

**位置**: `macs_pkg/collaboration/hierarchical.py`

```python
# 关键：必须同时调用 think() 和 act()
leader_response = await self._leader.think(planner_msg)
leader_actions = await self._leader.act(leader_response)

# 从 act() 的输出消息中提取 subtasks
for action_msg in leader_actions:
    if isinstance(action_msg.content, dict) and "subtask" in action_msg.content:
        subtasks.append(action_msg.content["subtask"])
```

**Bug 修复**: 之前只调用 `think()` 导致 LLM 不生效。

### 9.3 Proactive RAG 关键词检测

**位置**: `macs_pkg/llm/agents.py` MiniMaxExecutorAgent

```python
erp_keywords = ["采购", "供应商", "库存", "财务", "审批",
                "销售", "订单", "报销", "付款", "管理"]
if any(kw in task_text for kw in erp_keywords):
    rag_result = await rag_tool.execute(query=task_text)
    if rag_result.success:
        rag_context = f"\n\n[RAG检索结果]\n{rag_result.output}\n\n"
```

---

## 10. 已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| torch DLL 加载失败 | Windows 环境下 PyTorch DLL 问题 | 使用 `chinese_char_ngram` 离线嵌入器 |
| MiniMax embedding API 返回空 | API 响应格式问题 | 使用离线 TF-IDF 嵌入器 |
| LLM 不生效 | hierarchical 模式只调用了 think() | 同时调用 think() + act() |
| reviewer.py 变量未定义 | 第195行 `message.sender` 笔误 | 改为 `response.sender` |
| SYSTEM_PROMPT 语法错误 | 多行字符串括号未闭合 | 重新编写字符串 |

---

## 11. API Key 配置

| 模型 | 环境变量 | 模型名 |
|------|---------|--------|
| MiniMax-M2.7 | `MINIMAX_API_KEY` | `MiniMax-M2.7` |
| Claude | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` |

MiniMax API Key 格式: `sk-cp-xxxxxxxxxxxx`

---

## 12. 示例文件清单

```
examples/
├── erp_knowledge_assistant.py  # 主演示：ERP + RAG + 多Agent + 追踪
├── rag_example.py             # RAG 单独使用示例
└── interview_qa.py            # 面试问答示例
```
