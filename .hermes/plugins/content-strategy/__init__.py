"""content-strategy plugin — structured output tool for the strategy endpoint.

Registers a single tool, `submit_strategy`, whose JSON schema IS the
output contract for POST /v1/content-strategy. The agent is prompted to
call this exactly once; the handler hands the structured payload back to
the FastAPI worker via api_server.strategy_buffer.

This plugin is harmless outside the FastAPI server — if strategy_buffer
isn't importable (e.g. you're running hermes via the CLI), the handler
returns a clear error so the agent stops trying.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_VALID_TYPES = ("IMAGE", "VIDEO", "STORY")


SUBMIT_STRATEGY_SCHEMA = {
    "name": "submit_strategy",
    "description": (
        "Submit the final content strategy as your answer to the user. "
        "CALL THIS EXACTLY ONCE after you have analyzed feedback, past "
        "engagement, and the user's requirement. After calling it, STOP. "
        "The tool call IS your final response — do not also write prose."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": (
                    "Session ID from the system prompt. Pass it verbatim so "
                    "the API can route this result to the correct job."
                ),
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 50,
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": list(_VALID_TYPES),
                            "description": "Post format.",
                        },
                        "scheduled_at": {
                            "type": "string",
                            "description": (
                                "ISO 8601 UTC timestamp, e.g. "
                                "2026-04-22T09:00:00Z."
                            ),
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One-sentence reason for this slot.",
                        },
                        "prompt": {
                            "type": "string",
                            "description": (
                                "Production-ready generation prompt for this "
                                "piece of content. For IMAGE/VIDEO this is a "
                                "visual prompt ready to hand to an image or "
                                "video model (subject, composition, lighting, "
                                "style, mood). For STORY this is the caption / "
                                "copy text the post should contain. Must be "
                                "personalized using the user's feedback and "
                                "past engagement patterns."
                            ),
                        },
                    },
                    "required": ["type", "scheduled_at", "prompt"],
                },
            },
        },
        "required": ["session_id", "items"],
    },
}


def _validate_item(item: dict) -> tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "item must be an object"
    t = item.get("type")
    if t not in _VALID_TYPES:
        return False, f"type must be one of {_VALID_TYPES}, got {t!r}"
    s = item.get("scheduled_at")
    if not isinstance(s, str):
        return False, "scheduled_at must be a string"
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e:
        return False, f"invalid scheduled_at ({e})"
    prompt = item.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return False, "prompt is required and must be a non-empty string"
    if len(prompt) > 4000:
        return False, f"prompt too long ({len(prompt)} chars, max 4000)"
    return True, ""


def tool_submit_strategy(args: dict, **_kw) -> str:
    session_id = args.get("session_id")
    items = args.get("items")

    if not isinstance(session_id, str) or not session_id:
        return json.dumps({"error": "session_id is required (pass the value from the system prompt)."})
    if not isinstance(items, list) or not items:
        return json.dumps({"error": "items must be a non-empty array."})

    for i, item in enumerate(items):
        ok, err = _validate_item(item)
        if not ok:
            return json.dumps({"error": f"items[{i}]: {err}"})

    # Import late so the plugin also loads cleanly under `hermes` CLI,
    # even when api_server isn't on the sys.path.
    try:
        from api_server.strategy_buffer import submit
    except ImportError:
        return json.dumps({
            "error": (
                "submit_strategy is only usable inside the hermes-api FastAPI "
                "server. The strategy_buffer module isn't importable here."
            )
        })

    accepted = submit(session_id, {"items": items})
    if not accepted:
        return json.dumps({
            "error": (
                f"session_id {session_id!r} is not registered. Pass the exact "
                "session_id from the system prompt."
            )
        })

    return json.dumps({"ok": True, "item_count": len(items)})


def register(ctx) -> None:
    ctx.register_tool(
        name="submit_strategy",
        toolset="content-strategy",
        schema=SUBMIT_STRATEGY_SCHEMA,
        handler=tool_submit_strategy,
        emoji="📅",
    )
    logger.info("content-strategy: registered submit_strategy tool")
