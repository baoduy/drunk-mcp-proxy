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


def build_name_from_url(url: str) -> str:
    """Derive a logical resource name from a URL.

    Takes the last two meaningful path segments (parent-folder/filename) and
    removes the file extension to produce a short, readable identifier.

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

    # Drop filename part; use directory name as primary identifier
    if len(parts) >= 2 and "." in parts[-1]:
        dir_name = parts[-2]
    elif "." in parts[-1]:
        dir_name = parts[-1].rsplit(".", 1)[0]
    else:
        dir_name = parts[-1]

    return dir_name.lower()


def build_skill_resource_uris(urls: list[str]) -> dict[str, str]:
    """Map skill URLs to their MCP resource URIs.

    The URL containing ``SKILL.md`` maps to the main skill resource URI
    (``skill://<skill-name>``). Every other URL maps to a support-file URI
    (``skill://<skill-name>/<filename>``).

    Args:
        urls: List of HTTPS URLs for a single skill entry; must include
            one URL ending with ``SKILL.md``.

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

    skill_md_url = skill_md_urls[0]
    parsed = urlparse(skill_md_url)
    path_parts = [p for p in parsed.path.split("/") if p]
    # Remove SKILL.md filename to get the skill folder name
    skill_name = path_parts[-2] if len(path_parts) >= 2 else "remote-skill"

    uri_map: dict[str, str] = {}
    for url in urls:
        if url.endswith(_SKILL_MAIN):
            uri_map[url] = f"skill://{skill_name}"
        else:
            filename = urlparse(url).path.rsplit("/", 1)[-1]
            uri_map[url] = f"skill://{skill_name}/{filename}"

    return uri_map


def build_agent_resource_uri(url: str) -> str:
    """Derive the MCP resource URI for a remote agent URL.

    Args:
        url: Single HTTPS URL for an agent markdown file.

    Returns:
        Resource URI string in the form ``agent://<name>``.
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return "agent://remote-agent"

    filename = parts[-1]
    name = filename.rsplit(".", 1)[0].lower() if "." in filename else filename.lower()
    return f"agent://{name}"


def build_prompt_resource_uri(url: str) -> str:
    """Derive the MCP resource URI for a remote prompt URL.

    Args:
        url: Single HTTPS URL for a prompt markdown file.

    Returns:
        Resource URI string in the form ``prompt://<name>``.
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return "prompt://remote-prompt"

    filename = parts[-1]
    name = filename.rsplit(".", 1)[0].lower() if "." in filename else filename.lower()
    return f"prompt://{name}"
