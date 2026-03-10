"""Custom agents directory provider with namespace support."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from fastmcp.resources.resource import Resource
from fastmcp.resources.template import ResourceTemplate
from fastmcp.server.providers.aggregate import AggregateProvider
from fastmcp.utilities.versions import VersionSpec
from .agent_provider import AgentProvider

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

class CustomAgentsDirectoryProvider(AggregateProvider):
    """Discover agent markdown files and expose them with optional namespace paths.

    Scans a directory (recursively) for markdown files and loads them as agents.
    Each agent file must have YAML frontmatter with at minimum a 'description' field.

    Supports both layouts under each root:
    - Flat: <root>/agent-name.md
    - Namespaced: <root>/<namespace>/agent-name.md

    When a namespace folder is used, agents are exposed as
    agent://<namespace>/<agent_name> via AggregateProvider namespaces.

    Example:
        ```python
        from pathlib import Path
        from fastmcp.server.providers.custom_agents_directory import CustomAgentsDirectoryProvider

        provider = CustomAgentsDirectoryProvider(
            roots=Path("data/agents"),
            reload=False
        )
        ```
    """

    def __init__(
        self,
        roots: str | Path | Sequence[str | Path],
        reload: bool = False,
    ) -> None:
        """Initialize the provider.

        Args:
            roots: Root directory or directories containing agent markdown files.
            reload: If True, re-discover agents on each request.
        """
        super().__init__()
        if isinstance(roots, (str, Path)):
            roots = [roots]

        self._roots = [Path(r).resolve() for r in roots]
        self._reload = reload
        self._discovered = False

        self._discover_agents()

    def _sanitize_agent_name(self, name: str) -> str:
        """Sanitize agent name from filename.

        Converts filename to a valid agent name by:
        - Removing .md extension
        - Converting to lowercase
        - Replacing spaces and special chars with underscores
        - Keeping only alphanumeric, underscores, and hyphens

        Args:
            name: Original filename (with or without .md).

        Returns:
            Sanitized agent name.
        """
        # Remove .md extension if present
        if name.endswith(".md"):
            name = name[:-3]
        
        # Convert to lowercase
        name = name.lower()
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Keep only alphanumeric, underscores, and hyphens
        name = re.sub(r"[^a-z0-9_-]", "", name)
        # Remove leading/trailing underscores or hyphens
        name = name.strip("_-")
        return name

    def _parse_frontmatter(self, content: str) -> dict[str, str]:
        """Parse YAML frontmatter from markdown content.

        Expects frontmatter delimited by --- at start and end:
        ---
        description: Some description
        enabled: true
        ---

        Args:
            content: Full markdown file content.

        Returns:
            Dictionary of frontmatter fields.
        """
        if not content.startswith("---"):
            return {}

        # Find the closing --- delimiter
        end_marker = content.find("\n---", 4)
        if end_marker == -1:
            return {}

        # Extract frontmatter block
        fm_block = content[3:end_marker].strip()
        result: dict[str, str] = {}

        # Simple YAML parsing for basic key: value pairs
        for line in fm_block.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip().strip('"\'')

        return result

    def _iter_agent_files(self, root: Path) -> list[tuple[str | None, Path]]:
        """Collect agent markdown files and their optional namespace.

        Supports two structures:
        - Flat: root/*.md -> no namespace
        - Namespaced: root/namespace/*.md -> namespace prefix

        Args:
            root: Root directory to scan.

        Returns:
            List of (namespace, file_path) tuples.
        """
        if not root.exists():
            return []

        results: list[tuple[str | None, Path]] = []

        # Flat structure: root/*.md
        for md_file in sorted(root.glob("*.md")):
            if md_file.is_file():
                results.append((None, md_file))

        # Check for namespaced structure: root/namespace/*.md
        for namespace_dir in sorted(root.iterdir()):
            if namespace_dir.is_dir() and not namespace_dir.name.startswith("."):
                for md_file in sorted(namespace_dir.glob("*.md")):
                    if md_file.is_file():
                        results.append((namespace_dir.name, md_file))

        return results

    def _discover_agents(self) -> None:
        """Scan root directories and create AgentProvider instances."""
        self.providers.clear()
        seen_agent_names: set[str] = set()

        for root in self._roots:
            for namespace, agent_file in self._iter_agent_files(root):
                try:
                    # Read file content for frontmatter
                    content = agent_file.read_text()
                    frontmatter = self._parse_frontmatter(content)
                    
                    # Build full agent name with namespace and .agent.md suffix
                    # e.g., "core/analysis.agent.md" or "reasoning.agent.md"
                    if agent_file.name.endswith(".agent.md"):
                        agent_resource_name = agent_file.name
                    elif agent_file.name.endswith(".md"):
                        agent_resource_name = f"{agent_file.name[:-3]}.agent.md"
                    else:
                        agent_resource_name = f"{agent_file.name}.agent.md"

                    if namespace:
                        full_agent_name = f"{namespace}/{agent_resource_name}"
                    else:
                        full_agent_name = agent_resource_name
                    
                    # Build qualified name for deduplication (same as full_agent_name)
                    qualified_name = full_agent_name
                    
                    # Skip duplicates
                    if qualified_name in seen_agent_names:
                        logger.warning(
                            "Duplicate agent name '%s' (from %s); skipping",
                            qualified_name,
                            agent_file,
                        )
                        continue

                    # Get description from frontmatter (required)
                    description = frontmatter.get("description", "")
                    if not description:
                        logger.warning(
                            "Agent file missing 'description' field: %s; skipping",
                            agent_file,
                        )
                        continue

                    # Get enabled status (default to true)
                    enabled_str = frontmatter.get("enabled", "true").lower()
                    enabled = enabled_str not in ("false", "no", "0")

                    # Create AgentProvider for this agent
                    provider = AgentProvider(
                        agent_path=agent_file,
                        agent_name=full_agent_name,
                        description=description,
                        enabled=enabled,
                    )

                    # Add to aggregate provider (no namespace prefix needed)
                    self.add_provider(provider)

                    seen_agent_names.add(qualified_name)
                    logger.info(
                        "Discovered agent: %s (enabled=%s)",
                        qualified_name,
                        enabled,
                    )

                except ValueError as e:
                    logger.error(
                        "Failed to load agent %s: %s",
                        agent_file.name,
                        type(e).__name__,
                    )
                    continue
                except Exception as e:
                    logger.error(
                        "Unexpected error loading agent %s: %s",
                        agent_file.name,
                        type(e).__name__,
                    )
                    continue

        self._discovered = True
        logger.info(
            "Agent discovery complete: %d agent(s) loaded",
            len(seen_agent_names),
        )

    async def _ensure_discovered(self) -> None:
        """Ensure agents are discovered, rediscovering if reload is enabled."""
        if self._reload or not self._discovered:
            self._discover_agents()

    async def _list_resources(self) -> Sequence[Resource]:
        await self._ensure_discovered()
        return await super()._list_resources()

    async def _list_resource_templates(self) -> Sequence[ResourceTemplate]:
        await self._ensure_discovered()
        return await super()._list_resource_templates()

    async def _get_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> Resource | None:
        await self._ensure_discovered()
        return await super()._get_resource(uri, version)

    async def _get_resource_template(
        self, uri: str, version: VersionSpec | None = None
    ) -> ResourceTemplate | None:
        await self._ensure_discovered()
        return await super()._get_resource_template(uri, version)

    def __repr__(self) -> str:
        roots_repr = self._roots[0] if len(self._roots) == 1 else self._roots
        return (
            f"CustomAgentsDirectoryProvider(roots={roots_repr!r}, "
            f"reload={self._reload}, agents={len(self.providers)})"
        )
