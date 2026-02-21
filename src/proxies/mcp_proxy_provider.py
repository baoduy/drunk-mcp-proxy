"""MCP Proxy Provider module.

This module provides a class for creating FastMCP instances from MCP configurations.
"""
from __future__ import annotations
from fastmcp import FastMCP

from proxies.static_mcp_provider import StaticMcpProvider, McpProxyConfig
from tools import SpecConfig
from tools.env import SERVER_NAME, SERVER_VERSION
from tools.logging_config import setup_logging

class McpProxyProvider(StaticMcpProvider):
    """Provider class for creating FastMCP instances from MCP configurations."""

    def __init__(self, config: SpecConfig, root_mcp:FastMCP|None=None) -> None:
        super().__init__(config)
        self.root_mcp = root_mcp
        self.mcp: FastMCP | None = None
        self.logger = setup_logging(__name__)

    def _create_proxy(self, mcp:FastMCP):
        if self.config.spec_data is None:
            self.logger.warning(f"spec_data or mcp_servers is required for MCP config '{self.config.path}'")
            return None
        
        self.logger.info("Creating proxy for MCP config: %s", self.config.path)
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
        self.mcp.auth = super()._get_global_auth_provider()
        self._create_proxy(self.mcp)
        self._create_skill_proxy(self.mcp)

        return self.mcp

    @staticmethod
    def create_mcp_proxies_configs(configs: list[SpecConfig]) -> list[McpProxyConfig]:
        """
        Create MCP proxy configurations from a list of SpecConfig instances.
        
        This method handles the special case of root MCP ("/") which serves as
        the main MCP server, and creates individual FastMCP instances for other paths.
        
        Args:
            configs: List of MCP SpecConfig instances
            
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        logger = setup_logging(__name__)
        
        if len(configs) == 0:
            logger.warning("No MCP configurations found")
            return []

        root_mcp = FastMCP(SERVER_NAME, version=SERVER_VERSION)
        mcp_proxy_configs: list[McpProxyConfig] = [McpProxyConfig(path="/", mcp_server=root_mcp)]

        for config in configs:
            if config.spec_data is None:
                logger.warning(f"Skipping MCP config '{config.path}' because spec_data is None")
                continue

            mcp=McpProxyProvider(config, root_mcp=root_mcp)
            mcp_proxy_configs.append(mcp.get_mcp_proxy_config())

        return mcp_proxy_configs
