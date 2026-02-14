"""
Proxies package.

This package contains loaders for creating MCP proxies and servers:
- StaticProxyLoader: Creates proxies to remote MCP servers from *.mcp.json files
- OpenApiMcpProxyLoader: Creates MCP servers from OpenAPI specifications in *.openapi.json files
- ProxyConfigProvider: Loads and manages proxy configurations from config.json
"""

from .config_provider import ProxyConfigProvider

__all__ = [
    "ProxyConfigProvider",
]
