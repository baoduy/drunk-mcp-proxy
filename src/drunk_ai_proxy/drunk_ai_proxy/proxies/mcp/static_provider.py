"""Static MCP/OpenAPI proxy configuration provider module."""

from typing import TYPE_CHECKING
from drunk_ai_proxy.utils import SpecType, McpConfig
from drunk_ai_proxy.utils.protocols import AuthProviderFactory

if TYPE_CHECKING:
    from .base_provider import McpProxyConfig

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

class StaticProxiesProvider:
    """Provider class for loading and managing static proxy configurations.

    This class uses `McpConfig` instances loaded from the `mcp` section of
    `config.yaml` and prepares both OpenAPI and MCP specification configs for
    proxy creation.

    Attributes:
        configs: List of loaded `McpConfig` instances.
    """

    def __init__(
        self,
        configs: list[McpConfig],
        auth_factory: AuthProviderFactory | None = None,
    ) -> None:
        """Initialize the StaticProxiesProvider."""
        self.configs = configs
        self._auth_factory = auth_factory

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
        from .proxy_provider import McpProxyProvider
        
        mcp_configs = self.mcp_configs
        if len(mcp_configs) == 0:
            logger.warning("No MCP configurations found in config file")
            return []
        return McpProxyProvider.create_mcp_proxies_configs(
            mcp_configs,
            auth_factory=self._auth_factory,
        )

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
            logger.warning("No OpenAPI configurations found in config file")
            return []
        
        from .proxy_provider import McpProxyProvider

        return McpProxyProvider.create_openapi_proxies_configs(
            openapi_configs,
            auth_factory=self._auth_factory,
        )
        
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
