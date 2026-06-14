"""Single ERP Copilot Agent — a :class:`ToolAgent` with the full ERP toolbox.

This is the Day-8 deliverable. It wraps three capability layers behind one
:class:`ToolAgent`:

1. **MCP inventory/sales/procurement tools** (5 read-only functions)
2. **RAG knowledge base lookup** (the 17-file ``data/erp_kb/`` corpus)
3. **NL→SQL translation + safe execution** (via :class:`SafeSQLExecutor`)

The base :class:`ToolAgent` already does LLM-driven tool selection (see
``ToolAgent._llm_select_tool``). We register 7 tools and feed it a
domain-specific system prompt so the LLM knows when to pick which tool.

Quickstart::

    from macs_pkg.erp.agents.copilot_agent import build_copilot_agent

    agent = build_copilot_agent(provider=my_provider, pool=my_pool)
    result = await agent.ask("哪些商品库存低于安全线？")
    print(result["answer"])

Architecture::

    user question
        ↓
    ToolAgent.think  ──→  ToolAgent._llm_select_tool  (LLM picks a tool)
        ↓
    ToolAgent.act    ──→  tool function (MCP / RAG / NL→SQL)
        ↓
    tool_result dict (with rows / context / citations)
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from ..db.connection import DatabasePool
from ..nl2sql import (
    NLSQLResult,
    NL2SQLTranslator,
    SafeSQLExecutor,
    UnsafeSQLError,
)
from ..prompts import load_prompt
from ..rag.query import ask_kb
from ..tools.inventory_tools import (
    get_inventory_levels,
    get_low_stock_products,
    get_sales_velocity,
    get_supplier_price_history,
    get_top_selling_products,
)

logger = logging.getLogger(__name__)


# ===== System prompt ================================================

DEFAULT_SYSTEM_PROMPT_FILE = "copilot_system.txt"


def _load_system_prompt() -> str:
    """Load the canonical copilot system prompt from ``prompts/``."""
    return load_prompt(DEFAULT_SYSTEM_PROMPT_FILE)


# ===== Tool wrappers =================================================
#
# Each tool takes keyword-only arguments and returns a JSON-serialisable
# dict. We follow the ToolAgent contract: the dict is the tool result;
# the LLM sees the dict (or its digest) and decides what to do next.

async def _tool_get_inventory_levels(
    pool: DatabasePool,
    product_id: Optional[int] = None,
    category: Optional[str] = None,
) -> dict:
    """MCP tool 1: current on-hand per (product × warehouse).

    Returns ``{"rows": [...], "rowcount": N}``.
    """
    rows = await get_inventory_levels(pool, product_id=product_id, category=category)
    return {"rows": rows, "rowcount": len(rows)}


async def _tool_get_low_stock_products(
    pool: DatabasePool,
    threshold: int = 0,
) -> dict:
    """MCP tool 2: products whose total stock < safety_stock.

    Returns ``{"rows": [...], "rowcount": N}``.
    """
    rows = await get_low_stock_products(pool, threshold=threshold)
    return {"rows": rows, "rowcount": len(rows)}


async def _tool_get_supplier_price_history(
    pool: DatabasePool,
    product_id: int,
    days: int = 180,
) -> dict:
    """MCP tool 3: per-supplier unit_cost trend for a product.

    Returns ``{"rows": [...], "rowcount": N}``.
    """
    rows = await get_supplier_price_history(pool, product_id=product_id, days=days)
    return {"rows": rows, "rowcount": len(rows)}


async def _tool_get_top_selling_products(
    pool: DatabasePool,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """MCP tool 4: top-N products by units sold.

    Returns ``{"rows": [...], "rowcount": N}``.
    """
    rows = await get_top_selling_products(
        pool, start_date=start_date, end_date=end_date, limit=limit
    )
    return {"rows": rows, "rowcount": len(rows)}


async def _tool_get_sales_velocity(
    pool: DatabasePool,
    product_id: int,
    days: int = 30,
) -> dict:
    """MCP tool 5: sales velocity & reorder recommendation.

    Returns ``{"row": {...}}`` (single product → single dict).
    """
    row = await get_sales_velocity(pool, product_id=product_id, days=days)
    return {"row": row}


async def _tool_ask_knowledge_base(question: str, top_k: int = 3) -> dict:
    """RAG tool: query the ERP knowledge base.

    Returns ``{"chunks": [...], "context": str, "elapsed_ms": int,
    "citations": [...]}``. ``citations`` is a list of
    ``{title, source_path, rel_path, category}`` dicts extracted from
    the top chunks, for the LLM to cite in its answer.
    """
    result = await ask_kb(question, top_k=top_k)
    citations = [
        {
            "title": c.title,
            "source_path": c.source_path,
            "rel_path": c.rel_path,
            "category": c.category,
            "score": c.score,
        }
        for c in result.chunks
    ]
    return {
        "chunks": [
            {"text": c.text, "score": c.score, "title": c.title}
            for c in result.chunks
        ],
        "context": result.context,
        "elapsed_ms": result.elapsed_ms,
        "citations": citations,
    }


async def _tool_query_database(
    pool: DatabasePool,
    translator: NL2SQLTranslator,
    executor: SafeSQLExecutor,
    question: str,
) -> dict:
    """NL→SQL tool: translate a free-form question into a safe SELECT and
    run it.

    Returns ``{"sql": str, "params": [...], "rows": [...], "rowcount": N,
    "elapsed_ms": int, "explanation": str, "confidence": float}``.

    Raises:
        UnsafeSQLError: if the translator produced SQL the validator
                       refuses (defence-in-depth — should never happen
                       in normal flow but is propagated for visibility).
    """
    nlsql = await translator.translate(question)
    try:
        result = await executor.execute(nlsql)
    except UnsafeSQLError as e:
        logger.warning("query_database: SQL rejected by validator: %s", e)
        return {
            "error": "unsafe_sql",
            "message": str(e),
            "sql": nlsql.sql,
            "explanation": nlsql.explanation,
        }
    # Truncate rows to a printable size; the full set is in the dict.
    return result


# ===== Agent ========================================================

class ERPCopilotAgent:
    """Single ERP Copilot agent with 7 mixed tools (MCP + RAG + NL→SQL).

    Why a thin wrapper around :class:`ToolAgent`? The base ToolAgent
    already implements LLM-driven tool selection (``think`` → choose
    tool → ``act`` → run tool). All we need is:

        1. Construct the ToolAgent
        2. Register our 7 tools (which need a DB pool / translator)
        3. Set the ERP-specific system prompt

    The :meth:`ask` method below is a thin convenience wrapper that
    sends a question and returns the final tool result.
    """

    # Names of all 7 tools the LLM can pick from.
    TOOL_NAMES: tuple[str, ...] = (
        "get_inventory_levels",
        "get_low_stock_products",
        "get_supplier_price_history",
        "get_top_selling_products",
        "get_sales_velocity",
        "ask_knowledge_base",
        "query_database",
    )

    def __init__(
        self,
        pool: DatabasePool,
        provider: Any,  # LLMProvider — typed as Any to avoid the import cycle
        nl2sql_translator: Optional[NL2SQLTranslator] = None,
        nl2sql_executor: Optional[SafeSQLExecutor] = None,
        system_prompt: Optional[str] = None,
        enable_llm: bool = True,
        name: str = "erp_copilot",
        model: str = "claude-sonnet-4-6",
    ) -> None:
        # Local imports keep the erp package import-time cost low; the
        # base ToolAgent pulls in core.agent → memory → loguru etc.
        from macs_pkg.agents.tool_agent import ToolAgent

        self.pool = pool
        self.provider = provider
        self.name = name
        self.model = model

        # NL→SQL bits are optional — the agent still works without
        # them (the LLM will just see one fewer tool). Useful for
        # smoke tests that don't want to mock the LLM chain.
        self.translator = nl2sql_translator
        self.executor = nl2sql_executor

        prompt = system_prompt or _load_system_prompt()

        # Build the underlying ToolAgent.  We let the ToolAgent do the
        # LLM-driven tool selection (see ToolAgent._llm_select_tool).
        self._agent = ToolAgent(
            name=name,
            model=model,
            system_prompt=prompt,
            provider=provider,
            enable_llm=enable_llm,
        )

        # Register MCP tools (5). Each is an async closure that closes
        # over ``self.pool`` so the tool's signature stays clean. We use
        # ``async def`` explicitly (not lambda) so that
        # :func:`asyncio.iscoroutinefunction` returns True and the
        # ToolAgent dispatcher actually awaits the coroutine.
        #
        # Toolset selection: when the pool exposes ``backend == "sqlite"``
        # we use the SQLite-compatible implementations (see
        # :mod:`macs_pkg.erp.tools.sqlite_tools`); otherwise we use the
        # Postgres-flavoured tools. The function signatures are identical
        # so callers don't notice the swap.
        if getattr(self.pool, "backend", None) == "sqlite":
            from ..tools import sqlite_tools as _tools
        else:
            from ..tools import inventory_tools as _tools  # type: ignore

        async def _t_get_inventory_levels(product_id=None, category=None):
            return await _tools.get_inventory_levels(
                self.pool, product_id=product_id, category=category
            )

        async def _t_get_low_stock_products(threshold=0):
            return await _tools.get_low_stock_products(self.pool, threshold=threshold)

        async def _t_get_supplier_price_history(product_id, days=180):
            return await _tools.get_supplier_price_history(
                self.pool, product_id=product_id, days=days
            )

        async def _t_get_top_selling_products(start_date=None, end_date=None, limit=10):
            return await _tools.get_top_selling_products(
                self.pool, start_date=start_date, end_date=end_date, limit=limit
            )

        async def _t_get_sales_velocity(product_id, days=30):
            return await _tools.get_sales_velocity(
                self.pool, product_id=product_id, days=days
            )

        self._agent.register_tool("get_inventory_levels", _t_get_inventory_levels)
        self._agent.register_tool("get_low_stock_products", _t_get_low_stock_products)
        self._agent.register_tool(
            "get_supplier_price_history", _t_get_supplier_price_history
        )
        self._agent.register_tool(
            "get_top_selling_products", _t_get_top_selling_products
        )
        self._agent.register_tool("get_sales_velocity", _t_get_sales_velocity)

        # RAG tool — no pool needed.
        async def _t_ask_knowledge_base(question: str, top_k: int = 3):
            return await _tool_ask_knowledge_base(question, top_k=top_k)

        self._agent.register_tool("ask_knowledge_base", _t_ask_knowledge_base)

        # NL→SQL tool — needs both translator and executor.
        if self.translator is not None and self.executor is not None:
            async def _t_query_database(question: str):
                return await _tool_query_database(
                    self.pool, self.translator, self.executor, question
                )

            self._agent.register_tool("query_database", _t_query_database)
        else:
            logger.warning(
                "ERPCopilotAgent: NL2SQLTranslator/SafeSQLExecutor not provided; "
                "the 'query_database' tool is not registered."
            )

        # Wire the underlying agent's history list so callers can
        # inspect it through `agent.execution_history`.
        self.execution_history: list[dict[str, Any]] = []

    # ----- introspection --------------------------------------------

    @property
    def tool_names(self) -> list[str]:
        return list(self.TOOL_NAMES)

    def list_tools(self) -> list[str]:
        return self._agent.list_tools()

    # ----- main API -------------------------------------------------

    async def ask(self, question: str) -> dict[str, Any]:
        """Run the agent on a user question and return a structured result.

        Args:
            question: a natural-language question in Chinese or English.

        Returns:
            A dict with the following shape on success::

                {
                    "question":  str,
                    "tool":      str,  # which tool was chosen
                    "result":    dict, # raw tool result
                    "messages":  list, # trace of think/act messages
                }

            On error the dict has ``{"error": str, ...}`` instead of
            ``result``. Never raises (errors are caught and reported).
        """
        from macs_pkg.core.agent import Message

        if not question or not question.strip():
            return {"error": "empty question", "question": question}

        # Construct the user message in the ToolAgent contract.
        # ``description`` is what the LLM-based selector sees; ``action``
        # = "execute_tool" forces the tool-selection code path.
        user_msg = Message(
            sender="user",
            receiver=self.name,
            content={
                "action": "execute_tool",
                "description": question.strip(),
            },
            msg_type="text",
        )

        try:
            think_response = await self._agent.think(user_msg)
        except Exception as e:
            logger.exception("ERPCopilotAgent.think failed")
            return {"error": f"think failed: {e}", "question": question}

        try:
            act_messages = await self._agent.act(think_response)
        except Exception as e:
            logger.exception("ERPCopilotAgent.act failed")
            return {
                "error": f"act failed: {e}",
                "question": question,
                "tool": think_response.content.get("tool"),
            }

        # Drill into the act message for the raw tool result.
        if not act_messages:
            err = think_response.content.get("error", "no tool selected")
            return {
                "error": err,
                "question": question,
                "available_tools": self._agent.list_tools(),
            }

        tool_result_msg = act_messages[0]
        result_content = tool_result_msg.content or {}
        tool_result = result_content.get("result", {})
        tool_name = result_content.get("tool") or think_response.content.get("tool")

        # Mirror into our own history for easy inspection.
        record = {
            "question": question,
            "tool": tool_name,
            "result": tool_result,
            "success": "error" not in tool_result if isinstance(tool_result, dict) else True,
        }
        self.execution_history.append(record)

        return {
            "question": question,
            "tool": tool_name,
            "result": tool_result,
            "messages": [think_response.to_dict(), tool_result_msg.to_dict()],
        }

    # ----- manual override -----------------------------------------

    async def run_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Call a registered tool directly (bypassing the LLM).

        Useful for tests, demo scripts, and forcing a specific tool.

        Why not route through ``self._agent.think`` / ``act``? Because
        the base :class:`ToolAgent` always goes through LLM-driven
        tool selection when ``enable_llm=True``. To call a tool by
        name deterministically we invoke the tool function directly.
        """
        if tool_name not in self._agent._tool_registry:
            return {
                "error": f"tool not found: {tool_name}",
                "available_tools": self._agent.list_tools(),
            }

        # Record into the agent's execution history to keep the audit
        # trail consistent with LLM-driven invocations.
        try:
            result = await self._agent._execute_tool(tool_name, kwargs)
        except Exception as e:  # pragma: no cover — _execute_tool already catches
            logger.exception("run_tool(%s) failed", tool_name)
            return {"error": f"tool execution failed: {e}", "tool": tool_name}

        self.execution_history.append({
            "tool": tool_name,
            "args": kwargs,
            "result": result,
            "success": "error" not in result if isinstance(result, dict) else True,
        })
        return result

    # ----- access to the underlying ToolAgent (for advanced uses) --

    @property
    def tool_agent(self):
        return self._agent


# ===== Convenience builder ==========================================

def build_copilot_agent(
    pool: DatabasePool,
    provider: Any,
    *,
    system_prompt: Optional[str] = None,
    enable_llm: bool = True,
    name: str = "erp_copilot",
    model: str = "claude-sonnet-4-6",
) -> ERPCopilotAgent:
    """Convenience builder that wires a default NL2SQL stack.

    Use this from examples and the Web UI; tests should construct
    :class:`ERPCopilotAgent` directly so they can inject mocks.
    """
    translator = NL2SQLTranslator(provider=provider)
    executor = SafeSQLExecutor(pool=pool)

    return ERPCopilotAgent(
        pool=pool,
        provider=provider,
        nl2sql_translator=translator,
        nl2sql_executor=executor,
        system_prompt=system_prompt,
        enable_llm=enable_llm,
        name=name,
        model=model,
    )


__all__ = [
    "ERPCopilotAgent",
    "build_copilot_agent",
]
