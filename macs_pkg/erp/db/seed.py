"""Deterministic seed data for the ERP AI Copilot demo database.

Uses :mod:`faker` with a fixed :class:`random.Random` seed so the same scale
produces byte-identical output across runs and across machines — useful for
reproducible demos, regression tests, and recorded Demo videos.

Quickstart::

    from macs_pkg.erp.db import DatabasePool, DatabaseConfig, apply_schema
    from macs_pkg.erp.db.seed import seed_database

    pool = DatabasePool(DatabaseConfig.from_env())
    await pool.open()
    await apply_schema(pool)
    await seed_database(pool, scale="medium")
    await pool.close()
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import Iterable, Optional

from faker import Faker

from .connection import DatabasePool

logger = logging.getLogger(__name__)

# ===== Scale presets =================================================

SCALE_ROWS: dict[str, int] = {
    "small": 300,    # 300 rows per fact table — fast smoke tests
    "medium": 1000,  # 1000 rows per fact table — default for demos
    "large": 5000,   # 5000 rows per fact table — stress / perf testing
}

# ===== Fixed master data (deterministic) ============================

# 20 products, 5 categories x 4 SKUs each. Prices realistic for Chinese B2B.
PRODUCTS: list[dict] = [
    # category: 五金件
    {"sku": "SKU-0001", "name": "不锈钢螺栓 M8x40",        "category": "五金件",   "unit_price": 0.85,  "safety_stock": 200, "lead_time_days": 14},
    {"sku": "SKU-0002", "name": "内六角螺钉 M6x20",        "category": "五金件",   "unit_price": 0.65,  "safety_stock": 250, "lead_time_days": 14},
    {"sku": "SKU-0003", "name": "尼龙垫圈 M10",            "category": "五金件",   "unit_price": 0.12,  "safety_stock": 500, "lead_time_days": 7},
    {"sku": "SKU-0004", "name": "自攻螺丝 4x16",           "category": "五金件",   "unit_price": 0.08,  "safety_stock": 800, "lead_time_days": 7},
    # category: 电子元件
    {"sku": "SKU-0005", "name": "USB-C 数据线 1m",         "category": "电子元件", "unit_price": 12.50, "safety_stock": 80,  "lead_time_days": 21},
    {"sku": "SKU-0006", "name": "DC 电源适配器 12V 2A",    "category": "电子元件", "unit_price": 28.00, "safety_stock": 40,  "lead_time_days": 21},
    {"sku": "SKU-0007", "name": "PCB 板 10x10 双面",       "category": "电子元件", "unit_price": 8.50,  "safety_stock": 100, "lead_time_days": 30},
    {"sku": "SKU-0008", "name": "LED 灯珠 5mm 白光 100只", "category": "电子元件", "unit_price": 18.00, "safety_stock": 60,  "lead_time_days": 14},
    # category: 包装材料
    {"sku": "SKU-0009",  "name": "气泡信封 300x400",       "category": "包装材料", "unit_price": 1.20,  "safety_stock": 300, "lead_time_days": 10},
    {"sku": "SKU-0010",  "name": "瓦楞纸箱 50x40x30",      "category": "包装材料", "unit_price": 3.50,  "safety_stock": 150, "lead_time_days": 10},
    {"sku": "SKU-0011",  "name": "透明胶带 48mm x 100m",   "category": "包装材料", "unit_price": 5.80,  "safety_stock": 100, "lead_time_days": 14},
    {"sku": "SKU-0012",  "name": "PE 缠绕膜 50cm x 300m",  "category": "包装材料", "unit_price": 22.00, "safety_stock": 50,  "lead_time_days": 14},
    # category: 办公用品
    {"sku": "SKU-0013", "name": "A4 复印纸 80g 500张/包",  "category": "办公用品", "unit_price": 28.00, "safety_stock": 100, "lead_time_days": 7},
    {"sku": "SKU-0014", "name": "中性笔 0.5mm 黑色 12支",  "category": "办公用品", "unit_price": 18.00, "safety_stock": 80,  "lead_time_days": 7},
    {"sku": "SKU-0015", "name": "订书机 标准号",            "category": "办公用品", "unit_price": 15.50, "safety_stock": 60,  "lead_time_days": 14},  # demo: low stock
    {"sku": "SKU-0016", "name": "档案盒 A4 蓝色",          "category": "办公用品", "unit_price": 8.50,  "safety_stock": 100, "lead_time_days": 7},
    # category: 工具
    {"sku": "SKU-0017", "name": "十字螺丝刀 PH2 x 100mm",  "category": "工具",     "unit_price": 12.00, "safety_stock": 50,  "lead_time_days": 21},
    {"sku": "SKU-0018", "name": "数显万用表",               "category": "工具",     "unit_price": 88.00, "safety_stock": 20,  "lead_time_days": 30},  # demo: low stock
    {"sku": "SKU-0019", "name": "电烙铁 60W 可调温",       "category": "工具",     "unit_price": 65.00, "safety_stock": 30,  "lead_time_days": 21},
    {"sku": "SKU-0020", "name": "热风枪 1500W",            "category": "工具",     "unit_price": 168.00, "safety_stock": 15,  "lead_time_days": 30},
]

# 10 suppliers, with realistic Chinese vendor names.
SUPPLIERS: list[dict] = [
    {"name": "深圳五金制品有限公司",      "contact_email": "sales@sz-hardware.cn",     "rating": 4.50, "payment_terms": "Net 30", "country": "CN"},
    {"name": "东莞电子元件供应商",        "contact_email": "biz@dg-electronics.cn",   "rating": 4.20, "payment_terms": "Net 45", "country": "CN"},
    {"name": "上海包装材料贸易",          "contact_email": "order@sh-packaging.cn",    "rating": 3.80, "payment_terms": "Net 30", "country": "CN"},  # demo: 涨价最快
    {"name": "广州办公用品批发",          "contact_email": "info@gz-office.cn",        "rating": 4.70, "payment_terms": "Net 30", "country": "CN"},
    {"name": "宁波工具制造",              "contact_email": "sales@nb-tools.cn",        "rating": 4.40, "payment_terms": "Net 60", "country": "CN"},
    {"name": "苏州精密五金",              "contact_email": "contact@sz-precision.cn",  "rating": 4.90, "payment_terms": "Net 30", "country": "CN"},
    {"name": "杭州电子科技",              "contact_email": "biz@hz-tech.cn",           "rating": 4.10, "payment_terms": "Net 45", "country": "CN"},
    {"name": "佛山包装实业",              "contact_email": "order@fs-package.cn",      "rating": 3.95, "payment_terms": "Net 30", "country": "CN"},
    {"name": "中山办公设备",              "contact_email": "sales@zs-office.cn",       "rating": 4.30, "payment_terms": "Net 30", "country": "CN"},
    {"name": "青岛工业工具",              "contact_email": "info@qd-industrial.cn",    "rating": 4.60, "payment_terms": "Net 45", "country": "CN"},
]

# 3 warehouses
WAREHOUSES: list[int] = [1, 2, 3]  # 1=深圳总仓, 2=上海分仓, 3=北京分仓

CUSTOMER_REGIONS: list[str] = ["CN-South", "CN-North", "CN-East", "海外"]
REGION_WEIGHTS: list[int] = [40, 30, 20, 10]

PO_STATUSES: list[str] = ["pending", "received", "cancelled"]
PO_STATUS_WEIGHTS: list[int] = [25, 70, 5]


# ===== Helpers =======================================================

def _make_faker(seed: int = 42) -> Faker:
    """Return a deterministic Faker instance rooted in Chinese locale."""
    fake = Faker("zh_CN")
    Faker.seed(seed)
    return fake


def _weighted_choice(rng: random.Random, choices: list, weights: list[int]):
    return rng.choices(choices, weights=weights, k=1)[0]


def _recent_date(rng: random.Random, days_back: int) -> date:
    """Random date in the last ``days_back`` days (inclusive)."""
    today = date.today()
    offset = rng.randint(0, days_back)
    return today - timedelta(days=offset)


# ===== Data generators ==============================================

def generate_products(rng: random.Random) -> list[tuple]:
    """Yield ``(sku, name, category, unit_price, safety_stock, lead_time_days)`` rows."""
    return [
        (
            p["sku"],
            p["name"],
            p["category"],
            p["unit_price"],
            p["safety_stock"],
            p["lead_time_days"],
        )
        for p in PRODUCTS
    ]


def generate_suppliers(rng: random.Random) -> list[tuple]:
    """Yield supplier rows."""
    return [
        (
            s["name"],
            s["contact_email"],
            s["rating"],
            s["payment_terms"],
            s["country"],
        )
        for s in SUPPLIERS
    ]


def generate_inventory(rng: random.Random, product_ids: list[int]) -> list[tuple]:
    """Yield ``(product_id, warehouse_id, on_hand, last_counted)`` rows.

    Notes:
        * SKU-0015 and SKU-0018 are intentionally seeded with on_hand below
          safety_stock to drive the inventory risk demo (Day 10).
        * Some products get a small stock to amplify the "low stock alert" KPI.
    """
    low_stock_skus = {"SKU-0015", "SKU-0018", "SKU-0003", "SKU-0004"}
    rows: list[tuple] = []
    for sku, pid in zip([p["sku"] for p in PRODUCTS], product_ids):
        for wh in WAREHOUSES:
            if sku in low_stock_skus:
                on_hand = rng.randint(0, 15)  # intentionally low
            else:
                on_hand = rng.randint(50, 600)
            last_counted = _recent_date(rng, 60)
            rows.append((pid, wh, on_hand, last_counted))
    return rows


def generate_purchase_orders(
    rng: random.Random,
    supplier_ids: list[int],
    product_ids: list[int],
    count: int,
) -> list[tuple]:
    """Yield purchase_order rows.

    Supplier #3 (id index 2 in supplier_ids) is intentionally biased with an
    upward unit_cost trend to drive the "supplier price trend" demo (Day 5).
    """
    today = date.today()
    growing_supplier_id = supplier_ids[2]  # 上海包装材料贸易
    rows: list[tuple] = []
    for _ in range(count):
        sid = rng.choice(supplier_ids)
        pid = rng.choice(product_ids)
        qty = rng.randint(50, 500)
        # 50-70% of list price is a realistic wholesale cost
        base_cost = PRODUCTS[[p["sku"] for p in PRODUCTS].index(
            _sku_for_product_id(product_ids, pid)
        )]["unit_price"] * rng.uniform(0.5, 0.7)

        # Apply growth bias for the "涨价最快" supplier
        order_date = _recent_date(rng, 180)
        days_ago = (today - order_date).days
        if sid == growing_supplier_id:
            # +0.5% per day going back, capped at +30%
            growth = min(0.30, 0.005 * (180 - days_ago))
            unit_cost = round(base_cost * (1 + growth), 2)
        else:
            unit_cost = round(base_cost, 2)

        expected_delivery = order_date + timedelta(days=rng.randint(7, 30))
        status = _weighted_choice(rng, PO_STATUSES, PO_STATUS_WEIGHTS)
        rows.append((sid, pid, qty, unit_cost, order_date, expected_delivery, status))
    return rows


def generate_sales_orders(
    rng: random.Random,
    product_ids: list[int],
    count: int,
    faker: Faker,
) -> list[tuple]:
    """Yield sales_order rows."""
    rows: list[tuple] = []
    for _ in range(count):
        pid = rng.choice(product_ids)
        qty = rng.randint(1, 100)
        base_price = PRODUCTS[[p["sku"] for p in PRODUCTS].index(
            _sku_for_product_id(product_ids, pid)
        )]["unit_price"]
        # Sale price varies ±10% from list
        unit_price = round(base_price * rng.uniform(0.90, 1.10), 2)
        sale_date = _recent_date(rng, 90)
        region = _weighted_choice(rng, CUSTOMER_REGIONS, REGION_WEIGHTS)
        customer_name = faker.company() if rng.random() < 0.4 else None
        rows.append((pid, qty, unit_price, sale_date, region, customer_name))
    return rows


def _sku_for_product_id(product_ids: list[int], pid: int) -> str:
    """Look up SKU string for a given product_id (sequential insert order)."""
    idx = product_ids.index(pid)
    return PRODUCTS[idx]["sku"]


# ===== Main entry point =============================================

async def seed_database(
    pool: DatabasePool,
    scale: str = "medium",
    seed: int = 42,
    truncate_first: bool = True,
) -> dict:
    """Seed the ERP database. Idempotent when ``truncate_first=True``.

    Returns a summary dict with row counts for verification.
    """
    if scale not in SCALE_ROWS:
        raise ValueError(f"Unknown scale '{scale}'. Choose from {list(SCALE_ROWS)}")
    count = SCALE_ROWS[scale]

    rng = random.Random(seed)
    faker = _make_faker(seed)
    logger.info("Seeding ERP database (scale=%s, target=%d rows per fact table)", scale, count)

    async with pool.connection() as conn:
        if truncate_first:
            logger.info("Truncating existing ERP tables (in reverse FK order)")
            await conn.execute(
                "TRUNCATE TABLE sales_orders, purchase_orders, inventory, products, suppliers "
                "RESTART IDENTITY CASCADE"
            )

        # 1. suppliers
        sup_rows = generate_suppliers(rng)
        supplier_ids: list[int] = []
        async with conn.cursor() as cur:
            for row in sup_rows:
                await cur.execute(
                    "INSERT INTO suppliers (name, contact_email, rating, payment_terms, country) "
                    "VALUES (%s,%s,%s,%s,%s) RETURNING supplier_id",
                    row,
                )
                (sid,) = await cur.fetchone()
                supplier_ids.append(sid)
        logger.info("  suppliers: %d rows", len(supplier_ids))

        # 2. products
        prod_rows = generate_products(rng)
        product_ids: list[int] = []
        async with conn.cursor() as cur:
            for row in prod_rows:
                await cur.execute(
                    "INSERT INTO products (sku, name, category, unit_price, safety_stock, lead_time_days) "
                    "VALUES (%s,%s,%s,%s,%s,%s) RETURNING product_id",
                    row,
                )
                (pid,) = await cur.fetchone()
                product_ids.append(pid)
        logger.info("  products:  %d rows", len(product_ids))

        # 3. inventory
        inv_rows = generate_inventory(rng, product_ids)
        async with conn.cursor() as cur:
            await cur.executemany(
                "INSERT INTO inventory (product_id, warehouse_id, on_hand, last_counted) "
                "VALUES (%s,%s,%s,%s)",
                inv_rows,
            )
        logger.info("  inventory: %d rows", len(inv_rows))

        # 4. purchase_orders
        po_rows = generate_purchase_orders(rng, supplier_ids, product_ids, count)
        async with conn.cursor() as cur:
            # Batched executemany (psycopg handles serialization)
            BATCH = 500
            for i in range(0, len(po_rows), BATCH):
                await cur.executemany(
                    "INSERT INTO purchase_orders "
                    "(supplier_id, product_id, quantity, unit_cost, order_date, expected_delivery, status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    po_rows[i : i + BATCH],
                )
        logger.info("  purchase_orders: %d rows", len(po_rows))

        # 5. sales_orders
        so_rows = generate_sales_orders(rng, product_ids, count, faker)
        async with conn.cursor() as cur:
            for i in range(0, len(so_rows), BATCH):
                await cur.executemany(
                    "INSERT INTO sales_orders "
                    "(product_id, quantity, unit_price, sale_date, customer_region, customer_name) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    so_rows[i : i + BATCH],
                )
        logger.info("  sales_orders: %d rows", len(so_rows))

        await conn.commit()

    summary = {
        "scale": scale,
        "suppliers": len(supplier_ids),
        "products": len(product_ids),
        "inventory": len(inv_rows),
        "purchase_orders": len(po_rows),
        "sales_orders": len(so_rows),
    }
    logger.info("Seed complete: %s", summary)
    return summary


__all__ = [
    "SCALE_ROWS",
    "PRODUCTS",
    "SUPPLIERS",
    "WAREHOUSES",
    "CUSTOMER_REGIONS",
    "seed_database",
]
