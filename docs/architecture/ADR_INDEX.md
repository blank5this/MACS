# Architecture Decision Records (ADR)

> Why we built it this way, not another. These records capture the *non-obvious* technical decisions that shape MACS / ERP AI Copilot.
> Format follows the [MADR](https://adr.github.io/madr/) template (lightweight).

---

## Index

| # | Decision | Status | Date |
|---|----------|--------|------|
| 001 | [Use async Python throughout](ADR-001-async-python.md) | ✅ Accepted | 2026-04 |
| 002 | [Pluggable LLM provider abstraction](ADR-002-llm-provider-abstraction.md) | ✅ Accepted | 2026-04 |
| 003 | [4-layer SQL safety guardrail](ADR-003-sql-safety-guardrail.md) | ✅ Accepted | 2026-04 |
| 004 | [Hybrid retrieval (char-ngram + BM25 + RRF)](ADR-004-hybrid-retrieval.md) | ✅ Accepted | 2026-04 |
| 005 | [Self-correction with exponential backoff + jitter](ADR-005-self-correction-backoff.md) | ✅ Accepted | 2026-05 |
| 006 | [Conversation history capping at 100 messages](ADR-006-conversation-cap.md) | ✅ Accepted | 2026-05 |
| 007 | [Read-only NL→SQL by default](ADR-007-readonly-default.md) | ✅ Accepted | 2026-04 |
| 008 | [Proactive RAG over Reactive RAG](ADR-008-proactive-rag.md) | ✅ Accepted | 2026-04 |

---

## How to read these

Each ADR answers 3 questions:
1. **What** decision did we make?
2. **Why** this over the alternatives?
3. **What** are the consequences (tradeoffs)?

If you're interviewing me, you can ask about any of these. The reasoning, not the conclusion, is what matters.