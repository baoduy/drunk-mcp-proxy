"""STDIO MCP bridge client for remote Drunk AI Proxy servers.

This module creates a local FastMCP server in stdio mode that proxies all
operations to a remote MCP endpoint with optional Bearer authentication.

Environment variables:
    API_URL: Remote MCP endpoint URL (required).
    API_KEY: Bearer token for authentication (optional).
    SKILL_DIR: Local directory where remote skills are synced at startup (optional).
    AGENTS_DIR: Local directory where remote agents are synced at startup (optional).
    ALLOWS_OVERWRITE: Whether to overwrite existing resources during sync (default: false).
        Accepts: true, 1, yes (case-insensitive).
    SYNC_ENABLED: Whether to enable resource sync at startup (default: true).
        Accepts: true, 1, yes (case-insensitive). Set to false, 0, or no to disable.

Example:
    export API_URL="https://example.com/mcp"
    export API_KEY="your-token-here"
    export ALLOWS_OVERWRITE="true"
    python client.py
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import mcp.types

# FastMCP reads log level during initialization, so set default before importing it.
os.environ.setdefault("FASTMCP_LOG_LEVEL", "INFO")

from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.server import create_proxy
from fastmcp.utilities import skills, logging

logger = logging.get_logger(__name__)


@dataclass
class ResourceSummary:
    """Summary information about a resource available on a server."""

    name: str
    description: str
    uri: str


@dataclass
class ResourceFile:
    """Information about a file within a resource."""

    path: str
    size: int
    hash: str


@dataclass
class ResourceManifest:
    """Full manifest of a resource including all files."""

    name: str
    files: list[ResourceFile]


class ResourceSyncManager:
    """Manages synchronization of resources matching a configurable URI pattern."""

    def __init__(
        self,
        client: Client[Any],
        scheme: str,
        file_suffix: str | None = None,
    ) -> None:
        """Initialize ResourceSyncManager.

        Args:
            client: Connected FastMCP client with list_resources() and
                read_resource() methods.
            scheme: URI scheme (e.g., "skill", "agent")
            file_suffix: File suffix to match (e.g., "SKILL.md", "agent.md").
                If None, matches all files with the scheme.

        Raises:
            ValueError: If scheme is empty.
        """
        if not scheme:
            raise ValueError("scheme cannot be empty")

        self.client = client
        self.scheme = scheme
        self.file_suffix = file_suffix

    async def list_resources(self) -> list[ResourceSummary]:
        """List all available resources matching the configured pattern."""
        resources = await self.client.list_resources()
        matched_resources: list[ResourceSummary] = []
        seen_names: set[str] = set()

        for resource in resources:
            uri = str(resource.uri)  # type: ignore[attr-defined]
            if self._matches_pattern(uri):
                name = self._extract_name(uri)
                if name not in seen_names:
                    seen_names.add(name)
                    matched_resources.append(
                        ResourceSummary(
                            name=name,
                            description=resource.description or "",  # type: ignore[attr-defined]
                            uri=uri,
                        )
                    )

        return matched_resources

    async def download_resource(
        self,
        resource_name: str,
        target_dir: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Download a resource and all associated files to a local directory.

        Attempts to download using a manifest first (if available), then falls back
        to discovering files via list_resources().

        Args:
            resource_name: Name of the resource to download (may include path).
            target_dir: Directory where resource will be saved.
            overwrite: Whether to overwrite existing resource.

        Returns:
            Path to the downloaded resource file or directory.

        Raises:
            FileExistsError: If resource exists and overwrite=False.
        """
        target_dir = Path(target_dir).expanduser().resolve()
        resource_path = target_dir / resource_name

        if resource_path.exists() and not overwrite:
            raise FileExistsError(
                f"{self.scheme.capitalize()} already exists: {resource_path}. "
                "Use overwrite=True to replace."
            )

        # Create parent directory structure
        resource_path.parent.mkdir(parents=True, exist_ok=True)

        # Try to use manifest first
        manifest = await self._get_resource_manifest(resource_name)
        if manifest:
            await self._download_from_manifest(manifest, target_dir, resource_name)
        else:
            # Fall back to list_resources approach
            await self._download_from_list(resource_name, target_dir)

        return resource_path

    async def _get_resource_manifest(
        self, resource_name: str
    ) -> ResourceManifest | None:
        """Get the manifest for a specific resource.

        Args:
            resource_name: Name of the resource.

        Returns:
            ResourceManifest if available, None if manifest not found or invalid.
        """
        import json

        manifest_uri = f"{self.scheme}://{resource_name}/_manifest"
        try:
            result = await self.client.read_resource(manifest_uri)
            if not result:
                return None

            content = result[0]  # type: ignore[index]
            if isinstance(content, mcp.types.TextResourceContents):
                try:
                    manifest_data = json.loads(content.text)
                except (json.JSONDecodeError, TypeError):
                    return None
            else:
                return None

            # Parse manifest JSON structure
            try:
                # Files are at root level
                files_list = manifest_data.get("files", [])  # type: ignore[union-attr]
                if not files_list:
                    return None

                # Get resource identifier from scheme-specific key (e.g., "agent", "skill")
                resource_id_key = self.scheme
                resource_id = manifest_data.get(resource_id_key, resource_name)  # type: ignore[union-attr]

                # If resource_id is a dict, get name; if string, use as-is
                extracted_name: str
                if isinstance(resource_id, dict):
                    name_val = resource_id.get("name", resource_name)  # type: ignore[index]
                    extracted_name = (
                        name_val if isinstance(name_val, str) else resource_name
                    )
                else:
                    extracted_name = (
                        resource_id if isinstance(resource_id, str) else resource_name
                    )

                return ResourceManifest(
                    name=extracted_name,
                    files=[
                        ResourceFile(
                            path=f["path"],  # type: ignore[index]
                            size=f.get("size", 0),  # type: ignore[union-attr]
                            hash=f.get("hash", ""),  # type: ignore[union-attr]
                        )
                        for f in files_list
                    ],
                )
            except (KeyError, TypeError, AttributeError):
                return None
        except Exception:
            return None

    async def _download_from_manifest(
        self,
        manifest: ResourceManifest,
        target_dir: Path,
        resource_name: str,
    ) -> None:
        """Download files listed in a manifest.

        Args:
            manifest: Resource manifest containing file list.
            target_dir: Base target directory.
            resource_name: Full resource name/path from URI.
        """
        # For single-file resources, save directly based on resource_name
        file_path = (target_dir / resource_name).resolve()

        # Security: ensure file is within target directory
        if not file_path.is_relative_to(target_dir):
            return

        file_uri = f"{self.scheme}://{manifest.name}"
        result = await self.client.read_resource(file_uri)
        if not result:
            return

        content = result[0]  # type: ignore[index]
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, mcp.types.TextResourceContents):
            file_path.write_text(content.text)
        else:
            # BlobResourceContents
            file_path.write_bytes(base64.b64decode(content.blob))  # type: ignore[union-attr]

    async def _download_from_list(
        self,
        resource_name: str,
        target_dir: Path,
    ) -> None:
        """Download files by discovering them via list_resources().

        Args:
            resource_name: Name of the resource.
            target_dir: Base target directory.
        """
        all_resources = await self.client.list_resources()
        resource_uri = f"{self.scheme}://{resource_name}"

        for resource in all_resources:
            uri = str(resource.uri)  # type: ignore[attr-defined]
            if uri == resource_uri:
                # Single-file resource - save directly as resource_name
                file_path = (target_dir / resource_name).resolve()

                if not file_path.is_relative_to(target_dir):
                    continue

                result = await self.client.read_resource(uri)
                if not result:
                    continue

                content = result[0]  # type: ignore[index]
                file_path.parent.mkdir(parents=True, exist_ok=True)

                if isinstance(content, mcp.types.TextResourceContents):
                    file_path.write_text(content.text)
                else:
                    # BlobResourceContents
                    file_path.write_bytes(base64.b64decode(content.blob))  # type: ignore[union-attr]
                break

    async def sync(
        self,
        target_dir: str | Path,
        *,
        overwrite: bool = False,
    ) -> list[Path]:
        """Sync all resources matching pattern to target directory."""
        resources = await self.list_resources()
        downloaded: list[Path] = []

        for resource in resources:
            try:
                path = await self.download_resource(
                    resource.name, target_dir, overwrite=overwrite
                )
                downloaded.append(path)
            except FileExistsError:
                continue

        return downloaded

    def _matches_pattern(self, uri: str) -> bool:
        """Check if URI matches configured pattern."""
        prefix = f"{self.scheme}://"
        if not uri.startswith(prefix):
            return False

        if self.file_suffix is None:
            return uri != prefix and "/_" not in uri

        # Accept both styles:
        # 1) Nested file resource: <scheme>://name/<file_suffix>
        # 2) Resource-name suffix: <scheme>://name.<file_suffix>
        return uri.endswith(f"/{self.file_suffix}") or uri.endswith(
            f".{self.file_suffix}"
        )

    def _extract_name(self, uri: str) -> str:
        """Extract resource name from URI."""
        prefix = f"{self.scheme}://"
        path_part = uri[len(prefix) :]

        if self.file_suffix is None:
            return path_part.rsplit("/", 1)[0]

        slash_suffix = f"/{self.file_suffix}"
        if path_part.endswith(slash_suffix):
            return path_part[: -len(slash_suffix)]

        dot_suffix = f".{self.file_suffix}"
        if path_part.endswith(dot_suffix):
            return path_part

        return path_part.rsplit("/", 1)[0]


