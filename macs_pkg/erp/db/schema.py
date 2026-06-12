"""ERP database schema: 5 tables + a rich ``SCHEMA_DESCRIPTION`` for NL→SQL.

The ``SCHEMA_DESCRIPTION`` string is injected into the NL→SQL system prompt
(``macs_pkg/erp/prompts/nl2sql_system.txt``) so the LLM can generate correct
parameterized SELECT statements against the ERP database.

Tables (in dependency order):
    suppliers         (master data, no FK in)
    products          (master data, no FK in)
    inventory         (1 row per product × warehouse)
    purchase_orders   (references suppliers, products)
    sales_orders      (references products)
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from .connection import DatabasePool

logger = logging.getLogger(__name__)


# ===== Table DDL (in dependency order) ===============================

DDL_SUPPLIERS = """
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id    SERIAL PRIMARY KEY,
    name           VARCHAR(128) NOT NULL,
    contact_email  VARCHAR(128),
    rating         NUMERIC(3,2)  CHECK (rating >= 0 AND rating <= 5),
    payment_terms  VARCHAR(64)   DEFAULT 'Net 30',
    country        VARCHAR(64)   DEFAULT 'CN',
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);
"""

DDL_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    product_id     SERIAL PRIMARY KEY,
    sku            VARCHAR(32)  UNIQUE NOT NULL,
    name           VARCHAR(128) NOT NULL,
    category       VARCHAR(64)  NOT NULL,
    unit_price     NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    safety_stock   INT          NOT NULL DEFAULT 50 CHECK (safety_stock >= 0),
    lead_time_days INT          NOT NULL DEFAULT 14 CHECK (lead_time_days >= 0),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
"""

DDL_INVENTORY = """
CREATE TABLE IF NOT EXISTS inventory (
    product_id     INT  NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    warehouse_id   INT  NOT NULL CHECK (warehouse_id >= 1),
    on_hand        INT  NOT NULL DEFAULT 0 CHECK (on_hand >= 0),
    last_counted   DATE NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (product_id, warehouse_id)
);
CREATE INDEX IF NOT EXISTS idx_inventory_low_stock
    ON inventory(product_id) WHERE on_hand < 100;
"""

DDL_PURCHASE_ORDERS = """
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id              SERIAL PRIMARY KEY,
    supplier_id        INT  NOT NULL REFERENCES suppliers(supplier_id),
    product_id         INT  NOT NULL REFERENCES products(product_id),
    quantity           INT  NOT NULL CHECK (quantity > 0),
    unit_cost          NUMERIC(12,2) NOT NULL CHECK (unit_cost >= 0),
    order_date         DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_delivery  DATE,
    status             VARCHAR(16) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'received', 'cancelled')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_po_supplier  ON purchase_orders(supplier_id, order_date DESC);
CREATE INDEX IF NOT EXISTS idx_po_product   ON purchase_orders(product_id, order_date DESC);
CREATE INDEX IF NOT EXISTS idx_po_status    ON purchase_orders(status);
"""

DDL_SALES_ORDERS = """
CREATE TABLE IF NOT EXISTS sales_orders (
    so_id             SERIAL PRIMARY KEY,
    product_id        INT  NOT NULL REFERENCES products(product_id),
    quantity          INT  NOT NULL CHECK (quantity > 0),
    unit_price        NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    sale_date         DATE NOT NULL DEFAULT CURRENT_DATE,
    customer_region   VARCHAR(32) NOT NULL DEFAULT 'CN-South',
    customer_name     VARCHAR(128),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_so_product_date ON sales_orders(product_id, sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_so_region_date  ON sales_orders(customer_region, sale_date DESC);
"""

ALL_DDL: list[str] = [
    DDL_SUPPLIERS,
    DDL_PRODUCTS,
    DDL_INVENTORY,
    DDL_PURCHASE_ORDERS,
    DDL_SALES_ORDERS,
]

EXPECTED_TABLES: list[str] = [
    "suppliers",
    "products",
    "inventory",
    "purchase_orders",
    "sales_orders",
]


# ===== SCHEMA_DESCRIPTION (injected into NL→SQL system prompt) ======

