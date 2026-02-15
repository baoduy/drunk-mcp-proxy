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

from typing import TYPE_CHECKING

from starlette.middleware import Middleware

from proxies import ProxyConfigProvider
from proxies.mcp_proxy_config import McpProxyConfig
from tools.env import (
    CONFIG_DIR,
    LOG_LEVEL,
    HOST,
    PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from tools.logging_config import setup_logging
from .auth import build_auth_provider
from .middleware import build_middleware
from .starlette_app import StarletteApp

if TYPE_CHECKING:
    pass

# Initialize logging with server name from environment
# Can be controlled via FASTMCP_LOG_LEVEL environment variable
logger = setup_logging(SERVER_NAME)

# Build authentication provider from environment variables
# Authentication is optional - will be None if FASTMCP_SERVER_AUTH is not set
_auth_provider = build_auth_provider()


class MCPProxyServer:
    """
    MCP Proxy Server class for managing MCP proxy server lifecycle and configuration.

    This class encapsulates the server startup process, proxy mounting, and request routing.
    It provides a clean interface for creating and running an MCP proxy server with
    multiple backend MCP servers.

    Attributes:
        logger: Logger instance for server logs
        auth_provider: Authentication provider instance (AuthProvider | None)
    """

    def __init__(self):
        """Initialize the MCP Proxy Server."""
        self.logger = logger
        self.auth_provider = _auth_provider

    # Server Management Methods
    # =========================

    async def _start_server(
            self,
            mcp_list: list[McpProxyConfig],
            middleware: list[Middleware] | None = None,
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
        try:
            # Create StarletteApp with middleware
            # Host, port, and service name are loaded from environment variables
            starlette_app = StarletteApp(middleware=middleware)

            # Add all MCP mounts
            starlette_app.add_mcp_services(mcp_list)

            # Build the Starlette application with lifespan management
            app = starlette_app.build()

            # Get host and port for uvicorn
            server_host = HOST or "0.0.0.0"
            server_port = PORT or 9123

            self.logger.info("Creating uvicorn server (host=%s, port=%s, log_level=%s)",
                             server_host, server_port, LOG_LEVEL.lower())

            import uvicorn
            config = uvicorn.Config(app, host=server_host, port=server_port, log_level=LOG_LEVEL.lower())
            server = uvicorn.Server(config)

            self.logger.info("Starting uvicorn server")
            await server.serve()

        except ImportError as e:
            self.logger.error("Failed to import uvicorn: %s", str(e))
            raise ImportError(
                "uvicorn is required to run the MCP proxy server. Install it with: pip install uvicorn") from e
        except Exception as e:
            self.logger.error("Server startup failed: %s", str(e), exc_info=True)
            raise

    # Utility Methods
    # ===============

    def _retrieve_configuration(self) -> dict[str, str | bool | int]:
        """
        Retrieve the current server configuration as a dictionary.

        Returns all relevant server configuration values for inspection,
        debugging, and logging purposes.

        Returns:
            Dictionary containing server configuration details:
            - server_name: Name of the server
            - server_version: Version string
            - host: Server hostname/IP address
            - port: Server port number
            - log_level: Logging level
            - config_dir: Configuration directory path
            - auth_enabled: Whether authentication is enabled
        """
        return {
            "server_name": SERVER_NAME,
            "server_version": SERVER_VERSION,
            "host": HOST or "0.0.0.0",
            "port": PORT or 9123,
            "log_level": LOG_LEVEL,
            "config_dir": CONFIG_DIR,
            "auth_enabled": self.auth_provider is not None,
        }

    def _log_startup_configuration(self) -> None:
        """
        Log server configuration details at startup.

        Outputs complete server configuration information including name, version,
        host, port, logging level, configuration directory, and authentication status.
        This provides visibility into the server setup during initialization.

        Called during server startup to provide visibility into the server configuration
        and aid in troubleshooting and monitoring.
        """
        config = self._retrieve_configuration()
        self.logger.info("MCP Proxy Server Configuration:")
        self.logger.info("  Server Name: %s", config["server_name"])
        self.logger.info("  Server Version: %s", config["server_version"])
        self.logger.info("  Host: %s", config["host"])
        self.logger.info("  Port: %s", config["port"])
        self.logger.info("  Log Level: %s", config["log_level"])
        self.logger.info("  Config Directory: %s", config["config_dir"])
        self.logger.info("  Authentication: %s", "Enabled" if config["auth_enabled"] else "Disabled")

    # Application Entry Points
    # ========================

    async def run_async(self) -> None:
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
        try:
            self.logger.info("Starting MCP Proxy Server")
            self._log_startup_configuration()
            print("=" * 50)

            provider = ProxyConfigProvider(config_dir=CONFIG_DIR)
            services = provider.get_config_services()
            self.logger.info("Total MCP servers loaded: %d", len(services))

            print("MCP Proxy Server is ready!")
            print("=" * 50)

            # Step 2: Start the MCP server
            # Starts the async server with the configured transport and middleware
            # This call blocks until the server is shut down
            await self._start_server(services, build_middleware())

        except KeyboardInterrupt:
            self.logger.info("Server interrupted by user")
        except Exception as e:
            self.logger.error("Server startup failed: %s", str(e), exc_info=True)
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
        asyncio.run(self.run_async())
