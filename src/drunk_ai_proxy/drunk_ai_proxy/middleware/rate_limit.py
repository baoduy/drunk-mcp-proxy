"""Fixed-window client IP rate limiting middleware."""

from __future__ import annotations

import asyncio
import math
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from drunk_ai_proxy.app.cache_provider import TTLAsyncKeyValue


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter based on client IP address."""

    def __init__(
        self,
        app: ASGIApp,
        cache: TTLAsyncKeyValue,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        super().__init__(app)
        self._cache = cache
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._lock = asyncio.Lock()
        self._key_prefix = "RATELIMIT_"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        client_ip = self._get_client_ip(request)
        now = time.time()
        window_start = int(now // self._window_seconds) * self._window_seconds
        cache_key = f"{self._key_prefix}{client_ip}_{window_start}"

        async with self._lock:
            cached_count = await self._cache.get(cache_key)
            try:
                count = int(cached_count) if cached_count is not None else 0
            except (TypeError, ValueError):
                count = 0

            if count >= self._max_requests:
                retry_after = max(1, math.ceil((window_start + self._window_seconds) - now))
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded. please try again later."},
                    headers={"Retry-After": str(retry_after)},
                )

            await self._cache.set(
                cache_key,
                count + 1,
                ttl_seconds=self._window_seconds,
            )

        return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
            if parts:
                return parts[0]

        if request.client and request.client.host:
            return request.client.host

        return "unknown"
