"""
Middleware registry for MCP proxy server.

This module aggregates all middleware components and provides a unified
interface for building the middleware stack.

Current Middleware:
    - CORS: Cross-Origin Resource Sharing for web clients

Future Middleware:
    - Rate limiting
    - Request logging
    - Authentication
    - Compression
"""

from __future__ import annotations

from starlette.middleware import Middleware

from .cros_middleware import build_cors_middleware


def build_middleware() -> list[Middleware]:
    """
    Build the complete middleware stack for the MCP server.

    Collects all enabled middleware components and returns them as a list.
    The order matters - middleware is applied in the order it appears in the list.

    Middleware Flow (Request):
        Client → CORS → [Future Middleware] → MCP Server

    Middleware Flow (Response):
        MCP Server → [Future Middleware] → CORS → Client

    Current Middleware:
        1. CORS: Enabled if FASTMCP_CORS_ALLOW_ORIGINS is set

    Returns:
        List of configured Starlette middleware instances

    Example:
        middleware = build_middleware()
        await run_server_async(mcp_server, host, port, transport, middleware)
    """
    middleware: list[Middleware] = []

    # Add CORS middleware if configured
    middleware.extend(build_cors_middleware())

    # Future middleware can be added here:
    # middleware.extend(build_rate_limit_middleware())
    # middleware.extend(build_logging_middleware())

    return middleware


__all__ = ["build_middleware"]
