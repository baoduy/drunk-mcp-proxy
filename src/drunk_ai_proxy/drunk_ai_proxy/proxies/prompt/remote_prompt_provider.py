"""Remote on-demand prompt provider backed by HTTPS fetch and TTL cache.

Fetches a markdown prompt template file lazily (once on first use) from a
remote HTTPS URL, parses YAML frontmatter metadata, and registers the
resulting prompt with FastMCP.
"""

from __future__ import annotations

import inspect
from typing import Any

from fastmcp import FastMCP
from fastmcp.prompts import Message

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
        self._resource_uri: str = build_prompt_resource_uri(
            remote_config.url,
            resource_name=remote_config.name,
        )

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
                template = _parse_template_from_content(
                    name=name,
                    content=raw_content,
                    source=url,
                )
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
        _remote_prompt.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
            parameters=[],
            return_annotation=list[Message],
        )

        try:
            mcp.prompt(_remote_prompt)
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


def _parse_template_from_content(
    name: str,
    content: str,
    source: str | None = None,
) -> PromptTemplate:
    """Parse a :class:`PromptTemplate` from raw markdown content.

    Uses :meth:`PromptTemplate.from_markdown_content` for direct in-memory
    parsing without temporary files.

    Args:
        name: Logical prompt name to assign.
        content: Raw markdown content (with YAML frontmatter).
        source: Optional source label used in parsing errors.

    Returns:
        Parsed :class:`PromptTemplate` instance.

    Raises:
        ValueError: If the content cannot be parsed as a valid prompt template.
    """
    source_label = source if source else f"remote prompt '{name}'"
    try:
        return PromptTemplate.from_markdown_content(
            content=content,
            name=name,
            source=source_label,
        )
    except ValueError as e:
        if "must start with YAML frontmatter" not in str(e):
            raise

        logger.warning(
            "Remote prompt '%s' from '%s' has no YAML frontmatter; "
            "using raw markdown content with default metadata",
            name,
            source_label,
        )
        return PromptTemplate(
            name=name,
            description=f"Remote prompt '{name}'",
            parameters={},
            content=content,
            role="user",
            enabled=True,
        )


def _render_template(template: PromptTemplate, kwargs: dict[str, Any]) -> list[Message]:
    """Render a prompt template and wrap result in Message objects.

    Args:
        template: Parsed prompt template.
        kwargs: Template parameter values.

    Returns:
        List containing one :class:`~fastmcp.prompts.Message`.
    """
    content = template.render(**kwargs)
    return [Message(role=template.role, content=content)]  # type: ignore[arg-type]
