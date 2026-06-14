"""Async PostgreSQL connection pool for the ERP AI Copilot.

Wraps psycopg3's ``AsyncConnectionPool`` with a thin, ergonomic API and a
``DatabaseConfig`` dataclass that auto-loads from environment variables.

Quickstart::

    from macs_pkg.erp.db import DatabasePool, DatabaseConfig

    pool = DatabasePool(DatabaseConfig.from_env())
    await pool.open()
    rows = await pool.fetch("SELECT * FROM products LIMIT 5")
    await pool.close()

Or use the module-level singleton factory::

    from macs_pkg.erp.db import get_default_pool
    pool = get_default_pool()
    await pool.open()
    ...
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import psycopg
from psycopg_pool import AsyncConnectionPool

# psycopg3 async does NOT work with the default ProactorEventLoop on Windows.
# Force the selector loop policy at import time on Win32. This is a no-op on
# Linux/macOS. See: https://www.psycopg.org/psycopg3/docs/advanced/async.html
#
# `WindowsSelectorEventLoopPolicy` is "slated for removal" in Python 3.16 and
# already raises DeprecationWarning on 3.14. We suppress the warning here
# because there is no public, cross-version replacement yet (3.16 introduces
# `asyncio.loop_factory`-based loop creation, which callers should adopt).
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:  # Python < 3.8 fallback
        pass
    import warnings
    warnings.filterwarnings(
        "ignore",
        message=r"asyncio\.(set_event_loop_policy|WindowsSelectorEventLoopPolicy).*",
        category=DeprecationWarning,
    )

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """PostgreSQL connection configuration.

    Defaults match the ``docker-compose.yml`` ``postgres`` service so a fresh
    checkout works without any environment variables.
    """

    host: str = "localhost"
    port: int = 5432
    dbname: str = "erp_copilot"
    user: str = "erp"
    password: str = "erp_pass"
    pool_min_size: int = 2
    pool_max_size: int = 10
    pool_timeout: float = 30.0
    schema_name: str = "public"

    @classmethod
    def from_env(cls, prefix: str = "POSTGRES_") -> "DatabaseConfig":
        """Build a config from environment variables (e.g. ``POSTGRES_HOST``)."""
        return cls(
            host=os.getenv(f"{prefix}HOST", "localhost"),
            port=int(os.getenv(f"{prefix}PORT", "5432")),
            dbname=os.getenv(f"{prefix}DB", "erp_copilot"),
            user=os.getenv(f"{prefix}USER", "erp"),
            password=os.getenv(f"{prefix}PASSWORD", "erp_pass"),
        )

    def conninfo(self) -> str:
        """Return a libpq ``conninfo`` string for psycopg."""
        return psycopg.conninfo.make_conninfo(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
        )


class DatabasePool:
    """Thin async wrapper around ``psycopg_pool.AsyncConnectionPool``.

    The pool is lazy: ``open()`` must be awaited before queries. ``close()``
    is idempotent and safe to call multiple times. The ``connection()``
    context manager handles transaction commit/rollback automatically.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        self.config = config or DatabaseConfig()
        self._pool: Optional[AsyncConnectionPool] = None

    async def open(self) -> None:
        if self._pool is not None:
            return
        self._pool = AsyncConnectionPool(
            conninfo=self.config.conninfo(),
            min_size=self.config.pool_min_size,
            max_size=self.config.pool_max_size,
            timeout=self.config.pool_timeout,
            open=False,
        )
        await self._pool.open()
        await self._pool.wait()
        logger.info(
            "DatabasePool opened: %s:%s/%s (min=%d, max=%d)",
            self.config.host,
            self.config.port,
            self.config.dbname,
            self.config.pool_min_size,
            self.config.pool_max_size,
        )

    async def close(self) -> None:
        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None
        logger.info("DatabasePool closed")

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[psycopg.AsyncConnection]:
        if self._pool is None:
            await self.open()
        async with self._pool.connection() as conn:  # type: ignore[union-attr]
            yield conn

    async def execute(self, sql: str, params: tuple = ()) -> None:
        async with self.connection() as conn:
            await conn.execute(sql, params)

    async def executemany(self, sql: str, seq_of_params: list[tuple]) -> None:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(sql, seq_of_params)

    async def fetch(self, sql: str, params: tuple = ()) -> list[dict]:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                if cur.description is None:
                    return []
                cols = [c.name for c in cur.description]
                rows = await cur.fetchall()
                return [dict(zip(cols, row)) for row in rows]

    async def fetchrow(self, sql: str, params: tuple = ()) -> Optional[dict]:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                if cur.description is None:
                    return None
                row = await cur.fetchone()
                if row is None:
                    return None
                cols = [c.name for c in cur.description]
                return dict(zip(cols, row))

    async def fetchval(self, sql: str, params: tuple = ()) -> object:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                row = await cur.fetchone()
                return row[0] if row else None


_default_pool: Optional[DatabasePool] = None


def get_default_pool() -> DatabasePool:
    """Return the module-level singleton pool (does not open it)."""
    global _default_pool
    if _default_pool is None:
        _default_pool = DatabasePool(DatabaseConfig.from_env())
    return _default_pool


async def reset_default_pool() -> None:
    """Close and clear the singleton. Used by tests and config reloads."""
    global _default_pool
    if _default_pool is not None:
        await _default_pool.close()
        _default_pool = None


__all__ = [
    "DatabaseConfig",
    "DatabasePool",
    "get_default_pool",
    "reset_default_pool",
]
