"""Thin wrapper around hermes's AIAgent for one-shot programmatic use.

AIAgent.run_conversation() is synchronous, so we run it on a thread via
asyncio.to_thread to avoid blocking the FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _default_model() -> str:
    return os.environ.get(
        "HERMES_MODEL_DEFAULT",
        "google/gemini-2.5-flash",
    )


def _base_url() -> str:
    return os.environ.get(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1",
    )


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return key


async def run_agent_turn(
    *,
    session_id: str,
    user_id: str,
    user_message: str,
    system_prompt: str,
    model: Optional[str] = None,
    max_iterations: int = 20,
) -> dict[str, Any]:
    """Run one hermes agent turn. Returns the full result dict from
    AIAgent.run_conversation — the caller can pull out `final_response`
    (for the improve endpoint) or rely on a tool-call side-effect (for
    the content-strategy endpoint).
    """
    # Import here so FastAPI startup doesn't pay the cost of pulling in
    # run_agent's heavy dependency graph until the first request.
    from run_agent import AIAgent

    model_slug = model or _default_model()

    def _run() -> dict[str, Any]:
        agent = AIAgent(
            base_url=_base_url(),
            api_key=_api_key(),
            model=model_slug,
            session_id=session_id,
            user_id=user_id,
            max_iterations=max_iterations,
        )
        return agent.run_conversation(
            user_message=user_message,
            system_message=system_prompt,
        )

    return await asyncio.to_thread(_run)
