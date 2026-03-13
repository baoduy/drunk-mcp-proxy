"""Middleware assembly for the MCP proxy server.

This module provides the :class:`MiddlewareProvider` class that builds all
configured Starlette middlewares from environment variables.
"""

from __future__ import annotations

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from drunk_ai_proxy.middleware.auth_header import AuthHeaderMiddleware
from drunk_ai_proxy.middleware.rate_limit import RateLimitMiddleware
from drunk_ai_proxy.middleware.security_headers import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from drunk_ai_proxy.utils.env import (
    AUTH_ENABLED,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_ORIGINS,
    CORS_EXPOSE_HEADERS,
    CORS_MAX_AGE,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)

from fastmcp.utilities import logging

logger = logging.get_logger(__name__)


class MiddlewareProvider:
    """Assembles and returns all configured Starlette middlewares.

    Reads CORS, auth, rate-limit, and security-header configuration from
    environment variables and produces the corresponding middleware list.
    """

    def __init__(self, cache: object) -> None:
        """Initialize with the application cache store.

        Args:
            cache: Shared TTL key-value cache used by :class:`RateLimitMiddleware`.
        """
        self._cache = cache

    @staticmethod
    def _parse_csv(value: str) -> list[str]:
        """Split a comma-separated string into a stripped list of non-empty items.

        Args:
            value: Comma-separated string.

        Returns:
            List of stripped, non-empty items.
        """
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _create_cors_middleware(self) -> Middleware:
        """Build the CORS middleware from environment configuration."""
        origins = self._parse_csv(CORS_ALLOW_ORIGINS) if CORS_ALLOW_ORIGINS else ["*"]
        methods = self._parse_csv(CORS_ALLOW_METHODS) or ["*"]
        headers = self._parse_csv(CORS_ALLOW_HEADERS) or ["*"]
        expose_headers = self._parse_csv(CORS_EXPOSE_HEADERS)

        return Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=methods,
            allow_headers=headers,
            allow_credentials=bool(CORS_ALLOW_CREDENTIALS),
            max_age=CORS_MAX_AGE,
            expose_headers=expose_headers,
        )

    def _create_auth_header_middleware(self) -> Middleware:
        """Build the Authorization-header validation middleware."""
        return Middleware(AuthHeaderMiddleware)

    def _create_rate_limit_middleware(self) -> Middleware:
        """Build the fixed-window rate-limit middleware.

        Raises:
            ValueError: If rate-limit env vars are non-positive.
        """
        if RATE_LIMIT_REQUESTS <= 0 or RATE_LIMIT_WINDOW_SECONDS <= 0:
            raise ValueError(
                "RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW_SECONDS must be greater than 0 "
                "when RATE_LIMIT_ENABLED=true"
            )
        return Middleware(
            RateLimitMiddleware,
            cache=self._cache,
            max_requests=RATE_LIMIT_REQUESTS,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )

    def _create_request_size_limit_middleware(self) -> Middleware:
        """Build the request-body size-limit middleware."""
        return Middleware(RequestSizeLimitMiddleware)

    def _create_security_headers_middleware(self) -> Middleware:
        """Build the security-headers middleware."""
        return Middleware(SecurityHeadersMiddleware)

    def build(self) -> list[Middleware]:
        """Assemble and return the configured middleware list.

        Returns:
            A list of Starlette :class:`Middleware` instances in application order.
        """
        middlewares: list[Middleware] = [
            self._create_cors_middleware(),
            self._create_request_size_limit_middleware(),
            self._create_security_headers_middleware(),
        ]
        if AUTH_ENABLED:
            middlewares.append(self._create_auth_header_middleware())
        if RATE_LIMIT_ENABLED:
            middlewares.append(self._create_rate_limit_middleware())

        return middlewares


def _parse_csv(value: str | None) -> list[str]:
    """Backwards-compatible CSV parser helper."""
    return MiddlewareProvider._parse_csv(value or "")


def _create_cors_middleware() -> Middleware:
    """Backwards-compatible CORS middleware builder."""
    origins = _parse_csv(CORS_ALLOW_ORIGINS) if CORS_ALLOW_ORIGINS else ["*"]
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
    """Backwards-compatible auth-header middleware builder."""
    return Middleware(AuthHeaderMiddleware)


def _create_rate_limit_middleware(cache: object | None = None) -> Middleware:
    """Backwards-compatible rate-limit middleware builder."""
    if RATE_LIMIT_REQUESTS <= 0 or RATE_LIMIT_WINDOW_SECONDS <= 0:
        raise ValueError(
            "RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW_SECONDS must be greater than 0 "
            "when RATE_LIMIT_ENABLED=true"
        )
    cache_store = cache if cache is not None else CacheProvider.get_cache_store()
    return Middleware(
        RateLimitMiddleware,
        cache=cache_store,
        max_requests=RATE_LIMIT_REQUESTS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )


def _create_request_size_limit_middleware() -> Middleware:
    """Backwards-compatible request-size middleware builder."""
    return Middleware(RequestSizeLimitMiddleware)


def _create_security_headers_middleware() -> Middleware:
    """Backwards-compatible security-headers middleware builder."""
    return Middleware(SecurityHeadersMiddleware)


def get_middlewares() -> list[Middleware]:
    """Build and return the application middleware list.

    This is a backwards-compatible shim that instantiates
    :class:`MiddlewareProvider` with the shared cache store.

    Returns:
        A list of Starlette :class:`Middleware` instances.
    """
    from drunk_ai_proxy.app.cache_provider import CacheProvider

    cache = CacheProvider.get_cache_store()
    middlewares: list[Middleware] = [
        _create_cors_middleware(),
        _create_request_size_limit_middleware(),
        _create_security_headers_middleware(),
    ]
    if AUTH_ENABLED:
        middlewares.append(_create_auth_header_middleware())
    if RATE_LIMIT_ENABLED:
        middlewares.append(_create_rate_limit_middleware(cache))
    return middlewares