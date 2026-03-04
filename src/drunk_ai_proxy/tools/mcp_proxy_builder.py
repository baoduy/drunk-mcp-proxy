"""MCP proxy configuration builders."""

from __future__ import annotations

from collections.abc import Callable
from logging import Logger

from fastmcp import FastMCP

from drunk_ai_proxy.proxies.mcp_base_provider import McpBaseProvider, McpProxyConfig
from drunk_ai_proxy.tools import McpConfig
from drunk_ai_proxy.tools.logging_config import setup_logging


def build_mcp_proxy_configs(
    configs: list[McpConfig],
    provider_factory: Callable[[McpConfig, FastMCP], McpBaseProvider],
    server_name: str,
    server_version: str,
) -> list[McpProxyConfig]:
    """Build MCP proxy configs with a shared root MCP server.

    Args:
        configs: List of MCP configurations.
        provider_factory: Factory that returns a provider for a config and root MCP.
        server_name: Service name for root MCP.
        server_version: Service version for root MCP.

    Returns:
        List of MCP proxy configs.
    """
    logger: Logger = setup_logging(__name__)
    if not configs:
        logger.warning("No MCP configurations found")
        return []

    root_mcp = FastMCP(server_name, version=server_version)
    proxy_configs: list[McpProxyConfig] = [
        McpProxyConfig(path="/", mcp_server=root_mcp)
    ]

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


def build_openapi_proxy_configs(
    configs: list[McpConfig],
    provider_factory: Callable[[McpConfig], McpBaseProvider],
) -> list[McpProxyConfig]:
    """Build MCP proxy configs for OpenAPI providers.

    Args:
        configs: List of MCP configurations.
        provider_factory: Factory that returns a provider for a config.

    Returns:
        List of MCP proxy configs.
    """
    proxy_configs: list[McpProxyConfig] = []
    for config in configs:
        if config.spec_data is None:
            continue

        provider = provider_factory(config)
        proxy_configs.append(provider.get_mcp_proxy_config())

    return proxy_configs
