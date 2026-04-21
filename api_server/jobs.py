"""Postgres-backed job queue for async endpoints.

Table: hermes.api_jobs (created by api_server.db on startup).

Workers claim queued jobs atomically with FOR UPDATE SKIP LOCKED so that
multiple FastAPI replicas can share the queue without duplicating work.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from .db import get_pool

logger = logging.getLogger(__name__)


async def create_job(endpoint: str, user_id: str, input: dict) -> str:
    """Insert a new queued job, return its UUID as a string."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO hermes.api_jobs (endpoint, user_id, input)
            VALUES ($1, $2, $3::jsonb)
            RETURNING id
            """,
            endpoint,
            user_id,
            json.dumps(input),
        )
        return str(row["id"])


def _row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    d["id"] = str(d["id"])
    for key in ("input", "result"):
        v = d.get(key)
        if isinstance(v, str):
            try:
                d[key] = json.loads(v)
            except json.JSONDecodeError:
                pass
    return d


async def get_job(job_id: str) -> Optional[dict]:
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, endpoint, user_id, status, result, error,
                   created_at, started_at, finished_at
            FROM   hermes.api_jobs
            WHERE  id = $1
            """,
            uid,
        )
    return _row_to_dict(row) if row else None


async def claim_job() -> Optional[dict]:
    """Atomically claim the oldest queued job.

    Returns dict with {id, endpoint, user_id, input} on success, None when
    the queue is empty. Uses SKIP LOCKED so racing workers never block.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT id, endpoint, user_id, input
                FROM   hermes.api_jobs
                WHERE  status = 'queued'
                ORDER  BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT  1
                """
            )
            if row is None:
                return None
            await conn.execute(
                "UPDATE hermes.api_jobs "
                "SET    status = 'running', started_at = now() "
                "WHERE  id = $1",
                row["id"],
            )
    return _row_to_dict(row)


async def finish_job(job_id: str, result: dict) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE hermes.api_jobs
            SET    status = 'done',
                   result = $2::jsonb,
                   finished_at = now()
            WHERE  id = $1
            """,
            uuid.UUID(job_id),
            json.dumps(result),
        )


async def fail_job(job_id: str, error: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE hermes.api_jobs
            SET    status = 'failed',
                   error  = $2,
                   finished_at = now()
            WHERE  id = $1
            """,
            uuid.UUID(job_id),
            (error or "")[:4000],
        )
