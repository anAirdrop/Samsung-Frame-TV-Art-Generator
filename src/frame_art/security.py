"""Authentication and request-rate controls for public API routes."""

from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Header, HTTPException, status

from .config import (
    ConfigurationError,
    Settings,
    load_settings,
    validate_runtime_settings,
)


def require_api_token(
    authorization: Annotated[str | None, Header()] = None,
) -> Settings:
    """Validate a bearer token and return the current settings."""
    settings = load_settings()
    try:
        validate_runtime_settings(settings)
    except ConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Frame Art setup is incomplete",
        ) from error

    scheme, separator, token = (authorization or "").partition(" ")
    valid = (
        separator == " "
        and scheme.lower() == "bearer"
        and hmac.compare_digest(token, settings.webhook_api_key)
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return settings


class RateLimiter:
    """Thread-safe fixed-window limiter for generation requests."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, identity: str, limit_per_hour: int) -> None:
        now = time.monotonic()
        cutoff = now - 3600.0
        with self._lock:
            events = self._events[identity]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= limit_per_hour:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Generation rate limit reached; try again later",
                )
            events.append(now)
