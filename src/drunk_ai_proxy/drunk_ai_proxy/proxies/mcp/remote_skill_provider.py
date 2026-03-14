"""Remote on-demand skill provider backed by HTTPS fetch and TTL cache.

Exposes skills that live behind HTTPS URLs as MCP resources without
downloading content to local disk at startup.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import cast

from pydantic import AnyUrl, PrivateAttr
from fastmcp.resources.resource import Resource
from fastmcp.resources.template import ResourceTemplate
from fastmcp.server.providers.base import Provider
from fastmcp.utilities.versions import VersionSpec

from drunk_ai_proxy.app.cache_provider import TTLAsyncKeyValue
from drunk_ai_proxy.proxies.resource.on_demand_remote_resource_service import (
    OnDemandRemoteResourceService,
)
from drunk_ai_proxy.utils.config_yaml import OnDemandRemoteResourceConfig
from drunk_ai_proxy.utils.config_yaml_uri import build_skill_resource_uris

import httpx
from fastmcp.utilities import logging

logger = logging.get_logger(__name__)

_SKILL_MAIN = "SKILL.md"
_MANIFEST_SUFFIX = "_manifest"


class RemoteSkillResource(Resource):
    """A resource backed by a remote HTTPS skill file or synthetic manifest."""

    skill_name: str
    """Logical skill identifier derived from the SKILL.md URL path segment."""

    remote_url: str | None = None
    """HTTPS source URL; ``None`` for synthetic manifest resources."""

    remote_uri: str
    remote_headers: dict[str, str] | None = None
    is_manifest: bool = False
    """When ``True``, ``read()`` generates a JSON file-listing manifest."""

    # Non-serialisable private state injected after construction.
    _service: OnDemandRemoteResourceService | None = PrivateAttr(default=None)
    _uri_map: dict[str, str] = PrivateAttr(default_factory=lambda: cast(dict[str, str], {}))

    def bind_service(self, service: OnDemandRemoteResourceService) -> None:
        """Bind the fetch/cache service used for remote content fetches.

        Args:
            service: The on-demand remote resource service instance.
        """
        self._service = service

    def bind_uri_map(self, uri_map: dict[str, str]) -> None:
        """Bind the URL\u2192URI mapping used to generate the manifest.

        Args:
            uri_map: Dict mapping each remote HTTPS URL to its MCP resource URI.
        """
        self._uri_map = uri_map

    async def read(self) -> str | bytes:
        """Return resource content \u2014 fetched remotely or generated as manifest.

        Returns:
            JSON manifest string when ``is_manifest`` is ``True``, otherwise
            the decoded text content of the remote HTTPS file.
        """
        if self.is_manifest:
            return await self._generate_manifest()
        assert self._service is not None, "Service not bound; call bind_service() first"
        assert self.remote_url is not None, "remote_url required for non-manifest resources"
        return await self._service.get_content(
            uri=self.remote_uri,
            url=self.remote_url,
            headers=self.remote_headers,
        )

    async def _generate_manifest(self) -> str:
        """Generate a JSON manifest listing all files in the remote skill.

        Returns:
            JSON string with the skill name and an entry per file.
        """
        assert self._service is not None, "Service not bound; call bind_service() first"
        files: list[dict[str, str | int]] = []
        for url, uri in self._uri_map.items():
            content = await self._service.get_content(
                uri=uri,
                url=url,
                headers=self.remote_headers,
            )
            content_bytes = content.encode("utf-8")
            files.append(
                {
                    "path": url.rsplit("/", 1)[-1],
                    "size": len(content_bytes),
                    "hash": f"sha256:{hashlib.sha256(content_bytes).hexdigest()}",
                }
            )
        return json.dumps({"skill": self.skill_name, "files": files}, indent=2)


class RemoteSkillProvider(Provider):
    """Provider that serves a single remote skill as MCP resources.

    Each skill may contain multiple URLs; the URL ending with ``SKILL.md``
    maps to the main skill resource URI and all other URLs map to support-file
    resource URIs under the same skill namespace.

    Content is fetched on first access and cached by TTL.

    Args:
        config: Normalized remote resource configuration entry.
        cache: TTL cache store from :class:`~drunk_ai_proxy.app.cache_provider.CacheProvider`.
        http_client: Shared async HTTP client for outbound requests.
    """

    def __init__(
        self,
        config: OnDemandRemoteResourceConfig,
        cache: TTLAsyncKeyValue,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Initialize the remote skill provider.

        Args:
            config: Remote resource configuration (must use ``urls``).
            cache: TTL cache store instance.
            http_client: Shared httpx async client.

        Raises:
            ValueError: If ``urls`` list is missing or contains no SKILL.md entry.
        """
        super().__init__()
        if not config.urls:
            raise ValueError(
                f"RemoteSkillProvider requires 'urls' list for entry '{config.name}'"
            )

        self._config = config
        self._service = OnDemandRemoteResourceService(cache=cache, http_client=http_client)

        # Build URI map: url -> mcp resource uri
        self._uri_map: dict[str, str] = build_skill_resource_uris(
            config.urls,
            resource_name=config.name,
        )
        # Build reverse map: mcp resource uri -> url
        self._reverse_map: dict[str, str] = {v: k for k, v in self._uri_map.items()}
        # Derive skill name from the main URI (skill://<skill_name>/SKILL.md)
        main_uri = next(
            (uri for url, uri in self._uri_map.items() if url.endswith(_SKILL_MAIN)),
            next(iter(self._uri_map.values()), None),
        )
        uri_tail = main_uri.split("://", 1)[1] if main_uri and "://" in main_uri else config.name
        main_suffix = f"/{_SKILL_MAIN}"
        if uri_tail.endswith(main_suffix):
            self._skill_name = uri_tail[: -len(main_suffix)]
        else:
            self._skill_name = uri_tail
        self._legacy_main_uri: str = f"skill://{self._skill_name}"
        self._main_uri: str = f"skill://{self._skill_name}/{_SKILL_MAIN}"

    async def _list_resources(self) -> Sequence[Resource]:
        """Return the list of resource descriptors for this skill."""
        resources: list[Resource] = []
        for url, uri in self._uri_map.items():
            filename = url.rsplit("/", 1)[-1]
            is_main = filename == _SKILL_MAIN
            mime_type = "text/markdown" if filename.endswith(".md") else "text/plain"
            name = self._uri_map_to_name(uri)
            resource = RemoteSkillResource(
                uri=AnyUrl(uri),
                name=name,
                description=(
                    f"Remote skill: {self._config.name}"
                    if is_main
                    else f"Remote skill support file: {filename}"
                ),
                mime_type=mime_type,
                skill_name=self._skill_name,
                remote_url=url,
                remote_uri=uri,
                remote_headers=self._config.headers,
            )
            resource.bind_service(self._service)
            resources.append(resource)
        resources.append(self._build_manifest_resource())
        return resources

    async def _list_resource_templates(self) -> Sequence[ResourceTemplate]:
        return []

    async def _get_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> Resource | None:
        """Return resource descriptor if the URI belongs to this provider."""
        if uri == f"skill://{self._skill_name}/{_MANIFEST_SUFFIX}":
            return self._build_manifest_resource()
        if uri == self._legacy_main_uri and self._main_uri in self._reverse_map:
            uri = self._main_uri
        if uri not in self._reverse_map:
            return None

        url = self._reverse_map[uri]
        filename = url.rsplit("/", 1)[-1]
        mime_type = "text/markdown" if filename.endswith(".md") else "text/plain"
        name = self._uri_map_to_name(uri)
        resource = RemoteSkillResource(
            uri=AnyUrl(uri),
            name=name,
            description=f"Remote skill file: {filename}",
            mime_type=mime_type,
            skill_name=self._skill_name,
            remote_url=url,
            remote_uri=uri,
            remote_headers=self._config.headers,
        )
        resource.bind_service(self._service)
        return resource

    async def _get_resource_template(
        self, uri: str, version: VersionSpec | None = None
    ) -> ResourceTemplate | None:
        return None

    def _build_manifest_resource(self) -> "RemoteSkillResource":
        """Build the synthetic JSON manifest resource for this skill.

        Returns:
            A :class:`RemoteSkillResource` with ``is_manifest=True`` that
            generates a JSON file listing on ``read()``.
        """
        manifest_uri = f"skill://{self._skill_name}/{_MANIFEST_SUFFIX}"
        resource = RemoteSkillResource(
            uri=AnyUrl(manifest_uri),
            name=f"{self._skill_name}/{_MANIFEST_SUFFIX}",
            description=f"File listing for remote skill: {self._config.name}",
            mime_type="application/json",
            skill_name=self._skill_name,
            remote_url=None,
            remote_uri=manifest_uri,
            remote_headers=None,
            is_manifest=True,
        )
        resource.bind_service(self._service)
        resource.bind_uri_map(self._uri_map)
        return resource

    @staticmethod
    def _uri_map_to_name(uri: str) -> str:
        """Derive a human-readable name from a skill URI."""
        # e.g. skill://my-skill/SKILL.md -> my-skill/SKILL.md
        # e.g. skill://my-skill/query-plan.md -> my-skill/query-plan.md
        if uri.startswith("skill://"):
            return uri[len("skill://"):]
        return uri
