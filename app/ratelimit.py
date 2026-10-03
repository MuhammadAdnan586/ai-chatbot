"""A tiny sliding-window rate limiter, used as a FastAPI dependency.

Limitation: state is in process memory, so it is per-instance. With several
server instances you would move this to Redis (or use a gateway / proxy limit).
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import settings

WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = defaultdict(deque)


def reset() -> None:
    _hits.clear()


def check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _hits[ip]
    while window and now - window[0] > WINDOW_SECONDS:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )
    window.append(now)