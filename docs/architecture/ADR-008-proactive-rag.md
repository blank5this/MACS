# ADR-008: Proactive RAG over Reactive RAG

- **Status**: Accepted
- **Date**: 2026-04
- **Deciders**: Core team

## Context

Two patterns exist for giving an agent RAG capabilities:

**Reactive RAG (LLM-decided tool calls):**
The LLM sees the list of tools (`search_kb(query)`) in its system prompt. When needed, it emits a tool call. The framework executes it and feeds the result back.

**Proactive RAG (framework-decided retrieval):**
The framework inspects the user message, detects relevant keywords/topics, retrieves context *before* calling the LLM, and prepends the context to the LLM prompt.

## Decision

We use **Proactive RAG** by default, with keywords tuned to the ERP domain.

```python
ERP_KEYWORDS = [
    "采购", "供应商", "库存", "财务", "审批",
    "销售", "订单", "报销", "付款", "管理"
]

async def execute_subtask(self, task):
    if any(kw in task.text for kw in ERP_KEYWORDS):
        chunks = await rag.search(task.text, top_k=3)
        context = format_chunks(chunks)
        task.text = f"{context}\n\n用户问题: {task.text}"
    return await self._llm_chat(task.text)
```

## Why?

1. **Reliability**: We don't depend on the LLM correctly choosing to call the search tool. Some smaller models (and MiniMax-M2.7 specifically) miss tool calls ~10-20% of the time.
2. **Latency**: Reactive RAG requires 2 LLM roundtrips (decide to search, then answer). Proactive RAG is 1 roundtrip + 1 cheap retrieval.
3. **Predictability**: For known domains (ERP), keyword heuristics work well. We don't need the LLM to "discover" that the user is asking about inventory.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Reactive RAG (LLM-decided) | Flexible, general | Unreliable for small models, 2 roundtrips |
| Pure prompt engineering (no retrieval) | Simplest | Hallucinates |
| **Proactive RAG (chosen)** | Reliable, 1 roundtrip, domain-tuned | Brittle to new domains |

## Consequences

**Positive:**
- Stable RAG behavior across all 6 LLM providers (including MiniMax-M2.7).
- Lower latency (avg 4-6s vs 8-12s for reactive).
- Keyword list is a single source of truth — easy to extend.

**Negative:**
- Adding a new domain (e.g., HR) requires updating the keyword list.
- Edge cases where the LLM would have *correctly* decided not to retrieve but we retrieve anyway (wasted cost).
- Hard-coded keywords don't generalize.

## When to switch

If we ever support a general-purpose domain where we can't enumerate keywords, we'd switch to a hybrid:
- Default: Proactive RAG (fast, reliable)
- Fallback: Reactive RAG (if no keyword matched and LLM still decides to search)

## Verification

```python
async def test_proactive_rag_triggers():
    """Keywords trigger RAG retrieval."""
    task = Task(text="如何处理采购退货？")
    agent._inject_rag(task)
    assert "知识库片段" in task.text or "[1]" in task.text

async def test_proactive_rag_skips():
    """Non-ERP queries don't trigger RAG."""
    task = Task(text="What's the weather?")
    agent._inject_rag(task)
    assert task.text == "What's the weather?"  # unchanged
```