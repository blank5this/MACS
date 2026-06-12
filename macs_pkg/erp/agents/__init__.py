"""ERP agents: single copilot agent (Day 8) + domain templates (Day 9)."""

from .copilot_agent import ERPCopilotAgent, build_copilot_agent
from .templates import (
    ERP_TEMPLATES,
    ERP_PLANNER,
    ERP_INVENTORY_ANALYST,
    ERP_PURCHASE_SPECIALIST,
    ERP_REPORT_WRITER,
    register_erp_templates,
)

__all__ = [
    # Day 8: single copilot
    "ERPCopilotAgent",
    "build_copilot_agent",
    # Day 9: domain templates
    "ERP_TEMPLATES",
    "ERP_PLANNER",
    "ERP_INVENTORY_ANALYST",
    "ERP_PURCHASE_SPECIALIST",
    "ERP_REPORT_WRITER",
    "register_erp_templates",
]
