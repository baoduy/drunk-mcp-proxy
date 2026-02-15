"""
Proxy configuration provider module.

This module provides a centralized class for loading and managing proxy
configurations using SpecConfig from the CONFIG_DIR/config.json file.
"""

import os
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server import create_proxy

from src.tools.env import CONFIG_DIR, SERVER_NAME, SERVER_VERSION
from src.tools.logging_config import setup_logging
from src.tools.spec_config import SpecConfig
from .mcp_proxy_config import McpProxyConfig
from ..tools.spec_config import SpecType


class ProxyConfigProvider:
    """
    Provider class for loading and managing proxy configurations.
    
    This class uses SpecConfig to load proxy configurations from the
    config.json file located in the CONFIG_DIR directory. It handles
    both OpenAPI and MCP specification configurations.
    
    Attributes:
        config_dir: Directory containing configuration files
        config_file_path: Full path to the config.json file
        configs: List of loaded SpecConfig instances
        logger: Logger instance for this class
    
    Example:
        provider = ProxyConfigProvider()
        provider.load_configs()
        
        for config in provider.configs:
            print(f"Loaded {config.name} ({config.spec_type})")
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the ProxyConfigProvider.
        
        Args:
            config_dir: Optional custom config directory. If not provided,
                       uses the CONFIG_DIR from environment variables.
        """
        self.config_dir = config_dir or CONFIG_DIR
        self.config_file_path = os.path.join(self.config_dir, "config.json")
        self.configs: list[SpecConfig] = []
        self.logger = setup_logging(__name__)

    def _load_configs(self) -> list[SpecConfig]:
        """
        Load proxy configurations from config.json file.
        
        This method uses SpecConfig.load_from_file() to load and validate
        all proxy configurations. Each config's spec file is also loaded
        and validated during this process.
        
        Returns:
            List of loaded and validated SpecConfig instances
            
        Raises:
            FileNotFoundError: If config.json or any spec file doesn't exist
            json.JSONDecodeError: If any JSON file is invalid
            ValueError: If validation fails for any configuration
        
        Example:
            provider = ProxyConfigProvider()
            configs = provider.load_configs()
            print(f"Loaded {len(configs)} configurations")
        """
        self.logger.info(f"Loading proxy configurations from: {self.config_file_path}")

        if (len(self.configs) > 0):
            self.logger.info(f"Proxy configurations already loaded, returning cached configs")
            return self.configs

        try:
            self.configs = SpecConfig.load_from_file(self.config_file_path)
            self.logger.info(f"Successfully loaded {len(self.configs)} proxy configurations")
            return self.configs

        except FileNotFoundError as e:
            self.logger.error(f"Configuration file not found: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load configurations: {e}")
            raise

    def _get_configs_by_type(self, spec_type: SpecType) -> list[SpecConfig]:
        """
        Get all configurations of a specific type.
        
        Args:
            spec_type: Type of specification ("openapi" or "mcp")
            
        Returns:
            List of SpecConfig instances matching the specified type
            
        Example:
            provider = ProxyConfigProvider()
            provider.load_configs()
            openapi_configs = provider.get_configs_by_type("openapi")
            mcp_configs = provider.get_configs_by_type("mcp")
        """
        self._load_configs()
        return [config for config in self.configs if config.spec_type == spec_type]

    def _get_mcp_services(self) -> list[McpProxyConfig]:
        """
        Set up MCP services based on loaded MCP configurations.
        
        This method creates FastMCP server instances for each MCP configuration
        and returns a list of McpProxyConfig containing the server details.
        
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        mcp_configs = self.mcp_configs
        if len(mcp_configs) == 0:
            self.logger.warning("No MCP configurations found in config file")
            return []

        root_mcp = FastMCP(SERVER_NAME, version=SERVER_VERSION)

        mcp_proxy_configs: list[McpProxyConfig] = [McpProxyConfig(name="root", mcp_server=root_mcp)]

        for config in mcp_configs:
            if config.spec_data is None:
                self.logger.warning(f"Skipping MCP config '{config.name}' because spec_data is None")
                continue

            proxy = create_proxy(config.spec_data, name=config.name)
            if config.path == "/":
                root_mcp.mount(proxy, namespace=config.namespace)
                self.logger.info(f"Set up MCP proxy for config: {config.name} at root (path='/')")
            else:
                mcp = FastMCP(f"{SERVER_NAME}-{config.name}", version=SERVER_VERSION)
                mcp.mount(proxy, namespace=config.namespace)
                mcp_proxy_configs.append(McpProxyConfig(name=config.name, mcp_server=mcp))
                self.logger.info(f"Set up MCP proxy for config: {config.name}, path='{config.path}')")

        return mcp_proxy_configs

    def _get_openapi_services(self) -> list[McpProxyConfig]:
        """
        Set up MCP services based on loaded MCP configurations.
        
        This method creates FastMCP server instances for each MCP configuration
        and returns a list of McpProxyConfig containing the server details.
        
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        # Import here to avoid circular dependency
        from .openapi_mcp_provider import OpenApiMcpProvider

        openapi_configs = self.openapi_configs
        if len(openapi_configs) == 0:
            self.logger.warning("No OpenAPI configurations found in config file")
            return []

        mcp_proxy_configs: list[McpProxyConfig] = []
        for config in openapi_configs:
            if config.spec_data is None:
                self.logger.warning(f"Skipping OpenAPI config '{config.name}' because spec_data is None")
                continue

            mcp = OpenApiMcpProvider(config).create_proxy()
            mcp_proxy_configs.append(McpProxyConfig(name=config.name, mcp_server=mcp))
            self.logger.info(f"Set up OpenAPI proxy for config: {config.name}, path='{config.path}')")
        return mcp_proxy_configs

    def get_config_services(self) -> list[McpProxyConfig]:
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
    def openapi_configs(self) -> list[SpecConfig]:
        """
        Get all OpenAPI configurations.
        
        Returns:
            List of SpecConfig instances with spec_type="openapi"
        """
        return self._get_configs_by_type(SpecType.OPENAPI)

    @property
    def mcp_configs(self) -> list[SpecConfig]:
        """
        Get all MCP configurations.
        
        Returns:
            List of SpecConfig instances with spec_type="mcp"
        """
        return self._get_configs_by_type(SpecType.MCP)
