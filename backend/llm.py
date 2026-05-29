"""Process-level circuit breaker for OpenAI availability.

When an OpenAI call fails in a way that will not fix itself on the next request
(quota exhausted, invalid key, rate limited), we "trip" the breaker so subsequent
requests skip OpenAI and use the local RAG / rule-based path immediately, instead
of repeatedly paying the latency of failing API calls. The breaker auto-resets
after a cooldown so genuinely transient issues can recover.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 300.0


class OpenAICircuit:
    def __init__(self, cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS) -> None:
        self._cooldown = cooldown_seconds
        self._disabled_until = 0.0
        self._reason = ""
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        with self._lock:
            return time.monotonic() >= self._disabled_until

    def trip(self, reason: str) -> None:
        with self._lock:
            self._disabled_until = time.monotonic() + self._cooldown
            self._reason = reason
        logger.warning(
            "OpenAI disabled for %.0fs; using local fallback. Reason: %s",
            self._cooldown,
            reason,
        )

    def reset(self) -> None:
        with self._lock:
            self._disabled_until = 0.0
            self._reason = ""

    def status(self) -> dict[str, object]:
        with self._lock:
            remaining = max(0.0, self._disabled_until - time.monotonic())
            reason = self._reason
        return {
            "available": remaining == 0.0,
            "cooldown_remaining_s": round(remaining, 1),
            "last_reason": reason,
        }


_circuit = OpenAICircuit()


def get_circuit() -> OpenAICircuit:
    return _circuit


def is_quota_or_auth_error(exc: BaseException) -> bool:
    """True for OpenAI errors that mean 'stop trying for a while' (quota/auth/rate)."""
    try:
        from openai import (
            APIStatusError,
            AuthenticationError,
            PermissionDeniedError,
            RateLimitError,
        )
    except Exception:  # openai not installed
        return False

    if isinstance(exc, (RateLimitError, AuthenticationError, PermissionDeniedError)):
        return True
    # Catch insufficient_quota surfaced as a generic status error too.
    if isinstance(exc, APIStatusError):
        code = getattr(exc, "code", None)
        return exc.status_code in (401, 403, 429) or code == "insufficient_quota"
    return False
