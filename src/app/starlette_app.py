"""
Starlette Application Factory Module

This module provides a reusable StarletteApp class for creating Starlette applications
with MCP server mounts, health check endpoints, middleware, and lifespan management.
"""

from functools import partial
from typing import TYPE_CHECKING

from fastmcp.server.http import StarletteWithLifespan
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.schemas import SchemaGenerator
from .lifespan import AppLifespanManager
from tools.env import SERVER_NAME, HOST, PORT, OPENAPI_ENABLED
from tools.logging_config import setup_logging

if TYPE_CHECKING:
    from proxies.static_mcp_provider import McpProxyConfig

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
        # Initialize schema generator
        self.schemas = SchemaGenerator(
            {"openapi": "3.0.0", "info": {"title": self.service_name, "version": "1.0"}}
        )

    def _openapi_schema(self, request: Request) -> JSONResponse:
        """
        Generate and return OpenAPI schema as JSON.
        
        Returns JSON response with proper content-type to display in browser
        instead of triggering download.
        ---
        responses:
          200:
            description: OpenAPI schema in JSON format
        """
        # Generate schema from app routes
        schema = self.schemas.get_schema(routes=request.app.routes)
        
        # Manually add mounted MCP services to the schema
        if "paths" not in schema:
            schema["paths"] = {}
            
        for mount_path, _ in self.mcp_apps:
            if mount_path:
                # Add MCP endpoint documentation
                schema["paths"][f"{mount_path}/"] = {
                    "get": {
                        "summary": mount_path,
                        "description": f"Model Context Protocol server endpoint: {mount_path}",
                        "responses": {
                            "200": {"description": "MCP server response"}
                        }
                    },
                    "post": {
                        "summary": mount_path,
                        "description": f"Model Context Protocol server endpoint: {mount_path}",
                        "responses": {
                            "200": {"description": "MCP server response"}
                        }
                    }
                }
        
        # Return as JSON with explicit content-type to display in browser
        return JSONResponse(
            content=schema,
            headers={
                "Content-Type": "application/json; charset=utf-8"
            }
        )

    def _health_check_handler(self, request: Request) -> JSONResponse:
        """
        Health check endpoint.
        
        Returns the health status of the service.
        ---
        responses:
          200:
            description: Service health status
        """
        return JSONResponse({"status": "healthy", "service": self.service_name})

    def _redoc_html(self, request: Request) -> HTMLResponse:
        """
        ReDoc endpoint for alternative API documentation UI.
        
        Provides interactive API documentation using ReDoc.
        ---
        responses:
          200:
            description: ReDoc HTML page
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <title>{title} - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url='/openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
</body>
</html>""".format(title=self.service_name)
        return HTMLResponse(content=html)

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
        logger.info("Adding MCP mount (path=%s) at %s", service.path, mount_path)

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
        logger.info("Adding %d MCP mount(s)", len(services))

        for service in services:
            self.add_mcp_service(service)
           

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
        app.add_route("/health", self._health_check_handler, methods=["GET"], include_in_schema=True)
        
        # Add OpenAPI documentation endpoints if enabled
        if OPENAPI_ENABLED:
            app.add_route("/openapi.json", self._openapi_schema, methods=["GET"], include_in_schema=False)
            app.add_route("/docs", self._redoc_html, methods=["GET"], include_in_schema=False)
            logger.info("OpenAPI endpoints enabled: /openapi.json, /docs")

        return app
