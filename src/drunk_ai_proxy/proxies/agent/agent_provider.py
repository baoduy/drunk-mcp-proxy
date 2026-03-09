"""Agent provider for exposing individual agents as MCP resources."""

from __future__ import annotations

import mimetypes
from collections.abc import Sequence
from logging import Logger
from pathlib import Path
from typing import Any, cast

from pydantic import AnyUrl, Field

from drunk_ai_proxy.utils.logging_config import setup_logging
from fastmcp.resources.resource import Resource
from fastmcp.server.providers.base import Provider
from fastmcp.utilities.versions import VersionSpec

# Ensure .md is recognized as text/markdown on all platforms
mimetypes.add_type("text/markdown", ".md")


class AgentResource(Resource):
    """A resource representing an agent markdown file."""

    enabled: bool = Field(default=True)
    file_path: Path = Field(default=None)  # type: ignore[assignment]

    def get_meta(self) -> dict[str, Any]:
        """Get resource metadata including agent-specific fields."""
        meta = super().get_meta()
        fastmcp = cast(dict[str, Any], meta["fastmcp"])
        fastmcp["agent"] = {
            "enabled": self.enabled,
        }
        return meta

    async def read(self) -> str | bytes:
        """Read the agent markdown content."""
        if not self.file_path:
            raise ValueError("File path not set for agent resource")
        return self.file_path.read_text()


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
        self._logger: Logger = setup_logging(__name__)

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

        self._logger.debug(
            "Initialized AgentProvider for agent '%s' at %s",
            agent_name,
            self._agent_path,
        )

    async def _list_resources(self) -> Sequence[Resource]:
        """List agent resources."""
        # Only return the agent resource if enabled
        if not self._enabled:
            self._logger.debug("Agent '%s' is disabled, not listing", self._agent_name)
            return []

        resource = AgentResource(
            uri=AnyUrl(f"agent://{self._agent_name}"),
            name=self._agent_name,
            description=self._description,
            mime_type="text/markdown",
            enabled=self._enabled,
            file_path=self._agent_path,
        )
        self._logger.debug("Listed agent resource: agent://%s", self._agent_name)
        return [resource]

    async def _get_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> Resource | None:
        """Get a resource by URI.

        Args:
            uri: The resource URI (e.g., "agent://agent_name").
            version: Optional version specification (not used for static agents).

        Returns:
            The resource if found and enabled, None otherwise.
        """
        if not self._enabled:
            return None

        # Parse URI: agent://{agent_name}
        if not uri.startswith("agent://"):
            return None

        agent_name = uri[len("agent://") :]

        # Check if this URI matches our agent
        if agent_name != self._agent_name:
            return None

        resource = AgentResource(
            uri=AnyUrl(uri),
            name=self._agent_name,
            description=self._description,
            mime_type="text/markdown",
            enabled=self._enabled,
            file_path=self._agent_path,
        )
        self._logger.debug("Retrieved agent resource: %s", uri)
        return resource

    async def _read_resource(
        self, uri: str, version: VersionSpec | None = None
    ) -> str | bytes:
        """Read the content of an agent resource.

        Args:
            uri: The resource URI.
            version: Optional version specification.

        Returns:
            The raw markdown content of the agent file.

        Raises:
            FileNotFoundError: If the resource URI doesn't match this agent.
        """
        # Parse URI and verify it matches
        if not uri.startswith("agent://"):
            raise FileNotFoundError(f"Invalid agent URI: {uri}")

        agent_name = uri[len("agent://") :]
        if agent_name != self._agent_name:
            raise FileNotFoundError(f"Agent not found: {agent_name}")

        # Read and return the full markdown content
        content = self._agent_path.read_text()
        self._logger.debug("Read agent markdown for: %s", uri)
        return content
