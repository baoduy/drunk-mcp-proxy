"""
MCP Proxy Server - Server Configuration and Application Module

This is the main module for the MCP (Model Context Protocol) Proxy Server.
The proxy server dynamically routes requests to multiple configured backend MCP servers,
allowing clients to interact with multiple MCP services through a single endpoint.

Key Features:
- Dynamic routing to multiple backend MCP servers
- Starlette routing with per-proxy mounts
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

from contextlib import asynccontextmanager
from typing import AsyncContextManager

from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan
from fastmcp.server.providers.proxy import FastMCPProxy
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from src.proxies.static_proxies import create_static_proxies
from src.tools.env import (
    CONFIG_DIR,
    LOG_LEVEL,
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


# Health Check Endpoint
# =====================

async def _health_check_starlette(request: Request) -> JSONResponse:
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


async def _run_server_async(
        mcp_list: list[tuple[str | None, FastMCP]],
        middleware: list[Middleware] | None = None,
) -> None:
    """
    Run the MCP server asynchronously using Starlette and uvicorn.

    This function builds a Starlette app that mounts each FastMCP app at its
    configured path and exposes a `/health` endpoint. The assembled app is
    served via uvicorn for ASGI middleware support.

    Mounting Rules:
        - If name is None: mount at "/"
        - If name is set: mount at f"/{name}"

    Args:
        mcp_list: List of (name, FastMCP) tuples to mount
        middleware: Optional list of Starlette middleware

    Raises:
        ImportError: If uvicorn is required but not installed
        Exception: Various server startup errors

    Example:
        await _run_server_async(
            [("stock", stock_mcp), (None, root_mcp)],
            [cors_middleware]
        )
    """

    mcp_apps: list[tuple[str | None, StarletteWithLifespan]] = []
    routes: list[Mount | Route] = [
        Route("/health", endpoint=_health_check_starlette, methods=["GET"]),
    ]

    for name, mcp in mcp_list:
        if name is None:
            # Root mount: serve at /mcp
            mount_path = "/mcp"
            mcp_app = mcp.http_app(path="/")
            logger.info("Mounting MCP app (name=%s) at %s", name, mount_path)
        else:
            # Namespaced mount: mount at /{name}
            mount_path = f"/{name}/mcp"
            mcp_app = mcp.http_app(path="/")
            logger.info("Mounting MCP app (name=%s) at %s", name, mount_path)

        routes.append(Mount(mount_path, app=mcp_app))
        mcp_apps.append((name, mcp_app))

    @asynccontextmanager
    async def _combined_lifespan(app: Starlette):
        lifespan_contexts: list[AsyncContextManager[None]] = []
        try:
            for name, mcp_app in mcp_apps:
                lifespan = getattr(mcp_app, "lifespan", None)
                if lifespan is None:
                    logger.warning("MCP app missing lifespan (name=%s)", name)
                    continue
                ctx: AsyncContextManager[None] = lifespan(mcp_app)
                await ctx.__aenter__()
                lifespan_contexts.append(ctx)
            yield
        finally:
            for ctx in reversed(lifespan_contexts):
                await ctx.__aexit__(None, None, None)

    app = Starlette(
        routes=routes,
        middleware=middleware,
        lifespan=_combined_lifespan,
    )

    import uvicorn
    config = uvicorn.Config(app, host=HOST or "0.0.0.0", port=PORT or 9123, log_level=LOG_LEVEL.lower())
    server = uvicorn.Server(config)
    await server.serve()


# Helper Functions
# ================


def _mount_proxies(proxies: list[tuple[str | None, FastMCPProxy]]) -> list[tuple[str | None, FastMCP]]:
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
    root_server = FastMCP(SERVER_NAME, version=SERVER_VERSION, auth=_auth_provider)
    mcp_servers: list[tuple[str | None, FastMCP]] = [(None, root_server)]

    for namespace, proxy in proxies:
        if namespace is None:
            root_server.mount(proxy)
            continue
        mcp = FastMCP(f"{SERVER_NAME}_{namespace}", version=SERVER_VERSION, auth=_auth_provider)
        mcp.mount(proxy)
        mcp_servers.append((namespace, mcp))
    return mcp_servers


# Application Entry Points
# ========================


async def _main_async() -> None:
    """
    Asynchronous entry point for the MCP proxy server.

    This function orchestrates the server startup process:
    1. Loads proxy configurations from the config directory
    2. Builds per-proxy FastMCP instances for Starlette mounts
    3. Starts the Starlette/uvicorn server with configured middleware

    Startup Flow:
        Environment Config → Create Proxies → Build MCP List → Start Server

    Configuration Sources:
        - CONFIG_DIR: FASTMCP_CONFIG_DIR environment variable (default: "data")
    """
    logger.info("Starting MCP Proxy Server")
    print("=" * 50)

    # Step 2: Create proxies from configuration files
    # Loads all *.mcp.json files from CONFIG_DIR and creates proxy instances
    # Returns list of (namespace, proxy_instance) tuples
    proxies = create_static_proxies(CONFIG_DIR)

    # Step 3: Mount all proxies to the MCP server
    # Each proxy is mounted with its namespace to avoid tool name conflicts
    mcp_list = _mount_proxies(proxies)

    print("MCP Proxy Server is ready!")
    print("=" * 50)

    # Step 4: Run the MCP server
    # Starts the async server with the configured transport and middleware
    # This call blocks until the server is shut down
    await _run_server_async(mcp_list, build_middleware())


def main() -> None:
    """
    Synchronous entry point for the MCP proxy server.

    This is the main function called when the module is executed directly.
    It wraps the async _main_async() function using asyncio.run().

    Usage:
        python -m src.main
        # or
        python src/main.py
    """
    import asyncio
    asyncio.run(_main_async())
