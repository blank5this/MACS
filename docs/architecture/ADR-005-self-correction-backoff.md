# ADR-005: Self-correction with exponential backoff + jitter

- **Status**: Accepted
- **Date**: 2026-05
- **Deciders**: Core team

## Context

LLM APIs are flaky. Rate limits, transient network failures, server-side 5xx errors all happen. Naive retry hammers the API and worsens the outage.

## Decision

When an LLM call fails with a recoverable error, retry with **exponential backoff + ±25% random jitter**.

```python
async def complete_with_retry(self, messages, max_retries=4):
    for attempt in range(max_retries):
        try:
            return await self._call_llm(messages)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            base_delay = 0.5 * (2 ** attempt)  # 0.5, 1, 2, 4 seconds
            jitter = base_delay * 0.25 * (2 * random.random() - 1)
            delay = base_delay + jitter
            logger.warning(f"Rate limited, retry in {delay:.2f}s (attempt {attempt+1})")
            await asyncio.sleep(delay)
```

Backoff schedule: 0.5s → 1s → 2s → 4s → 8s (capped).

## Why jitter?

If 1000 clients all hit a rate limit at the same time and all retry after exactly 1s, they hammer the API at the same instant. Jitter spreads the retries uniformly across the next 250ms.

## Why ±25% (not full random)?

Full random (e.g., 0-1s) makes the behavior hard to reason about. ±25% gives predictable bounds while still spreading load.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Fixed delay (e.g., 1s) | Simplest | Doesn't backoff, thundering herd |
| Exponential, no jitter | Predictable | Synchronized retries |
| Linear backoff | Easy to reason about | Less aggressive recovery |
| **Exponential + jitter (chosen)** | Industry standard | Slightly more complex |

## Consequences

**Positive:**
- Recovery from rate limits without making them worse.
- Predictable bounds on total retry time (max ~7.5s for 4 retries).
- Configurable per-provider (different providers have different limits).

**Negative:**
- Adds latency to user-facing requests during outages.
- Retry budget must be tuned per-provider.
- Idempotency: most LLM calls are not strictly idempotent (especially with non-zero temperature).

## Verification

```python
async def test_backoff_schedule():
    """Verify exponential growth + jitter."""
    delays = []
    for attempt in range(4):
        delay = compute_backoff(attempt, base=0.5, jitter_pct=0.25)
        delays.append(delay)
    # Each delay should be ~2x previous, within ±25%
    assert 0.375 <= delays[0] <= 0.625
    assert 0.75 <= delays[1] <= 1.25
    assert 1.5 <= delays[2] <= 2.5
    assert 3.0 <= delays[3] <= 5.0
```