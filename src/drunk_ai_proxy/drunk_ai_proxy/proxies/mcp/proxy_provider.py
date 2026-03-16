"""MCP Proxy Provider module.

This module provides a class for creating FastMCP instances from MCP configurations.
"""
from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
import httpx
from fastmcp.server.providers import Provider
from fastmcp.server.providers.openapi import MCPType, OpenAPIProvider
from fastmcp.utilities.openapi import HTTPRoute
from drunk_ai_proxy.proxies.mcp.base_provider import McpBaseProvider, McpProxyConfig
from drunk_ai_proxy.utils.protocols import AuthProviderFactory, TokenStore
from drunk_ai_proxy.utils import McpConfig, SpecType, audit_log
from drunk_ai_proxy.utils.env import SERVER_NAME, SERVER_VERSION, CONFIG_DIR
from drunk_ai_proxy.proxies.mcp.mcp_server_factory import McpServerFactory
from drunk_ai_proxy.proxies.mcp.mcp_proxy_builder import McpProxyBuilder

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

class McpProxyProvider(McpBaseProvider):
    """Provider class for creating FastMCP instances from MCP configurations."""

    def __init__(
        self,
        config: McpConfig,
        root_mcp: FastMCP | None = None,
        auth_factory: AuthProviderFactory | None = None,
        cache_store: TokenStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            config,
            auth_factory=auth_factory,
            cache_store=cache_store,
            http_client=http_client,
        )
        self.root_mcp = root_mcp
        self.mcp: FastMCP | None = None

    def _add_mcp_proxy(self, mcp: FastMCP):
        if self.config.spec_data is None:
            return
        
        logger.info("Creating proxy for MCP config: %s", self.config.path)
        from fastmcp.server import create_proxy
        proxy = create_proxy(self.config.spec_data, name=self.config.path)
        mcp.mount(proxy)

    def _get_openapi_filters(self):
        """Return configured OpenAPI filters, if any."""
        return self.config.get_openapi_filters()

    def _openapi_route_mapper(
        self,
        route: HTTPRoute,
        mcp_type: MCPType,
    ) -> MCPType | None:
        """Map OpenAPI routes according to configured filters."""
        filters = self._get_openapi_filters()
        if filters is not None:
            if filters.methods and route.method not in filters.methods:
                return MCPType.EXCLUDE

            if filters.tags and not any(tag in route.tags for tag in filters.tags):
                return MCPType.EXCLUDE

        return mcp_type

    def _create_openapi_client(self) -> httpx.AsyncClient:
        """Create an HTTPX client for OpenAPI-based MCP proxies."""
        base_url = self.config.get_openapi_base_url()
        if not base_url:
            raise ValueError(
                "base_url is required for OpenAPI clients without Azure auth"
            )

        return httpx.AsyncClient(base_url=base_url, auth=self._create_client_auth())

    def _add_open_api_proxy(self, mcp: FastMCP) -> None:
        """Create and attach an OpenAPI provider to the current FastMCP server."""
        client = self._create_openapi_client()
        openapi_spec = self.config.get_openapi_spec_data()
        if openapi_spec is None:
            raise ValueError("open_api.spec_data is required for OpenAPI proxy creation")

        provider: Provider = OpenAPIProvider(
            openapi_spec=openapi_spec,
            client=client,
            route_map_fn=self._openapi_route_mapper,
            tags=self.config.tags,
            validate_output=True,
        )
        mcp.add_provider(provider)
    
    def create_proxy(self) -> FastMCP:
        """
        Create and return a FastMCP instance based on the MCP configuration.
        
        Returns:
            FastMCP instance with mounted MCP proxy
        """
        if self.mcp is not None:
            return self.mcp

        spec_type = getattr(self.config, "spec_type", SpecType.MCP)
        codemode_enabled = getattr(self.config, "codemode_enabled", True)

        if spec_type == SpecType.OPENAPI:
            self.mcp = McpServerFactory.create(
                self.config.path,
                codemode_enabled,
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
            )
            self._add_open_api_proxy(self.mcp)
        else:
            self.mcp = (
                self.root_mcp
                if self.config.path == "/" and self.root_mcp is not None
                else McpServerFactory.create(
                    self.config.path,
                    codemode_enabled,
                    server_name=SERVER_NAME,
                    server_version=SERVER_VERSION,
                )
            )

            self._add_mcp_proxy(self.mcp)

        McpServerFactory.configure_auth(self.mcp, self._get_app_auth_provider())
        self._add_skill_proxy(self.mcp)
        self._add_remote_skill_proxy(self.mcp)
        self._add_prompt_proxy(self.mcp)
        self._add_remote_prompt_proxy(self.mcp)
        self._add_agent_proxy(self.mcp)
        self._add_remote_agent_proxy(self.mcp)

        return self.mcp
    
    def _add_prompt_proxy(self, mcp: FastMCP) -> None:
        """Create and mount prompt provider if prompts are configured.
        
        Args:
            mcp: FastMCP instance to mount prompt provider to.
        """
        prompt_dirs = self.config.get_prompt_dirs()
        if not isinstance(prompt_dirs, list) or not prompt_dirs:
            return

        valid_prompt_paths = self._validate_resource_directories(prompt_dirs, "prompt")
        valid_prompt_path_set = {path.resolve() for path in valid_prompt_paths}
        valid_prompt_dirs = []
        for prompt_dir in prompt_dirs:
            prompt_path = Path(prompt_dir)
            if not prompt_path.is_absolute():
                prompt_path = Path(CONFIG_DIR) / prompt_path
            if prompt_path.resolve() in valid_prompt_path_set:
                valid_prompt_dirs.append(prompt_dir)

        if not valid_prompt_dirs:
            return
        
        try:
            from drunk_ai_proxy.proxies.prompt.prompt_provider import McpPromptProvider
            
            # Register prompts directly into the active MCP server so prompts/list includes them.
            prompt_provider = McpPromptProvider(self.config, prompt_dirs=valid_prompt_dirs)
            loaded_prompt_count = prompt_provider.register_to_mcp(mcp)
            
            logger.info(
                "Registered %d prompt(s) for path '%s' from directories: %s",
                loaded_prompt_count,
                self.config.path,
                ",".join(valid_prompt_dirs),
            )
        except Exception as e:
            logger.error(
                "Failed to create prompt provider for path '%s': %s",
                self.config.path,
                type(e).__name__
            )
            audit_log(
                logger=logger,
                event="mcp_prompt_provider_failed",
                status="failure",
                resource=self.config.path,
                details={"error_type": type(e).__name__},
            )

    @staticmethod
    def _should_include_no_spec_config(config: McpConfig) -> bool:
        """Return whether a config without spec_data should be included.

        Include when remote configuration is explicitly present and non-empty,
        or when configuration intent is unknown (defensive include).
        Skip when local directories are explicitly configured and no explicit
        remote resources are configured.
        """
        skill_remote = config.get_skill_remote_resources()
        prompt_remote = config.get_prompt_remote_resources()
        agent_remote = config.get_agent_remote_resources()

        remote_values = [skill_remote, prompt_remote, agent_remote]
        has_explicit_remote_config = any(isinstance(value, list) for value in remote_values)
        has_remote_resources = any(isinstance(value, list) and bool(value) for value in remote_values)
        if has_explicit_remote_config:
            return has_remote_resources

        local_values = [config.get_skill_dirs(), config.get_prompt_dirs(), config.get_agent_dirs()]
        has_explicit_local_config = any(isinstance(value, list) for value in local_values)
        if has_explicit_local_config:
            return False

        return True

    @staticmethod
    def create_mcp_proxies_configs(
        configs: list[McpConfig],
        auth_factory: AuthProviderFactory | None = None,
        cache_store: TokenStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[McpProxyConfig]:
        """
        Create MCP proxy configurations from a list of McpConfig instances.
        
        This method handles the special case of root MCP ("/") which serves as
        the main MCP server, and creates individual FastMCP instances for other paths.
        
        Args:
            configs: List of MCP McpConfig instances
            
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        filtered_configs = [
            config
            for config in configs
            if config.spec_data is not None
            or McpProxyProvider._should_include_no_spec_config(config)
        ]
        return McpProxyBuilder.build_mcp_proxy_configs(
            configs=filtered_configs,
            provider_factory=lambda config, root_mcp: McpProxyProvider(
                config,
                root_mcp=root_mcp,
                auth_factory=auth_factory,
                cache_store=cache_store,
                http_client=http_client,
            ),
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
        )

    @staticmethod
    def create_openapi_proxies_configs(
        configs: list[McpConfig],
        auth_factory: AuthProviderFactory | None = None,
        cache_store: TokenStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[McpProxyConfig]:
        """Create OpenAPI-backed MCP proxy configurations."""
        return McpProxyBuilder.build_openapi_proxy_configs(
            configs=configs,
            provider_factory=lambda config: McpProxyProvider(
                config=config,
                auth_factory=auth_factory,
                cache_store=cache_store,
                http_client=http_client,
            ),
        )
