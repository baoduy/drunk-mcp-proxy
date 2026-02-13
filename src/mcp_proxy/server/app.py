"""
MCP Proxy Server - Main Application Module

This is the main entry point for the MCP (Model Context Protocol) Proxy Server.
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
"""

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import build_auth_provider
from .middleware import build_middleware
from .server import _resolve_server_bind, run_server_async
from ..proxies.static_proxies import create_static_proxies
from ..tools.env import (
    CONFIG_DIR,
    SERVER_TRANSPORT,
    HOST,
    PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from ..tools.logging_config import setup_logging

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
    await run_server_async(mcp_server, host, port, SERVER_TRANSPORT, build_middleware())


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
