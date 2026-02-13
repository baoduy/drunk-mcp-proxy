"""Middleware registry for MCP proxy server."""

from __future__ import annotations

from starlette.middleware import Middleware

from .cros_middleware import build_cors_middleware


def build_middleware() -> list[Middleware]:
    middleware: list[Middleware] = []
    middleware.extend(build_cors_middleware())
    return middleware


__all__ = ["build_middleware"]
