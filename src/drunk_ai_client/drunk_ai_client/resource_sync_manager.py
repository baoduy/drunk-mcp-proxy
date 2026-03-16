"""Resource synchronization services for remote MCP resources."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import mcp.types
from fastmcp.utilities import logging

from drunk_ai_client.resource_models import ResourceFile, ResourceManifest, ResourceSummary

logger = logging.get_logger(__name__)


class ResourceClientProtocol(Protocol):
    """Protocol for FastMCP clients used by resource synchronization."""

    async def list_resources(self) -> list[object]:
        """Return all available resources from the remote endpoint."""
        ...

    async def read_resource(self, uri: str) -> list[object]:
        """Read the resource contents for a given URI."""
        ...


class ResourceUriStrategy:
    """Encapsulates URI matching and name extraction rules for resources."""

    def __init__(self, scheme: str, file_suffix: str | None = None) -> None:
        """Initialize URI strategy.

        Args:
            scheme: URI scheme such as "skill" or "agent".
            file_suffix: File suffix to match when using file-scoped resources.

        Raises:
            ValueError: If scheme is empty.
        """
        if not scheme:
            raise ValueError("scheme cannot be empty")

        self._scheme = scheme
        self._file_suffix = file_suffix

    @property
    def scheme(self) -> str:
        """Return the configured URI scheme."""
        return self._scheme

    def matches(self, uri: str) -> bool:
        """Check whether a URI matches the configured strategy."""
        prefix = f"{self._scheme}://"
        if not uri.startswith(prefix):
            return False

        if self._file_suffix is None:
            return uri != prefix and "/_" not in uri

        return uri.endswith(f"/{self._file_suffix}") or uri.endswith(
            f".{self._file_suffix}"
        )

    def extract_name(self, uri: str) -> str:
        """Extract the logical resource name from a URI."""
        prefix = f"{self._scheme}://"
        path_part = uri[len(prefix) :]

        if self._file_suffix is None:
            return path_part.rsplit("/", 1)[0]

        slash_suffix = f"/{self._file_suffix}"
        if path_part.endswith(slash_suffix):
            return path_part[: -len(slash_suffix)]

        dot_suffix = f".{self._file_suffix}"
        if path_part.endswith(dot_suffix):
            return path_part

        return path_part.rsplit("/", 1)[0]


class ResourceSyncManager:
    """Manages synchronization of remote resources to local directories."""

    def __init__(
        self,
        client: ResourceClientProtocol,
        scheme: str,
        file_suffix: str | None = None,
    ) -> None:
        """Initialize a resource synchronization manager.

        Args:
            client: Client that can list and read remote resources.
            scheme: URI scheme such as "skill" or "agent".
            file_suffix: File suffix for matching resources.
        """
        self._client = client
        self._uri_strategy = ResourceUriStrategy(scheme=scheme, file_suffix=file_suffix)

    async def list_resources(self) -> list[ResourceSummary]:
        """List all available resources matching the configured URI strategy."""
        resources = await self._client.list_resources()
        matched_resources: list[ResourceSummary] = []
        seen_names: set[str] = set()

        for resource in resources:
            resource_uri = str(resource.uri)  # type: ignore[attr-defined]
            if self._uri_strategy.matches(resource_uri):
                resource_name = self._uri_strategy.extract_name(resource_uri)
                if resource_name in seen_names:
                    continue

                seen_names.add(resource_name)
                matched_resources.append(
                    ResourceSummary(
                        name=resource_name,
                        description=resource.description or "",  # type: ignore[attr-defined]
                        uri=resource_uri,
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
        """Download a resource to a local directory.

        Args:
            resource_name: Name of the resource to download.
            target_dir: Base directory where resource files are written.
            overwrite: Whether to overwrite an existing file.

        Returns:
            Local path where the resource was written.

        Raises:
            FileExistsError: If target already exists and overwrite is disabled.
        """
        resolved_target = Path(target_dir).expanduser().resolve()
        resource_path = resolved_target / resource_name

        if resource_path.exists() and not overwrite:
            raise FileExistsError(
                f"{self._uri_strategy.scheme.capitalize()} already exists: {resource_path}. "
                "Use overwrite=True to replace."
            )

        resource_path.parent.mkdir(parents=True, exist_ok=True)
        await self._download_single_resource(resource_name=resource_name, target_dir=resolved_target)

        return resource_path

    async def sync(
        self,
        target_dir: str | Path,
        *,
        overwrite: bool = False,
    ) -> list[Path]:
        """Sync all matching remote resources into a local target directory."""
        resources = await self.list_resources()
        downloaded_paths: list[Path] = []

        for resource in resources:
            try:
                downloaded_paths.append(
                    await self.download_resource(
                        resource.name,
                        target_dir,
                        overwrite=overwrite,
                    )
                )
            except FileExistsError:
                continue

        return downloaded_paths

    async def _download_single_resource(self, resource_name: str, target_dir: Path) -> None:
        """Download a single resource using manifest-first, list-fallback strategy."""
        manifest = await self._get_resource_manifest(resource_name)
        if manifest is not None:
            await self._download_from_manifest(
                manifest=manifest,
                target_dir=target_dir,
                resource_name=resource_name,
            )
            return

        await self._download_from_list(resource_name=resource_name, target_dir=target_dir)

    async def _get_resource_manifest(self, resource_name: str) -> ResourceManifest | None:
        """Resolve and parse resource manifest data when available."""
        manifest_uri = f"{self._uri_strategy.scheme}://{resource_name}/_manifest"
        try:
            result = await self._client.read_resource(manifest_uri)
            if not result:
                return None

            content = result[0]  # type: ignore[index]
            if not isinstance(content, mcp.types.TextResourceContents):
                return None

            manifest_data_obj = json.loads(content.text)
            if not isinstance(manifest_data_obj, Mapping):
                return None

            manifest_data = cast(Mapping[str, object], manifest_data_obj)
            files_list = cast(list[object], manifest_data.get("files", []))
            if not files_list:
                return None

            resource_key = self._uri_strategy.scheme
            resource_id = manifest_data.get(resource_key, resource_name)
            manifest_name = self._extract_manifest_name(resource_id, resource_name)

            files: list[ResourceFile] = []
            for file_info in files_list:
                if not isinstance(file_info, Mapping):
                    return None

                file_item = cast(Mapping[str, object], file_info)
                path = file_item.get("path")
                if not isinstance(path, str):
                    return None
                size_value = file_item.get("size", 0)
                hash_value = file_item.get("hash", "")
                files.append(
                    ResourceFile(
                        path=path,
                        size=size_value if isinstance(size_value, int) else 0,
                        hash=hash_value if isinstance(hash_value, str) else "",
                    )
                )

            return ResourceManifest(name=manifest_name, files=files)
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            logger.error("Failed to parse resource manifest: %s", type(exc).__name__)
            return None

    def _extract_manifest_name(self, resource_id: object, resource_name: str) -> str:
        """Extract a normalized manifest name from manifest metadata."""
        if isinstance(resource_id, Mapping):
            name_value = cast(Mapping[str, object], resource_id).get("name", resource_name)
            return name_value if isinstance(name_value, str) else resource_name

        return resource_id if isinstance(resource_id, str) else resource_name

    async def _download_from_manifest(
        self,
        manifest: ResourceManifest,
        target_dir: Path,
        resource_name: str,
    ) -> None:
        """Download resource contents from manifest-derived resource URI."""
        file_path = self._resolve_safe_path(target_dir, resource_name)
        if file_path is None:
            return

        file_uri = f"{self._uri_strategy.scheme}://{manifest.name}"
        result = await self._client.read_resource(file_uri)
        if not result:
            return

        content = result[0]  # type: ignore[index]
        self._write_resource_content(file_path=file_path, content=content)

    async def _download_from_list(
        self,
        resource_name: str,
        target_dir: Path,
    ) -> None:
        """Download resource contents discovered by list_resources()."""
        all_resources = await self._client.list_resources()
        resource_uri = f"{self._uri_strategy.scheme}://{resource_name}"

        for resource in all_resources:
            uri = str(resource.uri)  # type: ignore[attr-defined]
            if uri != resource_uri:
                continue

            file_path = self._resolve_safe_path(target_dir, resource_name)
            if file_path is None:
                return

            result = await self._client.read_resource(uri)
            if not result:
                return

            content = result[0]  # type: ignore[index]
            self._write_resource_content(file_path=file_path, content=content)
            return

    def _resolve_safe_path(self, base_dir: Path, resource_name: str) -> Path | None:
        """Resolve a path and ensure it remains inside the configured base directory."""
        file_path = (base_dir / resource_name).resolve()
        if not file_path.is_relative_to(base_dir):
            return None

        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    def _write_resource_content(self, file_path: Path, content: object) -> None:
        """Write text or blob resource content to disk."""
        if isinstance(content, mcp.types.TextResourceContents):
            file_path.write_text(content.text)
            return

        blob_value = getattr(content, "blob", "")
        if isinstance(blob_value, str):
            file_path.write_bytes(base64.b64decode(blob_value))
