"""MCP Base Provider abstract base class.

This module provides an abstract base class for creating MCP provider implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from dataclasses import dataclass
from drunk_ai_proxy.utils import audit_log
from drunk_ai_proxy.utils.protocols import AuthProviderFactory
from drunk_ai_proxy.utils.env import SERVER_TRANSPORT

if TYPE_CHECKING:
    from drunk_ai_proxy.utils import McpConfig
    from fastmcp.server.auth import AuthProvider
    from httpx import Auth
    from fastmcp import FastMCP
    from fastmcp.server.middleware import Middleware
    from fastmcp.server.http import StarletteWithLifespan

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class AppConfigProvider:
    """Compatibility shim for tests patching legacy AppConfigProvider path."""

    @staticmethod
    def get_instance() -> None:
        return None

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

    def __init__(
        self,
        config: McpConfig,
        auth_factory: AuthProviderFactory | None = None,
    ) -> None:
        """Initialize the McpBaseProvider.

        Args:
            config: The McpConfig instance for this provider.
            auth_factory: Optional authentication provider factory.
        """
        self.config = config
        self._auth_factory = auth_factory

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
        if self._auth_factory is None:
            return None

        auth_provider = self._auth_factory.get_fast_mcp_auth_provider()
        return auth_provider if auth_provider is None else auth_provider

    def _validate_resource_directories(
        self,
        dirs: list[str],
        resource_type: str,
    ) -> list["Path"]:
        """Return resolved paths for directories with at least one markdown file.

        Emits warning logs for skipped directories.

        Args:
            dirs: Directory names relative to CONFIG_DIR unless absolute.
            resource_type: Resource label for warning messages.

        Returns:
            List of valid directory paths.
        """
        from pathlib import Path

        from drunk_ai_proxy.utils.env import CONFIG_DIR

        valid_paths: list[Path] = []
        for resource_dir in dirs:
            resource_path = Path(resource_dir)
            if not resource_path.is_absolute():
                resource_path = Path(CONFIG_DIR) / resource_path

            if not resource_path.exists() or not resource_path.is_dir():
                logger.warning(
                    "Skipping %s directory for path '%s' because it does not exist: %s",
                    resource_type,
                    self.config.path,
                    resource_path,
                )
                continue

            md_file_count = sum(1 for _ in resource_path.rglob("*.md"))
            if md_file_count < 1:
                logger.warning(
                    "Skipping %s directory for path '%s' because it has no markdown files: %s",
                    resource_type,
                    self.config.path,
                    resource_path,
                )
                continue

            valid_paths.append(resource_path)

        return valid_paths

    def _add_skill_proxy(self, mcp: FastMCP):
        skill_dirs = self.config.get_skill_dirs()
        if not skill_dirs:
            return

        from drunk_ai_proxy.proxies.mcp.custom_skills_directory_provider import (
            CustomSkillsDirectoryProvider,
        )

        skill_dir_paths = self._validate_resource_directories(skill_dirs, "skill")

        if not skill_dir_paths:
            return

        try:
            provider = CustomSkillsDirectoryProvider(roots=skill_dir_paths, reload=True)
            if not provider.providers:
                return

            mcp.add_provider(provider)
        except Exception as e:
            logger.error(
                "Failed to create skill provider for path '%s': %s",
                self.config.path,
                type(e).__name__,
            )
            audit_log(
                logger=logger,
                event="mcp_skill_provider_failed",
                status="failure",
                resource=self.config.path,
                details={"error_type": type(e).__name__},
            )

    def _add_remote_skill_proxy(self, mcp: FastMCP) -> None:
        """Mount remote on-demand skill providers from section-level remote_resources.

        Each entry in ``skills.remote_resources`` is wired to a
        :class:`~drunk_ai_proxy.proxies.mcp.remote_skill_provider.RemoteSkillProvider`
        backed by the shared on-demand service.

        Args:
            mcp: FastMCP instance to mount skill providers to.
        """
        remote_skills = self.config.get_skill_remote_resources()
        if not remote_skills:
            return

        if self.config.get_skill_dirs():
            logger.warning(
                "Path '%s' has both skills.dirs and skills.remote_resources configured. "
                "Local and remote skill URIs may overlap if names collide.",
                self.config.path,
            )

        from drunk_ai_proxy.app.cache_provider import CacheProvider
        from drunk_ai_proxy.proxies.mcp.remote_skill_provider import RemoteSkillProvider
        import httpx

        cache = CacheProvider.get_cache_store()
        http_client = httpx.AsyncClient()

        for entry in remote_skills:
            try:
                provider = RemoteSkillProvider(
                    config=entry,
                    cache=cache,
                    http_client=http_client,
                )
                mcp.add_provider(provider)
                logger.info(
                    "Registered remote skill provider '%s' for path '%s'",
                    entry.name,
                    self.config.path,
                )
            except Exception as e:
                logger.error(
                    "Failed to create remote skill provider '%s' for path '%s': %s",
                    entry.name,
                    self.config.path,
                    type(e).__name__,
                )
                audit_log(
                    logger=logger,
                    event="mcp_remote_skill_provider_failed",
                    status="failure",
                    resource=self.config.path,
                    details={"entry_name": entry.name, "error_type": type(e).__name__},
                )

    def _add_agent_proxy(self, mcp: FastMCP) -> None:
        """Create and mount agent provider if agents are configured.
        
        Args:
            mcp: FastMCP instance to mount agent provider to.
        """
        agent_dirs = self.config.get_agent_dirs()
        if not agent_dirs:
            return

        from drunk_ai_proxy.proxies.agent.custom_agents_directory_provider import (
            CustomAgentsDirectoryProvider,
        )

        agents_dir_paths = self._validate_resource_directories(agent_dirs, "agent")

        if not agents_dir_paths:
            return

        try:
            provider = CustomAgentsDirectoryProvider(roots=agents_dir_paths, reload=True)
            if not provider.providers:
                return

            mcp.add_provider(provider)
            logger.info(
                "Registered agent provider for path '%s' from directory: %s",
                self.config.path,
                ",".join(agent_dirs),
            )
        except Exception as e:
            logger.error(
                "Failed to create agent provider for path '%s': %s",
                self.config.path,
                type(e).__name__,
            )
            audit_log(
                logger=logger,
                event="mcp_agent_provider_failed",
                status="failure",
                resource=self.config.path,
                details={"error_type": type(e).__name__},
            )

    def _add_remote_agent_proxy(self, mcp: FastMCP) -> None:
        """Mount remote on-demand agent providers from section-level remote_resources.

        Each entry in ``agents.remote_resources`` is wired to a
        :class:`~drunk_ai_proxy.proxies.mcp.remote_agent_provider.RemoteAgentProvider`
        backed by the shared on-demand service.

        Args:
            mcp: FastMCP instance to mount agent providers to.
        """
        remote_agents = self.config.get_agent_remote_resources()
        if not remote_agents:
            return

        if self.config.get_agent_dirs():
            logger.warning(
                "Path '%s' has both agents.dirs and agents.remote_resources configured. "
                "Local and remote agent URIs may overlap if names collide.",
                self.config.path,
            )

        from drunk_ai_proxy.app.cache_provider import CacheProvider
        from drunk_ai_proxy.proxies.mcp.remote_agent_provider import RemoteAgentProvider
        import httpx

        cache = CacheProvider.get_cache_store()
        http_client = httpx.AsyncClient()

        for entry in remote_agents:
            try:
                provider = RemoteAgentProvider(
                    config=entry,
                    cache=cache,
                    http_client=http_client,
                )
                mcp.add_provider(provider)
                logger.info(
                    "Registered remote agent provider '%s' for path '%s'",
                    entry.name,
                    self.config.path,
                )
            except Exception as e:
                logger.error(
                    "Failed to create remote agent provider '%s' for path '%s': %s",
                    entry.name,
                    self.config.path,
                    type(e).__name__,
                )
                audit_log(
                    logger=logger,
                    event="mcp_remote_agent_provider_failed",
                    status="failure",
                    resource=self.config.path,
                    details={"entry_name": entry.name, "error_type": type(e).__name__},
                )

    def _add_remote_prompt_proxy(self, mcp: FastMCP) -> None:
        """Mount remote on-demand prompt providers from section-level remote_resources.

        Each entry in ``prompts.remote_resources`` is wired to a lazy remote
        prompt backed by the shared on-demand service.

        Args:
            mcp: FastMCP instance to register remote prompts to.
        """
        remote_prompts = self.config.get_prompt_remote_resources()
        if not remote_prompts:
            return

        if self.config.get_prompt_dirs():
            logger.warning(
                "Path '%s' has both prompts.dirs and prompts.remote_resources configured. "
                "Local and remote prompt names may collide.",
                self.config.path,
            )

        from drunk_ai_proxy.app.cache_provider import CacheProvider
        from drunk_ai_proxy.proxies.prompt.remote_prompt_provider import RemotePromptProvider
        import httpx

        cache = CacheProvider.get_cache_store()
        http_client = httpx.AsyncClient()

        for entry in remote_prompts:
            try:
                provider = RemotePromptProvider(
                    config=self.config,
                    remote_config=entry,
                    cache=cache,
                    http_client=http_client,
                )
                provider.register_to_mcp(mcp)
                logger.info(
                    "Registered remote prompt '%s' for path '%s'",
                    entry.name,
                    self.config.path,
                )
            except Exception as e:
                logger.error(
                    "Failed to create remote prompt provider '%s' for path '%s': %s",
                    entry.name,
                    self.config.path,
                    type(e).__name__,
                )
                audit_log(
                    logger=logger,
                    event="mcp_remote_prompt_provider_failed",
                    status="failure",
                    resource=self.config.path,
                    details={"entry_name": entry.name, "error_type": type(e).__name__},
                )

    def _create_client_auth(self) -> "Auth | None":
        pass_through = self.config.auth.pass_through if self.config.auth else False
        provider_name = self.config.auth.auth_provider if self.config.auth else None

        if self._auth_factory is None:
            return None

        client_auth_handler = self._auth_factory.get_client_auth_handler(
            provider_name,
            pass_through,
        )
        return client_auth_handler if client_auth_handler is None else client_auth_handler
