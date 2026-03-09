"""MCP Base Provider abstract base class.

This module provides an abstract base class for creating MCP provider implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from drunk_ai_proxy.app.app_config_provider import AppConfigProvider
from dataclasses import dataclass
from drunk_ai_proxy.utils.env import SERVER_TRANSPORT

if TYPE_CHECKING:
    from drunk_ai_proxy.utils import McpConfig
    from fastmcp.server.auth import AuthProvider
    from httpx import Auth
    from fastmcp import FastMCP
    from fastmcp.server.middleware import Middleware
    from fastmcp.server.http import StarletteWithLifespan

from drunk_ai_proxy.utils.logging_config import setup_logging
logger = setup_logging(__name__)

@dataclass
class McpProxyConfig:
    """
    Configuration model for MCP proxy instances.

    This model holds the configuration for a single MCP proxy,
    including its name and the associated FastMCP server instance.

    Attributes:
        path: The path identifier for the proxy
        mcp_server: The FastMCP server instance
    """

    path: str
    mcp_server: FastMCP

    def http_app(self, path: str = "/") -> "StarletteWithLifespan":
        """Return the underlying Web application for this MCP proxy."""
        return self.mcp_server.http_app(
            path=path, transport=SERVER_TRANSPORT or "streamable-http"  # type: ignore
        )  # type: ignore


class McpBaseProvider(ABC):
    """Abstract base class for MCP provider implementations."""

    def __init__(self, config: McpConfig) -> None:
        """Initialize the McpBaseProvider.

        Args:
            config: The McpConfig instance for this provider.
        """
        self.config = config

    def _get_middlewares(self) -> list[Middleware]:
        """Get the list of middlewares to apply to the FastMCP server.

        Returns:
            A list of Starlette Middleware instances.
        """
        return []

    @abstractmethod
    def create_proxy(self) -> "FastMCP":
        """
        Create and return a FastMCP instance based on the loaded configurations.

        This method loads the configurations if they haven't been loaded yet,
        sets up MCP services for both MCP and OpenAPI configurations, and
        returns a list of McpProxyConfig instances containing the server details.

        Returns:
            FastMCP instance with initialized proxy configurations
        """
        pass

    def get_mcp_proxy_config(self) -> McpProxyConfig:
        service = self.create_proxy()
        for middleware in self._get_middlewares():
            service.add_middleware(middleware)

        return McpProxyConfig(path=self.config.path, mcp_server=service)

    def _get_app_auth_provider(self) -> "AuthProvider | None":
        """Create and return an authentication handler.

        Returns:
            An Authentication provider instance for the provider.
        """
        # calling AppConfigProvider get_fast_mcp_auth_provider without parameters to get the default auth provider for FastMCP servers
        return AppConfigProvider.get_instance().get_fast_mcp_auth_provider()

    def _create_skill_proxy(self, mcp: FastMCP):
        if self.config.skill_dir is None:
            return

        from pathlib import Path
        from drunk_ai_proxy.utils.env import CONFIG_DIR
        from drunk_ai_proxy.proxies.mcp.custom_skills_directory_provider import (
            CustomSkillsDirectoryProvider,
        )

        skill_dir_path = Path(f"{CONFIG_DIR}/{self.config.skill_dir}")
        if not skill_dir_path.exists():
            # self.logger.warning(f"Skill directory '{self.config.skill_dir}' does not exist for MCP config '{self.config.path}'")
            return

        provider = CustomSkillsDirectoryProvider(roots=[skill_dir_path], reload=False)
        if not provider.providers:
            return

        # self.logger.info("Adding skill provider for MCP config '%s' with %d skill directories: %s",
        #                self.config.path, len(subdirs), [d.name for d in subdirs])
        mcp.add_provider(provider)

    def _create_agent_proxy(self, mcp: FastMCP) -> None:
        """Create and mount agent provider if agents_dir is configured.
        
        Args:
            mcp: FastMCP instance to mount agent provider to.
        """
        agents_dir = getattr(self.config, "agents_dir", None)
        if agents_dir is None:
            return

        from pathlib import Path
        from drunk_ai_proxy.utils.env import CONFIG_DIR
        from drunk_ai_proxy.proxies.agent.custom_agents_directory_provider import (
            CustomAgentsDirectoryProvider,
        )

        agents_dir_path = Path(f"{CONFIG_DIR}/{agents_dir}")
        if not agents_dir_path.exists():
            self._logger.warning(
                "Skipping agent provider for path '%s' because agents_dir does not exist: %s",
                self.config.path,
                agents_dir_path,
            )
            return

        md_file_count = sum(1 for _ in agents_dir_path.rglob("*.md"))
        if md_file_count < 1:
            self._logger.warning(
                "Skipping agent provider for path '%s' because agents_dir must contain at least 1 markdown file (found=%d)",
                self.config.path,
                md_file_count,
            )
            return

        try:
            provider = CustomAgentsDirectoryProvider(roots=[agents_dir_path], reload=False)
            if not provider.providers:
                return

            mcp.add_provider(provider)
            self._logger.info(
                "Registered agent provider for path '%s' from directory: %s",
                self.config.path,
                agents_dir,
            )
        except Exception as e:
            self._logger.error(
                "Failed to create agent provider for path '%s': %s",
                self.config.path,
                type(e).__name__,
            )

    def _create_client_auth(self) -> "Auth | None":
        pass_through = self.config.auth.pass_through if self.config.auth else False
        provider_Name = self.config.auth.auth_provider if self.config.auth else None

        return AppConfigProvider.get_instance().get_client_auth_handler(provider_Name, pass_through)
