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

from typing import TYPE_CHECKING, Any
from drunk_ai_proxy.proxies.llm.proxies_provider import LlmProxiesProvider
from drunk_ai_proxy.app.app_config_provider import AppConfigProvider
from .middleware_provider import get_middlewares
from .starlette_app import StarletteApp
from drunk_ai_proxy.proxies import StaticProxiesProvider
from drunk_ai_proxy.utils.env import (
    CONFIG_DIR,
    LLM_ROUTE_PREFIX,
    LOG_LEVEL,
    HOST,
    PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from drunk_ai_proxy.utils.logging_config import setup_logging

if TYPE_CHECKING:
    from drunk_ai_proxy.proxies.mcp.base_provider import McpProxyConfig

# Initialize logging with server name from environment
# Can be controlled via FASTMCP_LOG_LEVEL environment variable
logger = setup_logging(SERVER_NAME)


class MCPProxyServer:
    """
    MCP Proxy Server class for managing MCP proxy server lifecycle and configuration.

    This class encapsulates the server startup process, proxy mounting, and request routing.
    It provides a clean interface for creating and running an MCP proxy server with
    multiple backend MCP servers.

    Attributes:
        logger: Logger instance for server logs
    """

    def __init__(self):
        """Initialize the MCP Proxy Server."""
        self.logger = logger
        self.mcp_services: list["McpProxyConfig"] = []
        self.llm_services: list[tuple[str, Any]] = []

    # Server Management Methods
    # =========================

    async def _async_start_server(
            self
    ) -> None:
        """
        Initialize and run the MCP server with Starlette and uvicorn.

        This method builds a Starlette application that mounts each FastMCP server at its
        configured endpoint and exposes a `/health` health check route. The complete application
        is then served via uvicorn for ASGI compatibility and middleware support.

        Mount Paths:
            - Root server (name=None): /mcp
            - Namespaced servers: /{namespace}/mcp

        Args:
            mcp_list: List of (name, FastMCP) tuples to mount
            middleware: Optional list of Starlette middleware

        Raises:
            ImportError: If uvicorn is not installed
            Exception: On server startup or configuration errors

        Example:
            await server._start_server(
                [("stock", stock_mcp), (None, root_mcp)],
                [cors_middleware]
            )
        """
        
        # Create StarletteApp with middleware
        # Host, port, and service name are loaded from environment variables
        starlette_app = StarletteApp(middleware=get_middlewares())

        # Add all MCP mounts
        starlette_app.add_mcp_services(self.mcp_services)
        starlette_app.add_llm_services(self.llm_services)

        # Build the Starlette application with lifespan management
        app = starlette_app.build()

        # Get host and port for uvicorn
        server_host = HOST or "0.0.0.0"
        server_port = PORT or 9123

        self.logger.info("Creating uvicorn server (host=%s, port=%s, log_level=%s)",
                         server_host, server_port, LOG_LEVEL.lower())

        import uvicorn
        config = uvicorn.Config(
            app, host=server_host, port=server_port, log_level=LOG_LEVEL.lower()
        )
        server = uvicorn.Server(config)

        self.logger.info("Starting uvicorn server")
        await server.serve()

    # Utility Methods
    # ===============

    def _log_startup_configuration(self) -> None:
        """
        Log server configuration details at startup.

        Outputs complete server configuration information including name, version,
        host, port, logging level, configuration directory, and authentication status.
        This provides visibility into the server setup during initialization.

        Called during server startup to provide visibility into the server configuration
        and aid in troubleshooting and monitoring.
        """
        config: dict[str, str | bool | int] = {
            "server_name": SERVER_NAME,
            "server_version": SERVER_VERSION,
            "host": HOST or "0.0.0.0",
            "port": PORT or 9123,
            "log_level": LOG_LEVEL,
            "config_dir": CONFIG_DIR
        }
        self.logger.info("MCP Proxy Server Configuration:")
        self.logger.info("  Server Name: %s", config["server_name"])
        self.logger.info("  Server Version: %s", config["server_version"])
        self.logger.info("  Host: %s", config["host"])
        self.logger.info("  Port: %s", config["port"])
        self.logger.info("  Log Level: %s", config["log_level"])
        self.logger.info("  Config Directory: %s", config["config_dir"])

    # Application Entry Points
    # ========================

    async def async_run(self) -> None:
        """
        Asynchronous entry point for the MCP proxy server.

        This method orchestrates the server startup process:
        1. Logs server configuration information
        2. Loads and builds proxy servers via StaticProxyLoader
        3. Starts the Starlette/uvicorn server with configured middleware

        Startup Flow:
            Environment Config → Log Config → Load & Build Proxies → Start Server

        Configuration Sources:
            - CONFIG_DIR: FASTMCP_CONFIG_DIR environment variable (default: "data")

        Raises:
            Exception: Various server startup errors
        """
      
        self.logger.info("Starting MCP Proxy Server")
        self._log_startup_configuration()
        self.logger.info("%s", "=" * 50)

        config_provider = AppConfigProvider.get_instance()
        provider = StaticProxiesProvider(config_provider.get_mcp_configs())
        self.mcp_services = provider.get_config_services()

        llmProvider = LlmProxiesProvider(config_provider.get_llm_configs())
        self.llm_services.append((LLM_ROUTE_PREFIX, llmProvider))

        self.logger.info("MCP Proxy Server is ready!")
        self.logger.info("%s", "=" * 50)

        # Step 2: Start the MCP server
        # Starts the async server with the configured transport and middleware
        # This call blocks until the server is shut down
        await self._async_start_server()

    def run(self) -> None:
        """
        Synchronous entry point for the MCP proxy server.

        This method wraps the async run_async() method using asyncio.run().

        Usage:
            server = MCPProxyServer()
            server.run()
        """
        import asyncio
        asyncio.run(self.async_run())
