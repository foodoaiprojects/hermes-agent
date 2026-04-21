"""Writer-side Postgres pool (asyncpg) + schema bootstrap.

The FastAPI app uses this pool for its own state (job queue, future hermes
session mirror). Credentials come from the shared DB_HOST/PORT/DATABASE +
writer-specific DB_RW_USERNAME/DB_RW_PASSWORD.

The LLM-facing `postgres-reader` plugin maintains a separate (read-only)
connection pool — never mix them.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


_pool: Optional[asyncpg.Pool] = None


_MIGRATION_HINT = (
    "hermes.api_jobs is not reachable. Schema migrations are the operator's "
    "responsibility — the application role does not run DDL. Run "
    "`db_migrations/001_bootstrap.sql` as an admin against this database "
    "once, then restart the service."
)


def _writer_kwargs() -> dict:
    host = os.environ.get("DB_HOST")
    if not host:
        raise RuntimeError("DB_HOST is required for the writer pool")
    user = os.environ.get("DB_RW_USERNAME") or os.environ.get("DB_RW_USER")
    password = os.environ.get("DB_RW_PASSWORD", "")
    if not user:
        raise RuntimeError(
            "DB_RW_USERNAME is required for the writer pool. "
            "This must be a role with INSERT/UPDATE rights on the `hermes` schema."
        )
    port = int(os.environ.get("DB_PORT", "5432"))
    database = (
        os.environ.get("DB_DATABASE")
        or os.environ.get("DB_NAME")
        or "postgres"
    )
    sslmode = os.environ.get("DB_SSLMODE", "require")
    # asyncpg accepts ssl="require" / "prefer" / "disable" / etc.
    ssl = None if sslmode == "disable" else sslmode
    return {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": password,
        "ssl": ssl,
    }


async def get_pool() -> asyncpg.Pool:
    """Return the writer pool, initializing it on first call."""
    global _pool
    if _pool is not None:
        return _pool
    kwargs = _writer_kwargs()
    min_size = int(os.environ.get("HERMES_API_DB_MIN_POOL", "2"))
    max_size = int(os.environ.get("HERMES_API_DB_MAX_POOL", "20"))
    _pool = await asyncpg.create_pool(
        min_size=min_size,
        max_size=max_size,
        command_timeout=30,
        **kwargs,
    )
    # Verify the schema is in place. The app role is data-plane only — it
    # does not and should not run DDL. Migrations live in db_migrations/ and
    # are applied out-of-band (see docs/DEPLOY.md).
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                "SELECT 1 FROM hermes.api_jobs WHERE false"
            )
    except asyncpg.exceptions.UndefinedTableError as e:
        await _pool.close()
        _pool = None
        raise RuntimeError(_MIGRATION_HINT) from e
    except asyncpg.exceptions.InvalidSchemaNameError as e:
        await _pool.close()
        _pool = None
        raise RuntimeError(_MIGRATION_HINT) from e
    logger.info(
        "hermes-api: writer pool ready (min=%d, max=%d) — hermes.api_jobs reachable",
        min_size, max_size,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
