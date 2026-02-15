"""
Proxies package.

This package contains loaders for creating MCP proxies and servers:
- StaticProxyLoader: Creates proxies to remote MCP servers from *.mcp.json files
- OpenApiMcpProxyLoader: Creates MCP servers from OpenAPI specifications in *.openapi.json files
- ProxyConfigProvider: Loads and manages proxy configurations from config.json
- OpenApiMcpProvider: Creates FastMCP instances from McpProxyConfig
- McpProxyConfig: Configuration model for MCP proxy instances
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config_provider import ProxyConfigProvider
    from .mcp_proxy_config import McpProxyConfig
    from .openapi_mcp_provider import OpenApiMcpProvider

__all__ = [
    "McpProxyConfig",
    "ProxyConfigProvider",
    "OpenApiMcpProvider",
]


def __getattr__(name: str):
    if name == "McpProxyConfig":
        from .mcp_proxy_config import McpProxyConfig

        return McpProxyConfig
    if name == "ProxyConfigProvider":
        from .config_provider import ProxyConfigProvider

        return ProxyConfigProvider
    if name == "OpenApiMcpProvider":
        from .openapi_mcp_provider import OpenApiMcpProvider

        return OpenApiMcpProvider
    raise AttributeError(f"module 'proxies' has no attribute {name!r}")
