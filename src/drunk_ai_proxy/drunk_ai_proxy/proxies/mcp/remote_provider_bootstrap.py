"""Remote MCP resource provider bootstrap utilities."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

import httpx

from drunk_ai_proxy.utils import audit_log
from drunk_ai_proxy.utils.protocols import TokenStore

from fastmcp.utilities import logging

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from drunk_ai_proxy.utils import McpConfig

logger = logging.get_logger(__name__)

EntryT = TypeVar("EntryT")
ProviderT = TypeVar("ProviderT")


@dataclass(frozen=True)
class RemoteProviderRuntime:
    """Runtime dependencies for remote provider construction."""

    cache: TokenStore
    http_client: httpx.AsyncClient


class RemoteProviderBootstrap:
    """Build and attach remote resource providers for a single MCP config."""

    def __init__(
        self,
        config: McpConfig,
        cache_store: TokenStore | None,
        http_client: httpx.AsyncClient | None,
    ) -> None:
        self._config = config
        self._cache_store = cache_store
        self._http_client = http_client

    def _get_cache_store(self) -> TokenStore:
        if self._cache_store is None:
            raise ValueError(
                "TokenStore dependency is required for remote providers. "
                "Inject cache_store from the composition root."
            )
        return self._cache_store

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    def _build_runtime(self) -> RemoteProviderRuntime:
        return RemoteProviderRuntime(
            cache=self._get_cache_store(),
            http_client=self._get_http_client(),
        )

    def _warn_local_remote_overlap(self, resource_type: str, local_dirs: Sequence[str]) -> None:
        if not local_dirs:
            return
        logger.warning(
            "Path '%s' has both %ss.dirs and %ss.remote_resources configured. "
            "Local and remote %s identifiers may overlap if names collide.",
            self._config.path,
            resource_type,
            resource_type,
            resource_type,
        )

    def _attach_remote_providers(
        self,
        mcp: FastMCP,
        entries: Sequence[EntryT],
        resource_type: str,
        create_provider: Callable[[EntryT], ProviderT],
        register_provider: Callable[[ProviderT, FastMCP], None],
        failure_event: str,
    ) -> None:
        for entry in entries:
            entry_name = getattr(entry, "name", "unknown")
            try:
                provider = create_provider(entry)
                register_provider(provider, mcp)
                logger.info(
                    "Registered remote %s provider '%s' for path '%s'",
                    resource_type,
                    entry_name,
                    self._config.path,
                )
            except Exception as e:
                logger.error(
                    "Failed to create remote %s provider '%s' for path '%s': %s",
                    resource_type,
                    entry_name,
                    self._config.path,
                    type(e).__name__,
                )
                audit_log(
                    logger=logger,
                    event=failure_event,
                    status="failure",
                    resource=self._config.path,
                    details={"entry_name": entry_name, "error_type": type(e).__name__},
                )

    def add_remote_skill_proxy(self, mcp: FastMCP) -> None:
        remote_skills = self._config.get_skill_remote_resources()
        if not remote_skills:
            return

        self._warn_local_remote_overlap("skill", self._config.get_skill_dirs())

        from drunk_ai_proxy.proxies.mcp.remote_skill_provider import RemoteSkillProvider

        runtime = self._build_runtime()
        self._attach_remote_providers(
            mcp=mcp,
            entries=remote_skills,
            resource_type="skill",
            create_provider=lambda entry: RemoteSkillProvider(
                config=entry,
                cache=runtime.cache,
                http_client=runtime.http_client,
            ),
            register_provider=lambda provider, target_mcp: target_mcp.add_provider(provider),
            failure_event="mcp_remote_skill_provider_failed",
        )

    def add_remote_agent_proxy(self, mcp: FastMCP) -> None:
        remote_agents = self._config.get_agent_remote_resources()
        if not remote_agents:
            return

        self._warn_local_remote_overlap("agent", self._config.get_agent_dirs())

        from drunk_ai_proxy.proxies.mcp.remote_agent_provider import RemoteAgentProvider

        runtime = self._build_runtime()
        self._attach_remote_providers(
            mcp=mcp,
            entries=remote_agents,
            resource_type="agent",
            create_provider=lambda entry: RemoteAgentProvider(
                config=entry,
                cache=runtime.cache,
                http_client=runtime.http_client,
            ),
            register_provider=lambda provider, target_mcp: target_mcp.add_provider(provider),
            failure_event="mcp_remote_agent_provider_failed",
        )

    def add_remote_prompt_proxy(self, mcp: FastMCP) -> None:
        remote_prompts = self._config.get_prompt_remote_resources()
        if not remote_prompts:
            return

        self._warn_local_remote_overlap("prompt", self._config.get_prompt_dirs())

        from drunk_ai_proxy.proxies.prompt.remote_prompt_provider import RemotePromptProvider

        runtime = self._build_runtime()
        self._attach_remote_providers(
            mcp=mcp,
            entries=remote_prompts,
            resource_type="prompt",
            create_provider=lambda entry: RemotePromptProvider(
                config=self._config,
                remote_config=entry,
                cache=runtime.cache,
                http_client=runtime.http_client,
            ),
            register_provider=lambda provider, target_mcp: provider.register_to_mcp(target_mcp),
            failure_event="mcp_remote_prompt_provider_failed",
        )
