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
from drunk_ai_proxy.app.cache_provider import CacheProvider
from .middleware_provider import get_middlewares
from .starlette_app import StarletteApp
from drunk_ai_proxy.proxies import StaticProxiesProvider
from drunk_ai_proxy.utils.security import audit_log
from drunk_ai_proxy.utils.env import (
    CONFIG_DIR,
    LLM_ROUTE_PREFIX,
    LOG_LEVEL,
    HOST,
    PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

if TYPE_CHECKING:
    from drunk_ai_proxy.proxies.mcp.base_provider import McpProxyConfig
    from drunk_ai_proxy.utils import RemoteResourceConfig

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
        self.mcp_services: list["McpProxyConfig"] = []
        self.llm_services: list[tuple[str, Any]] = []
        self.remote_resources: list[RemoteResourceConfig] = []

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
        if hasattr(starlette_app, "add_remote_resources"):
            starlette_app.add_remote_resources(self.remote_resources)

        # Build the Starlette application with lifespan management
        app = starlette_app.build()

        # Get host and port for uvicorn
        server_host = HOST or "0.0.0.0"
        server_port = PORT or 9123

        logger.info("Creating uvicorn server (host=%s, port=%s, log_level=%s)",
                         server_host, server_port, LOG_LEVEL.lower())
        audit_log(
            logger=logger,
            event="server_start",
            status="in_progress",
            details={"host": server_host, "port": server_port, "log_level": LOG_LEVEL.lower()},
        )

        import uvicorn
        config = uvicorn.Config(
            app, host=server_host, port=server_port, log_level=LOG_LEVEL.lower()
        )
        server = uvicorn.Server(config)

        logger.info("Starting uvicorn server")
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
        logger.info("MCP Proxy Server Configuration:")
        logger.info("  Server Name: %s", config["server_name"])
        logger.info("  Server Version: %s", config["server_version"])
        logger.info("  Host: %s", config["host"])
        logger.info("  Port: %s", config["port"])
        logger.info("  Log Level: %s", config["log_level"])
        logger.info("  Config Directory: %s", config["config_dir"])

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
      
        logger.info("Starting MCP Proxy Server")
        audit_log(logger=logger, event="server_bootstrap", status="started")

        try:
            self._log_startup_configuration()
            logger.info("%s", "=" * 50)

            config_provider = AppConfigProvider.get_instance()
            provider = StaticProxiesProvider(
                config_provider.get_mcp_configs(),
                auth_factory=config_provider,
            )
            self.mcp_services = provider.get_config_services()
            remote_resources = config_provider.get_remote_resources()
            self.remote_resources = (
                remote_resources if isinstance(remote_resources, list) else []
            )

            llmProvider = LlmProxiesProvider(
                config_provider.get_llm_configs(),
                auth_factory=config_provider,
                cache=CacheProvider.get_cache_store(),
            )
            self.llm_services.append((LLM_ROUTE_PREFIX, llmProvider))

            audit_log(
                logger=logger,
                event="server_configuration_loaded",
                status="success",
                details={
                    "mcp_services": len(self.mcp_services),
                    "llm_service_mounts": len(self.llm_services),
                    "remote_resource_bundles": len(self.remote_resources),
                },
            )

            logger.info("MCP Proxy Server is ready!")
            logger.info("%s", "=" * 50)

            # Step 2: Start the MCP server
            # Starts the async server with the configured transport and middleware
            # This call blocks until the server is shut down
            await self._async_start_server()
        except Exception as e:
            audit_log(
                logger=logger,
                event="server_bootstrap",
                status="failure",
                details={"error_type": type(e).__name__},
            )
            raise

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
