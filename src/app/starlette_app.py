"""
Starlette Application Factory Module

This module provides a reusable StarletteApp class for creating Starlette applications
with MCP server mounts, health check endpoints, middleware, and lifespan management.
"""

from functools import partial
from typing import Callable

from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from src.tools.env import SERVER_NAME, HOST, PORT
from src.tools.logging_config import setup_logging
from .lifespan import AppLifespanManager

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
        1. Create instance: app = StarletteApp(middleware=...)
        2. Add mounts: app.add_mcp_mounts(mcp_list)
        3. Build with lifespan: starlette = app.build()

    The lifespan is managed by StarletteApp and can be overridden during build
    if a custom lifespan function is required.

    Attributes:
        routes: List of Starlette routes including health check and mounts
        middleware: Optional list of Starlette middleware
        mcp_apps: List of mounted MCP applications for lifespan management
        service_name: Service name loaded from SERVER_NAME env var
        host: Server host loaded from HOST env var
        port: Server port loaded from PORT env var
        lifespan_manager: Manager for MCP app lifespan handling
    """

    def __init__(
            self,
            routes: list[Mount | Route] | None = None,
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
        self.routes = routes or []
        self.middleware = middleware
        self.lifespan_manager = AppLifespanManager()

        # Get configuration from environment variables
        self.service_name = SERVER_NAME
        self.host = HOST or "0.0.0.0"
        self.port = PORT or 9123

        self.mcp_apps: list[tuple[str | None, StarletteWithLifespan]] = []

        # Add health check endpoint with default handler
        self._ensure_health_check_route()

    def _health_check_handler(self, _: Request) -> JSONResponse:
        """
        Health check endpoint handler.

        Args:
            _: The incoming HTTP request (unused)

        Returns:
            JSON response with status and service name
        """
        return JSONResponse({"status": "healthy", "service": self.service_name})

    def _ensure_health_check_route(self) -> None:
        """Ensure health check route is present in routes list."""
        # Check if health check route already exists
        has_health = any(
            isinstance(route, Route) and route.path == "/health"
            for route in self.routes
        )

        if not has_health:
            self.routes.insert(
                0,
                Route("/health", endpoint=self._health_check_handler, methods=["GET"])
            )

    def add_mcp_mount(
            self,
            name: str | None,
            mcp: FastMCP
    ) -> None:
        """
        Add an MCP server mount to the application.

        Host and port are automatically loaded from environment variables.

        Args:
            name: Namespace for the mount (None for root mount at /mcp)
            mcp: FastMCP server instance to mount
        """
        if name is None:
            # Root mount: serve at /mcp
            mount_path = "/mcp"
            mcp_app = mcp.http_app(path="/")
            full_url = f"http://{self.host}:{self.port}{mount_path}"
            logger.info("Adding root MCP mount at %s (full endpoint: %s)", mount_path, full_url)
        else:
            # Namespaced mount: mount at /{name}/mcp
            mount_path = f"/{name}/mcp"
            mcp_app = mcp.http_app(path="/")
            full_url = f"http://{self.host}:{self.port}{mount_path}"
            logger.info("Adding namespaced MCP mount (name=%s) at %s (full endpoint: %s)",
                        name, mount_path, full_url)

        self.routes.append(Mount(mount_path, app=mcp_app))
        self.mcp_apps.append((name, mcp_app))

    def add_mcp_mounts(
            self,
            mcp_list: list[tuple[str | None, FastMCP]]
    ) -> None:
        """
        Add multiple MCP server mounts to the application.

        Host and port are automatically loaded from environment variables.

        Args:
            mcp_list: List of (name, FastMCP) tuples to mount

        Raises:
            Exception: If any mount fails to be added
        """
        logger.info("Adding %d MCP mount(s)", len(mcp_list))

        for name, mcp in mcp_list:
            try:
                self.add_mcp_mount(name, mcp)
            except Exception as e:
                logger.error("Failed to add MCP mount (name=%s): %s", name, str(e), exc_info=True)
                raise

    def build(self) -> Starlette:
        """Build the Starlette app using the default lifespan manager."""
        return self._build_starlette_app(self.lifespan_manager.lifespans)

    def build_with_lifespan(self, lifespan_func: Callable | None = None) -> Starlette:
        """
        Build the Starlette app with a custom lifespan function.

        Args:
            lifespan_func: Optional lifespan function to override the default manager
        """
        return self._build_starlette_app(lifespan_func or self.lifespan_manager.lifespans)

    def _build_starlette_app(self, lifespan_func: Callable) -> Starlette:
        """Internal helper that assembles the Starlette app with optional lifespan."""
        logger.info("Building Starlette application with %d route(s)", len(self.routes))

        return Starlette(
            routes=self.routes,
            middleware=self.middleware,
            lifespan=partial(lifespan_func, mcp_apps=self.mcp_apps)
        )
