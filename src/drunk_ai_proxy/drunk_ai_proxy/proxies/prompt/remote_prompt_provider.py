"""Remote on-demand prompt provider backed by HTTPS fetch and TTL cache.

Fetches a markdown prompt template file lazily (once on first use) from a
remote HTTPS URL, parses YAML frontmatter metadata, and registers the
resulting prompt with FastMCP.
"""

from __future__ import annotations

import inspect
import json
import tempfile
import os
from collections.abc import Sequence
from typing import Any

from fastmcp import FastMCP
from fastmcp.prompts import Message
from fastmcp.resources.resource import Resource
from fastmcp.resources.template import ResourceTemplate
from fastmcp.server.providers.base import Provider
from fastmcp.utilities.versions import VersionSpec
from pydantic import AnyUrl

from drunk_ai_proxy.app.cache_provider import TTLAsyncKeyValue
from drunk_ai_proxy.proxies.prompt.prompt_template import PromptTemplate
from drunk_ai_proxy.proxies.resource.on_demand_remote_resource_service import (
    OnDemandRemoteResourceService,
)
from drunk_ai_proxy.utils.config_yaml import McpConfig, OnDemandRemoteResourceConfig
from drunk_ai_proxy.utils.config_yaml_uri import build_prompt_resource_uri
from drunk_ai_proxy.utils import audit_log

import httpx
from fastmcp.utilities import logging

logger = logging.get_logger(__name__)

_MANIFEST_SUFFIX = "_manifest"


class RemotePromptManifestResource(Resource):
    """Synthetic manifest resource for a remote prompt.

    Exposes prompt metadata (name, source URL, resource URI) as a static
    JSON resource at ``prompt://<name>/_manifest``.
    """

    prompt_name: str
    prompt_url: str
    prompt_uri: str

    async def read(self) -> str | bytes:
        """Generate the JSON manifest for this remote prompt.

        Returns:
            JSON string with prompt name, source URL, and resource URI.
        """
        manifest = {
            "prompt": self.prompt_name,
            "url": self.prompt_url,
            "uri": self.prompt_uri,
        }
        return json.dumps(manifest, indent=2)


class _RemotePromptManifestProvider(Provider):
    """Internal provider that serves the manifest for a single remote prompt.

    Args:
        name: Logical prompt name.
        url: Remote HTTPS URL of the prompt source file.
        resource_uri: MCP resource URI for the prompt (``prompt://<name>``).
    """

    def __init__(self, name: str, url: str, resource_uri: str) -> None:
        """Initialize the manifest provider.

        Args:
            name: Logical prompt name.
            url: Remote HTTPS prompt source URL.
            resource_uri: MCP prompt resource URI.
        """
        super().__init__()
        self._name = name
        self._url = url
        self._resource_uri = resource_uri
        self._manifest_uri = f"{resource_uri}/{_MANIFEST_SUFFIX}"

    def _build_resource(self) -> RemotePromptManifestResource:
        """Build the manifest resource descriptor."""
        return RemotePromptManifestResource(
            uri=AnyUrl(self._manifest_uri),
            name=f"{self._name}/{_MANIFEST_SUFFIX}",
            description=f"Manifest for remote prompt: {self._name}",
            mime_type="application/json",
            prompt_name=self._name,
            prompt_url=self._url,
            prompt_uri=self._resource_uri,
        )

    async def _list_resources(self) -> Sequence[Resource]:
        """Return the single manifest resource."""
        return [self._build_resource()]

    async def _list_resource_templates(self) -> Sequence[ResourceTemplate]:
        return []

    async def _get_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> Resource | None:
        """Return manifest resource if URI matches."""
        if uri == self._manifest_uri:
            return self._build_resource()
        return None

    async def _get_resource_template(
        self, uri: str, version: VersionSpec | None = None
    ) -> ResourceTemplate | None:
        return None


