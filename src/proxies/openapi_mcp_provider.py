"""OpenAPI MCP Provider module.

This module provides a class for creating FastMCP instances from McpProxyConfig.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from fastmcp.server.providers.openapi import MCPType
    from fastmcp.utilities.openapi import HTTPRoute

from src.tools import SpecConfig, OauthAsyncClient
from src.tools.env import SERVER_NAME
from src.tools.logging_config import setup_logging
from src.tools.spec_config import AzureAuthConfig


class OpenApiMcpProvider:
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
        azure_config = self.config.auth.azure if self.config.auth else None
        if azure_config is not None:
            return self._create_oauth_client(azure_config)

        if not self.config.base_url:
            raise ValueError("base_url is required for OpenAPI clients without Azure auth")

        return httpx.AsyncClient(base_url=self.config.base_url)

    def create_proxy(self) -> "FastMCP":
        from fastmcp import FastMCP

        if self.mcp is not None:
            return self.mcp

        self.logger.info("Creating proxy for config: %s", self.config.name)
        azure_cfg = self.config.auth.azure if self.config.auth else None
        if not self.config.base_url and azure_cfg is None:
            raise ValueError("base_url is required for OpenAPI proxies without Azure auth")

        client = self.create_client()

        self.mcp = FastMCP.from_openapi(
            name=f"{SERVER_NAME}-{self.config.name}",
            openapi_spec=self.config.spec_data,
            client=client,
            route_map_fn=self.custom_route_mapper,
            tags=self.config.tags,
        )
        if self.mcp is None:
            raise RuntimeError("FastMCP failed to initialize")
        return self.mcp

    def _create_oauth_client(self, azure_config: AzureAuthConfig) -> OauthAsyncClient:
        scope_value = self._scope_value(azure_config)
        assert self.config.base_url

        oauth_client = OauthAsyncClient(
            base_url=self.config.base_url,
            client_id=azure_config.client_id,
            client_secret=azure_config.client_secret,
            token_url=azure_config.token_url,
            scope=scope_value,
        )
        # if LOG_LEVEL == "DEBUG":
        #     async def _log_auth_header(request: httpx.Request) -> None:
        #         self.logger.debug("OAuth Authorization header: %s", request.headers.get("Authorization"))
        #
        #     oauth_client.event_hooks.setdefault("request", []).append(_log_auth_header)
        # oauth_client.token_endpoint = azure_config.token_url  # type: ignore[attr-defined]
        return oauth_client

    @staticmethod
    def _scope_value(config: AzureAuthConfig) -> Optional[str]:
        if not config.scopes:
            return None
        return " ".join(config.scopes)
