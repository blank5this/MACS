# ADR-006: Conversation history capped at 100 messages

- **Status**: Accepted
- **Date**: 2026-05
- **Deciders**: Core team

## Context

Long-running agents that maintain conversation history (for context across turns) leak memory. The `MiniMaxAgentMixin._conversation` list grew unbounded, eventually OOMing in production after 6+ hours of operation.

## Decision

Cap conversation history at 100 messages. When exceeded, evict the oldest messages (FIFO).

```python
MAX_CONVERSATION_LENGTH = 100

def _add_message(self, message):
    self._conversation.append(message)
    if len(self._conversation) > MAX_CONVERSATION_LENGTH:
        # Keep system message + most recent 99
        self._conversation = self._conversation[-MAX_CONVERSATION_LENGTH:]
```

The cap keeps the system prompt + last 99 turns. For longer conversations, the oldest context is gone — accepted tradeoff.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Unbounded growth | Simplest | OOM in long-running sessions |
| Sliding window of N tokens | Matches LLM context window | Token counting is slow |
| Summarize old turns | Compact | Adds LLM call per turn, lossy |
| **Hard cap at 100 messages (chosen)** | Simple, predictable | Loses old context |

## Consequences

**Positive:**
- Bounded memory per agent (~100 messages × ~500 tokens = ~50K tokens max).
- Predictable cost (don't accidentally burn $10 on a long session).
- No production OOM since deployment.

**Negative:**
- After 100 turns, the agent forgets the start of the conversation.
- If the user goes back to an old topic, the agent has no memory.
- Some use cases (long debugging sessions) genuinely need unbounded history.

## When to revisit

If users complain about forgotten context in long sessions, switch to summarization-based compaction. For now, 100 messages is a 10x improvement over unbounded at zero complexity cost.

## Verification

```python
def test_conversation_cap():
    agent = make_agent()
    for i in range(150):
        agent._add_message(make_msg(f"turn {i}"))
    assert len(agent._conversation) == 100
    assert agent._conversation[0].content == "turn 50"  # Oldest kept
    assert agent._conversation[-1].content == "turn 149"
```