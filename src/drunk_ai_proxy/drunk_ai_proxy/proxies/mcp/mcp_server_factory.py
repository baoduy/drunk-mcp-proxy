"""Factory helpers for creating and configuring FastMCP server instances."""

from __future__ import annotations

from fastmcp import FastMCP

from drunk_ai_proxy.proxies.mcp.mcp_proxy_builder import McpProxyBuilder
from drunk_ai_proxy.utils.env import SERVER_NAME, SERVER_VERSION


class McpServerFactory:
    """Factory for constructing configured FastMCP server instances."""

    @staticmethod
    def create(
        path: str,
        codemode_enabled: bool,
        server_name: str = SERVER_NAME,
        server_version: str = SERVER_VERSION,
    ) -> FastMCP:
        """Create a new FastMCP server for a given route path."""
        return McpProxyBuilder.create_fastmcp_server(
            f"{server_name}{path}",
            server_version,
            codemode_enabled,
        )

    @staticmethod
    def configure_auth(server: FastMCP, auth_provider: object | None) -> None:
        """Attach auth provider to server when provided."""
        server.auth = auth_provider
