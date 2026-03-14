"""URI derivation utilities for on-demand remote resources.

This module provides functions to deterministically build MCP URI strings
from remote HTTPS URLs for skills, agents, and prompts sections.

Rules:
- Skills: derive a base resource URI from the folder path of SKILL.md.
  All non-SKILL.md files in the same ``urls`` list become support-file URIs
  under the same skill namespace.
- Agents: derive one URI per single URL.
- Prompts: derive one URI per single URL.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastmcp.utilities import logging

logger = logging.get_logger(__name__)

_SKILL_MAIN = "SKILL.md"


def _normalize_resource_name(name: str) -> str:
    """Normalize configured resource names for URI usage."""
    return name.strip().strip("/").lower()


def build_name_from_url(url: str) -> str:
    """Derive a logical resource name from a URL.

    Uses the filename stem for most files, but when the filename is
    ``SKILL.md`` it uses the parent folder name as identifier.

    Args:
        url: An HTTPS URL string.

    Returns:
        A lowercase slug suitable as a resource name.

    Example:
        >>> build_name_from_url(
        ...     "https://example.com/skills/optimizing-ef-core-queries/SKILL.md"
        ... )
        'optimizing-ef-core-queries'
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return "remote-resource"

    filename = parts[-1]
    if filename.lower() == _SKILL_MAIN.lower() and len(parts) >= 2:
        return parts[-2].lower()

    if "." in filename:
        return filename.rsplit(".", 1)[0].lower()

    return filename.lower()


def build_skill_resource_uris(
    urls: list[str],
    resource_name: str | None = None,
) -> dict[str, str]:
    """Map skill URLs to their MCP resource URIs.

    The URL containing ``SKILL.md`` maps to the main skill resource URI
    (``skill://<skill-name>/SKILL.md``). Every other URL maps to a support-file URI
    (``skill://<skill-name>/<filename>``).

    Args:
        urls: List of HTTPS URLs for a single skill entry; must include
            one URL ending with ``SKILL.md``.
        resource_name: Optional explicit configured resource name to use
            as the skill namespace.

    Returns:
        Dict mapping each URL to its derived resource URI string.

    Raises:
        ValueError: If no URL ending with ``SKILL.md`` is found.
    """
    skill_md_urls = [u for u in urls if u.endswith(_SKILL_MAIN)]
    if not skill_md_urls:
        raise ValueError(
            f"Skill remote_resource urls must include a URL ending with '{_SKILL_MAIN}'. "
            f"Got: {urls}"
        )

    if resource_name:
        skill_name = _normalize_resource_name(resource_name)
    else:
        skill_md_url = skill_md_urls[0]
        parsed = urlparse(skill_md_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        # Remove SKILL.md filename to get the skill folder name
        skill_name = path_parts[-2] if len(path_parts) >= 2 else "remote-skill"

    uri_map: dict[str, str] = {}
    for url in urls:
        if url.endswith(_SKILL_MAIN):
            uri_map[url] = f"skill://{skill_name}/{_SKILL_MAIN}"
        else:
            filename = urlparse(url).path.rsplit("/", 1)[-1]
            uri_map[url] = f"skill://{skill_name}/{filename}"

    return uri_map


def build_agent_resource_uri(url: str, resource_name: str | None = None) -> str:
    """Derive the MCP resource URI for a remote agent URL.

    Args:
        url: Single HTTPS URL for an agent markdown file.
        resource_name: Optional explicit configured resource name.

    Returns:
        Resource URI string in the form ``agent://<path>/<file_name>.agent.md``.
    """
    if resource_name:
        normalized_name = _normalize_resource_name(resource_name)
        parts = [p for p in normalized_name.split("/") if p]
        file_name = parts[-1] if parts else "remote"
        if not file_name.endswith(".agent.md"):
            file_name = (
                f"{file_name.rsplit('.', 1)[0]}.agent.md"
                if "." in file_name
                else f"{file_name}.agent.md"
            )
        path_parts = parts[:-1]
        if path_parts:
            return f"agent://{'/'.join(path_parts)}/{file_name}"
        return f"agent://{file_name}"

    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return "agent://remote/remote.agent.md"

    filename = parts[-1].lower()
    if not filename.endswith(".agent.md"):
        filename = f"{filename.rsplit('.', 1)[0]}.agent.md" if "." in filename else f"{filename}.agent.md"

    if "agents" in parts:
        agent_index = parts.index("agents")
        path_parts = [part.lower() for part in parts[agent_index + 1 : -1]]
    else:
        path_parts = [part.lower() for part in parts[-2:-1]]

    if path_parts:
        return f"agent://{'/'.join(path_parts)}/{filename}"

    return f"agent://{filename}"


def build_prompt_resource_uri(url: str, resource_name: str | None = None) -> str:
    """Derive the MCP resource URI for a remote prompt URL.

    Args:
        url: Single HTTPS URL for a prompt markdown file.
        resource_name: Optional explicit configured resource name.

    Returns:
        Resource URI string in the form ``prompt://<name>``.
    """
    if resource_name:
        return f"prompt://{_normalize_resource_name(resource_name)}"

    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return "prompt://remote-prompt"

    filename = parts[-1]
    name = filename.rsplit(".", 1)[0].lower() if "." in filename else filename.lower()
    return f"prompt://{name}"
