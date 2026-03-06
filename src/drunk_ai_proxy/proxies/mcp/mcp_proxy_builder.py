"""MCP proxy configuration builders."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from logging import Logger

from fastmcp import FastMCP
from fastmcp.server.transforms import Transform

from drunk_ai_proxy.proxies.mcp.base_provider import McpBaseProvider, McpProxyConfig
from drunk_ai_proxy.utils import McpConfig
from drunk_ai_proxy.utils.env import CODEMODE_ENABLED
from drunk_ai_proxy.utils.logging_config import setup_logging


class McpProxyBuilder:
    """Class-based builders for MCP proxy configuration objects."""

    @staticmethod
    def _default_transforms() -> list[Transform]:
        """Default transforms for MCP servers."""
        from fastmcp.server.transforms.search import (RegexSearchTransform, BM25SearchTransform)
        return [RegexSearchTransform(max_results=10),BM25SearchTransform(max_results=3)]
    
    @staticmethod
    def _get_code_mode_transforms() -> list[Transform] | None:
        if not CODEMODE_ENABLED:
            return None

        logger: Logger = setup_logging(__name__)
        from fastmcp.experimental.transforms.code_mode import CodeMode
        from fastmcp.experimental.transforms.code_mode import GetSchemas
        from fastmcp.experimental.transforms.code_mode import Search

        code_mode = CodeMode(
            discovery_tools=[Search(default_detail="detailed"), GetSchemas()]
        )
        logger.info("Code Mode is enabled")
        return [code_mode]

    @staticmethod
    def get_transforms() -> Sequence[Transform]:
        """Get the appropriate transforms based on environment settings."""
        transforms = McpProxyBuilder._default_transforms()
        code_mode_transforms = McpProxyBuilder._get_code_mode_transforms()
        if code_mode_transforms:
            transforms.extend(code_mode_transforms)
        return transforms

    @classmethod
    def create_fastmcp_server(cls, server_name: str, server_version: str) -> FastMCP:
        """Create a FastMCP server with optional Code Mode transforms."""
        transforms = cls.get_transforms()
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
        logger: Logger = setup_logging(__name__)
        if not configs:
            logger.warning("No MCP configurations found")
            return []

        root_mcp = cls.create_fastmcp_server(server_name, server_version)
        proxy_configs: list[McpProxyConfig] = [McpProxyConfig(path="/", mcp_server=root_mcp)]

        for config in configs:
            if config.spec_data is None:
                logger.warning(
                    "Skipping MCP config '%s' because spec_data is None",
                    config.path,
                )
                continue

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
            if config.spec_data is None:
                continue

            provider = provider_factory(config)
            proxy_configs.append(provider.get_mcp_proxy_config())

        return proxy_configs
