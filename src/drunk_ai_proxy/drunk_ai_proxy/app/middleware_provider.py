from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from drunk_ai_proxy.app.cache_provider import CacheProvider
from drunk_ai_proxy.middleware.auth_header import AuthHeaderMiddleware
from drunk_ai_proxy.middleware.rate_limit import RateLimitMiddleware
from drunk_ai_proxy.middleware.security_headers import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

from drunk_ai_proxy.utils.env import (
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


def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _create_cors_middleware() -> Middleware:
    # Parse allowed origins from environment
    origins = _parse_csv(CORS_ALLOW_ORIGINS) if CORS_ALLOW_ORIGINS else ["*"]

    # Parse other CORS settings, with sensible defaults
    methods = _parse_csv(CORS_ALLOW_METHODS) or ["*"]
    headers = _parse_csv(CORS_ALLOW_HEADERS) or ["*"]
    expose_headers = _parse_csv(CORS_EXPOSE_HEADERS)

    return Middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=methods,
        allow_headers=headers,
        allow_credentials=bool(CORS_ALLOW_CREDENTIALS),
        max_age=CORS_MAX_AGE,
        expose_headers=expose_headers,
    )


def _create_auth_header_middleware() -> Middleware:
    """Create middleware to validate Authorization header when AUTH_ENABLED is true."""
    return Middleware(AuthHeaderMiddleware)


def _create_rate_limit_middleware() -> Middleware:
    """Create middleware to enforce a fixed-window rate limit by client IP."""
    if RATE_LIMIT_REQUESTS <= 0 or RATE_LIMIT_WINDOW_SECONDS <= 0:
        raise ValueError(
            "RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW_SECONDS must be greater than 0 "
            "when RATE_LIMIT_ENABLED=true"
        )
    return Middleware(
        RateLimitMiddleware,
        cache=CacheProvider.get_cache_store(),
        max_requests=RATE_LIMIT_REQUESTS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )


def _create_request_size_limit_middleware() -> Middleware:
    """Create middleware enforcing request size limits."""
    return Middleware(RequestSizeLimitMiddleware)


def _create_security_headers_middleware() -> Middleware:
    """Create middleware that appends standard security headers."""
    return Middleware(SecurityHeadersMiddleware)


def get_middlewares() -> list[Middleware]:
    """Get the list of middlewares to apply to the FastMCP server.

    Returns:
        A list of Starlette Middleware instances.
    """
    middlewares = [
        _create_cors_middleware(),
        _create_request_size_limit_middleware(),
        _create_security_headers_middleware(),
    ]
    if AUTH_ENABLED:
        middlewares.append(_create_auth_header_middleware())
    if RATE_LIMIT_ENABLED:
        middlewares.append(_create_rate_limit_middleware())

    return middlewares