"""
Server configuration and management module.

This module handles the low-level server configuration and execution,
including host/port resolution, transport selection, and middleware integration.

Supported Transports:
- http: Standard HTTP transport (default)
- sse: Server-Sent Events transport
- streamable-http: HTTP with streaming support

Middleware Support:
- CORS middleware for cross-origin requests
- Custom middleware can be added via the middleware parameter
"""

from typing import Union

from fastmcp import FastMCP
from starlette.middleware import Middleware

from ..tools.env import LOG_LEVEL, SERVER_TRANSPORT, SERVER_NAME
from ..tools.logging_config import setup_logging

logger = setup_logging(SERVER_NAME)


# Server Configuration Functions
# ===============================


def _resolve_server_bind(host_value: str, port_value: Union[str, int]) -> tuple[str, int]:
    """
    Resolve and validate server host/port configuration with safe defaults.

    This function ensures that the host and port are valid values, providing
    sensible defaults if the input is invalid or missing.

    Host Resolution:
        - If empty/None: defaults to "0.0.0.0" (all interfaces)
        - Otherwise: uses the provided value as-is

    Port Resolution:
        - If already an integer: uses it directly
        - If string: attempts to convert to integer
        - If conversion fails: defaults to 9123 with a warning

    Args:
        host_value: Host address or hostname (can be empty)
        port_value: Port number as string or integer

    Returns:
        Tuple of (host, port) with validated values

    Example:
        host, port = resolve_server_bind("localhost", "8080")
        # Returns: ("localhost", 8080)

        host, port = resolve_server_bind("", "invalid")
        # Returns: ("0.0.0.0", 9123) with warning logged
    """
    # Default to binding on all interfaces if no host specified
    host = host_value or "0.0.0.0"

    # If port is already an integer, use it directly
    if isinstance(port_value, int):
        return host, port_value

    # Try to convert string port to integer
    try:
        port = int(port_value)
    except (TypeError, ValueError):
        # Invalid port value - log warning and use default
        logger.warning("Invalid port='%s'; using 9123", port_value)
        port = 9123

    return host, port


async def run_server_async(
        mcp: FastMCP,
        host: str,
        port: int,
        transport: str = "http",
        middleware: list[Middleware] | None = None,
) -> None:
    """
    Run the MCP server asynchronously with optional transport and middleware.

    This is the core server execution function that handles multiple transport
    protocols and optional middleware integration. It supports both standard
    FastMCP transports and custom uvicorn-based serving for middleware support.

    Transport Selection Priority:
        1. Environment variable (FASTMCP_SERVER_TRANSPORT)
        2. Function parameter
        3. Default: "http"

    Supported Transports:
        - "http": Standard HTTP transport (default)
        - "sse": Server-Sent Events for streaming
        - "streamable-http": HTTP with streaming capabilities

    Middleware Handling:
        - If middleware is provided and transport is http/streamable-http,
          uses uvicorn for proper ASGI middleware support
        - Otherwise uses FastMCP's built-in server

    Error Handling:
        - Gracefully handles TypeError from FastMCP's run_async()
        - Falls back to simpler invocation if kwargs not supported
        - Logs errors and re-raises if critical

    Args:
        mcp: FastMCP server instance to run
        host: Host address to bind to
        port: Port number to listen on
        transport: Transport protocol to use (default: "http")
        middleware: Optional list of Starlette middleware

    Raises:
        ImportError: If uvicorn is required but not installed
        Exception: Various server startup errors

    Example:
        await run_server_async(
            mcp_server,
            "0.0.0.0",
            9123,
            "http",
            [cors_middleware]
        )
    """
    # Prepare server configuration
    run_kwargs: dict[str, Union[str, int, list[Middleware]]] = {"host": host, "port": port}

    # Transport selection: environment variable takes precedence over parameter
    # This allows runtime override without changing code
    transport = (transport or SERVER_TRANSPORT).strip().lower()

    # Default to HTTP if no transport specified
    # Note: There is no "auto" transport mode in FastMCP
    if not transport:
        transport = "http"

    # Special handling for middleware with HTTP transports
    # Middleware requires uvicorn for proper ASGI support
    if middleware and transport in {"http", "streamable-http"}:
        try:
            import uvicorn
        except Exception as exc:
            logger.error("CORS middleware requires uvicorn for ASGI serving: %s", exc)
            raise

        # Create ASGI app with middleware and run with uvicorn
        # This provides full ASGI middleware support (CORS, auth, etc.)
        app = mcp.http_app(middleware=middleware)
        config = uvicorn.Config(app, host=host, port=port, log_level=LOG_LEVEL.lower())
        server = uvicorn.Server(config)
        await server.serve()
        return

    # Validate transport type
    # Only these transport types are supported by FastMCP
    if transport not in {"http", "sse", "streamable-http"}:
        logger.warning("Invalid transport='%s'; using http", transport)
        transport = "http"

    # Build run arguments for FastMCP
    run_kwargs["transport"] = transport
    if middleware:
        run_kwargs["middleware"] = middleware

    logger.info("Starting server on %s:%s (transport=%s)", host, port, transport)

    # Try to run server with full kwargs support
    try:
        await mcp.run_async(**run_kwargs)
    except TypeError:
        # FastMCP version may not support all kwargs
        # Try with just transport parameter
        if "transport" in run_kwargs:
            try:
                transport_value = run_kwargs["transport"]
                if isinstance(transport_value, str):
                    await mcp.run_async(transport=transport_value)
                    return
            except TypeError:
                # Even transport not supported, use minimal invocation
                pass
        # Fall back to simplest invocation
        await mcp.run_async()
