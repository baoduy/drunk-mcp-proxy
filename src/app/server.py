"""
MCP Proxy Server - Server Configuration and Application Module

This is the main module for the MCP (Model Context Protocol) Proxy Server.
The proxy server dynamically routes requests to multiple configured backend MCP servers,
allowing clients to interact with multiple MCP services through a single endpoint.

Key Features:
- Dynamic routing to multiple backend MCP servers
- Support for multiple transports (HTTP, SSE, streamable-HTTP)
- Optional authentication via FastMCP auth providers
- CORS middleware support for web clients
- Health check endpoint for monitoring
- Namespace support to avoid tool name conflicts

Architecture:
    Client → Proxy Server → Backend MCP Servers
                          ↓
                    (stock, wiki, weather, etc.)

Supported Transports:
- http: Standard HTTP transport (default)
- sse: Server-Sent Events transport
- streamable-http: HTTP with streaming support
"""

from typing import Union

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.proxies.static_proxies import create_static_proxies
from src.tools.env import (
    CONFIG_DIR,
    LOG_LEVEL,
    SERVER_TRANSPORT,
    HOST,
    PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from src.tools.logging_config import setup_logging
from .auth import build_auth_provider
from .middleware import build_middleware

# Initialize logging with server name from environment
# Can be controlled via FASTMCP_LOG_LEVEL environment variable
logger = setup_logging(SERVER_NAME)

# Build authentication provider from environment variables
# Authentication is optional - will be None if FASTMCP_SERVER_AUTH is not set
_auth_provider = build_auth_provider()

# Initialize the main FastMCP server instance
# This server will mount all configured proxies and handle client requests
mcp_server = FastMCP(
    SERVER_NAME,
    version=SERVER_VERSION,
    auth=_auth_provider,
)


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
        host, port = _resolve_server_bind("localhost", "8080")
        # Returns: ("localhost", 8080)

        host, port = _resolve_server_bind("", "invalid")
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


async def _run_server_async(
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
        await _run_server_async(
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


# Helper Functions
# ================


def _mount_proxies(mcp: FastMCP, proxies: list[tuple[str | None, object]]) -> None:
    """
    Mount all proxy instances to the MCP server.

    This function registers each proxy with the main MCP server using the
    mcp.mount() method. Each proxy is mounted with its associated namespace,
    which prefixes all tool names to prevent naming conflicts.

    Namespacing Example:
        - Without namespace: tool "get_stock_price" remains "get_stock_price"
        - With namespace "stock": tool becomes "stock.get_stock_price"

    Error Handling:
        - If mounting fails for any proxy, the exception is logged
        - Processing continues for remaining proxies
        - This ensures partial success if some proxies fail to mount

    Args:
        mcp: The main FastMCP server instance to mount proxies to
        proxies: List of (namespace, proxy_instance) tuples to mount

    Example:
        proxies = create_static_proxies("data")
        _mount_proxies(mcp_server, proxies)
    """
    for namespace, proxy in proxies:
        try:
            # Mount the proxy to the MCP server with its namespace
            # The namespace will prefix all tool names from this proxy
            mcp.mount(proxy, namespace=namespace)  # type: ignore[arg-type]
            logger.info("Mounted proxy to MCP server (namespace=%s)", namespace)

        except Exception:
            # Log the full exception but continue mounting other proxies
            # This allows the server to start even if some proxies fail
            logger.exception("Failed to mount proxy (namespace=%s)", namespace)


# Health Check Endpoint
# =====================

@mcp_server.custom_route("/health", methods=["GET"])
async def _health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint for monitoring and load balancers.

    This endpoint can be used by:
    - Kubernetes liveness/readiness probes
    - Load balancers to check server health
    - Monitoring systems to verify server is running

    Returns:
        JSON response with status and service name

    Example Response:
        {"status": "healthy", "service": "drunk-mcp-server"}
    """
    return JSONResponse({"status": "healthy", "service": "drunk-mcp-server"})


# Application Entry Points
# ========================


async def _main_async() -> None:
    """
    Asynchronous entry point for the MCP proxy server.

    This function orchestrates the server startup process:
    1. Resolves server binding (host/port) configuration
    2. Loads proxy configurations from config directory
    3. Mounts all proxies to the MCP server
    4. Starts the MCP server with configured transport and middleware

    Startup Flow:
        Environment Config → Resolve Binding → Create Proxies → Mount Proxies → Start Server

    Configuration Sources:
        - HOST: FASTMCP_HOST environment variable (default: "0.0.0.0")
        - PORT: FASTMCP_PORT environment variable (default: 9123)
        - CONFIG_DIR: FASTMCP_CONFIG_DIR environment variable (default: "data")
        - SERVER_TRANSPORT: FASTMCP_SERVER_TRANSPORT (default: "http")

    Raises:
        Various exceptions if configuration is invalid or proxies fail to load
    """
    logger.info("Starting MCP Proxy Server")
    print("=" * 50)

    # Step 1: Resolve server binding configuration
    # Validates and normalizes host/port from environment variables
    host, port = _resolve_server_bind(HOST, PORT)

    # Step 2: Create proxies from configuration files
    # Loads all *.mcp.json files from CONFIG_DIR and creates proxy instances
    # Returns list of (namespace, proxy_instance) tuples
    proxies = create_static_proxies(CONFIG_DIR)

    # Step 3: Mount all proxies to the MCP server
    # Each proxy is mounted with its namespace to avoid tool name conflicts
    _mount_proxies(mcp_server, proxies)

    print("MCP Proxy Server is ready!")
    print("=" * 50)

    # Step 4: Run the MCP server
    # Starts the async server with the configured transport and middleware
    # This call blocks until the server is shut down
    await _run_server_async(mcp_server, host, port, SERVER_TRANSPORT, build_middleware())


def main() -> None:
    """
    Synchronous entry point for the MCP proxy server.

    This is the main function called when the module is executed directly.
    It wraps the async _main_async() function using asyncio.run().

    This function is the entry point defined in:
    - src/main.py (if __name__ == "__main__")
    - Package exports in __init__.py

    Usage:
        python -m src.main
        # or
        python src/main.py
    """
    import asyncio
    asyncio.run(_main_async())
