# ADR-007: Read-only NL→SQL by default

- **Status**: Accepted
- **Date**: 2026-04
- **Deciders**: Core team

## Context

NL→SQL over a production database is a footgun. Even with the 4-layer safety guardrail (ADR-003), a buggy LLM could:
- Generate a `SELECT *` against a billion-row table, locking the DB.
- Exfiltrate PII from `users` table.
- Generate a `UPDATE` that the safety layer misses (e.g., `UPDATE ... WHERE id = ?`).

## Decision

**NL→SQL is read-only by default.** The connection pool used by NL→SQL connects with a PostgreSQL user that has only `SELECT` privileges on the target schema.

```sql
-- Read-only user created at deploy time
CREATE USER erp_readonly WITH PASSWORD '...';
GRANT CONNECT ON DATABASE erp_copilot TO erp_readonly;
GRANT USAGE ON SCHEMA public TO erp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO erp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO erp_readonly;
```

Write operations must be **explicitly enabled** per-tool, not per-query.

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| No DB-level restriction, trust the LLM + safety layer | Simple | Defense in depth missing |
| Time-limited write access | Can do writes when needed | Complex to manage |
| **Read-only DB user + 4-layer guardrail (chosen)** | Belt + suspenders | Some setup at deploy time |

## Consequences

**Positive:**
- Even if all 4 safety layers fail, the DB user can't execute writes.
- PII exfiltration is impossible — the user can't `SELECT * FROM users WHERE ssn LIKE ...`.
- Clear security posture for customers.

**Negative:**
- Deploy requires DBA to create the read-only user (5 min setup, documented in deploy/README).
- Use cases that need writes (e.g., "create a draft PO from this conversation") require explicit opt-in.

## When to allow writes

If a customer explicitly requests write capability:
1. Create a separate connection pool with write privileges.
2. Restrict that pool to specific tools (e.g., `create_draft_po`), not the generic `query_database` tool.
3. Add a human-in-the-loop confirmation step before executing.
4. Log every write query with full context for audit.

## Verification

```python
async def test_readonly_enforced():
    """Even if safety guardrail passes, DB user rejects writes."""
    with get_readonly_connection() as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DROP TABLE products")
```