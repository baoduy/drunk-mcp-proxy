"""Static MCP Provider abstract base class.

This module provides an abstract base class for creating MCP provider implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from src.tools.auth_config import AuthProviderType
from src.tools.spec_config import AzureAuthConfig
from tools import SpecConfig
from auth_providers import AzureOauth
from dataclasses import dataclass
from tools.env import SERVER_TRANSPORT

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider
    from httpx import Auth
    from fastmcp import FastMCP
    from fastmcp.server.middleware import Middleware
    from fastmcp.server.http import StarletteWithLifespan

@dataclass
class McpProxyConfig:
    """
    Configuration model for MCP proxy instances.

    This model holds the configuration for a single MCP proxy,
    including its name and the associated FastMCP server instance.

    Attributes:
        path: The path identifier for the proxy
        mcp_server: The FastMCP server instance
    """
    path: str
    mcp_server: FastMCP

    def http_app(self, path: str = "/")-> "StarletteWithLifespan":
        """Return the underlying ASGI application for this MCP proxy."""
        return self.mcp_server.http_app(path=path, transport=SERVER_TRANSPORT or "streamable-http") # type: ignore
    
class StaticMcpProvider(ABC):
    """Abstract base class for MCP provider implementations."""

    def __init__(self, config: SpecConfig) -> None:
        """Initialize the StaticMcpProvider.

        Args:
            config: The SpecConfig instance for this provider.
        """
        self.config = config

    def _get_middlewares(self) -> list[Middleware]:
        """Get the list of middlewares to apply to the FastMCP server.

        Returns:
            A list of Starlette Middleware instances.
        """
        #from src.middleware.auth_header_middleware import AuthHeaderMiddleware
        return []
    
    @abstractmethod
    def create_proxy(self) -> "FastMCP":
        """
        Create and return a FastMCP instance based on the loaded configurations.
        
        This method loads the configurations if they haven't been loaded yet,
        sets up MCP services for both MCP and OpenAPI configurations, and
        returns a list of McpProxyConfig instances containing the server details.
        
        Returns:
            FastMCP instance with initialized proxy configurations
        """
        pass

    def get_mcp_proxy_config(self) -> McpProxyConfig:
        service = self.create_proxy()
        for middleware in self._get_middlewares():
            service.add_middleware(middleware)

        return McpProxyConfig(path=self.config.path, mcp_server=service)

    def _get_global_auth_provider(self, provider_name: AuthProviderType | None = None) -> AuthProvider | None:
        """Create and return an authentication handler.

        Returns:
            An Authentication provider instance for the provider.
        """
        from app import GlobalAuthProvider
        return GlobalAuthProvider.get_auth_provider(provider_name)
    
    @staticmethod
    def _scope_value(config: AzureAuthConfig) -> str | None:
        if not config.scopes:
            return None
        return " ".join(config.scopes)
    
    def _create_client_auth(self, azure_config: AzureAuthConfig) -> "Auth":
        if self.config.auth and self.config.auth.pass_through:
            from auth_providers import AuthPassThrough
            return AuthPassThrough()
        
        from src.app.cache_provider import CacheProvider
        
        scope_value = self._scope_value(azure_config)
        auth = AzureOauth(
            client_id=azure_config.client_id,
            client_secret=azure_config.client_secret,
            token_url=azure_config.token_url,
            scope=scope_value,
            token_storage=CacheProvider.get_oauth_store()
        )

        return auth
