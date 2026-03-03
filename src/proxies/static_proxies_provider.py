"""
Proxy configuration provider module.

This module provides a centralized class for loading and managing proxy
configurations using McpConfig from the CONFIG_DIR/config.json file.
"""

import os
from typing import TYPE_CHECKING, Optional
from app.app_config_provider import AppConfigProvider
from tools.logging_config import setup_logging
from tools import SpecType,McpConfig

if TYPE_CHECKING:
    from .mcp_base_provider import McpProxyConfig
    from .mcp_proxy_provider import McpProxyProvider


class StaticProxiesProvider:
    """
    Provider class for loading and managing proxy configurations.
    
    This class uses McpConfig to load proxy configurations from the
    config.json file located in the CONFIG_DIR directory. It handles
    both OpenAPI and MCP specification configurations.
    
    Attributes:
        config_dir: Directory containing configuration files
        config_file_path: Full path to the config.json file
        configs: List of loaded McpConfig instances
        logger: Logger instance for this class
    
    Example:
        provider = ProxyConfigProvider()
        provider.load_configs()
        
        for config in provider.configs:
            print(f"Loaded {config.name} ({config.spec_type})")
    """

    def __init__(self,configs: list[McpConfig]) -> None:
        """
        Initialize the ProxyConfigProvider.
        """
        self.configs = configs
        self.logger = setup_logging(__name__)

    def _get_configs_by_type(self, spec_type: SpecType) -> list[McpConfig]:
        """ Get all configurations of a specific type. """
        return [config for config in self.configs if config.spec_type == spec_type]

    def _get_mcp_services(self) -> list["McpProxyConfig"]:
        """
        Set up MCP services based on loaded MCP configurations.
        
        This method delegates to McpProxyProvider to create FastMCP server 
        instances for each MCP configuration and returns a list of McpProxyConfig 
        containing the server details.
        
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        from .mcp_proxy_provider import McpProxyProvider
        
        mcp_configs = self.mcp_configs
        if len(mcp_configs) == 0:
            self.logger.warning("No MCP configurations found in config file")
            return []
        return McpProxyProvider.create_mcp_proxies_configs(mcp_configs)

    def _get_openapi_services(self) -> list["McpProxyConfig"]:
        """
        Set up MCP services based on loaded MCP configurations.
        
        This method creates FastMCP server instances for each MCP configuration
        and returns a list of McpProxyConfig containing the server details.
        
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        # Import here to avoid circular dependency
        openapi_configs = self.openapi_configs
        if len(openapi_configs) == 0:
            self.logger.warning("No OpenAPI configurations found in config file")
            return []
        
        from .openapi_mcp_provider import OpenApiMcpProvider
        return OpenApiMcpProvider.create_mcp_proxies_configs(openapi_configs)
        
    def get_config_services(self) -> list["McpProxyConfig"]:
        """
        Set up MCP services based on loaded MCP configurations.
        
        This method creates FastMCP server instances for each MCP configuration
        and returns a list of McpProxyConfig containing the server details.
        
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        mcp_proxy_configs = self._get_mcp_services()
        openapi_proxy_configs = self._get_openapi_services()
        mcp_proxy_configs.extend(openapi_proxy_configs)
        return mcp_proxy_configs

    @property
    def openapi_configs(self) -> list[McpConfig]:
        """
        Get all OpenAPI configurations.
        
        Returns:
            List of McpConfig instances with spec_type="openapi"
        """
        return self._get_configs_by_type(SpecType.OPENAPI)

    @property
    def mcp_configs(self) -> list[McpConfig]:
        """
        Get all MCP configurations.
        
        Returns:
            List of McpConfig instances with spec_type="mcp"
        """
        return self._get_configs_by_type(SpecType.MCP)
