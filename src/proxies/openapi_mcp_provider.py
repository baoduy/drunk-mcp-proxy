"""OpenAPI MCP Provider module.

This module provides a class for creating FastMCP instances from McpProxyConfig.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from fastmcp import FastMCP
import httpx
from fastmcp.utilities.openapi import HTTPRoute

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from fastmcp.server.providers.openapi import MCPType
    from httpx import Auth
else:
    # Import for runtime use
    from fastmcp.server.providers.openapi import MCPType

from src.proxies.static_mcp_provider import StaticMcpProvider
from tools import SpecConfig
from tools.env import SERVER_NAME
from tools.logging_config import setup_logging


class OpenApiMcpProvider(StaticMcpProvider):
    """Provider class for creating FastMCP instances from McpProxyConfig."""

    def __init__(self, config: SpecConfig) -> None:
        self.mcp: FastMCP | None = None
        self.config = config
        self.logger = setup_logging(__name__)

    def custom_route_mapper(self, route: "HTTPRoute", mcp_type: "MCPType") -> "MCPType | None":
        if self.config.filters is not None:
            if self.config.filters.methods:
                if route.method not in self.config.filters.methods:
                    return MCPType.EXCLUDE

            if self.config.filters.tags:
                if not any(tag in route.tags for tag in self.config.filters.tags):
                    return MCPType.EXCLUDE

        return mcp_type

    def create_client(self) -> httpx.AsyncClient:
        """Return an appropriate HTTP client for the configured service."""
        if not self.config.base_url:
            raise ValueError("base_url is required for OpenAPI clients without Azure auth")

        auth: Auth | None = None
        headers: dict[str, str] = {}
        if self.config.auth and self.config.auth.azure:
            auth = self._create_client_auth(self.config.auth.azure)
        else:
            if self.config.auth is not None and self.config.auth.auth_token is not None:
                headers["Authorization"] = self.config.auth.auth_token

        return httpx.AsyncClient(base_url=self.config.base_url, auth=auth, headers=headers)

    def _create_proxy(self) -> "FastMCP":
        if self.mcp is not None:
            return self.mcp

        self.logger.info("Creating proxy for config: %s", self.config.path)
        azure_cfg = self.config.auth.azure if self.config.auth else None
        if not self.config.base_url and azure_cfg is None:
            raise ValueError("base_url is required for OpenAPI proxies without Azure auth")

        client = self.create_client()

        assert self.config.spec_data
        self.mcp = FastMCP.from_openapi(
            name=f"{SERVER_NAME}-{self.config.path}",
            openapi_spec=self.config.spec_data,
            client=client,
            route_map_fn=self.custom_route_mapper,
            tags=self.config.tags
        )
        
        if self.mcp is None:
            raise RuntimeError("FastMCP failed to initialize")
        self.mcp.auth = super()._create_auth_provider()
        return self.mcp
