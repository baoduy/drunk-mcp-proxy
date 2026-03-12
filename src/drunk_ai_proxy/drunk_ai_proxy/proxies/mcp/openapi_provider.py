"""OpenAPI MCP Provider module.

This module provides a class for creating FastMCP instances from McpProxyConfig.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP
import httpx
from fastmcp.utilities.openapi import HTTPRoute
from fastmcp.server.providers.openapi import MCPType

if TYPE_CHECKING:
    pass

from drunk_ai_proxy.proxies.mcp.base_provider import McpBaseProvider, McpProxyConfig
from drunk_ai_proxy.utils import McpConfig
from drunk_ai_proxy.utils.env import SERVER_NAME
from drunk_ai_proxy.proxies.mcp.mcp_proxy_builder import McpProxyBuilder

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

class OpenApiMcpProvider(McpBaseProvider):
    """Provider class for creating FastMCP instances from McpProxyConfig."""

    def __init__(self, config: McpConfig) -> None:
        super().__init__(config)
        self.mcp: FastMCP | None = None

    def _get_filters(self):
        """Return configured OpenAPI filters, if any."""
        return self.config.get_openapi_filters()

    def custom_route_mapper(self, route: "HTTPRoute", mcp_type: "MCPType") -> "MCPType | None":
        filters = self._get_filters()
        if filters is not None:
            if filters.methods:
                if route.method not in filters.methods:
                    return MCPType.EXCLUDE

            if filters.tags:
                if not any(tag in route.tags for tag in filters.tags):
                    return MCPType.EXCLUDE

        return mcp_type

    def create_client(self) -> httpx.AsyncClient:
        """Return an appropriate HTTP client for the configured service."""
        base_url = self.config.get_openapi_base_url()
        if not base_url:
            raise ValueError("base_url is required for OpenAPI clients without Azure auth")
        return httpx.AsyncClient(base_url=base_url, auth=self._create_client_auth())

    def create_proxy(self) -> FastMCP:
        """
        Create and return a FastMCP instance based on the loaded configurations.
        """
        if self.mcp is not None:
            return self.mcp

        client = self.create_client()

        openapi_spec = self.config.get_openapi_spec_data()
        if openapi_spec is None:
            raise ValueError("open_api.spec_data is required for OpenAPI proxy creation")

        self.mcp = FastMCP.from_openapi(
            name=f"{SERVER_NAME}{self.config.path}",
            openapi_spec=openapi_spec,
            client=client,
            route_map_fn=self.custom_route_mapper,
            tags=self.config.tags
        )
        
        self.mcp.auth = super()._get_app_auth_provider()
        self._create_skill_proxy(self.mcp)
        self._create_agent_proxy(self.mcp)
        
        return self.mcp

    @staticmethod
    def create_mcp_proxies_configs(configs: list[McpConfig]) -> list[McpProxyConfig]:
        return McpProxyBuilder.build_openapi_proxy_configs(
            configs=configs,
            provider_factory=lambda config: OpenApiMcpProvider(config),
        )