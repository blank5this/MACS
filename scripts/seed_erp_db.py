#!/usr/bin/env python
"""CLI entry point to seed the ERP AI Copilot demo database.

Usage::

    python scripts/seed_erp_db.py --scale small
    python scripts/seed_erp_db.py --scale medium --no-truncate
    python scripts/seed_erp_db.py --scale large --seed 2026

Environment variables (from .env or shell)::

    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Exit codes::

    0  success
    1  database connection / seed failure
    2  invalid arguments
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Make the project importable when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from macs_pkg.erp.db import (  # noqa: E402  (after sys.path mutation)
    DatabaseConfig,
    DatabasePool,
    SCALE_ROWS,
    apply_schema,
    assert_schema,
    seed_database,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Seed the ERP AI Copilot demo database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--scale",
        choices=sorted(SCALE_ROWS.keys()),
        default=os.getenv("ERP_SEED_SCALE", "small"),
        help="Seed scale (small=300, medium=1000, large=5000 rows per fact table)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic data generation",
    )
    p.add_argument(
        "--no-truncate",
        action="store_true",
        help="Skip truncation (will fail on duplicate PKs / unique constraints)",
    )
    p.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip apply_schema (use when tables already exist)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve config, connect, and exit before any DML",
    )
    return p.parse_args()


async def main() -> int:
    args = parse_args()
    config = DatabaseConfig.from_env()

    print(f"Target database: {config.user}@{config.host}:{config.port}/{config.dbname}")
    print(f"Scale: {args.scale} ({SCALE_ROWS[args.scale]} rows/fact table)")
    print(f"Random seed: {args.seed}")
    print()

    pool = DatabasePool(config)
    t0 = time.monotonic()
    try:
        await pool.open()
        print("[1/3] Connected. Schema check...", end=" ", flush=True)
        if not args.skip_schema:
            await apply_schema(pool)
            print("applied (or already present).")
        else:
            print("skipped (--skip-schema).")
        await assert_schema(pool)

        if args.dry_run:
            print("Dry run: would seed now. Exiting.")
            await pool.close()
            return 0

        print(f"[2/3] Seeding {args.scale} dataset...", end=" ", flush=True)
        summary = await seed_database(
            pool,
            scale=args.scale,
            seed=args.seed,
            truncate_first=not args.no_truncate,
        )
        print(f"done in {time.monotonic() - t0:.2f}s.")

        print("[3/3] Verifying row counts:")
        for table in ("suppliers", "products", "inventory", "purchase_orders", "sales_orders"):
            n = await pool.fetchval(f"SELECT count(*) FROM {table}")
            print(f"  {table:20s} {n:>6d} rows")

    except Exception as e:  # noqa: BLE001
        print(f"\n[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        await pool.close()

    print()
    print(f"Seed complete in {time.monotonic() - t0:.2f}s. Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
