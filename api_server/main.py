"""FastAPI app — entrypoint for the hermes-api container.

Run:
    uvicorn api_server.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
import requests
from contextlib import asynccontextmanager
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

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
    type: Literal["IMAGE", "VIDEO", "STORY"] = "IMAGE"
    reference_images: list[str] = Field(default_factory=list, max_length=8)
    mask_image: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: Any) -> str:
        if value is None:
            return "IMAGE"
        if isinstance(value, str):
            return value.strip().upper()
        return value


class ImproveResponse(BaseModel):
    improved_prompt: str
    session_id: str
    latency_ms: int
    agentic_canvas_plan: Optional[dict] = None


class StartImageWorkflowRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1, max_length=4000)
    type: Literal["IMAGE", "VIDEO", "STORY"] = "IMAGE"
    reference_images: list[str] = Field(default_factory=list, max_length=8)
    mask_image: Optional[str] = Field(default=None, max_length=2000)
    ai_model: str = Field(..., min_length=1, max_length=300)
    webhook_url: str = Field(..., min_length=1, max_length=2000)
    record_id: str = Field(..., min_length=1, max_length=200)
    aspect_ratio: Optional[str] = Field(default=None, max_length=20)


class StartImageWorkflowResponse(BaseModel):
    improved_prompt: str
    prediction_id: Optional[str] = None
    session_id: str
    latency_ms: int


class PostImageCanvasRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1, max_length=4000)
    improved_prompt: str = Field(..., min_length=1, max_length=6000)
    image_url: str = Field(..., min_length=1, max_length=4000)
    reference_images: list[str] = Field(default_factory=list, max_length=12)
    aspect_ratio: Optional[str] = Field(default=None, max_length=20)


class PostImageCanvasResponse(BaseModel):
    session_id: str
    latency_ms: int
    agentic_canvas_plan: dict


def _extract_json_object(raw_text: str) -> Optional[dict]:
    text = (raw_text or "").strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    return None


def _default_canvas_plan(improved_prompt: str) -> dict:
    return {
        "workflow_version": "v2",
        "planner": {
            "image_generation_prompt": improved_prompt,
            "content_copy": [
                {"id": "headline", "role": "headline", "text": "Chef Special"},
                {"id": "subheadline", "role": "subheadline", "text": "Freshly made today"},
                {"id": "cta", "role": "cta", "text": "Book Now"},
            ],
            "reference_images": [],
            "selected_logos": [],
            "placement_intent": {
                "logo_slot": "top-left",
                "headline_slot": "bottom-middle",
                "info_slot": "middle-top",
                "cta_slot": "center-below",
                "hero_slot": "center",
            },
            "text_style_intent": {
                "tone": "warm",
                "color_intent": "high-contrast-light",
            },
            "canvas": {"width": 1170, "height": 1456, "background": "#f5f3ec"},
        },
    }


def _normalize_placement_intent(raw: Any) -> dict:
    allowed = {
        "logo_slot": {"top-right", "bottom-right", "top-left", "bottom-left", "none"},
        "headline_slot": {"bottom-middle", "middle-top", "none"},
        "info_slot": {"bottom-middle", "middle-top", "none"},
        "cta_slot": {"center-below", "bottom-middle", "none"},
        "hero_slot": {"center"},
    }
    defaults = {
        "logo_slot": "top-left",
        "headline_slot": "bottom-middle",
        "info_slot": "middle-top",
        "cta_slot": "center-below",
        "hero_slot": "center",
    }
    payload = raw if isinstance(raw, dict) else {}
    out: dict[str, str] = {}
    for key, values in allowed.items():
        val = str(payload.get(key) or "").strip().lower()
        out[key] = val if val in values else defaults[key]
    return out


def _normalize_text_style_intent(raw: Any) -> dict:
    tone_values = {"warm", "bold", "minimal", "luxe"}
    color_values = {
        "high-contrast-light",
        "high-contrast-dark",
        "complementary-pop",
        "analogous-soft",
    }
    payload = raw if isinstance(raw, dict) else {}
    tone = str(payload.get("tone") or "").strip().lower()
    color_intent = str(payload.get("color_intent") or "").strip().lower()
    return {
        "tone": tone if tone in tone_values else "warm",
        "color_intent": color_intent if color_intent in color_values else "high-contrast-light",
    }


def _is_version_hash(model_or_version: str) -> bool:
    return "/" not in model_or_version and all(
        c in "0123456789abcdef" for c in model_or_version.lower()
    )


def _predict_path(model_or_version: str) -> tuple[str, dict]:
    if _is_version_hash(model_or_version):
        return "/v1/predictions", {"version": model_or_version}
    if ":" in model_or_version:
        sha = model_or_version.split(":", 1)[1]
        return "/v1/predictions", {"version": sha}
    owner, name = model_or_version.split("/", 1)
    return f"/v1/models/{owner}/{name}/predictions", {}


def _submit_replicate_prediction(
    *,
    model_or_version: str,
    replicate_input: dict,
    webhook_url: str,
) -> str:
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not set")

    path, extra = _predict_path(model_or_version)
    base = os.environ.get("REPLICATE_BASE_URL", "https://api.replicate.com")
    body = {
        **extra,
        "input": replicate_input,
        "webhook": webhook_url,
        "webhook_events_filter": ["start", "completed"],
    }
    resp = requests.post(
        f"{base.rstrip('/')}{path}",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    pred_id = data.get("id")
    if not pred_id:
        raise RuntimeError("Replicate response missing prediction id")
    return pred_id


def _sanitize_improved_prompt(raw: str, fallback: str) -> str:
    text = (raw or "").strip()
    if not text:
        return fallback.strip()

    lowered = text.lower()
    blocked_patterns = [
        "skill_view(",
        "pg_tables(",
        "pg_query(",
        "s3_list_objects(",
        "s3_head_object(",
        "vision_analyze(",
        "tool call",
    ]
    if any(p in lowered for p in blocked_patterns):
        return fallback.strip()

    # Reject obvious JSON/tool payloads mistakenly returned as final prompt.
    if text.startswith("{") or text.startswith("["):
        return fallback.strip()

    return text


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
    skill_by_type = {
        "IMAGE": "ai-image-generation",
        "VIDEO": "ai-video-generation",
        "STORY": "ai-image-generation",
    }
    reference_images_text = (
        "\n".join(f"- {url}" for url in body.reference_images)
        if body.reference_images
        else "- none"
    )
    mask_image_text = body.mask_image or "none"
    system_prompt = prompts.IMPROVE_PROMPT_SYSTEM.format(
        user_id=body.user_id,
        content_type=body.type,
        selected_skill=skill_by_type[body.type],
        reference_images=reference_images_text,
        mask_image=mask_image_text,
    )
    t0 = time.time()
    try:
        result = await run_agent_turn(
            session_id=session_id,
            user_id=body.user_id,
            user_message=body.prompt,
            system_prompt=system_prompt,
            model=os.environ.get("HERMES_MODEL_IMPROVE"),
            max_iterations=int(os.environ.get("HERMES_IMPROVE_MAX_ITERATIONS", "15")),
        )
    except Exception as e:
        logger.exception("improve_prompt failed for user_id=%s", body.user_id)
        raise HTTPException(status_code=500, detail=f"agent error: {e}")

    final_raw = (result.get("final_response") or "").strip()
    final = _sanitize_improved_prompt(final_raw, body.prompt)
    if not final:
        logger.warning(
            "improve_prompt empty response for user_id=%s; returning raw prompt fallback",
            body.user_id,
        )
        final = body.prompt.strip()

    return ImproveResponse(
        improved_prompt=final,
        session_id=session_id,
        latency_ms=int((time.time() - t0) * 1000),
        agentic_canvas_plan=None,
    )


@app.post("/v1/image-workflow/start", response_model=StartImageWorkflowResponse)
async def start_image_workflow(body: StartImageWorkflowRequest):
    session_id = f"api:image-start:{body.user_id}:{body.record_id}"
    reference_images_text = (
        "\n".join(f"- {url}" for url in body.reference_images)
        if body.reference_images
        else "- none"
    )
    mask_image_text = body.mask_image or "none"

    system_prompt = prompts.IMPROVE_PROMPT_SYSTEM.format(
        user_id=body.user_id,
        content_type=body.type,
        selected_skill="ai-image-generation",
        reference_images=reference_images_text,
        mask_image=mask_image_text,
    )
    t0 = time.time()

    try:
        result = await run_agent_turn(
            session_id=session_id,
            user_id=body.user_id,
            user_message=body.prompt,
            system_prompt=system_prompt,
            model=os.environ.get("HERMES_MODEL_IMPROVE"),
            max_iterations=int(os.environ.get("HERMES_IMPROVE_MAX_ITERATIONS", "15")),
        )
    except Exception as e:
        logger.exception("start_image_workflow improve failed for user_id=%s", body.user_id)
        raise HTTPException(status_code=500, detail=f"agent error: {e}")

    improved_raw = (result.get("final_response") or "").strip()
    improved_prompt = _sanitize_improved_prompt(improved_raw, body.prompt)

    replicate_input: dict[str, Any] = {
        "prompt": improved_prompt,
    }
    if body.aspect_ratio:
        replicate_input["aspect_ratio"] = body.aspect_ratio
    if body.reference_images:
        replicate_input["image_input"] = body.reference_images[:8]
    if body.mask_image:
        replicate_input["mask_image"] = body.mask_image

    prediction_id: Optional[str] = None
    try:
        prediction_id = _submit_replicate_prediction(
            model_or_version=body.ai_model,
            replicate_input=replicate_input,
            webhook_url=body.webhook_url,
        )
    except Exception as e:
        # Graceful fallback: consumer will submit locally when prediction_id is missing.
        logger.warning(
            "start_image_workflow replicate submit unavailable for user_id=%s: %s",
            body.user_id,
            e,
        )

    return StartImageWorkflowResponse(
        improved_prompt=improved_prompt,
        prediction_id=prediction_id,
        session_id=session_id,
        latency_ms=int((time.time() - t0) * 1000),
    )


@app.post("/v1/canvas/post-image-plan", response_model=PostImageCanvasResponse)
async def post_image_canvas_plan(body: PostImageCanvasRequest):
    t0 = time.time()
    session_id = f"api:canvas-post-image:{body.user_id}"

    reference_images_text = (
        "\n".join(f"- {url}" for url in body.reference_images)
        if body.reference_images
        else "- none"
    )

    planner_session_id = f"{session_id}:planner"

    try:
        planner_prompt = prompts.CANVAS_PLANNER_SYSTEM.format(
            user_id=body.user_id,
            content_type="IMAGE",
            selected_skill="ai-image-generation",
            reference_images=reference_images_text,
            generated_image_url=body.image_url,
            aspect_ratio=body.aspect_ratio or "unknown",
        )
        planner_result = await run_agent_turn(
            session_id=planner_session_id,
            user_id=body.user_id,
            user_message=f"User prompt: {body.prompt}\n\nImproved prompt: {body.improved_prompt}\n\nGenerated image URL: {body.image_url}",
            system_prompt=planner_prompt,
            model=os.environ.get("HERMES_MODEL_IMPROVE"),
            max_iterations=int(os.environ.get("HERMES_IMPROVE_MAX_ITERATIONS", "15")),
        )
        planner = _extract_json_object(planner_result.get("final_response") or "")
        if not planner:
            planner = _default_canvas_plan(body.improved_prompt)["planner"]

        planner["placement_intent"] = _normalize_placement_intent(
            planner.get("placement_intent")
        )
        planner["text_style_intent"] = _normalize_text_style_intent(
            planner.get("text_style_intent")
        )

        plan = {
            "workflow_version": "v2",
            "planner": planner,
        }
    except Exception:
        logger.exception("post_image_canvas_plan failed user_id=%s", body.user_id)
        plan = _default_canvas_plan(body.improved_prompt)

    return PostImageCanvasResponse(
        session_id=session_id,
        latency_ms=int((time.time() - t0) * 1000),
        agentic_canvas_plan=plan,
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
