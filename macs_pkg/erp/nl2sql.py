"""Natural language to SQL translation for the ERP AI Copilot.

Converts a user question in Chinese (or English) into a safe, parameterized
PostgreSQL SELECT statement using an LLM. Returns a typed ``NLSQLResult`` that
can be validated and executed by ``SafeSQLExecutor`` (see ``safety.py`` /
``Day 6``).

Quickstart::

    from macs_pkg.erp.db import DatabasePool, DatabaseConfig
    from macs_pkg.erp.llm import build_default_provider
    from macs_pkg.erp.nl2sql import NL2SQLTranslator

    pool = DatabasePool(DatabaseConfig.from_env())
    provider = build_default_provider()
    translator = NL2SQLTranslator(provider=provider, schema_description=SCHEMA_DESCRIPTION)
    result = await translator.translate("哪些商品库存低于安全库存？")
    print(result.sql, result.params)
"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .prompts import load_prompt

logger = logging.getLogger(__name__)


def _get_default_schema_description() -> str:
    """Lazily import the canonical SCHEMA_DESCRIPTION.

    Lazy because a top-level ``from .db.schema import ...`` makes the
    module fail to bind ``NL2SQLTranslator`` on first import in Python
    3.12+ when the parent package is still being initialised.
    """
    from .db.schema import SCHEMA_DESCRIPTION
    return SCHEMA_DESCRIPTION


# ===== LLM Provider protocol =======================================

class LLMMessageLike(BaseModel):
    """Minimal chat message shape — matches ``macs_pkg.llm.LLMMessage``."""

    role: str
    content: str


class LLMResponseLike(BaseModel):
    """Minimal chat response shape — matches ``macs_pkg.llm.LLMResponse``."""

    content: str
    model: str = ""
    usage: dict = Field(default_factory=dict)


class LLMProviderLike:
    """Duck-typed protocol: anything with ``async complete(messages, ...)``.

    Compatible with ``ClaudeProvider``, ``MiniMaxProvider``, and any other
    implementation behind ``macs_pkg.llm.LLMProvider``. We use a simple
    class instead of ``typing.Protocol`` to avoid the
    ``from __future__ import annotations`` interaction that prevents the
    class from being added to the module namespace on first import.
    """


# ===== Result model ================================================

class NLSQLResult(BaseModel):
    """Typed output of NL→SQL translation."""

    sql: str
    explanation: str = ""
    params: list[Any] = Field(default_factory=list)
    confidence: float = 1.0

    @field_validator("sql")
    @classmethod
    def _strip_trailing_semicolon(cls, v: str) -> str:
        return v.rstrip().rstrip(";").rstrip()

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


# ===== Translator =================================================

class NL2SQLTranslator:
    """Translate natural-language questions into safe PostgreSQL SELECTs.

    Args:
        provider: any object with ``async complete(messages, ...) -> Response``
        schema_description: schema text injected into the system prompt.
                           Defaults to the canonical ``SCHEMA_DESCRIPTION``
                           from :mod:`macs_pkg.erp.db.schema`.
        system_prompt: full system prompt. If ``None``, the default
                      ``prompts/nl2sql_system.txt`` is used with the schema
                      description substituted in.
        temperature: 0.0 (deterministic) by default. Bump to 0.1-0.3 for
                     more diverse rephrasings.
    """

    DEFAULT_SYSTEM_PROMPT_FILE = "nl2sql_system.txt"

    def __init__(
        self,
        provider: LLMProviderLike,
        schema_description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> None:
        self.provider = provider
        self.schema_description = schema_description or _get_default_schema_description()
        self.temperature = temperature

        if system_prompt is None:
            template = load_prompt(self.DEFAULT_SYSTEM_PROMPT_FILE)
            self.system_prompt = template.replace(
                "{SCHEMA_DESCRIPTION}", self.schema_description
            )
        else:
            self.system_prompt = system_prompt

    async def translate(self, question: str) -> NLSQLResult:
        """Translate a user question into an :class:`NLSQLResult`.

        Raises:
            NLSQLParseError: if the LLM does not return valid JSON.
            NLSQLValidationError: if the JSON is missing required keys.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question.strip()},
        ]

        logger.info("NL→SQL translating: %r", question[:80])
        response = await self.provider.complete(
            messages, temperature=self.temperature
        )
        raw = (response.content or "").strip()
        logger.debug("NL→SQL raw response: %s", raw[:200])

        data = self._parse_json(raw)
        return NLSQLResult(**data)

    # ----- helpers -------------------------------------------------

    _JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

    def _parse_json(self, raw: str) -> dict:
        """Extract and parse the JSON object from the LLM response.

        Tolerant of markdown code fences and leading/trailing prose.
        """
        # 1. Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 2. Try fenced block
        m = self._JSON_FENCE_RE.search(raw)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Try to find the first {...} block
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise NLSQLParseError(f"Could not extract JSON from LLM response: {raw[:300]}")