class RemotePromptProvider:
    """Provider that registers a single remote HTTPS prompt template with FastMCP.

    On :meth:`register_to_mcp`, this provider builds a lazy prompt callable that
    fetches (or returns cached) content at render time.  The content is parsed
    from YAML frontmatter + markdown body via :class:`~PromptTemplate`.

    Args:
        config: MCP section config owning this prompt (used for path/logging).
        remote_config: On-demand remote resource config entry (must use ``url``).
        cache: TTL cache store.
        http_client: Shared async HTTP client.
    """

    def __init__(
        self,
        config: McpConfig,
        remote_config: OnDemandRemoteResourceConfig,
        cache: TTLAsyncKeyValue,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Initialize the remote prompt provider.

        Args:
            config: MCP config section (used for audit / logging).
            remote_config: Remote resource config entry (must have ``url``).
            cache: TTL cache store instance.
            http_client: Shared httpx async client.

        Raises:
            ValueError: If ``url`` is missing from ``remote_config``.
        """
        if not remote_config.url:
            raise ValueError(
                f"RemotePromptProvider requires 'url' for entry '{remote_config.name}'"
            )

        self._config = config
        self._remote_config = remote_config
        self._service = OnDemandRemoteResourceService(cache=cache, http_client=http_client)
        self._resource_uri: str = build_prompt_resource_uri(remote_config.url)

    def register_to_mcp(self, mcp: FastMCP) -> None:
        """Register the remote prompt as a lazy-fetch FastMCP prompt.

        Registers an async callable that fetches (or returns cached) content
        on every invocation, parses frontmatter metadata, and renders the
        template with the provided keyword arguments.

        Args:
            mcp: Active FastMCP server instance to register the prompt with.
        """
        name = self._remote_config.name
        url = self._remote_config.url
        headers = self._remote_config.headers
        resource_uri = self._resource_uri
        service = self._service
        config_path = self._config.path

        async def _remote_prompt(**kwargs: Any) -> list[Message]:  # type: ignore[return]
            """Render the remote prompt template."""
            try:
                raw_content = await service.get_content(
                    uri=resource_uri,
                    url=url,  # type: ignore[arg-type]
                    headers=headers,
                )
                template = _parse_template_from_content(name=name, content=raw_content)
                return _render_template(template, kwargs)
            except Exception as e:
                logger.error(
                    "Failed to render remote prompt '%s' for path '%s': %s",
                    name,
                    config_path,
                    type(e).__name__,
                )
                audit_log(
                    logger=logger,
                    event="remote_prompt_render_failed",
                    status="failure",
                    resource=name,
                    details={"error_type": type(e).__name__},
                )
                raise

        _remote_prompt.__name__ = name
        _remote_prompt.__doc__ = f"Remote prompt: {name}"
        _remote_prompt.__annotations__ = {"return": list[Message]}

        try:
            mcp.prompt(_remote_prompt)
            # Register companion manifest resource at prompt://<name>/_manifest
            mcp.add_provider(
                _RemotePromptManifestProvider(
                    name=name,
                    url=url,  # type: ignore[arg-type]
                    resource_uri=resource_uri,
                )
            )
            logger.info(
                "Registered remote prompt '%s' (uri=%s) for path '%s'",
                name,
                resource_uri,
                config_path,
            )
        except Exception as e:
            logger.error(
                "Failed to register remote prompt '%s' for path '%s': %s",
                name,
                config_path,
                type(e).__name__,
            )
            audit_log(
                logger=logger,
                event="remote_prompt_registration_failed",
                status="failure",
                resource=name,
                details={"error_type": type(e).__name__},
            )
            raise


def _parse_template_from_content(name: str, content: str) -> PromptTemplate:
    """Parse a :class:`PromptTemplate` from raw markdown content.

    Uses :meth:`PromptTemplate.from_markdown_file` via a temporary file so
    that all existing validation logic is reused without duplication.

    Args:
        name: Logical prompt name to assign.
        content: Raw markdown content (with YAML frontmatter).

    Returns:
        Parsed :class:`PromptTemplate` instance.

    Raises:
        ValueError: If the content cannot be parsed as a valid prompt template.
    """
    # Write to a temp file so we can reuse PromptTemplate.from_markdown_file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        return PromptTemplate.from_markdown_file(tmp_path, name=name)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _render_template(template: PromptTemplate, kwargs: dict[str, Any]) -> list[Message]:
    """Render a prompt template and wrap result in Message objects.

    Args:
        template: Parsed prompt template.
        kwargs: Template parameter values.

    Returns:
        List containing one :class:`~fastmcp.prompts.Message`.
    """
    content = template.render(**kwargs)
    role = template.role
    return [Message(role=role, content=content)]


def _build_prompt_function(template: PromptTemplate) -> Any:
    """Build a sync callable that renders the prompt template.

    Mirrors the logic in
    :meth:`~drunk_ai_proxy.proxies.prompt.prompt_provider.McpPromptProvider._create_prompt_function`.

    Args:
        template: Parsed prompt template.

    Returns:
        Async callable that accepts template keyword arguments and returns
        a list of :class:`~fastmcp.prompts.Message` instances.
    """
    async def prompt_func(**kwargs: Any) -> list[Message]:
        return _render_template(template, kwargs)

    prompt_func.__name__ = template.name
    prompt_func.__doc__ = template.description

    annotations: dict[str, type] = {}
    for param_name, param_type in template.parameters.items():
        annotations[param_name] = param_type
    annotations["return"] = list[Message]
    prompt_func.__annotations__ = annotations

    params = [
        inspect.Parameter(
            name=param_name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=param_type,
        )
        for param_name, param_type in template.parameters.items()
    ]
    prompt_func.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters=params,
        return_annotation=list[Message],
    )

    return prompt_func
