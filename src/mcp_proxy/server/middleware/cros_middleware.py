"""CORS middleware setup."""

from __future__ import annotations

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from ...tools.env import (
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    CORS_EXPOSE_HEADERS,
)


def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_cors_middleware() -> list[Middleware]:
    origins = _parse_csv(CORS_ALLOW_ORIGINS)
    if not origins:
        return []

    methods = _parse_csv(CORS_ALLOW_METHODS) or ["*"]
    headers = _parse_csv(CORS_ALLOW_HEADERS) or ["*"]
    expose_headers = _parse_csv(CORS_EXPOSE_HEADERS)

    return [
        Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=methods,
            allow_headers=headers,
            expose_headers=expose_headers,
        )
    ]
