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

from proxies.mcp_base_provider import McpBaseProvider, McpProxyConfig
from tools import McpConfig
from tools.env import SERVER_NAME
from tools.logging_config import setup_logging


class OpenApiMcpProvider(McpBaseProvider):
    """Provider class for creating FastMCP instances from McpProxyConfig."""

    def __init__(self, config: McpConfig) -> None:
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
        return httpx.AsyncClient(base_url=self.config.base_url, auth=self._create_client_auth())

    def create_proxy(self) -> FastMCP:
        """
        Create and return a FastMCP instance based on the loaded configurations.
        """
        if self.mcp is not None:
            return self.mcp

        client = self.create_client()

        assert self.config.spec_data
        self.mcp = FastMCP.from_openapi(
            name=f"{SERVER_NAME}{self.config.path}",
            openapi_spec=self.config.spec_data,
            client=client,
            route_map_fn=self.custom_route_mapper,
            tags=self.config.tags
        )
        
        self.mcp.auth = super()._get_app_auth_provider()
        self._create_skill_proxy(self.mcp)
        
        return self.mcp

    @staticmethod
    def create_mcp_proxies_configs(configs: list[McpConfig]) -> list[McpProxyConfig]:
        mcp_proxy_configs: list[McpProxyConfig] = []
        for config in configs:
            if config.spec_data is None:
                continue

            mcp = OpenApiMcpProvider(config)
            mcp_proxy_configs.append(mcp.get_mcp_proxy_config())
        return mcp_proxy_configs