# MACS Architecture

> This document describes the system design of MACS — Multi-Agent Collaboration System.
> For API reference, see [SPEC.md](./SPEC.md).

---

## 1. System Overview

MACS is a Python framework for building multi-agent AI applications. It provides:

1. **Agent Framework** — BaseAgent with think()/act() lifecycle
2. **Collaboration Modes** — Hierarchical, Decentralized, Pipeline, Dynamic Selector
3. **LLM Providers** — Claude, MiniMax-M2.7, OpenAI-compatible
4. **RAG Pipeline** — Offline Chinese embedding + vector search
5. **Tool System** — Anthropic/OpenAI-format tool calling
6. **Memory System** — MemPalace long-term memory
7. **Observability** — Prometheus + OpenTelemetry exporters

---

## 2. Agent Lifecycle

Every agent implements two-phase execution:

```
Message → think() → Message → act() → List[Message]
              ↓
         LLM call happens here (if provider configured)
```

### Think Phase

- Process incoming message
- Optionally call LLM for reasoning
- Return response message

### Act Phase

- Execute actions based on think() response
- Send messages to other agents
- Update memory
- Return list of outgoing messages

---

## 3. Agent Roles

```python
class AgentRole(Enum):
    PLANNER = "planner"   # Task decomposition
    EXECUTOR = "executor" # Subtask execution
    REVIEWER = "reviewer" # Result validation
    TOOL = "tool"         # External tool invocation
```

---

## 4. Collaboration Modes

### 4.1 Hierarchical Mode (Most Common)

```
User Input
    ↓
Planner.think() + act()
    ↓ (subtasks distributed to executors)
[Executor₁, Executor₂, ...] — parallel execution
    ↓ (results collected)
Reviewer.think() + act()
    ↓
Final Output
```

**Key implementation:** `macs_pkg/collaboration/hierarchical.py`

**Critical:** Must call both `think()` and `act()` for each agent — calling only `think()` means LLM is never invoked.

### 4.2 Decentralized Mode

```
User Input → [Agent₁] ↔ [Agent₂] ↔ [Agent₃]
                      ↓         ↓         ↓
                   peer-to-peer negotiation
                      ↓
              voting / consensus mechanism
                      ↓
                  Final Output
```

### 4.3 Pipeline Mode

```
User Input → Agent₁ → Agent₂ → Agent₃ → Final Output
               ↓        ↓        ↓
          (each agent's output becomes next agent's input)
```

---

## 5. RAG Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Ingestion                       │
│  raw_text → DocumentChunker → chunks (200 chars, 30 overlap) │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Embedding Generation                       │
│  ChineseCharNgramEmbedder (offline, no GPU)                 │
│  character n-gram (1-3) + TF-IDF → 384-dim vector          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Vector Storage                           │
│  InMemoryVectorStore (cosine similarity)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Query Execution                           │
│  query → embed → vector search → top-k results              │
└─────────────────────────────────────────────────────────────┘
```

### Proactive RAG vs Reactive RAG

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Proactive** | Executor detects ERP keywords → auto-search → inject into LLM prompt | Stable, keyword-driven domains |
| **Reactive** | LLM decides via tool_use when to call RAG | Flexible, but may miss or fail |

---

## 6. LLM Integration

### 6.1 Provider Architecture

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        messages: List[LLMMessage],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse: ...
```

### 6.2 Supported Providers

| Provider | Model | Use Case |
|----------|-------|----------|
| MiniMax | MiniMax-M2.7 | Default, cost-effective |
| Claude | claude-sonnet-4-6 | High quality |
| OpenAI | gpt-4o | Broad compatibility |

### 6.3 Error Handling

```python
# openai_compatible.py
class LLMError(Exception): pass
class TimeoutError(LLMError):      # → {"fallback": True}
class RateLimitError(LLMError):    # → {"retry_after": True}
```

---

## 7. Tool Calling

MACS agents can call tools using Anthropic/OpenAI function-calling format:

```
LLM generates → tool_calls list → ToolRegistry.invoke() → ToolResult
```

**RAG Tool Schema Example:**

```python
{
    "name": "erp_knowledge_search",
    "description": "Search ERP knowledge base for policies and procedures",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
}
```

---

## 8. Memory System

MACS uses MemPalace for agent long-term memory:

```python
# Per-agent memory
await agent.remember("User prefers dark theme")
results = await agent.recall("theme preference")

# Shared memory across agents
await BaseAgent.init_shared_memory()
```

---

## 9. Observability

### 9.1 Tracing

`RuntimeEngine` with `enable_tracing=True` generates Mermaid sequence diagrams:

```python
runtime = RuntimeEngine(RuntimeConfig(enable_tracing=True))
tracer = runtime.get_tracer()
mermaid = tracer.generate_mermaid_sequence()
```

### 9.2 Metrics

```python
# Prometheus exporter
exporter = PrometheusExporter()
exporter.start()

# OpenTelemetry (planned)
exporter = OpenTelemetryExporter()
```

---

## 10. Data Flow

```
User Input (Task)
    ↓
RuntimeEngine.execute(task, mode="hierarchical")
    ↓
HierarchicalMode.execute()
    ↓
┌─ Planner.think() → Planner.act()
│       ↓ (subtask messages)
├─ Executor₁.think() + act() ─┐
├─ Executor₂.think() + act() ──┼─ parallel
└─ ... ────────────────────────┘
    ↓ (results)
┌─ Reviewer.think() → Reviewer.act()
    ↓
Final Result
```

---

## 11. Key Files

| File | Purpose |
|------|---------|
| `macs_pkg/core/agent.py` | BaseAgent, Message, AgentRole |
| `macs_pkg/agents/planner.py` | Task decomposition |
| `macs_pkg/llm/agents.py` | LLM-powered agents |
| `macs_pkg/llm/openai_compatible.py` | MiniMax/Claude providers |
| `macs_pkg/rag/rag_engine.py` | RAG engine |
| `macs_pkg/rag/chinese_embedder.py` | Offline Chinese embedder |
| `macs_pkg/collaboration/hierarchical.py` | Hierarchical mode |
| `macs_pkg/tools/registry.py` | Tool registry |

---

## 12. Extension Points

### Custom Agent

```python
class MyAgent(BaseAgent):
    async def think(self, message: Message) -> Message:
        # Custom processing
        return response

    async def act(self, response: Message) -> List[Message]:
        # Custom actions
        return [outgoing_msg]
```

### Custom Embedder

```python
from macs_pkg.rag import Embedder

class MyEmbedder(Embedder):
    async def embed(self, text: str) -> list[float]:
        # Custom embedding logic
        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Batch embedding
        return vectors
```

### Custom Collaboration Mode

```python
from macs_pkg.collaboration import CollaborationMode

class MyMode(CollaborationMode):
    name = "my_mode"
    description = "Custom collaboration pattern"

    async def execute(self, task, agents, context=None):
        # Custom execution logic
        return final_result
```