# ===== Errors ======================================================

class NLSQLError(Exception):
    """Base for NL→SQL errors."""


class NLSQLParseError(NLSQLError):
    """LLM response could not be parsed as JSON."""


class NLSQLValidationError(NLSQLError):
    """Parsed JSON missing required fields or invalid values."""


class UnsafeSQLError(NLSQLError):
    """SQL failed the safety validator and was rejected before execution."""


# ===== Safety net =================================================

import sqlparse  # noqa: E402  (deferred to keep top-of-module clean)


# Keywords that must NEVER appear in an NL→SQL output.
# Case-insensitive matching; matches on word boundaries.
_BLOCKED_KEYWORDS: tuple[str, ...] = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "COPY", "GRANT", "REVOKE", "EXEC", "EXECUTE", "VACUUM",
    "REINDEX", "CLUSTER", "LOCK", "CALL", "DO", "SET", "RESET",
    "CREATE",  # no DDL via NL→SQL; use apply_schema
)

# Read-only statement types we allow.
_ALLOWED_DML: frozenset[str] = frozenset({"SELECT", "WITH"})

# Tables / schemas the validator permits. Tighten in production.
_ALLOWED_TABLES: frozenset[str] = frozenset(
    {"products", "suppliers", "inventory", "purchase_orders", "sales_orders"}
)


class SQLValidator:
    """Multi-layer static safety check on a translated SQL string.

    Rejects any of:
        * Non-SELECT/WITH statement types
        * Multiple statements (anything after the first ``;``)
        * Blacklist keywords (case-insensitive, word-boundary)
        * References to tables / columns not in the allow-list

    Use :meth:`validate` (raises) or :meth:`is_safe` (bool).
    """

    def __init__(
        self,
        blocked_keywords: tuple[str, ...] = _BLOCKED_KEYWORDS,
        allowed_tables: frozenset[str] = _ALLOWED_TABLES,
    ) -> None:
        self.blocked_keywords = blocked_keywords
        self.allowed_tables = {t.lower() for t in allowed_tables}
        self._keyword_re = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in self.blocked_keywords) + r")\b",
            re.IGNORECASE,
        )

    def is_safe(self, sql: str) -> tuple[bool, str]:
        """Return ``(True, "")`` if safe, else ``(False, reason)``."""
        if not sql or not sql.strip():
            return False, "empty SQL"

        # 1. Single statement (no extra content after the first semicolon)
        #    sqlparse.split returns one or more non-empty statements.
        try:
            statements = [s for s in sqlparse.split(sql) if s.strip()]
        except Exception as e:  # pragma: no cover — sqlparse is robust
            return False, f"sqlparse failed: {e}"
        if len(statements) > 1:
            return False, f"multiple statements detected ({len(statements)})"

        # 2. Top-level statement must be SELECT or WITH (which selects).
        parsed = sqlparse.parse(statements[0])
        if not parsed:
            return False, "sqlparse returned no statements"
        stmt = parsed[0]
        stmt_type = (stmt.get_type() or "").upper()
        if stmt_type not in _ALLOWED_DML:
            return False, f"disallowed statement type: {stmt_type!r}"

        # 3. Blacklist keyword scan (defence-in-depth even after type check)
        m = self._keyword_re.search(statements[0])
        if m:
            return False, f"blocked keyword: {m.group(0).upper()}"

        # 4. Table / column reference allow-list.
        #    Walk all tokens (including Name tokens) and check identifiers.
        for token in parsed[0].flatten():
            value = (token.value or "").strip()
            if not value:
                continue
            ttype_str = str(token.ttype)
            # Look for Name tokens (e.g. "secret_table") and complex
            # Identifier nodes that wrap them
            is_name = ttype_str.endswith("Name")
            is_identifier = ttype_str == "None"  # complex Identifier wrapper
            if not (is_name or is_identifier):
                continue
            # Strip quotes / brackets / parens
            ident = value.strip("`\"'()[],")
            if not ident or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", ident):
                continue
            ident_lower = ident.lower()
            # SQL keywords / built-in functions / common types
            if ident_lower in {
                "select", "from", "where", "and", "or", "not", "null", "is",
                "as", "on", "in", "case", "when", "then", "else", "end",
                "group", "by", "order", "having", "limit", "offset",
                "asc", "desc", "distinct", "all", "any", "some", "between",
                "like", "ilike", "exists", "true", "false", "current_date",
                "interval", "with", "union", "intersect", "except",
                "join", "left", "right", "inner", "outer", "full", "cross",
                "coalesce", "round", "sum", "count", "avg", "min", "max",
                "date", "text", "int", "integer", "numeric", "varchar",
                "now",
            }:
                continue
            # Common table aliases
            if ident_lower in {"p", "s", "i", "po", "so"}:
                continue
            # Known table
            if ident_lower in self.allowed_tables:
                continue
            # Known column names (loose allow-list)
            if ident_lower in {
                "product_id", "supplier_id", "warehouse_id", "po_id", "so_id",
                "sku", "name", "category", "unit_price", "safety_stock",
                "lead_time_days", "rating", "payment_terms", "country",
                "contact_email", "on_hand", "last_counted",
                "quantity", "unit_cost", "order_date", "expected_delivery",
                "status", "sale_date", "customer_region", "customer_name",
                "units_sold", "revenue", "order_count", "deficit",
                "recent_avg", "older_avg", "delta", "delta_pct",
                "avg_daily_units", "days_of_inventory", "reorder_recommendation",
                "below_safety", "total_inventory_value_cny",
                "created_at", "total",
            }:
                continue
            # Unknown identifier — reject conservatively in v1
            return False, f"unknown identifier: {ident!r}"

        return True, ""

    def validate(self, sql: str) -> str:
        """Raise :class:`UnsafeSQLError` if the SQL is not safe.

        Returns the SQL unchanged on success (for fluent chaining).
        """
        ok, reason = self.is_safe(sql)
        if not ok:
            raise UnsafeSQLError(f"SQL rejected: {reason}. SQL: {sql[:200]}")
        return sql


