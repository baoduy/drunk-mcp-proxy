"""
MCP Proxy Server
A proxy server for Model Context Protocol (MCP) that dynamically routes requests to configured backend servers.
"""

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from .auth import build_auth_provider
from .middleware import build_middleware
from .server import resolve_server_bind, run_server_async
from ..proxies.static_proxies import initialize_static_proxies
from ..tools.env import (
    CONFIG_FILE,
    SERVER_TRANSPORT,
    HOST,
    PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from ..tools.logging_config import setup_logging

# Basic logging setup (override with FASTMCP_LOG_LEVEL env var)
logger = setup_logging("mcp-proxy")

# Initialize FastMCP server
_auth_provider = build_auth_provider()
mcp = FastMCP(
    SERVER_NAME,
    version=SERVER_VERSION,
    auth=_auth_provider,
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "drunk-mcp-server"})


async def main_async() -> None:
    """Async entry point for the MCP proxy server."""
    logger.info("Starting MCP Proxy Server")
    print("=" * 50)

    # Resolve server binding configuration
    host, port = resolve_server_bind(HOST, PORT)

    # Initialize proxies from configuration files
    initialize_static_proxies(mcp, CONFIG_FILE, host, port)

    print("=" * 50)
    print("MCP Proxy Server is ready!")
    print("=" * 50)

    # Run the MCP server
    await run_server_async(mcp, host, port, SERVER_TRANSPORT, build_middleware())


def main() -> None:
    """Main entry point for the MCP proxy server."""
    import asyncio

    asyncio.run(main_async())
