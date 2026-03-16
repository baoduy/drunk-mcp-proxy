"""Resource model definitions for synchronized MCP resources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSummary:
    """Summary information about a resource available on a server."""

    name: str
    description: str
    uri: str


@dataclass(frozen=True)
class ResourceFile:
    """Information about a file within a resource manifest."""

    path: str
    size: int
    hash: str


@dataclass(frozen=True)
class ResourceManifest:
    """Full manifest of a resource including all files."""

    name: str
    files: list[ResourceFile]
