"""Custom skills directory provider with namespace support."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from fastmcp.resources.resource import Resource
from fastmcp.resources.template import ResourceTemplate
from fastmcp.server.providers.aggregate import AggregateProvider
from fastmcp.server.providers.skills.skill_provider import SkillProvider
from fastmcp.utilities.versions import VersionSpec

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

class CustomSkillsDirectoryProvider(AggregateProvider):
    """Discover skill folders and expose them with optional namespace paths.

    Supports both layouts under each root:
    - Flat: <root>/<skill>/SKILL.md
    - Namespaced: <root>/<namespace>/<skill>/SKILL.md

    When a namespace folder is used, resources are exposed as
    skill://<namespace>/<skill>/... via AggregateProvider namespaces.
    """

    def __init__(
        self,
        roots: str | Path | Sequence[str | Path],
        reload: bool = False,
        main_file_name: str = "SKILL.md",
    ) -> None:
        """Initialize the provider.

        Args:
            roots: Root directory or directories containing skill folders.
            reload: If True, re-discover skills on each request.
            main_file_name: Name of the main skill file.
            supporting_files: How supporting files are exposed.
        """
        super().__init__()
        if isinstance(roots, (str, Path)):
            roots = [roots]

        self._roots = [Path(r).resolve() for r in roots]
        self._reload = reload
        self._main_file_name = main_file_name
        self._discovered = False

        self._discover_skills()

    def _iter_skill_dirs(self, root: Path) -> list[tuple[str | None, Path]]:
        """Collect skill directories and their optional namespace."""
        if not root.exists():
            return []

        entries = sorted([entry for entry in root.iterdir() if entry.is_dir()])
        results: list[tuple[str | None, Path]] = []

        for entry in entries:
            main_file = entry / self._main_file_name
            if main_file.exists():
                results.append((None, entry))
                continue

            namespaced_entries = sorted(
                [child for child in entry.iterdir() if child.is_dir()]
            )
            for skill_dir in namespaced_entries:
                if (skill_dir / self._main_file_name).exists():
                    results.append((entry.name, skill_dir))

        return results

    def _discover_skills(self) -> None:
        """Scan root directories and create SkillProvider instances."""
        self.providers.clear()
        seen_skill_names: set[str] = set()

        for root in self._roots:
            for namespace, skill_dir in self._iter_skill_dirs(root):
                skill_name = skill_dir.name
                qualified_name = (
                    f"{namespace}/{skill_name}" if namespace else skill_name
                )
                if qualified_name in seen_skill_names:
                    continue

                try:
                    provider = SkillProvider(
                        skill_path=skill_dir,
                        main_file_name=self._main_file_name,
                    )
                    if namespace:
                        self.add_provider(provider, namespace=namespace)
                    else:
                        self.add_provider(provider)
                    seen_skill_names.add(qualified_name)
                except (FileNotFoundError, PermissionError, OSError) as exc:
                    logger.error("Failed to load skill: %s", type(exc).__name__)

        self._discovered = True

    async def _ensure_discovered(self) -> None:
        """Ensure skills are discovered, rediscovering if reload is enabled."""
        if self._reload or not self._discovered:
            self._discover_skills()

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
            f"CustomSkillsDirectoryProvider(roots={roots_repr!r}, "
            f"reload={self._reload}, skills={len(self.providers)})"
        )