@dataclass
class ClientConfig:
    """Configuration for remote MCP connection."""

    url: str
    api_key: str | None = None
    skill_dir: Path | None = None
    agents_dir: Path | None = None
    allows_overwrite: bool = False
    sync_enabled: bool = True

    @classmethod
    def from_env(cls) -> "ClientConfig":
        """Load configuration from environment variables and CLI arguments.

        Returns:
            ClientConfig: Validated configuration.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        parser = argparse.ArgumentParser(
            description="FastMCP stdio bridge to remote MCP endpoint"
        )
        parser.add_argument("--url", help="Remote MCP endpoint URL")
        parser.add_argument("--api-key", help="Bearer token for authentication")
        args = parser.parse_args()

        # Prefer CLI args, fallback to env vars
        url = args.url or cls._get_env_string("API_URL")
        if not url:
            raise ValueError("API_URL environment variable or --url argument required")

        # Validate URL format
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url} (must be http:// or https://)")

        api_key = args.api_key or cls._get_env_string("API_KEY")
        skill_dir: Path | None = None
        skill_dir_value = cls._get_env_string("SKILL_DIR")
        if skill_dir_value:
            skill_dir = Path(skill_dir_value).expanduser()
            skill_dir.mkdir(parents=True, exist_ok=True)

        agents_dir: Path | None = None
        agents_dir_value = cls._get_env_string("AGENTS_DIR")
        if agents_dir_value:
            agents_dir = Path(agents_dir_value).expanduser()
            agents_dir.mkdir(parents=True, exist_ok=True)

        allows_overwrite = cls._get_env_bool("ALLOWS_OVERWRITE", False)
        sync_enabled = cls._get_env_bool("SYNC_ENABLED", True)

        return cls(
            url=url,
            api_key=api_key,
            skill_dir=skill_dir,
            agents_dir=agents_dir,
            allows_overwrite=allows_overwrite,
            sync_enabled=sync_enabled,
        )

    @staticmethod
    def _get_env_string(name: str) -> str | None:
        """Return the env value for a name, trying upper then lower.

        Args:
            name: Environment variable name to check.

        Returns:
            Env value if found, otherwise None.
        """
        value = os.getenv(name.upper())
        if value:
            return value

        value = os.getenv(name.lower())
        if value:
            return value

        return None

    @staticmethod
    def _get_env_int(key: str, default: int = 0) -> int:
        try:
            return int(ClientConfig._get_env_string(key) or str(default))
        except ValueError:
            return default

    @staticmethod
    def _get_env_bool(key: str, default: bool = False) -> bool:
        value = ClientConfig._get_env_string(key)
        if value is not None:
            value = value.strip().lower()
            if value in {"1", "true", "yes", "on"}:
                return True
            if value in {"0", "false", "no", "off"}:
                return False
        return default

def create_authenticated_client(config: ClientConfig) -> Client[Any]:
    """Create FastMCP Client with optional authentication.

    Args:
        config: Client configuration with URL and optional API key.

    Returns:
        Client: Configured FastMCP Client instance.
    """
    if config.api_key:
        logger.info(
            f"Creating authenticated client for {config.url} (api_key=...{config.api_key[-4:]})"
        )
        return Client(config.url, auth=BearerAuth(config.api_key))

    logger.info(f"Creating unauthenticated client for {config.url}")
    return Client(config.url)


async def sync_remove_resources(config: ClientConfig) -> None:
    """Sync configured remote resources to local directories once at startup.

    Actions:
        1. If config.skill_dir is provided, sync remote skills using sync_skills.
        2. If config.agents_dir is provided, sync remote agents using ResourceSyncManager.

    Args:
        config: Client configuration containing remote endpoint and local directories.
    """
    if config.skill_dir is None and config.agents_dir is None:
        return

    sync_client = create_authenticated_client(config)
    async with sync_client:
        if config.skill_dir is not None:
            skill_paths = await skills.sync_skills(  # pyright: ignore[reportUnknownMemberType]
                sync_client, config.skill_dir, overwrite=config.allows_overwrite
            )
            logger.info(f"Synced {len(skill_paths)} skills into {config.skill_dir}")

        if config.agents_dir is not None:
            agent_manager = ResourceSyncManager(
                sync_client,
                scheme="agent",
                file_suffix="agent.md",
            )
            agent_paths = await agent_manager.sync(
                config.agents_dir, overwrite=config.allows_overwrite
            )
            logger.info(f"Synced {len(agent_paths)} agents into {config.agents_dir}")


# https://gofastmcp.com/clients/client#creating-a-client
def run_stdio_bridge() -> None:
    """Run FastMCP stdio bridge server.

    This creates a local stdio MCP server that proxies all operations
    to the configured remote endpoint.
    """
    config = ClientConfig.from_env()

    if config.sync_enabled and (
        config.skill_dir is not None or config.agents_dir is not None
    ):
        # Sync configured resources from remote server once before exposing stdio proxy.
        asyncio.run(sync_remove_resources(config))

    # Create authenticated client
    client = create_authenticated_client(config)

    # Create proxy from client (automatically handles connection lifecycle)
    proxy = create_proxy(client)

    # Create local stdio server and mount the remote proxy
    from fastmcp.server.transforms.search import (
        BM25SearchTransform,
        RegexSearchTransform,
    )

    transforms = [
        RegexSearchTransform(max_results=10),
        BM25SearchTransform(max_results=3),
    ]
    server = FastMCP(name="drunk-ai-client-stdio", transforms=transforms)
    server.mount(proxy)

    logger.info(f"Starting stdio bridge to {config.url}")
    server.run(transport="stdio")


if __name__ == "__main__":
    try:
        run_stdio_bridge()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    except Exception as exc:
        logger.error("Fatal error: %s", type(exc).__name__)
        raise
