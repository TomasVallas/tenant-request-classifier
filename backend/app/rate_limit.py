"""Small in-memory per-IP rate limit for the public demo."""

import time
from collections import deque
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

RATE_LIMIT_MESSAGE = "Liian monta pyyntöä. Yritä hetken kuluttua uudelleen."


class SlidingWindowRateLimiter:
    """Allows `limit` requests per key within a sliding time window."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._last_purge = clock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        cutoff = now - self._window
        self._purge_inactive_keys(now, cutoff)

        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True

    @property
    def tracked_keys(self) -> int:
        return len(self._hits)

    def _purge_inactive_keys(self, now: float, cutoff: float) -> None:
        """Keep memory bounded by the number of clients seen within one window."""
        if now - self._last_purge < self._window:
            return
        self._hits = {key: hits for key, hits in self._hits.items() if hits and hits[-1] > cutoff}
        self._last_purge = now


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, limiter: SlidingWindowRateLimiter, path: str) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._path = path

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "POST" and request.url.path == self._path:
            client_ip = request.client.host if request.client else "unknown"
            if not self._limiter.allow(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": RATE_LIMIT_MESSAGE},
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)
