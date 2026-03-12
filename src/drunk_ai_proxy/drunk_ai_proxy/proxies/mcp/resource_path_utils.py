"""Utilities for extracting root namespace from resource directory paths."""

from __future__ import annotations

from pathlib import Path


def get_root_namespace(dir_path: str | Path) -> str | None:
    """Extract root namespace from directory path.

    Logic for string paths:
    - If path contains `/`, return the last folder in the path.
    - If path doesn't contain `/`:
      - Return None if name is a reserved keyword (skills, agents, prompts).
      - Otherwise return the directory name itself.

    Logic for Path objects:
    - Check if any parent is a reserved keyword (skills, agents, prompts).
    - Return None if not explicitly under a reserved keyword folder.
    - This allows precise detection of configured root namespaces without false positives.

    Examples (strings):
        'skills/dknet' → 'dknet'
        'agents/dknet' → 'dknet'
        'prompts/dotnet' → 'dotnet'
        'skills' → None
        'agents' → None
        'prompts' → None
        'dknet' → 'dknet'
        'custom-skills' → 'custom-skills'

    Examples (Path objects):
        Path('/data/skills/dknet') → 'dknet'
        Path('/data/agents/dknet') → 'dknet'
        Path('/data/prompts/dotnet') → 'dotnet'
        Path('/tmp/dknet') → None (not under reserved keyword)
        Path('/data/skills') → None
        Path('/data/agents') → None

    Args:
        dir_path: Directory path as string or Path object.
                  Strings should be relative (e.g., 'skills/dknet').
                  Path objects can be absolute or relative.

    Returns:
        Root namespace name, or None if not applicable.
    """
    if isinstance(dir_path, Path):
        # For Path objects, only detect namespace if explicitly under
        # a reserved keyword folder (skills, agents, prompts)
        for parent in dir_path.parents:
            if parent.name in ("skills", "agents", "prompts"):
                # Return the immediate child of the reserved keyword folder
                # e.g., for /data/skills/dknet/..., return dknet
                relative = dir_path.relative_to(parent)
                return relative.parts[0] if relative.parts else None

        # Not under any reserved keyword folder
        return None

    # For strings, apply the split logic
    path_str = str(dir_path).rstrip("/")

    if "/" in path_str:
        # Get the last folder in the path
        return path_str.split("/")[-1]

    # No slash: check if it's a reserved keyword
    if path_str in ("skills", "agents", "prompts"):
        return None

    # Return the directory name itself
    return path_str
