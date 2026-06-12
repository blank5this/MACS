"""Tests for the ERP domain Agent templates (Day 9).

These tests cover:

* All 4 templates are registered into the singleton
  ``AgentTemplateRegistry``.
* Required variables in each template are detected.
* ``render_prompt`` substitutes all variables and warns on missing ones.
* Each template's role and tool list match the design.
* Each template can be instantiated as a real ``BaseAgent`` subclass
  (no LLM required for instantiation).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import macs_pkg.erp.agents.templates as _tmpl
from macs_pkg.agents.executor import ExecutorAgent
from macs_pkg.agents.planner import PlannerAgent
from macs_pkg.agents.reviewer import ReviewerAgent
from macs_pkg.core.agent import AgentRole
from macs_pkg.core.agent_template import (
    AgentTemplate,
    AgentTemplateRegistry,
    get_template_registry,
)
from macs_pkg.erp.agents.templates import (
    ERP_INVENTORY_ANALYST,
    ERP_PLANNER,
    ERP_PURCHASE_SPECIALIST,
    ERP_REPORT_WRITER,
    ERP_TEMPLATES,
    register_erp_templates,
)


# ===== Fixtures =====================================================

@pytest.fixture
def fresh_registry():
    """Reset the singleton registry so tests don't pollute each other."""
    AgentTemplateRegistry.reset_instance()
    yield AgentTemplateRegistry()
    AgentTemplateRegistry.reset_instance()


# ===== Module exports ===============================================

def test_module_exposes_all_four_templates():
    assert set(ERP_TEMPLATES.keys()) == {
        "erp_planner",
        "erp_inventory_analyst",
        "erp_purchase_specialist",
        "erp_report_writer",
    }
    for name, t in ERP_TEMPLATES.items():
        assert isinstance(t, AgentTemplate), f"{name} is not an AgentTemplate"


def test_module_exposes_template_instances():
    for t in (
        ERP_PLANNER,
        ERP_INVENTORY_ANALYST,
        ERP_PURCHASE_SPECIALIST,
        ERP_REPORT_WRITER,
    ):
        assert isinstance(t, AgentTemplate)


def test_module_exposes_register_function():
    assert callable(register_erp_templates)


# ===== Roles ========================================================

def test_erp_planner_role_is_planner():
    assert ERP_PLANNER.role == AgentRole.PLANNER


def test_erp_inventory_analyst_role_is_executor():
    assert ERP_INVENTORY_ANALYST.role == AgentRole.EXECUTOR


def test_erp_purchase_specialist_role_is_executor():
    assert ERP_PURCHASE_SPECIALIST.role == AgentRole.EXECUTOR


def test_erp_report_writer_role_is_reviewer():
    assert ERP_REPORT_WRITER.role == AgentRole.REVIEWER


# ===== Tools ========================================================

def test_erp_planner_has_no_tools():
    """Planner doesn't need tools — it just decomposes tasks."""
    assert ERP_PLANNER.tools == []


def test_erp_inventory_analyst_tools_include_inventory_and_nl2sql():
    tools = set(ERP_INVENTORY_ANALYST.tools)
    assert "get_low_stock_products" in tools
    assert "get_sales_velocity" in tools
    assert "get_inventory_levels" in tools
    assert "query_database" in tools


def test_erp_purchase_specialist_tools_include_kb_and_prices():
    tools = set(ERP_PURCHASE_SPECIALIST.tools)
    assert "get_supplier_price_history" in tools
    assert "ask_knowledge_base" in tools
    assert "query_database" in tools


def test_erp_report_writer_uses_kb_for_citations():
    assert "ask_knowledge_base" in ERP_REPORT_WRITER.tools


# ===== Required variables ==========================================

def test_erp_planner_required_vars():
    required = set(ERP_PLANNER.get_required_variables())
    assert {"current_date", "project_context", "question"}.issubset(required)


def test_erp_inventory_analyst_required_vars():
    required = set(ERP_INVENTORY_ANALYST.get_required_variables())
    assert {"current_date", "task_id", "upstream_context"}.issubset(required)


def test_erp_purchase_specialist_required_vars():
    required = set(ERP_PURCHASE_SPECIALIST.get_required_variables())
    assert {"current_date", "task_id", "upstream_context"}.issubset(required)


def test_erp_report_writer_required_vars():
    required = set(ERP_REPORT_WRITER.get_required_variables())
    assert {"current_date", "task_id", "upstream_context"}.issubset(required)


# ===== Render =======================================================

def test_render_prompt_substitutes_all_variables():
    rendered = ERP_PLANNER.render_prompt(
        variables={
            "current_date": "2026-06-12",
            "project_context": "Q2 stock review",
            "question": "哪些商品缺货?",
        }
    )
    assert "2026-06-12" in rendered
    assert "Q2 stock review" in rendered
    assert "哪些商品缺货?" in rendered
    # No leftover user-supplied placeholders. Note: the prompt
    # contains a deliberate `{{"subtasks": [...]}}` example showing
    # the LLM the output format; that one is content, not a
    # placeholder.
    assert "{{current_date}}" not in rendered
    assert "{{project_context}}" not in rendered
    assert "{{question}}" not in rendered


def test_render_prompt_rejects_none_variables():
    with pytest.raises(ValueError):
        ERP_PLANNER.render_prompt(variables=None)


