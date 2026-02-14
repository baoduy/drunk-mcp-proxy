"""
Proxies package.

This package contains loaders for creating MCP proxies and servers:
- StaticProxyLoader: Creates proxies to remote MCP servers from *.mcp.json files
- OpenApiMcpProxyLoader: Creates MCP servers from OpenAPI specifications in *.openapi.json files
"""

from .openapi_proxies import OpenApiMcpProxyLoader, create_openapi_servers
from .static_proxies import StaticProxyLoader, create_static_proxies

__all__ = [
    "StaticProxyLoader",
    "create_static_proxies",
    "OpenApiMcpProxyLoader",
    "create_openapi_servers",
]
