"""ERP AI Copilot - Natural Language Interface for ERP Systems.

Built on top of MACS multi-agent framework. Provides:
- PostgreSQL-backed business data (products, suppliers, sales/purchase orders)
- Natural language to SQL translation with safety guardrails
- MCP-exposed inventory/sales/procurement tools
- RAG knowledge base for ERP policies and procedures
- Multi-agent inventory risk analysis and purchase recommendation workflows
- Lightweight web UI for demos

Quickstart::

    from macs_pkg.erp.db import DatabasePool, apply_schema, seed_database
    from macs_pkg.erp.nl2sql import NL2SQLTranslator
    from macs_pkg.erp.tools import build_erp_mcp_server
    from macs_pkg.erp.rag import ask_kb
    from macs_pkg.erp.workflows import InventoryRiskWorkflow
"""

__version__ = "0.1.0-erp-copilot"
