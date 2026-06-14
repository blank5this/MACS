"""ERP AI Copilot demo utilities (no infrastructure required)."""
from macs_pkg.erp.demo.text2sql_demo import (
    DEFAULT_SQLITE_PATH,
    INTENT_EXAMPLES,
    Text2SQLResult,
    init_db,
    route_intent,
    run,
    safety_check,
)

__all__ = [
    "DEFAULT_SQLITE_PATH",
    "INTENT_EXAMPLES",
    "Text2SQLResult",
    "init_db",
    "route_intent",
    "run",
    "safety_check",
]