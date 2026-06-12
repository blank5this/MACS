"""ERP multi-agent workflows: inventory risk analysis, purchase recommendation."""

from .inventory_risk import InventoryRiskWorkflow, run_inventory_risk_analysis

__all__ = [
    "InventoryRiskWorkflow",
    "run_inventory_risk_analysis",
]
