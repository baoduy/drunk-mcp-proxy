import asyncio
import math
import time

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.cache_provider import CacheProvider, TTLAsyncKeyValue

from tools.env import (
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_CREDENTIALS,
    CORS_MAX_AGE,
    CORS_EXPOSE_HEADERS,
    AUTH_ENABLED,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)

class AuthHeaderMiddleware(BaseHTTPMiddleware):
    """Middleware to validate that Authorization header is not empty when AUTH_ENABLED is true."""
    
    async def dispatch(self, request: Request, call_next):
        authorization = request.headers.get("authorization", "").strip()
        if not authorization:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or empty Authorization header"},
            )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter based on client IP address."""

    def __init__(self, app, cache: TTLAsyncKeyValue, max_requests: int, window_seconds: int) -> None:
        super().__init__(app)
        self._cache = cache
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._enabled = max_requests > 0 and window_seconds > 0
        self._lock = asyncio.Lock()
        self._key_prefix = "RATELIMIT_"

    async def dispatch(self, request: Request, call_next):
        if not self._enabled:
            return await call_next(request)

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

def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _create_cros_middleware() -> Middleware:
    # Parse allowed origins from environment
    origins = _parse_csv(CORS_ALLOW_ORIGINS) if CORS_ALLOW_ORIGINS else ['*']  # Default: allow all origins

    # Parse other CORS settings, with sensible defaults
    methods = _parse_csv(CORS_ALLOW_METHODS) or ["*"]  # Default: allow all methods
    headers = _parse_csv(CORS_ALLOW_HEADERS) or ["*"]  # Default: allow all headers
    expose_headers = _parse_csv(CORS_EXPOSE_HEADERS)  # Only expose if specified

    # Build and return CORS middleware
    return Middleware(
            CORSMiddleware,
            allow_origins=origins,  # Which origins can access
            allow_methods=methods,  # Which HTTP methods are allowed
            allow_headers=headers,  # Which request headers are allowed
            allow_credentials=bool(CORS_ALLOW_CREDENTIALS),
            max_age=CORS_MAX_AGE,
            expose_headers=expose_headers,  # Which response headers to expose
        )

def _create_auth_header_middleware() -> Middleware:
    """Create middleware to validate Authorization header when AUTH_ENABLED is true."""
    return Middleware(AuthHeaderMiddleware)


def _create_rate_limit_middleware() -> Middleware:
    """Create middleware to enforce a fixed-window rate limit by client IP."""
    return Middleware(
        RateLimitMiddleware,
        cache=CacheProvider.get_cache_store(),
        max_requests=RATE_LIMIT_REQUESTS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )
    
def get_middlewares() -> list[Middleware]:
    """Get the list of middlewares to apply to the FastMCP server.

    Returns:
        A list of Starlette Middleware instances.
    """

    list = [
        _create_cros_middleware(),
    ]
    if AUTH_ENABLED:
        list.append(_create_auth_header_middleware())
    if RATE_LIMIT_ENABLED:
        list.append(_create_rate_limit_middleware())

    return list