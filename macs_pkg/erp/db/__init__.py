"""ERP database layer: connection pool, schema DDL, seed data."""

from .connection import (
    DatabaseConfig,
    DatabasePool,
    get_default_pool,
    reset_default_pool,
)
from .schema import (
    ALL_DDL,
    DDL_INVENTORY,
    DDL_PRODUCTS,
    DDL_PURCHASE_ORDERS,
    DDL_SALES_ORDERS,
    DDL_SUPPLIERS,
    EXPECTED_TABLES,
    SCHEMA_DESCRIPTION,
    apply_schema,
    assert_schema,
    drop_schema,
)
from .seed import (
    CUSTOMER_REGIONS,
    PRODUCTS,
    SCALE_ROWS,
    SUPPLIERS,
    WAREHOUSES,
    seed_database,
)

__all__ = [
    # connection
    "DatabaseConfig",
    "DatabasePool",
    "get_default_pool",
    "reset_default_pool",
    # schema
    "DDL_SUPPLIERS",
    "DDL_PRODUCTS",
    "DDL_INVENTORY",
    "DDL_PURCHASE_ORDERS",
    "DDL_SALES_ORDERS",
    "ALL_DDL",
    "EXPECTED_TABLES",
    "SCHEMA_DESCRIPTION",
    "apply_schema",
    "assert_schema",
    "drop_schema",
    # seed
    "SCALE_ROWS",
    "PRODUCTS",
    "SUPPLIERS",
    "WAREHOUSES",
    "CUSTOMER_REGIONS",
    "seed_database",
]
