"""
Proxies package.

This package contains loaders for creating MCP proxies and servers:
- StaticProxyLoader: Creates proxies to remote MCP servers from *.mcp.json files
- OpenApiMcpProxyLoader: Creates MCP servers from OpenAPI specifications in *.openapi.json files
- ProxyConfigProvider: Loads and manages proxy configurations from config.json
- AuthConfigProvider: Loads and manages authentication configurations from auth.json
- OpenApiMcpProvider: Creates FastMCP instances from McpProxyConfig
- McpProxyConfig: Configuration model for MCP proxy instances
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .static_proxies_provider import StaticProxiesProvider
    from .auth_config_provider import AuthConfigProvider
    from .mcp_proxy_config import McpProxyConfig
    from .openapi_mcp_provider import OpenApiMcpProvider

__all__ = [
    "McpProxyConfig",
    "StaticProxiesProvider",
    "AuthConfigProvider",
    "OpenApiMcpProvider",
]


def __getattr__(name: str):
    if name == "McpProxyConfig":
        from .mcp_proxy_config import McpProxyConfig
        return McpProxyConfig
    
    if name == "StaticProxiesProvider":
        from .static_proxies_provider import StaticProxiesProvider
        return StaticProxiesProvider
    
    if name == "AuthConfigProvider":
        from .auth_config_provider import AuthConfigProvider
        return AuthConfigProvider
    
    if name == "OpenApiMcpProvider":
        from .openapi_mcp_provider import OpenApiMcpProvider
        return OpenApiMcpProvider
    
    raise AttributeError(f"module 'proxies' has no attribute {name!r}")
