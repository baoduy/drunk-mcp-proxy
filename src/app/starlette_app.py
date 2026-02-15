"""
Starlette Application Factory Module

This module provides a reusable StarletteApp class for creating Starlette applications
with MCP server mounts, health check endpoints, middleware, and lifespan management.
"""

from fastmcp.server.http import StarletteWithLifespan
from functools import partial
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from proxies.mcp_proxy_config import McpProxyConfig
from .lifespan import AppLifespanManager
from ..tools.env import SERVER_NAME, HOST, PORT
from ..tools.logging_config import setup_logging

logger = setup_logging("StarletteApp")


class StarletteApp:
    """
    Starlette application factory for MCP proxy servers.

    This class encapsulates the creation of a Starlette application with:
    - Health check endpoint (automatically added)
    - MCP server mounts with full URL logging
    - Custom middleware
    - Lifespan management (via build_with_lifespan method)

    Design Pattern:
        1. Create instance: app_factory = StarletteApp(middleware=...)
        2. Add mounts: app_factory.add_mcp_mounts(mcp_list)
        3. Get app: starlette_app = app_factory.build()

    The Starlette app is created at initialization and routes/mounts are added
    dynamically using the app's mount() and add_route() methods. The lifespan
    is managed by StarletteApp and can be overridden during build if needed.

    Attributes:
        app: The Starlette application instance
        middleware: Optional list of Starlette middleware
        mcp_apps: List of mounted MCP applications for lifespan management
        service_name: Service name loaded from SERVER_NAME env var
        host: Server host loaded from HOST env var
        port: Server port loaded from PORT env var
        lifespan_manager: Manager for MCP app lifespan handling
    """

    def __init__(
            self,
            middleware: list[Middleware] | None = None
    ):
        """
        Initialize the Starlette application factory.

        Server configuration (host, port, service name) is automatically loaded from
        environment variables (HOST, PORT, SERVER_NAME).

        Note: Lifespan management is handled by StarletteApp and may be overridden
        via build_with_lifespan() if needed.

        Args:
            routes: Initial list of routes (health check will be added automatically)
            middleware: Optional list of Starlette middleware
        """
        self.middleware = middleware
        self.lifespan_manager = AppLifespanManager()
        # Get configuration from environment variables
        self.service_name = SERVER_NAME
        self.host = HOST or "0.0.0.0"
        self.port = PORT or 9123
        self.mcp_apps: list[tuple[str | None, StarletteWithLifespan]] = []

    def _health_check_handler(self, _: Request) -> JSONResponse:
        """
        Health check endpoint handler.

        Args:
            _: The incoming HTTP request (unused)

        Returns:
            JSON response with status and service name
        """
        return JSONResponse({"status": "healthy", "service": self.service_name})

    def add_mcp_service(self, service: McpProxyConfig
                        ) -> None:
        """
        Add an MCP server mount to the application.
        Host and port are automatically loaded from environment variables.

        Args:
            name: Namespace for the mount (None for root mount at /mcp)
            mcp: FastMCP server instance to mount
        """
        if service.name == "root":
            # Root mount: serve at /mcp
            mount_path = "/mcp"
            mcp_app = service.mcp_server.http_app(path="/")
            full_url = f"http://{self.host}:{self.port}{mount_path}"
            logger.info(
                "Adding root MCP mount at %s (full endpoint: %s)", mount_path, full_url)
        else:
            # Namespaced mount: mount at /{name}/mcp
            mount_path = f"/{service.name}/mcp"
            mcp_app = service.mcp_server.http_app(path="/")
            full_url = f"http://{self.host}:{self.port}{mount_path}"
            logger.info("Adding MCP mount (name=%s) at %s (full endpoint: %s)",
                        service.name, mount_path, full_url)

        self.mcp_apps.append((mount_path, mcp_app))

    def add_mcp_services(
            self,
            services: list[McpProxyConfig]
    ) -> None:
        """
        Add multiple MCP server mounts to the application.

        Host and port are automatically loaded from environment variables.

        Args:
            services: List of McpProxyConfig instances to mount

        Raises:
            Exception: If any mount fails to be added
        """
        logger.info("Adding %d MCP mount(s)", len(services))

        for service in services:
            try:
                self.add_mcp_service(service)
            except Exception as e:
                logger.error("Failed to add MCP mount (name=%s): %s",
                             service.name, str(e), exc_info=True)
                raise

    def build(self) -> Starlette:
        """
        Return the Starlette app with a custom lifespan function.
        Note: If a custom lifespan is provided, the app will be recreated with the new lifespan.
        """
        logger.info(
            "Returning Starlette application with %d MCP mount(s)", len(self.mcp_apps))

        # Create new app with custom lifespan
        app = Starlette(
            middleware=self.middleware,
            lifespan=partial(self.lifespan_manager.lifespans, mcp_apps=self.mcp_apps)
        )

        for mount_path, mcp_app in self.mcp_apps:
            assert mount_path is not None  # Always set to string in add_mcp_service
            app.mount(mount_path, mcp_app)

        # Add health check endpoint
        app.add_route("/health", self._health_check_handler, methods=["GET"])

        return app
