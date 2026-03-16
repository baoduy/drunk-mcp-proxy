"""Remote on-demand agent provider backed by HTTPS fetch and TTL cache.

Exposes a single agent markdown file hosted at a remote HTTPS URL as an
MCP resource without downloading to local disk at startup.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from pydantic import AnyUrl, PrivateAttr
from fastmcp.resources.resource import Resource
from fastmcp.resources.template import ResourceTemplate
from fastmcp.server.providers.base import Provider
from fastmcp.utilities.versions import VersionSpec

from drunk_ai_proxy.proxies.resource.on_demand_remote_resource_service import (
    OnDemandRemoteResourceService,
)
from drunk_ai_proxy.utils.config_yaml import OnDemandRemoteResourceConfig
from drunk_ai_proxy.utils.config_yaml_uri import ConfigYamlUriBuilder
from drunk_ai_proxy.utils.protocols import TokenStore

import httpx
from fastmcp.utilities import logging

logger = logging.get_logger(__name__)

_MANIFEST_SUFFIX = "_manifest"


class RemoteAgentResource(Resource):
    """A resource backed by a remote HTTPS agent markdown file or synthetic manifest."""

    agent_name: str
    """Logical agent identifier."""

    remote_url: str | None = None
    """HTTPS source URL; ``None`` for synthetic manifest resources."""

    remote_uri: str
    """MCP resource URI for the agent content (without ``/_manifest`` suffix)."""

    remote_headers: dict[str, str] | None = None
    is_manifest: bool = False
    """When ``True``, ``read()`` generates a JSON manifest instead of fetching."""

    # Non-serialisable private state injected after construction.
    _service: OnDemandRemoteResourceService | None = PrivateAttr(default=None)

    def bind_service(self, service: OnDemandRemoteResourceService) -> None:
        """Bind the fetch/cache service to this resource instance.

        Args:
            service: The on-demand remote resource service to use for fetching.
        """
        self._service = service

    async def read(self) -> str | bytes:
        """Return resource content \u2014 fetched remotely or generated as manifest.

        Returns:
            JSON manifest string when ``is_manifest`` is ``True``, otherwise
            the decoded text content of the remote agent markdown file.
        """
        if self.is_manifest:
            return self._generate_manifest()
        assert self._service is not None, "Service not bound; call bind_service() first"
        assert self.remote_url is not None, "remote_url required for non-manifest resources"
        return await self._service.get_content(
            uri=self.remote_uri,
            url=self.remote_url,
            headers=self.remote_headers,
        )

    def _generate_manifest(self) -> str:
        """Generate a JSON manifest for this remote agent.

        Returns:
            JSON string with agent name, source URL, and content URI.
        """
        manifest = {
            "agent": self.agent_name,
            "url": self.remote_url,
            "uri": self.remote_uri,
        }
        return json.dumps(manifest, indent=2)


class RemoteAgentProvider(Provider):
    """Provider that serves a single remote agent as an MCP resource.

    A remote agent is a single HTTPS URL pointing to a markdown file.  The
    content is fetched on first access and cached by TTL.  The derived URI
    follows the ``agent://<name>`` scheme.

    Args:
        config: Normalized remote resource configuration entry (must use ``url``).
        cache: TTL cache store.
        http_client: Shared async HTTP client.
    """

    def __init__(
        self,
        config: OnDemandRemoteResourceConfig,
        cache: TokenStore,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Initialize the remote agent provider.

        Args:
            config: Remote resource configuration (must use ``url``).
            cache: TTL cache store instance.
            http_client: Shared httpx async client.

        Raises:
            ValueError: If ``url`` is missing from the config entry.
        """
        super().__init__()
        if not config.url:
            raise ValueError(
                f"RemoteAgentProvider requires single 'url' for entry '{config.name}'"
            )

        self._config = config
        self._service = OnDemandRemoteResourceService(cache=cache, http_client=http_client)
        self._resource_uri: str = ConfigYamlUriBuilder.build_agent_resource_uri(
            config.url,
            resource_name=config.name,
        )
        # Derive agent name from the content URI (agent://<name>)
        uri_parts = self._resource_uri.split("://", 1)
        self._agent_name: str = uri_parts[1] if len(uri_parts) == 2 else config.name

    def _build_content_resource(self) -> RemoteAgentResource:
        """Build the content resource descriptor for this agent."""
        resource = RemoteAgentResource(
            uri=AnyUrl(self._resource_uri),
            name=self._agent_name,
            description=f"Remote agent: {self._config.name}",
            mime_type="text/markdown",
            agent_name=self._agent_name,
            remote_url=self._config.url,
            remote_uri=self._resource_uri,
            remote_headers=self._config.headers,
            is_manifest=False,
        )
        resource.bind_service(self._service)
        return resource

    def _build_manifest_resource(self) -> RemoteAgentResource:
        """Build the synthetic JSON manifest resource for this agent."""
        manifest_uri = f"{self._resource_uri}/{_MANIFEST_SUFFIX}"
        return RemoteAgentResource(
            uri=AnyUrl(manifest_uri),
            name=f"{self._agent_name}/{_MANIFEST_SUFFIX}",
            description=f"Manifest for remote agent: {self._config.name}",
            mime_type="application/json",
            agent_name=self._agent_name,
            remote_url=self._config.url,
            remote_uri=self._resource_uri,
            remote_headers=None,
            is_manifest=True,
        )

    async def _list_resources(self) -> Sequence[Resource]:
        """Return content and manifest resource descriptors for this agent."""
        return [self._build_content_resource(), self._build_manifest_resource()]

    async def _list_resource_templates(self) -> Sequence[ResourceTemplate]:
        return []

    async def _get_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> Resource | None:
        """Return resource descriptor if the URI belongs to this provider."""
        if uri == self._resource_uri:
            return self._build_content_resource()
        if uri == f"{self._resource_uri}/{_MANIFEST_SUFFIX}":
            return self._build_manifest_resource()
        return None

    async def _get_resource_template(
        self, uri: str, version: VersionSpec | None = None
    ) -> ResourceTemplate | None:
        return None
