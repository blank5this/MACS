# ADR-003: 4-layer SQL safety guardrail

- **Status**: Accepted
- **Date**: 2026-04
- **Deciders**: Core team

## Context

NL→SQL over a real database is dangerous. A hallucinated `DROP TABLE` or `DELETE FROM orders` would destroy production data. Naive string substitution is SQL-injection bait. We needed a guarantee: **only safe SELECT queries, parameterized values, period.**

## Decision

Every NL→SQL translation passes through 4 sequential guards. Any one can block the query.

### Layer 1: AST whitelist
Parse the generated SQL into an AST. Walk the tree. **Allow only SELECT and WITH statements.** Any DDL/DML node (DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, CREATE, GRANT) → reject.

### Layer 2: SQL keyword blacklist
Catch keywords that shouldn't appear in read-only queries: `INTO OUTFILE`, `LOAD_FILE`, `pg_read_file`, `COPY ... FROM`, `CALL`, `EXEC`.

### Layer 3: Statement-type whitelist
For PostgreSQL specifically, use `pg_catalog.pg_class` lookups to confirm the query targets only `TABLE` and `VIEW` objects. Block queries against `pg_catalog`, `information_schema`, `pg_user`.

### Layer 4: Parameterized values
All user-supplied values (e.g., "last month" → date range) are bound as parameters, never interpolated as string literals. Use `psycopg`'s `%s` placeholders + parameter tuple.

```python
# Bad: string interpolation
sql = f"SELECT * FROM products WHERE name = '{user_input}'"

# Good: parameterized
sql = "SELECT * FROM products WHERE name = %s"
cursor.execute(sql, (user_input,))
```

## Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| Single regex check | Fast | Easy to bypass with comments, case variation, unicode |
| Read-only DB user only | True defense | Requires DBA setup, doesn't help if the LLM hallucinates a wrong query |
| Sandboxed execution (e.g., DuckDB) | No real DB access | Doesn't query user's actual data |
| **4-layer (chosen)** | Defense in depth | More code, more tests |

## Consequences

**Positive:**
- 50+ adversarial injection attempts in `test_nl2sql_safety.py` — all blocked.
- Production deployments can run with read-only DB user + 4-layer guard (belt + suspenders).
- Clear audit log of which layer rejected which query.

**Negative:**
- Slightly higher latency (10-50ms per query for AST parse).
- Some legitimate queries get rejected (e.g., `SELECT ... FOR UPDATE`) — intentional.
- Users who *want* write access must explicitly opt in per-tool, not per-query.

## Verification

```python
def test_drop_blocked():
    """The classic adversarial test."""
    bad_sql = "DROP TABLE products"
    with pytest.raises(SQLSafetyError) as exc:
        guard.check(bad_sql)
    assert exc.value.layer == "ast"

def test_injection_blocked():
    """SQL injection via string interpolation."""
    bad = "SELECT * FROM users WHERE name = 'x'; DROP TABLE users; --'"
    with pytest.raises(SQLSafetyError):
        guard.check(bad)

def test_pg_catalog_blocked():
    """Data exfiltration via system catalog."""
    bad = "SELECT * FROM pg_shadow"
    with pytest.raises(SQLSafetyError) as exc:
        guard.check(bad)
    assert exc.value.layer == "statement_type"
```