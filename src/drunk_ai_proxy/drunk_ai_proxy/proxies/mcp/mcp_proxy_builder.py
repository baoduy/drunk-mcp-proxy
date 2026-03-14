"""MCP proxy configuration builders."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from fastmcp import FastMCP
from fastmcp.server.transforms import Transform

from drunk_ai_proxy.proxies.mcp.base_provider import McpBaseProvider, McpProxyConfig
from drunk_ai_proxy.utils import McpConfig
from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

class McpProxyBuilder:
    """Class-based builders for MCP proxy configuration objects."""

    @staticmethod
    def _get_code_mode_transforms(codemode_enabled: bool) -> list[Transform]:
        if not codemode_enabled:
            return []

        from fastmcp.experimental.transforms.code_mode import CodeMode
        from fastmcp.experimental.transforms.code_mode import GetSchemas
        from fastmcp.experimental.transforms.code_mode import Search
        #from fastmcp.server.transforms.search import (RegexSearchTransform, BM25SearchTransform)
     
        code_mode = CodeMode(
            discovery_tools=[Search(default_detail="detailed"), GetSchemas()]
        )
        logger.info("Code Mode is enabled")
        return [code_mode]

    @staticmethod
    def get_transforms(codemode_enabled: bool) -> Sequence[Transform]:
        """Get the appropriate transforms based on MCP route configuration."""
        return McpProxyBuilder._get_code_mode_transforms(codemode_enabled)

    @classmethod
    def create_fastmcp_server(
        cls,
        server_name: str,
        server_version: str,
        codemode_enabled: bool,
    ) -> FastMCP:
        """Create a FastMCP server with optional Code Mode transforms."""
        transforms = cls.get_transforms(codemode_enabled)
        if transforms:
            return FastMCP(server_name, version=server_version, transforms=transforms)
        return FastMCP(server_name, version=server_version)

    @classmethod
    def build_mcp_proxy_configs(
        cls,
        configs: list[McpConfig],
        provider_factory: Callable[[McpConfig, FastMCP], McpBaseProvider],
        server_name: str,
        server_version: str,
    ) -> list[McpProxyConfig]:
        """Build MCP proxy configs with a shared root MCP server."""
        if not configs:
            logger.warning("No MCP configurations found")
            return []

        root_config = next((config for config in configs if config.path == "/"), None)
        root_codemode_enabled = getattr(root_config, "codemode_enabled", True)

        root_mcp = cls.create_fastmcp_server(
            server_name,
            server_version,
            root_codemode_enabled,
        )
        proxy_configs: list[McpProxyConfig] = [McpProxyConfig(path="/", mcp_server=root_mcp)]

        for config in configs:
            provider = provider_factory(config, root_mcp)
            proxy_configs.append(provider.get_mcp_proxy_config())

        return proxy_configs

    @staticmethod
    def build_openapi_proxy_configs(
        configs: list[McpConfig],
        provider_factory: Callable[[McpConfig], McpBaseProvider],
    ) -> list[McpProxyConfig]:
        """Build MCP proxy configs for OpenAPI providers."""
        proxy_configs: list[McpProxyConfig] = []
        for config in configs:
            if config.get_openapi_spec_data() is None:
                continue

            provider = provider_factory(config)
            proxy_configs.append(provider.get_mcp_proxy_config())

        return proxy_configs
