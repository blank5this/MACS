"""Tests for the NL→SQL translator.

These tests use a ``MockLLMProvider`` that returns canned JSON responses for
each golden question, so they run with no API key and no network. Live tests
against Claude / MiniMax are kept out of the default suite (see
``test_nl2sql_live.py`` for opt-in live runs).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Use `import X; X.Y` instead of `from X import Y` because pytest's import
# machinery (assertion rewriter) interacts badly with the NL2SQL module's
# class-binding order in Python 3.12+. The module is fully importable; the
# strict `from X import Y` syntax is what fails.
import macs_pkg.erp.nl2sql as _nl2sql  # noqa: E402
_nl2sql.NLSQLResult = _nl2sql.NLSQLResult
NLSQLTranslator = _nl2sql.NL2SQLTranslator
_nl2sql.NLSQLParseError = _nl2sql.NLSQLParseError


# ===== Mock provider ===============================================

class MockLLMProvider:
    """Routes ``complete()`` calls to canned responses keyed by substring."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[list[dict]] = []

    async def complete(
        self,
        messages: list,
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> Any:
        self.calls.append(messages)
        user_msg = next((m for m in messages if m.get("role") == "user"), {})
        user_text = user_msg.get("content", "")
        for needle, response in self.responses.items():
            if needle in user_text:
                return _MockResponse(content=response)
        return _MockResponse(content='{"sql":"SELECT 1","explanation":"fallback","params":[],"confidence":0.5}')

    def last_user_message(self) -> str:
        if not self.calls:
            return ""
        last = self.calls[-1]
        user = next((m for m in last if m.get("role") == "user"), {})
        return user.get("content", "")


class _MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.model = "mock"
        self.usage = {}


# ===== Golden questions ==========================================

GOLDEN_QUESTIONS: list[tuple[str, dict]] = [
    (
        "哪些商品库存低于安全库存？",
        {
            "sql_contains": ["FROM products", "safety_stock", "HAVING", "SUM(i.on_hand)"],
            "params": [],
        },
    ),
    (
        "最近30天销量最高商品是什么？",
        {
            "sql_contains": ["FROM sales_orders", "INTERVAL '30 days'", "ORDER BY", "LIMIT"],
            "params": [],
        },
    ),
    (
        "哪个供应商涨价最快？",
        {
            "sql_contains": ["FROM purchase_orders", "suppliers", "INTERVAL '90 days'", "delta"],
            "params": [],
        },
    ),
    (
        "上海地区客户的销售额",
        {
            "sql_contains": ["FROM sales_orders", "customer_region = %s"],
            "params": ["CN-East"],
        },
    ),
    (
        "A4 复印纸的库存",
        {
            "sql_contains": ["FROM inventory", "products", "ILIKE %s"],
            "params": ["%A4%"],
        },
    ),
    (
        "库存总价值多少？",
        {
            "sql_contains": ["SUM(", "unit_price"],
            "params": [],
        },
    ),
    (
        "过去7天各品类的销售额",
        {
            "sql_contains": ["FROM sales_orders", "category", "INTERVAL '7 days'"],
            "params": [],
        },
    ),
    (
        "深圳五金制品有限公司最近3个月的采购总额",
        {
            "sql_contains": ["FROM purchase_orders", "suppliers", "INTERVAL '3 months'"],
            "params": [],
        },
    ),
]


def _build_canned_response(question: str, expected: dict) -> str:
    """Build a mock LLM JSON response for a question, using the expected SQL
    skeleton (substituting %s placeholders) and a confidence score."""
    sql = "SELECT 1"
    if "FROM products" in str(expected):
        if "HAVING" in str(expected):
            sql = (
                "SELECT p.sku, p.name, COALESCE(SUM(i.on_hand),0)::int AS on_hand "
                "FROM products p LEFT JOIN inventory i ON i.product_id=p.product_id "
                "GROUP BY p.product_id, p.sku, p.name, p.safety_stock "
                "HAVING COALESCE(SUM(i.on_hand),0) < p.safety_stock "
                "ORDER BY on_hand LIMIT 200"
            )
        else:
            sql = "SELECT p.sku, p.name FROM products p LIMIT 10"
    elif "FROM sales_orders" in str(expected):
        if "customer_region" in str(expected):
            sql = (
                "SELECT COUNT(*) AS order_count, ROUND(SUM(s.quantity*s.unit_price)::numeric,2) AS revenue "
                "FROM sales_orders s WHERE s.customer_region = %s"
            )
        elif "category" in str(expected):
            sql = (
                "SELECT p.category, SUM(s.quantity)::int AS qty, ROUND(SUM(s.quantity*s.unit_price)::numeric,2) AS revenue "
                "FROM sales_orders s JOIN products p ON p.product_id=s.product_id "
                "WHERE s.sale_date >= CURRENT_DATE - INTERVAL '7 days' "
                "GROUP BY p.category ORDER BY revenue DESC LIMIT 200"
            )
        else:
            sql = (
                "SELECT p.sku, p.name, SUM(s.quantity)::int AS units_sold "
                "FROM sales_orders s JOIN products p ON p.product_id=s.product_id "
                "WHERE s.sale_date >= CURRENT_DATE - INTERVAL '30 days' "
                "GROUP BY p.product_id, p.sku, p.name ORDER BY units_sold DESC LIMIT 10"
            )
    elif "FROM purchase_orders" in str(expected):
        if "suppliers" in str(expected) and "3 months" in str(expected):
            sql = (
                "SELECT s.name, ROUND(SUM(po.quantity*po.unit_cost)::numeric,2) AS total "
                "FROM purchase_orders po JOIN suppliers s ON s.supplier_id=po.supplier_id "
                "WHERE s.name ILIKE %s AND po.order_date >= CURRENT_DATE - INTERVAL '3 months' "
                "GROUP BY s.supplier_id, s.name LIMIT 200"
            )
        else:
            sql = (
                "SELECT s.name, ROUND(AVG(CASE WHEN po.order_date >= CURRENT_DATE - INTERVAL '90 days' "
                "THEN po.unit_cost END)::numeric,2) AS recent, "
                "ROUND(AVG(CASE WHEN po.order_date < CURRENT_DATE - INTERVAL '90 days' "
                "THEN po.unit_cost END)::numeric,2) AS older, "
                "ROUND((AVG(CASE WHEN po.order_date >= CURRENT_DATE - INTERVAL '90 days' "
                "THEN po.unit_cost END) - AVG(CASE WHEN po.order_date < CURRENT_DATE - INTERVAL '90 days' "
                "THEN po.unit_cost END))::numeric,2) AS delta "
                "FROM purchase_orders po JOIN suppliers s ON s.supplier_id=po.supplier_id "
                "WHERE po.order_date >= CURRENT_DATE - INTERVAL '180 days' "
                "GROUP BY s.supplier_id, s.name ORDER BY delta DESC NULLS LAST LIMIT 10"
            )
    elif "FROM inventory" in str(expected):
        sql = (
            "SELECT p.sku, p.name, i.warehouse_id, i.on_hand "
            "FROM inventory i JOIN products p ON p.product_id=i.product_id "
            "WHERE p.name ILIKE %s ORDER BY p.sku LIMIT 200"
        )
    elif "SUM(" in str(expected) and "unit_price" in str(expected):
        sql = (
            "SELECT ROUND(SUM(i.on_hand * p.unit_price)::numeric, 2) AS total_inventory_value_cny "
            "FROM inventory i JOIN products p ON p.product_id=i.product_id"
        )

    return (
        f'{{"sql": "{sql}", '
        f'"explanation": "Mock translation of: {question[:30]}", '
        f'"params": {json.dumps(expected["params"])}, '
        f'"confidence": 0.95}}'
    )


# ===== Translator unit tests =====================================

def test_translator_loads_default_system_prompt():
    provider = MockLLMProvider()
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    assert "expert PostgreSQL" in translator.system_prompt
    assert "products" in translator.system_prompt
    assert "purchase_orders" in translator.system_prompt


def test_translator_accepts_custom_schema():
    provider = MockLLMProvider()
    translator = _nl2sql.NL2SQLTranslator(
        provider=provider, schema_description="MY CUSTOM SCHEMA"
    )
    assert "MY CUSTOM SCHEMA" in translator.system_prompt


@pytest.mark.asyncio
async def test_translate_parses_clean_json():
    provider = MockLLMProvider(
        {"哪些商品库存低于安全库存": _build_canned_response("哪些商品", {"sql_contains": ["products"], "params": []})}
    )
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    result = await translator.translate("哪些商品库存低于安全库存？")
    assert isinstance(result, _nl2sql.NLSQLResult)
    assert "SELECT" in result.sql.upper()
    assert result.confidence == 0.95
    assert result.params == []


@pytest.mark.asyncio
async def test_translate_handles_markdown_fence():
    provider = MockLLMProvider(
        {
            "test": (
                "Here is the query:\n"
                "```json\n"
                '{"sql": "SELECT 1", "explanation": "ok", "params": [], "confidence": 0.9}\n'
                "```\n"
                "Let me know if you need anything else."
            )
        }
    )
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    result = await translator.translate("test")
    assert result.sql == "SELECT 1"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_translate_handles_prose_around_json():
    provider = MockLLMProvider(
        {
            "test": (
                'Sure! The query you want is {"sql": "SELECT 2", '
                '"explanation": "two", "params": ["x"], "confidence": 0.8} - that should work.'
            )
        }
    )
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    result = await translator.translate("test")
    assert result.sql == "SELECT 2"
    assert result.params == ["x"]


@pytest.mark.asyncio
async def test_translate_raises_on_garbage():
    provider = MockLLMProvider({"test": "I'm sorry, I cannot answer that."})
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    with pytest.raises(_nl2sql.NLSQLParseError):
        await translator.translate("test")


@pytest.mark.asyncio
async def test_translate_strips_trailing_semicolon():
    provider = MockLLMProvider(
        {"test": '{"sql": "SELECT 1;", "explanation": "x", "params": [], "confidence": 1.0}'}
    )
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    result = await translator.translate("test")
    assert result.sql == "SELECT 1"


@pytest.mark.asyncio
async def test_translate_clamps_confidence():
    provider = MockLLMProvider(
        {"test": '{"sql": "SELECT 1", "explanation": "x", "params": [], "confidence": 5.0}'}
    )
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    result = await translator.translate("test")
    assert result.confidence == 1.0


# ===== Golden-question parametrized tests =========================

@pytest.mark.asyncio
@pytest.mark.parametrize("question,expected", GOLDEN_QUESTIONS)
async def test_golden_questions(question: str, expected: dict):
    """Each golden question must produce SQL containing the expected tokens."""
    provider = MockLLMProvider({question: _build_canned_response(question, expected)})
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    result = await translator.translate(question)

    sql_upper = result.sql.upper()
    for token in expected["sql_contains"]:
        assert token.upper() in sql_upper, (
            f"Question: {question!r}\n"
            f"Expected token {token!r} in SQL.\nGot: {result.sql}"
        )
    assert result.params == expected["params"]


# ===== System prompt sanity checks ===============================

def test_system_prompt_contains_schema():
    provider = MockLLMProvider()
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    for table in (
        "products", "suppliers", "inventory",
        "purchase_orders", "sales_orders",
    ):
        assert table in translator.system_prompt, f"Missing table {table!r} in system prompt"


def test_system_prompt_includes_output_contract():
    provider = MockLLMProvider()
    translator = _nl2sql.NL2SQLTranslator(provider=provider)
    for key in ("sql", "explanation", "params", "confidence"):
        assert key in translator.system_prompt


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=short"]))
