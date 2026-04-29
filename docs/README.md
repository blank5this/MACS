# MACS - Multi-Agent Collaboration System

A general-purpose, extensible multi-agent collaboration framework with support for hierarchical, decentralized, pipeline, and dynamic-selector collaboration modes.

## Features

- **General-purpose Architecture**: Not tied to any specific use case — adapt it to your needs
- **Multiple Collaboration Modes**: Hierarchical (Leader-Agent), Decentralized (negotiation), Pipeline, and Dynamic mode selection
- **Modular Design**: Agents, collaboration engine, context management, and message routing are independently extensible
- **Based on Proven Frameworks**: AutoGen for collaboration core, LangChain for tool layer
- **Async-first**: Full async architecture supporting high concurrency
- **RAG Knowledge Base**: Built-in offline Chinese text embedding (character n-gram TF-IDF)
- **LLM Integration**: Connect to Claude, MiniMax-M2.7, OpenAI-compatible models
- **Enterprise Ready**: OpenTelemetry metrics, audit logging, Docker/K8s deployment

## Installation

```bash
pip install -e ".[dev]"
```

Or with specific dependencies:

```bash
pip install autogen-agentchat langchain langchain-openai pydantic loguru
```

## Quick Start

```python
import asyncio
from macs_pkg import (
    RuntimeEngine, RuntimeConfig,
    MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent,
    MiniMaxProvider,
)

async def main():
    # 1. Create LLM provider
    provider = MiniMaxProvider(
        api_key="your_api_key",
        model="MiniMax-M2.7",
    )

    # 2. Create agents
    planner = MiniMaxPlannerAgent("planner", provider=provider)
    executor = MiniMaxExecutorAgent("executor", provider=provider)
    reviewer = MiniMaxReviewerAgent("reviewer", provider=provider)

    # 3. Create runtime engine
    runtime = RuntimeEngine(RuntimeConfig(
        enable_tracing=True,
        default_mode="hierarchical",
    ))
    runtime.register_agent(planner)
    runtime.register_agent(executor)
    runtime.register_agent(reviewer)

    # 4. Execute a task
    result = await runtime.execute({
        "type": "erp_qa",
        "description": "How does an employee submit a purchase requisition?",
    })

    print(result)

asyncio.run(main())
```

## Collaboration Modes

### Hierarchical (Leader-Agent)

```
User Input → Planner (decompose) → [Executor₁, Executor₂, ...] (parallel)
                                          ↓
                                    Reviewer (review)
                                          ↓
                                      Final Output
```

### Decentralized

```
User Input → [Agent₁] ↔ [Agent₂] ↔ [Agent₃] (peer-to-peer negotiation)
                      ↓         ↓         ↓
                   [voting / consensus]
                      ↓
                  Final Output
```

### Pipeline

```
User Input → Agent₁ → Agent₂ → Agent₃ → Final Output
           (output of each step becomes input of next)
```

## Project Structure

```
macs_pkg/
├── core/                      # Core abstractions
│   ├── agent.py              # BaseAgent, AgentRole, Message
│   ├── message.py            # MessageType
│   ├── context.py            # ContextManager
│   └── router.py             # MessageRouter
├── agents/                   # Agent implementations
│   ├── planner.py           # PlannerAgent (task decomposition)
│   ├── executor.py          # ExecutorAgent (subtask execution)
│   └── reviewer.py          # ReviewerAgent (result validation)
├── llm/                      # LLM providers
│   ├── base.py              # LLMProvider, LLMMessage, LLMResponse
│   ├── claude.py            # ClaudeProvider (Anthropic)
│   ├── openai_compatible.py # OpenAICompatibleProvider, MiniMaxProvider
│   └── agents.py            # LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent
├── rag/                      # RAG engine
│   ├── rag_engine.py       # RAGEngine, RAGConfig
│   ├── chinese_embedder.py  # ChineseCharNgramEmbedder (offline TF-IDF)
│   └── vector_store.py     # VectorStore, InMemoryVectorStore
├── tools/                    # Tool system
│   ├── registry.py         # ToolRegistry
│   └── rag_tool.py         # RAGSearchTool
├── collaboration/          # Collaboration modes
│   ├── hierarchical.py     # HierarchicalMode
│   └── decentralized.py    # DecentralizedMode
├── memory/                  # Memory system
│   └── agent_memory.py     # MemPalace long-term memory
└── runtime/                 # Runtime engine
    └── engine.py           # RuntimeEngine
```