def test_render_prompt_warns_on_missing_variables(caplog):
    """Unbound placeholders should be flagged in the warning."""
    with caplog.at_level("WARNING"):
        rendered = ERP_PLANNER.render_prompt(
            variables={"current_date": "2026-06-12"}  # missing project_context, question
        )
    # The warning is logged; the prompt is still returned (with
    # placeholders left intact so the LLM sees them).
    assert "{{project_context}}" in rendered
    assert "{{question}}" in rendered
    assert any("unbound" in m.lower() for m in caplog.messages)


# ===== Registration ================================================

def test_register_erp_templates_registers_all_four(fresh_registry):
    n = register_erp_templates(fresh_registry)
    assert n == 4
    for name in ERP_TEMPLATES:
        assert fresh_registry.get(name) is not None


def test_register_erp_templates_is_idempotent(fresh_registry):
    """Calling register twice without allow_override is a no-op
    (idempotent); with ``allow_override=True`` it re-registers."""
    n1 = register_erp_templates(fresh_registry)
    assert n1 == 4
    # Second call without allow_override: no-op, returns 0 new
    n2 = register_erp_templates(fresh_registry, allow_override=False)
    assert n2 == 0
    # With allow_override=True it should succeed and count 4
    n3 = register_erp_templates(fresh_registry, allow_override=True)
    assert n3 == 4


def test_register_into_default_registry():
    """Without args, register_erp_templates uses the global singleton."""
    AgentTemplateRegistry.reset_instance()
    try:
        n = register_erp_templates()
        assert n == 4
        reg = get_template_registry()
        for name in ERP_TEMPLATES:
            assert reg.get(name) is not None
    finally:
        AgentTemplateRegistry.reset_instance()


# ===== Agent instantiation (no LLM) ================================

class _NullProvider:
    """No-op LLM provider that just exists for instantiation."""
    async def complete(self, *a, **k):
        raise RuntimeError("not used in these tests")
    def model_name(self): return "null"


def test_erp_planner_creates_planner_agent():
    provider = _NullProvider()
    agent = ERP_PLANNER.create_agent(
        variables={
            "current_date": "2026-06-12",
            "project_context": "Q2",
            "question": "哪些缺货?",
        },
        provider=provider,
    )
    assert isinstance(agent, PlannerAgent)


def test_erp_inventory_analyst_creates_executor_agent():
    provider = _NullProvider()
    agent = ERP_INVENTORY_ANALYST.create_agent(
        variables={
            "current_date": "2026-06-12",
            "task_id": "t1",
            "upstream_context": "{}",
        },
        provider=provider,
    )
    assert isinstance(agent, ExecutorAgent)


def test_erp_purchase_specialist_creates_executor_agent():
    provider = _NullProvider()
    agent = ERP_PURCHASE_SPECIALIST.create_agent(
        variables={
            "current_date": "2026-06-12",
            "task_id": "t2",
            "upstream_context": "{}",
        },
        provider=provider,
    )
    assert isinstance(agent, ExecutorAgent)


def test_erp_report_writer_creates_reviewer_agent():
    provider = _NullProvider()
    agent = ERP_REPORT_WRITER.create_agent(
        variables={
            "current_date": "2026-06-12",
            "task_id": "t3",
            "upstream_context": "{}",
        },
        provider=provider,
    )
    assert isinstance(agent, ReviewerAgent)


def test_create_agent_picks_up_system_prompt():
    """Without an LLM provider, the rendered prompt is passed through
    verbatim to the agent's ``system_prompt`` attribute.

    (When a provider IS supplied, :class:`AgentTemplate.create_agent`
    uses an LLM-powered agent subclass like ``LLMPlannerAgent`` that
    has its own hardcoded ``SYSTEM_PROMPT`` class variable; in that
    case we just verify the agent was instantiated with the right
    name and role.)
    """
    agent = ERP_PLANNER.create_agent(
        variables={
            "current_date": "2026-06-12",
            "project_context": "Q2",
            "question": "哪些缺货?",
        },
        provider=None,
    )
    assert "2026-06-12" in agent.system_prompt
    assert "Q2" in agent.system_prompt
    assert "哪些缺货?" in agent.system_prompt


def test_create_agent_with_provider_uses_llm_subclass():
    """With a provider, the agent is an LLM-powered subclass that
    has its own hardcoded SYSTEM_PROMPT — we verify the name and
    role were still wired correctly."""
    provider = _NullProvider()
    agent = ERP_PLANNER.create_agent(
        variables={
            "current_date": "2026-06-12",
            "project_context": "Q2",
            "question": "哪些缺货?",
        },
        provider=provider,
    )
    assert agent.name == "erp_planner"
    assert agent.role == AgentRole.PLANNER


# ===== Metadata ====================================================

def test_templates_have_domain_metadata():
    """Each template tags itself with domain=erp for filtering."""
    for t in ERP_TEMPLATES.values():
        assert t.metadata.get("domain") == "erp"


def test_templates_have_phase_metadata():
    phases = {
        ERP_PLANNER.metadata.get("phase"),
        ERP_INVENTORY_ANALYST.metadata.get("phase"),
        ERP_PURCHASE_SPECIALIST.metadata.get("phase"),
        ERP_REPORT_WRITER.metadata.get("phase"),
    }
    assert phases == {"planning", "analysis", "recommendation", "reporting"}


# ===== __init__ exports ============================================

def test_agents_package_reexports_templates():
    from macs_pkg.erp.agents import (
        ERP_TEMPLATES as re_exported,
        register_erp_templates as re_register,
    )
    assert re_exported is ERP_TEMPLATES
    assert re_register is register_erp_templates


if __name__ == "__main__":
    sys.exit(
        __import__("subprocess").call(
            ["pytest", __file__, "-v", "--tb=short"]
        )
    )