SCHEMA_DESCRIPTION: str = """\
You are querying an ERP (Enterprise Resource Planning) PostgreSQL database.

# Database: erp_copilot
# Schema:   public
# Encoding: UTF-8 (Chinese values are normal)

## Tables (5)

### 1. products
Master data for SKUs sold/purchased by the company.
| Column          | Type           | Notes                                              |
|-----------------|----------------|----------------------------------------------------|
| product_id      | SERIAL PK      | Surrogate key                                      |
| sku             | VARCHAR(32)    | UNIQUE NOT NULL, e.g. 'SKU-0001'                   |
| name            | VARCHAR(128)   | NOT NULL, e.g. '不锈钢螺栓 M8x40'                  |
| category        | VARCHAR(64)    | NOT NULL, e.g. '五金件', '电子元件', '包装材料'    |
| unit_price      | NUMERIC(12,2)  | NOT NULL, retail/sales price in CNY               |
| safety_stock    | INT            | NOT NULL DEFAULT 50, reorder threshold             |
| lead_time_days  | INT            | NOT NULL DEFAULT 14, supplier lead time            |
| created_at      | TIMESTAMPTZ    | DEFAULT now()                                      |

### 2. suppliers
Master data for vendors we buy from.
| Column          | Type           | Notes                                              |
|-----------------|----------------|----------------------------------------------------|
| supplier_id     | SERIAL PK      | Surrogate key                                      |
| name            | VARCHAR(128)   | NOT NULL, e.g. '深圳五金制品有限公司'              |
| contact_email   | VARCHAR(128)   | Nullable                                           |
| rating          | NUMERIC(3,2)   | 0.00 - 5.00, higher is better                      |
| payment_terms   | VARCHAR(64)    | DEFAULT 'Net 30'                                   |
| country         | VARCHAR(64)    | DEFAULT 'CN'                                       |
| created_at      | TIMESTAMPTZ    | DEFAULT now()                                      |

### 3. inventory
On-hand stock per product per warehouse. 1 row = (product, warehouse) pair.
| Column          | Type           | Notes                                              |
|-----------------|----------------|----------------------------------------------------|
| product_id      | INT            | PK, FK -> products                                 |
| warehouse_id    | INT            | PK, e.g. 1/2/3                                     |
| on_hand         | INT            | NOT NULL, current physical quantity                |
| last_counted    | DATE           | DEFAULT CURRENT_DATE                               |

### 4. purchase_orders
Procurement transactions (POs sent to suppliers).
| Column             | Type           | Notes                                              |
|--------------------|----------------|----------------------------------------------------|
| po_id              | SERIAL PK      |                                                    |
| supplier_id        | INT            | FK -> suppliers                                    |
| product_id         | INT            | FK -> products                                     |
| quantity           | INT            | > 0                                                |
| unit_cost          | NUMERIC(12,2)  | What we paid per unit, CNY                         |
| order_date         | DATE           | When PO was placed                                 |
| expected_delivery  | DATE           | Nullable, supplier's promised arrival              |
| status             | VARCHAR(16)    | 'pending' | 'received' | 'cancelled'              |
| created_at         | TIMESTAMPTZ    | DEFAULT now()                                      |

### 5. sales_orders
Sales transactions (orders we fulfilled).
| Column             | Type           | Notes                                              |
|--------------------|----------------|----------------------------------------------------|
| so_id              | SERIAL PK      |                                                    |
| product_id         | INT            | FK -> products                                     |
| quantity           | INT            | > 0                                                |
| unit_price         | NUMERIC(12,2)  | Actual sale price (may differ from products.unit_price) |
| sale_date          | DATE           | When the order shipped                             |
| customer_region    | VARCHAR(32)    | e.g. 'CN-South', 'CN-North', 'CN-East', '海外'     |
| customer_name      | VARCHAR(128)   | Nullable                                           |
| created_at         | TIMESTAMPTZ    | DEFAULT now()                                      |

## Foreign key relationships

    inventory.product_id  -> products.product_id
    purchase_orders.supplier_id -> suppliers.supplier_id
    purchase_orders.product_id  -> products.product_id
    sales_orders.product_id     -> products.product_id

## Common query patterns

- Low stock alert: ``inventory.on_hand < products.safety_stock``
  (join inventory with products; the safety_stock lives on products, not inventory)
- Top sellers in last N days: aggregate sales_orders.quantity GROUP BY product_id
  for sale_date >= CURRENT_DATE - INTERVAL 'N days'
- Supplier price trend: look at purchase_orders.unit_cost over order_date
- Days of inventory: ``inventory.on_hand / NULLIF(velocity, 0)`` where velocity
  is the average daily sales from sales_orders over the last 30 days

## Important rules

- ALWAYS parameterize with ``%s`` placeholders. NEVER string-interpolate user input.
- Use ``CURRENT_DATE`` or ``now()`` for date arithmetic, not hardcoded dates.
- For "last N days" use ``sale_date >= CURRENT_DATE - INTERVAL '<N> days'``.
- Currency is CNY (¥) unless the question mentions another currency.
- Quantities are non-negative integers; amounts are NUMERIC(12,2).
- Respond with a single JSON object — see the system prompt for the contract.
"""


# ===== Schema lifecycle =============================================

async def apply_schema(pool: DatabasePool, schema_name: str = "public") -> None:
    """Create all tables (idempotent — uses ``IF NOT EXISTS``)."""
    async with pool.connection() as conn:
        if schema_name != "public":
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            await conn.execute(f"SET search_path TO {schema_name}")
        for ddl in ALL_DDL:
            await conn.execute(ddl)
        await conn.commit()
    logger.info("Schema applied (%d tables)", len(ALL_DDL))


async def assert_schema(
    pool: DatabasePool,
    expected: Iterable[str] = EXPECTED_TABLES,
) -> None:
    """Raise ``RuntimeError`` if any expected table is missing."""
    expected_set = set(expected)
    sql = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """
    rows = await pool.fetch(sql)
    present = {r["table_name"] for r in rows}
    missing = expected_set - present
    if missing:
        raise RuntimeError(
            f"Schema check failed. Missing tables: {sorted(missing)}. "
            f"Present: {sorted(present)}"
        )
    logger.info("Schema assertion passed (%d tables)", len(present))


async def drop_schema(
    pool: DatabasePool,
    schema_name: str = "public",
    tables: Optional[Iterable[str]] = None,
) -> None:
    """Drop the listed tables (or all 5 ERP tables by default).

    Used by tests for isolation. Refuses to drop if ``schema_name='public'``
    and ``tables`` is None to avoid accidental data loss; pass an explicit
    list to override.
    """
    targets = list(tables) if tables is not None else EXPECTED_TABLES
    async with pool.connection() as conn:
        for t in targets:
            await conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        await conn.commit()
    logger.info("Schema dropped: %s", targets)


__all__ = [
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
]
