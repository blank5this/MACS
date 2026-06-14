# ADR-002: Pluggable LLM provider abstraction

- **Status**: Accepted
- **Date**: 2026-04
- **Deciders**: Core team

## Context

We support 6+ LLM providers (Claude, GPT-4o, MiniMax-M2.7, Qwen, DeepSeek, Zhipu, Hunyuan). Each has its own API contract, rate limits, error semantics, and pricing. Hard-coding one vendor would lock us in and make A/B testing impossible.

## Decision

Define a `LLMProvider` abstract base class with a single required method:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        system: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        ...
```

All concrete providers (`ClaudeProvider`, `OpenAICompatibleProvider`, `MiniMaxProvider`, `QwenProvider`, etc.) implement this interface.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Use LangChain's ChatModel directly | Less code | Vendor lock-in (LangChain API), can't swap out cleanly |
| One provider only (e.g., OpenAI) | Simplest | Single point of failure, can't A/B test |
| **Pluggable abstraction (chosen)** | Provider-agnostic, testable | More boilerplate |

## Consequences

**Positive:**
- Swapping providers is a 1-line config change.
- Tests can use a mock provider; no real API calls during CI.
- A/B testing different LLMs for the same task is trivial.

**Negative:**
- New providers need to implement the interface (~50-100 lines).
- Provider-specific features (e.g., Anthropic's prompt caching, OpenAI's function calling) require extension points.
- The "lowest common denominator" problem: we can't use cutting-edge features from any one provider.

## Verification

```python
# Swap providers in tests
def test_agent_routing():
    mock_provider = MockProvider(responses=["tool: get_low_stock_products"])
    agent = ERPCopilotAgent(provider=mock_provider)
    result = await agent.ask("Which products are low?")
    assert result["tool"] == "get_low_stock_products"
```