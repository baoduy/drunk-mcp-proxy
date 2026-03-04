"""MCP Proxy Provider module.

This module provides a class for creating FastMCP instances from MCP configurations.
"""
from __future__ import annotations
from logging import Logger

from fastmcp import FastMCP
from proxies.mcp_base_provider import McpBaseProvider, McpProxyConfig
from tools import McpConfig
from tools.env import SERVER_NAME, SERVER_VERSION
from tools.logging_config import setup_logging
from tools.mcp_proxy_builder import build_mcp_proxy_configs

class McpProxyProvider(McpBaseProvider):
    """Provider class for creating FastMCP instances from MCP configurations."""

    def __init__(self, config: McpConfig, root_mcp:FastMCP|None=None) -> None:
        super().__init__(config)
        self.root_mcp = root_mcp
        self.mcp: FastMCP | None = None
        self._logger: Logger = setup_logging(__name__)

    def _create_proxy(self, mcp:FastMCP):
        if self.config.spec_data is None:
            self._logger.warning(
                "spec_data or mcp_servers is required for MCP config '%s'",
                self.config.path,
            )
            return None
        
        self._logger.info("Creating proxy for MCP config: %s", self.config.path)
        from fastmcp.server import create_proxy
        proxy= create_proxy(self.config.spec_data, name=self.config.path)
        mcp.mount(proxy)
    
    def create_proxy(self) -> FastMCP:
        """
        Create and return a FastMCP instance based on the MCP configuration.
        
        Returns:
            FastMCP instance with mounted MCP proxy
        """
        if self.mcp is not None:
            return self.mcp

        self.mcp = self.root_mcp if self.config.path == "/" and self.root_mcp is not None else FastMCP(
            f"{SERVER_NAME}{self.config.path}",
            version=SERVER_VERSION
        )
        self.mcp.auth = self._get_app_auth_provider()
        self._create_proxy(self.mcp)
        self._create_skill_proxy(self.mcp)

        return self.mcp

    @staticmethod
    def create_mcp_proxies_configs(configs: list[McpConfig]) -> list[McpProxyConfig]:
        """
        Create MCP proxy configurations from a list of McpConfig instances.
        
        This method handles the special case of root MCP ("/") which serves as
        the main MCP server, and creates individual FastMCP instances for other paths.
        
        Args:
            configs: List of MCP McpConfig instances
            
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        return build_mcp_proxy_configs(
            configs=configs,
            provider_factory=lambda config, root_mcp: McpProxyProvider(
                config,
                root_mcp=root_mcp,
            ),
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
        )
