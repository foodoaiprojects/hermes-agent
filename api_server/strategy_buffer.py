"""In-process buffer linking a content-strategy job to its submit_strategy call.

When the background worker starts a strategy job, it registers the job's
session_id here. The content-strategy plugin's submit_strategy handler
(which runs inside the same process during the hermes agent loop) calls
submit() to stash the structured output. The worker then pops it after the
hermes turn completes.

Scope: per-process. Fine because the worker and the agent loop run in the
same Python process — the worker just awaits the blocking agent call on a
thread.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

_lock = threading.Lock()
_slots: dict[str, Any] = {}
_registered: set[str] = set()


def register(session_id: str) -> None:
    """Mark that a job is about to accept a submit_strategy call."""
    with _lock:
        _registered.add(session_id)
        _slots.pop(session_id, None)


def submit(session_id: str, payload: dict) -> bool:
    """Store the plugin's structured output. Returns False if not registered."""
    with _lock:
        if session_id not in _registered:
            return False
        _slots[session_id] = payload
        return True


def pop(session_id: str) -> Optional[dict]:
    """Retrieve and remove the stored output, if any."""
    with _lock:
        return _slots.pop(session_id, None)


def clear(session_id: str) -> None:
    """Discard any state for a session (cleanup on error)."""
    with _lock:
        _slots.pop(session_id, None)
        _registered.discard(session_id)