# ===== Safe SQL executor ==========================================

class SafeSQLExecutor:
    """Execute a translated :class:`NLSQLResult` against a :class:`DatabasePool`.

    Combines :class:`SQLValidator` + a typed result envelope. Use::

        executor = SafeSQLExecutor(pool, validator=SQLValidator())
        result = await executor.execute(nlsql_result)   # from NLSQLTranslator
        # result == {"sql": ..., "rows": [...], "rowcount": N, "elapsed_ms": ...}
    """

    def __init__(
        self,
        pool: Any,  # DatabasePool — typed as Any to avoid the import cycle
        validator: Optional[SQLValidator] = None,
        max_rows: int = 200,
        timeout_ms: int = 5000,
    ) -> None:
        self.pool = pool
        self.validator = validator or SQLValidator()
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms

    async def execute(self, result: NLSQLResult) -> dict:
        """Validate, run, and shape the result.

        Returns a dict with keys ``sql``, ``rows``, ``rowcount``, ``elapsed_ms``,
        and ``confidence`` (echoed from the NLSQLResult).
        """
        # 1. Safety check
        self.validator.validate(result.sql)

        # 2. Add a hard LIMIT to the query (defence-in-depth in case the
        #    LLM-generated SQL didn't include one).
        sql = result.sql.rstrip().rstrip(";")
        if not re.search(r"\bLIMIT\s+\d+", sql, re.IGNORECASE):
            sql = f"{sql} LIMIT {self.max_rows}"

        # 3. Parameter substitution (the params from NLSQLResult)
        params = tuple(result.params)

        # 4. Execute
        import time
        t0 = time.monotonic()
        rows = await self.pool.fetch(sql, params)
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        return {
            "sql": sql,
            "params": list(params),
            "rows": rows,
            "rowcount": len(rows),
            "elapsed_ms": elapsed_ms,
            "confidence": result.confidence,
            "explanation": result.explanation,
        }


# ===== Convenience builders =======================================

def build_default_provider(prefer: str = "claude") -> LLMProviderLike:
    """Build the best available LLM provider, preferring Claude.

    Falls back to MiniMax, then any registered provider. Raises
    ``RuntimeError`` if no provider can be built (no API key set).

    Args:
        prefer: ``"claude"`` or ``"MiniMax"`` to control the preference order.
    """
    try:
        from macs_pkg.llm import ClaudeProvider, MiniMaxProvider
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "macs_pkg.llm not importable. Install full MACS deps first "
            "(pip install -r requirements.txt)."
        ) from e

    import os

    if prefer == "claude" and os.getenv("ANTHROPIC_API_KEY"):
        from macs_pkg.llm import ClaudeProvider
        return ClaudeProvider()
    if os.getenv("MINIMAX_API_KEY"):
        from macs_pkg.llm import MiniMaxProvider
        return MiniMaxProvider()
    if os.getenv("ANTHROPIC_API_KEY"):
        from macs_pkg.llm import ClaudeProvider
        return ClaudeProvider()

    raise RuntimeError(
        "No LLM API key found. Set ANTHROPIC_API_KEY or MINIMAX_API_KEY in your env."
    )


__all__ = [
    "LLMMessageLike",
    "LLMResponseLike",
    "LLMProviderLike",
    "NLSQLResult",
    "NLSQLTranslator",
    "NLSQLError",
    "NLSQLParseError",
    "NLSQLValidationError",
    "UnsafeSQLError",
    "SQLValidator",
    "SafeSQLExecutor",
    "build_default_provider",
]
