# ADR-001: Use async Python throughout

- **Status**: Accepted
- **Date**: 2026-04
- **Deciders**: Core team

## Context

AI agent systems are inherently I/O-bound: every agent step involves an LLM API call (200ms–10s), a database query, a vector store lookup, or a tool invocation. Synchronous code would serialize all of these.

## Decision

All framework code is `async def`. The runtime engine uses `asyncio` for scheduling, the database layer uses `psycopg[async]`, and LLM providers expose `async def complete()`.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Sync Python | Simpler, easier to debug | Blocks on every I/O, can't run multi-agent in parallel |
| `threading` + sync | Familiar | GIL contention, doesn't help for I/O-bound |
| `multiprocessing` | True parallelism | Process overhead, can't share memory |
| **Async (chosen)** | Native I/O concurrency, single-threaded | Steeper learning curve, harder to mix with sync libs |

## Consequences

**Positive:**
- Single agent can fan out tool calls in parallel (e.g., RAG search + DB query + KB lookup).
- Multi-agent workflows benefit from cooperative scheduling.
- Connection pool reuse is straightforward.

**Negative:**
- Mixing async with sync libraries (e.g., some MCP stdio servers) requires bridging.
- Windows requires `SelectorEventLoop` (not `ProactorEventLoop`) for psycopg — handled in `db/connection.py:40`.
- Stack traces are harder to read.

## Verification

```python
# Parallel tool execution inside one agent
async def think(self, message):
    rag_task = asyncio.create_task(self.rag_search(message))
    db_task = asyncio.create_task(self.db_query(message))
    rag, db = await asyncio.gather(rag_task, db_task)
    return self.synthesize(rag, db)
```