## Agent Types

| Role | Description |
|------|-------------|
| **Planner** | Decomposes complex tasks into subtasks |
| **Executor** | Executes assigned subtasks |
| **Reviewer** | Reviews and validates results |
| **Tool** | Invokes external tools and functions |

## Configuration

### Runtime Configuration

```python
from macs_pkg import RuntimeConfig

config = RuntimeConfig(
    enable_tracing=True,
    default_mode="hierarchical",
    log_level="INFO",
)
```

### Environment Variables

```bash
export MINIMAX_API_KEY=your_key        # MiniMax API key
export ANTHROPIC_API_KEY=your_key     # Claude API key
export MACS_LOG_LEVEL=DEBUG
```

## Running Tests

```bash
cd C:\Users\admin\Desktop\macs
pytest tests/ -v
```

## Examples

See `examples/`:

- `erp_knowledge_assistant.py` — ERP Knowledge Q&A with RAG + multi-agent
- `rag_example.py` — Standalone RAG usage
- `interview_qa.py` — Interview Q&A assistant

## Live Demo

Try MACS without installing anything:

```bash
# Start demo server locally
python demo_server.py

# Then POST a request
curl -X POST http://localhost:8000/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "How do I submit a purchase requisition?", "mode": "hierarchical"}'
```

**Deploy to Railway (one click):**
[![Deploy to Railway](https://railway.app/button.svg)](https://railway.app/new?template=https://github.com/blank5this/MACS)

Or connect your GitHub repo on [Railway](https://railway.app) and set:
- Start command: `python demo_server.py`
- Environment: `MINIMAX_API_KEY=your_key`

## Benchmark

See `docs/BENCHMARK.md` for detailed comparison with LangChain Agents and AutoGen.

| Criterion | MACS | LangChain | AutoGen |
|-----------|------|-----------|---------|
| Chinese RAG (offline) | **5** | 2 | 2 |
| Multi-agent modes | **5** | 2 | 3 |
| Enterprise ready | **4** | 4 | 4 |
| **Total** | **27** | 25 | 18 |

## Extending MACS

### Custom Agent

```python
from macs_pkg import BaseAgent, AgentRole, Message

class MyAgent(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name, AgentRole.EXECUTOR)

    async def think(self, message: Message) -> Message:
        # Process message
        pass

    async def act(self, response: Message) -> list[Message]:
        # Perform actions
        pass
```

### Custom Collaboration Mode

```python
from macs_pkg.collaboration.base import CollaborationMode

class MyMode(CollaborationMode):
    async def execute(self, task, agents, context=None):
        # Custom collaboration logic
        pass
```

## Enterprise Features

### OpenTelemetry Metrics

```python
from macs_pkg.monitoring import PrometheusExporter

exporter = PrometheusExporter()
exporter.start()
```

### Docker Deployment

```bash
docker build -t macs/macs:latest .
docker run -e MINIMAX_API_KEY=xxx macs/macs:latest
```

### RAG Knowledge Base

```python
from macs_pkg.rag import RAGEngine, RAGConfig

config = RAGConfig(
    embedder_provider="chinese_char_ngram",  # Offline, no GPU needed
    vector_store_type="memory",
    embedding_dim=384,
)
engine = RAGEngine(config)
await engine.add_documents(texts, metadatas)
results = await engine.search("purchase requisition")
```

## License

MIT
