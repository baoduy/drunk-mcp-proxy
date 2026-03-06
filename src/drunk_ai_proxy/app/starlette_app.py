"""
Starlette Application Factory Module

This module provides a reusable StarletteApp class for creating Starlette applications
with MCP server mounts, health check endpoints, middleware, and lifespan management.
"""

from __future__ import annotations

from functools import partial
from logging import Logger
from typing import TYPE_CHECKING

from fastmcp.server.http import StarletteWithLifespan
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from .lifespan import AppLifespanManager
from .swagger_provider import SwaggerProvider
from drunk_ai_proxy.utils.env import SERVER_NAME, HOST, PORT, SWAGGER_ENABLED
from drunk_ai_proxy.utils.error_utils import sanitize_error_message
from drunk_ai_proxy.utils.logging_config import setup_logging

if TYPE_CHECKING:
    from ..proxies.mcp.base_provider import McpProxyConfig
    from ..proxies.llm.proxies_provider import LlmProxiesProvider


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
        self._logger: Logger = setup_logging(__name__)
        self.middleware = middleware
        self.lifespan_manager = AppLifespanManager()
        # Get configuration from environment variables
        self.service_name = SERVER_NAME
        self.host = HOST or "0.0.0.0"
        self.port = PORT or 9123
        self.mcp_apps: list[tuple[str | None, StarletteWithLifespan]] = []
        self.llm_services: list[tuple[str, "LlmProxiesProvider"]] = []
        # Initialize Swagger provider
        self.swagger_provider = SwaggerProvider(self.service_name)

    def _health_check_endpoint(self, request: Request) -> JSONResponse:
        """
        Health check endpoint.
        
        Returns the health status of the service.
        ---
        responses:
          200:
            description: Service health status
        """
        return JSONResponse({"status": "healthy", "service": self.service_name})

    def _exception_handler(self, request: Request, exc: Exception) -> JSONResponse:
        """
        Global exception handler for the application.

        Args:
            request: The incoming request that caused the exception
            exc: The exception that was raised
        """
        self._logger.error("Unhandled exception: %s", type(exc).__name__)
        return JSONResponse(
            {"error": sanitize_error_message(str(exc))},
            status_code=500,
        )

    def add_mcp_service(self, service: "McpProxyConfig"
                        ) -> None:
        """
        Add an MCP server mount to the application.
        Host and port are automatically loaded from environment variables.

        Args:
            service: FastMCP server instance to mount
        """
        mount_path = "/mcp" if service.path == "/" else f"{service.path}/mcp"
        mcp_app = service.http_app()
        self.mcp_apps.append((mount_path, mcp_app))
        self._logger.info("Adding MCP mount (path=%s) at %s", service.path, mount_path)

    def add_mcp_services(
            self,
            services: list["McpProxyConfig"]
    ) -> None:
        """
        Add multiple MCP server mounts to the application.

        Host and port are automatically loaded from environment variables.

        Args:
            services: List of McpProxyConfig instances to mount

        Raises:
            Exception: If any mount fails to be added
        """
        self._logger.info("Adding %d MCP mount(s)", len(services))

        for service in services:
            self.add_mcp_service(service)
           
    def _add_llm_service(self, path: str, service: LlmProxiesProvider) -> None:
        """
        Add an LLM provider service mount to the application.

        Args:
            service: LLM provider instance (HTTP or WebSocket) to mount
        """
        # For LLM providers, we can use a fixed mount path based on the provider name
        self.llm_services.append((path, service))

    def add_llm_services(
            self,
            services: list[tuple[str, LlmProxiesProvider]]
    ) -> None:
        """
        Add multiple LLM provider service mounts to the application.

        Args:
            services: List of (path, LlmProxiesProvider) tuples to mount

        Raises:
            Exception: If any mount fails to be added
        """
        self._logger.info("Adding %d LLM provider service(s)", len(services))

        for path, service in services:
            self._add_llm_service(path, service)

    def build(self) -> Starlette:
        """
        Return the Starlette app with a custom lifespan function.
        Note: If a custom lifespan is provided, the app will be recreated with the new lifespan.
        """
        self._logger.info(
            "Returning Starlette application with %d MCP mount(s)", len(self.mcp_apps))

        # Create new app with custom lifespan
        app = Starlette(
            middleware=self.middleware,
            lifespan=partial(self.lifespan_manager.lifespans, mcp_apps=self.mcp_apps),
            exception_handlers={Exception: self._exception_handler}
        )

        for mount_path, mcp_app in self.mcp_apps:
            assert mount_path is not None  # Always set to string in add_mcp_service
            app.mount(mount_path, mcp_app)

        for path, llm_service in self.llm_services:
            llm_service.mount(app, route_prefix=path)

        # Add health check endpoint
        app.add_route(
            "/health", self._health_check_endpoint, methods=["GET"], include_in_schema=True
        )
        app.add_route("/", self._health_check_endpoint, methods=["GET"], include_in_schema=False)

        # Add OpenAPI documentation endpoints
        if SWAGGER_ENABLED:
            self.swagger_provider.mount(
                app=app, mcp_apps=self.mcp_apps, llm_services=self.llm_services
            )

        return app
