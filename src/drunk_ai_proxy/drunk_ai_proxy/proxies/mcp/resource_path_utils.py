"""Utilities for extracting root namespace from resource directory paths."""

from __future__ import annotations

from pathlib import Path


class ResourcePathNamespaceResolver:
    """Class-first helper to extract resource root namespaces."""

    _RESERVED_NAMES = ("skills", "agents", "prompts")

    @staticmethod
    def get_root_namespace(dir_path: str | Path) -> str | None:
        """Extract root namespace from directory path."""
        if isinstance(dir_path, Path):
            for parent in dir_path.parents:
                if parent.name in ResourcePathNamespaceResolver._RESERVED_NAMES:
                    relative = dir_path.relative_to(parent)
                    return relative.parts[0] if relative.parts else None
            return None

        path_str = str(dir_path).rstrip("/")

        if "/" in path_str:
            return path_str.split("/")[-1]

        if path_str in ResourcePathNamespaceResolver._RESERVED_NAMES:
            return None

        return path_str
