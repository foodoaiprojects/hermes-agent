"""FastAPI app — entrypoint for the hermes-api container.

Run:
    uvicorn api_server.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import db, jobs, prompts, strategy_buffer
from .agent_runner import run_agent_turn

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("hermes.api")


_worker_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB pool + schema bootstrap
    await db.get_pool()
    # Background worker for async jobs
    global _worker_task
    _worker_task = asyncio.create_task(_job_worker_loop(), name="job-worker")
    logger.info("hermes-api: ready")
    try:
        yield
    finally:
        if _worker_task is not None:
            _worker_task.cancel()
            try:
                await _worker_task
            except (asyncio.CancelledError, Exception):
                pass
        await db.close_pool()
        logger.info("hermes-api: stopped")


app = FastAPI(title="hermes-api", version="0.1.0", lifespan=lifespan)


# ─── Request / response schemas ────────────────────────────────────────────


class ImproveRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1, max_length=4000)


class ImproveResponse(BaseModel):
    improved_prompt: str
    session_id: str
    latency_ms: int


class StrategyRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=200)
    user_requirement: str = Field(..., min_length=1, max_length=4000)


class JobAccepted(BaseModel):
    job_id: str
    status: str = "queued"


class JobStatus(BaseModel):
    id: str
    endpoint: str
    user_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Any = None
    started_at: Any = None
    finished_at: Any = None


# ─── Routes ────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"ok": True}


@app.post("/v1/prompts/improve", response_model=ImproveResponse)
async def improve_prompt(body: ImproveRequest):
    session_id = f"api:improve:{body.user_id}"
    system_prompt = prompts.IMPROVE_PROMPT_SYSTEM.format(user_id=body.user_id)
    t0 = time.time()
    try:
        result = await run_agent_turn(
            session_id=session_id,
            user_id=body.user_id,
            user_message=body.prompt,
            system_prompt=system_prompt,
            model=os.environ.get("HERMES_MODEL_IMPROVE"),
        )
    except Exception as e:
        logger.exception("improve_prompt failed for user_id=%s", body.user_id)
        raise HTTPException(status_code=500, detail=f"agent error: {e}")

    final = (result.get("final_response") or "").strip()
    if not final:
        raise HTTPException(status_code=502, detail="agent returned an empty response")

    return ImproveResponse(
        improved_prompt=final,
        session_id=session_id,
        latency_ms=int((time.time() - t0) * 1000),
    )


@app.post("/v1/content-strategy", response_model=JobAccepted, status_code=202)
async def start_strategy(body: StrategyRequest):
    job_id = await jobs.create_job(
        endpoint="content_strategy",
        user_id=body.user_id,
        input={"user_requirement": body.user_requirement},
    )
    return JobAccepted(job_id=job_id)


@app.get("/v1/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    try:
        job = await jobs.get_job(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid job_id")
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatus(**job)


# ─── Background job worker ─────────────────────────────────────────────────


async def _job_worker_loop(poll_interval: float = 2.0) -> None:
    worker_id = str(uuid.uuid4())[:8]
    logger.info("job-worker %s: started", worker_id)
    while True:
        try:
            job = await jobs.claim_job()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("job-worker %s: claim_job failed", worker_id)
            await asyncio.sleep(poll_interval)
            continue

        if job is None:
            try:
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                raise
            continue

        try:
            await _handle_job(job)
        except asyncio.CancelledError:
            # Job was mid-flight when shutdown hit — best-effort mark failed.
            try:
                await jobs.fail_job(job["id"], "worker cancelled mid-run")
            finally:
                raise
        except Exception as e:
            logger.exception("job-worker %s: job %s crashed", worker_id, job.get("id"))
            try:
                await jobs.fail_job(job["id"], f"unhandled error: {e}")
            except Exception:
                logger.exception("fail_job itself failed")


async def _handle_job(job: dict) -> None:
    endpoint = job.get("endpoint")
    if endpoint == "content_strategy":
        await _handle_strategy_job(job)
    else:
        await jobs.fail_job(job["id"], f"unknown endpoint: {endpoint!r}")


async def _handle_strategy_job(job: dict) -> None:
    job_id = job["id"]
    user_id = job["user_id"]
    user_requirement = (job.get("input") or {}).get("user_requirement", "")
    # Per-job session_id so submit_strategy can't be confused between jobs.
    session_id = f"api:strategy:{user_id}:{job_id}"
    system_prompt = prompts.CONTENT_STRATEGY_SYSTEM.format(
        user_id=user_id,
        session_id=session_id,
        job_id=job_id,
    )

    strategy_buffer.register(session_id)
    try:
        await run_agent_turn(
            session_id=session_id,
            user_id=user_id,
            user_message=user_requirement,
            system_prompt=system_prompt,
            model=os.environ.get("HERMES_MODEL_STRATEGY"),
            max_iterations=int(os.environ.get("HERMES_STRATEGY_MAX_ITERATIONS", "30")),
        )
        submitted = strategy_buffer.pop(session_id)
        if submitted is None:
            await jobs.fail_job(
                job_id,
                "agent did not call submit_strategy — output contract violated",
            )
            return
        await jobs.finish_job(job_id, submitted)
    finally:
        strategy_buffer.clear(session_id)
