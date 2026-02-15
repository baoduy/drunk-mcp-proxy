"""
CORS (Cross-Origin Resource Sharing) middleware setup.

This module configures CORS middleware for the MCP proxy server,
enabling web clients from different origins to access the API.

CORS Configuration via Environment Variables:
    FASTMCP_CORS_ALLOW_ORIGINS: Comma-separated list of allowed origins
    FASTMCP_CORS_ALLOW_METHODS: Comma-separated list of allowed HTTP methods
    FASTMCP_CORS_ALLOW_HEADERS: Comma-separated list of allowed headers
    FASTMCP_CORS_EXPOSE_HEADERS: Comma-separated list of headers to expose

Example:
    FASTMCP_CORS_ALLOW_ORIGINS=https://example.com,https://app.example.com
    FASTMCP_CORS_ALLOW_METHODS=GET,POST,OPTIONS
    FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization
    FASTMCP_CORS_EXPOSE_HEADERS=X-Request-ID

Behavior:
    - If FASTMCP_CORS_ALLOW_ORIGINS is empty: CORS is disabled (no middleware)
    - If FASTMCP_CORS_ALLOW_ORIGINS is set: CORS is enabled with specified origins
    - Methods/Headers default to "*" (all allowed) if not specified
"""

from __future__ import annotations

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from tools.env import (
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_CREDENTIALS,
    CORS_MAX_AGE,
    CORS_EXPOSE_HEADERS,
)


# Private Helper Functions
# ========================


def _parse_csv(value: str) -> list[str]:
    """
    Parse comma-separated value string into a list.

    Handles:
    - Empty strings -> empty list
    - Whitespace trimming around each value
    - Empty items are filtered out

    Args:
        value: Comma-separated string

    Returns:
        List of trimmed, non-empty strings

    Examples:
        _parse_csv("a,b,c") -> ["a", "b", "c"]
        _parse_csv("a, b , c") -> ["a", "b", "c"]
        _parse_csv("") -> []
        _parse_csv("a,,b") -> ["a", "b"]
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# Public API Functions
# ====================


def build_cors_middleware() -> list[Middleware]:
    """
    Build CORS middleware from environment configuration.

    Constructs a Starlette CORS middleware instance if CORS is enabled.
    CORS is considered enabled if FASTMCP_CORS_ALLOW_ORIGINS is set.

    Default Behavior:
        - If no origins specified: Returns empty list (CORS disabled)
        - If no methods specified: Allows all methods (["*"])
        - If no headers specified: Allows all headers (["*"])
        - Expose headers: Only exposes if explicitly configured

    Returns:
        List containing CORS middleware, or empty list if CORS is disabled

    Security Note:
        Using "*" for methods/headers is permissive but common for public APIs.
        For production, consider specifying exact allowed methods and headers.

    Example:
        # In app.py
        middleware = build_cors_middleware()
        await run_server_async(mcp_server, host, port, transport, middleware)
    """
    # Parse allowed origins from environment
    origins = _parse_csv(CORS_ALLOW_ORIGINS)

    # If no origins specified, CORS is disabled
    if not origins:
        return []

    # Parse other CORS settings, with sensible defaults
    methods = _parse_csv(CORS_ALLOW_METHODS) or ["*"]  # Default: allow all methods
    headers = _parse_csv(CORS_ALLOW_HEADERS) or ["*"]  # Default: allow all headers
    expose_headers = _parse_csv(CORS_EXPOSE_HEADERS)  # Only expose if specified

    # Build and return CORS middleware
    return [
        Middleware(
            CORSMiddleware,
            allow_origins=origins,  # Which origins can access
            allow_methods=methods,  # Which HTTP methods are allowed
            allow_headers=headers,  # Which request headers are allowed
            allow_credentials=bool(CORS_ALLOW_CREDENTIALS),
            max_age=CORS_MAX_AGE or None,
            expose_headers=expose_headers,  # Which response headers to expose
        )
    ]
