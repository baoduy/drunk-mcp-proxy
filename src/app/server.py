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

from functools import partial

from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from src.proxies.static_proxies import StaticProxyLoader
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
from .lifespan import AppLifespanManager
from .middleware import build_middleware

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
        auth_provider: Authentication provider instance
        lifespan_manager: Manager for application lifespan handling
    """

    def __init__(self):
        """Initialize the MCP Proxy Server."""
        self.logger = logger
        self.auth_provider = _auth_provider
        self.lifespan_manager = AppLifespanManager()

    # Health Check Endpoint
    # =====================

    @staticmethod
    async def _handle_health_check(_: Request) -> JSONResponse:
        """
        Health check endpoint handler for monitoring and load balancers.

        This endpoint can be used by:
        - Kubernetes liveness/readiness probes
        - Load balancers to check server health
        - Monitoring systems to verify server is running

        Args:
            _: The incoming HTTP request (unused)

        Returns:
            JSON response with status and service name

        Example Response:
            {"status": "healthy", "service": "drunk-mcp-server"}
        """
        return JSONResponse({"status": "healthy", "service": "drunk-mcp-server"})

    # Server Management Methods
    # =========================

    async def _start_server(
            self,
            mcp_list: list[tuple[str | None, FastMCP]],
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
            mcp_apps: list[tuple[str | None, StarletteWithLifespan]] = []
            routes: list[Mount | Route] = [
                Route("/health", endpoint=self._handle_health_check, methods=["GET"]),
            ]

            self.logger.info("Mounting %d MCP application(s)", len(mcp_list))

            for name, mcp in mcp_list:
                try:
                    if name is None:
                        # Root mount: serve at /mcp
                        mount_path = "/mcp"
                        mcp_app = mcp.http_app(path="/")
                        self.logger.info("Mounting root MCP app at %s", mount_path)
                    else:
                        # Namespaced mount: mount at /{name}
                        mount_path = f"/{name}/mcp"
                        mcp_app = mcp.http_app(path="/")
                        self.logger.info("Mounting namespaced MCP app (name=%s) at %s", name, mount_path)

                    routes.append(Mount(mount_path, app=mcp_app))
                    mcp_apps.append((name, mcp_app))

                except Exception as e:
                    self.logger.error("Failed to mount MCP app (name=%s): %s", name, str(e), exc_info=True)
                    raise

            app = Starlette(
                routes=routes,
                middleware=middleware,
                lifespan=partial(self.lifespan_manager.lifespans, mcp_apps=mcp_apps),
            )

            self.logger.info("Creating uvicorn server (host=%s, port=%s, log_level=%s)",
                             HOST or "0.0.0.0", PORT or 9123, LOG_LEVEL.lower())

            import uvicorn
            config = uvicorn.Config(app, host=HOST or "0.0.0.0", port=PORT or 9123, log_level=LOG_LEVEL.lower())
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

    def _retrieve_configuration(self) -> dict:
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

            # Step 1: Load and build proxy servers using StaticProxyLoader
            self.logger.info("Loading proxy configurations from %s", CONFIG_DIR)
            loader = StaticProxyLoader(CONFIG_DIR)

            # Create root FastMCP server and build all proxy servers
            root_mcp = FastMCP(SERVER_NAME, version=SERVER_VERSION, auth=self.auth_provider)
            mcp_list = loader.build_mcp_servers(root_mcp, auth_provider=self.auth_provider)

            if not mcp_list or len(mcp_list) == 1:
                self.logger.warning("No proxies loaded from configuration directory")
            else:
                self.logger.info("Loaded and built %d proxy server(s)", len(mcp_list) - 1)

            print("MCP Proxy Server is ready!")
            print("=" * 50)

            # Step 2: Start the MCP server
            # Starts the async server with the configured transport and middleware
            # This call blocks until the server is shut down
            await self._start_server(mcp_list, build_middleware())

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
