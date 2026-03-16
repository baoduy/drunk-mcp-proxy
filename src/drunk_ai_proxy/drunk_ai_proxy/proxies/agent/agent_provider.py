"""Agent provider for exposing individual agents as MCP resources."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from pydantic import AnyUrl, Field
from fastmcp.resources.resource import Resource
from fastmcp.server.providers.base import Provider
from fastmcp.utilities.versions import VersionSpec

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

# Ensure .md is recognized as text/markdown on all platforms
mimetypes.add_type("text/markdown", ".md")


@dataclass
class AgentFileInfo:
    """Information about a file within an agent directory."""

    path: str  # Relative path within agent directory
    size: int
    hash: str  # sha256 hash


@dataclass
class AgentInfo:
    """Parsed information about an agent."""

    name: str  # Agent name (canonical identifier)
    description: str  # From frontmatter
    enabled: bool  # Whether agent is enabled
    path: Path  # Absolute path to agent file
    files: list[AgentFileInfo] = field(default_factory=lambda: list[AgentFileInfo]())
    frontmatter: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


class AgentParser:
    """Parser utilities for agent markdown files and metadata."""

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from markdown content.

        Args:
            content: Markdown content potentially starting with ---

        Returns:
            Tuple of (frontmatter dict, remaining content).
        """
        if not content.startswith("---"):
            return {}, content

        end_match = re.search(r"\n---\s*\n", content[3:])
        if not end_match:
            return {}, content

        frontmatter_text = content[3 : 3 + end_match.start()]
        remaining = content[3 + end_match.end() :]

        frontmatter: dict[str, Any] = {}
        for line in frontmatter_text.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()

                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]

                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"

                if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
                    items = value[1:-1].split(",")
                    value = [item.strip().strip("\"'") for item in items if item.strip()]

                frontmatter[key] = value

        return frontmatter, remaining

    @staticmethod
    def compute_file_hash(path: Path) -> str:
        """Compute SHA256 hash of a file.

        Args:
            path: Path to the file.

        Returns:
            Hash string in format 'sha256:hexdigest'.
        """
        sha256 = hashlib.sha256()
        with open(path, "rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(8192), b""):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()}"

    @staticmethod
    def scan_agent_files(agent_path: Path) -> list[AgentFileInfo]:
        """Scan agent file for manifest information.

        Args:
            agent_path: Path to the agent markdown file.

        Returns:
            List containing file info for the agent markdown file.
        """
        files: list[AgentFileInfo] = []
        if agent_path.is_file():
            files.append(
                AgentFileInfo(
                    path=agent_path.name,
                    size=agent_path.stat().st_size,
                    hash=AgentParser.compute_file_hash(agent_path),
                )
            )
        return files


parse_frontmatter = AgentParser.parse_frontmatter
compute_file_hash = AgentParser.compute_file_hash
scan_agent_files = AgentParser.scan_agent_files


class AgentResource(Resource):
    """A resource representing an agent markdown file or manifest."""

    enabled: bool = Field(default=True)
    file_path: Path | None = Field(default=None)
    agent_info: AgentInfo | None = Field(default=None)
    is_manifest: bool = Field(default=False)

    def get_meta(self) -> dict[str, Any]:
        """Get resource metadata including agent-specific fields."""
        meta = super().get_meta()
        fastmcp = cast(dict[str, Any], meta["fastmcp"])
        fastmcp["agent"] = {
            "enabled": self.enabled,
            "is_manifest": self.is_manifest,
        }
        return meta

    async def read(self) -> str | bytes:
        """Read the agent markdown content or generate manifest."""
        if self.is_manifest:
            return self._generate_manifest()
        
        if not self.file_path:
            raise ValueError("File path not set for agent resource")
        return self.file_path.read_text()
    
    def _generate_manifest(self) -> str:
        """Generate JSON manifest for the agent.
        
        Returns:
            JSON string with agent manifest including file information.
        """
        if not self.agent_info:
            raise ValueError("Agent info not set for manifest generation")
        
        manifest = {
            "agent": self.agent_info.name,
            "enabled": self.agent_info.enabled,
            "description": self.agent_info.description,
            "files": [
                {"path": f.path, "size": f.size, "hash": f.hash}
                for f in self.agent_info.files
            ],
        }
        return json.dumps(manifest, indent=2)


class AgentProvider(Provider):
    """Provider that exposes a single agent markdown file as an MCP resource.

    An agent is a static markdown file with minimal YAML frontmatter:
    - description: Brief description of the agent (required)
    - enabled: Whether the agent is active (optional, defaults to true)

    The entire markdown content (after frontmatter) is served as static content
    with mime_type="text/markdown".

    Args:
        agent_path: Path to the agent markdown file.
        agent_name: Name of the agent (used in URI).
        description: Description of the agent from frontmatter.
        enabled: Whether the agent is enabled.

    Example:
        ```python
        from pathlib import Path
        from fastmcp.server.providers.agent import AgentProvider

        provider = AgentProvider(
            agent_path=Path("/path/to/agent.md"),
            agent_name="code_analyzer",
            description="Analyzes code for issues",
            enabled=True
        )
        ```
    """

    def __init__(
        self,
        agent_path: str | Path,
        agent_name: str,
        description: str,
        enabled: bool = True,
    ) -> None:
        """Initialize AgentProvider.

        Args:
            agent_path: Path to the agent markdown file.
            agent_name: Name of the agent (used in resource URI).
            description: Description of the agent.
            enabled: Whether the agent is enabled.

        Raises:
            FileNotFoundError: If agent file doesn't exist.
            ValueError: If agent_name is empty.
        """
        super().__init__()

        if not agent_name:
            raise ValueError("agent_name cannot be empty")

        self._agent_path = Path(agent_path).resolve()
        self._agent_name = agent_name
        self._description = description
        self._enabled = enabled

        # Validate file exists
        if not self._agent_path.exists():
            raise FileNotFoundError(f"Agent file not found: {self._agent_path}")

        if not self._agent_path.is_file():
            raise ValueError(f"Agent path is not a file: {self._agent_path}")

        # Scan agent files for manifest
        files = AgentParser.scan_agent_files(self._agent_path)
        
        # Load frontmatter for metadata
        content = self._agent_path.read_text()
        frontmatter, _ = AgentParser.parse_frontmatter(content)
        
        # Create agent info
        self._agent_info = AgentInfo(
            name=agent_name,
            description=description,
            enabled=enabled,
            path=self._agent_path,
            files=files,
            frontmatter=frontmatter,
        )

        logger.debug(
            "Initialized AgentProvider for agent '%s' at %s (files=%d)",
            agent_name,
            self._agent_path,
            len(files),
        )

    async def _list_resources(self) -> Sequence[Resource]:
        """List agent resources including main file and manifest."""
        # Only return the agent resource if enabled
        if not self._enabled:
            logger.debug("Agent '%s' is disabled, not listing", self._agent_name)
            return []

        resources: list[Resource] = []
        
        # Main agent markdown file
        resources.append(
            AgentResource(
                uri=AnyUrl(f"agent://{self._agent_name}"),
                name=self._agent_name,
                description=self._description,
                mime_type="text/markdown",
                enabled=self._enabled,
                file_path=self._agent_path,
                agent_info=self._agent_info,
                is_manifest=False,
            )
        )
        
        # Synthetic manifest
        resources.append(
            AgentResource(
                uri=AnyUrl(f"agent://{self._agent_name}/_manifest"),
                name=f"{self._agent_name}/_manifest",
                description=f"File listing for {self._agent_name}",
                mime_type="application/json",
                enabled=self._enabled,
                file_path=None,
                agent_info=self._agent_info,
                is_manifest=True,
            )
        )
        
        logger.debug(
            "Listed agent resources: agent://%s and agent://%s/_manifest",
            self._agent_name,
            self._agent_name,
        )
        return resources

    async def _get_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> Resource | None:
        """Get a resource by URI.

        Args:
            uri: The resource URI (e.g., "agent://agent_name" or "agent://agent_name/_manifest").
            version: Optional version specification (not used for static agents).

        Returns:
            The resource if found and enabled, None otherwise.
        """
        if not self._enabled:
            return None

        # Parse URI: agent://{agent_name} or agent://{agent_name}/_manifest
        if not uri.startswith("agent://"):
            return None

        agent_path = uri[len("agent://") :]
        
        # Check for manifest URI
        if agent_path == f"{self._agent_name}/_manifest":
            resource = AgentResource(
                uri=AnyUrl(uri),
                name=f"{self._agent_name}/_manifest",
                description=f"File listing for {self._agent_name}",
                mime_type="application/json",
                enabled=self._enabled,
                file_path=None,
                agent_info=self._agent_info,
                is_manifest=True,
            )
            logger.debug("Retrieved agent manifest resource: %s", uri)
            return resource
        
        # Check if this URI matches our agent (exact match including any namespace path)
        if agent_path != self._agent_name:
            return None

        resource = AgentResource(
            uri=AnyUrl(uri),
            name=self._agent_name,
            description=self._description,
            mime_type="text/markdown",
            enabled=self._enabled,
            file_path=self._agent_path,
            agent_info=self._agent_info,
            is_manifest=False,
        )
        logger.debug("Retrieved agent resource: %s", uri)
        return resource

    async def _read_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> str | bytes:
        """Read the content of an agent resource.

        Args:
            uri: The resource URI.
            version: Optional version specification.

        Returns:
            The raw markdown content of the agent file or JSON manifest.

        Raises:
            FileNotFoundError: If the resource URI doesn't match this agent.
        """
        # Parse URI and verify it matches
        if not uri.startswith("agent://"):
            raise FileNotFoundError(f"Invalid agent URI: {uri}")

        agent_path = uri[len("agent://") :]
        
        # Check for manifest request
        if agent_path == f"{self._agent_name}/_manifest":
            manifest = {
                "agent": self._agent_info.name,
                "enabled": self._agent_info.enabled,
                "description": self._agent_info.description,
                "files": [
                    {"path": f.path, "size": f.size, "hash": f.hash}
                    for f in self._agent_info.files
                ],
            }
            logger.debug("Generated manifest for: %s", uri)
            return json.dumps(manifest, indent=2)
        
        # Check if URI matches main agent file
        if agent_path != self._agent_name:
            raise FileNotFoundError(f"Agent not found: {agent_path}")

        # Read and return the full markdown content
        content = self._agent_path.read_text()
        logger.debug("Read agent markdown for: %s", uri)
        return content
