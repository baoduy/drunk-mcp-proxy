"""Background task for syncing remote resource files into local config directories."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from fastmcp.utilities import logging

from drunk_ai_proxy.utils import RemoteResourceConfig
from drunk_ai_proxy.utils.env import (
    CONFIG_DIR,
    REMOTE_RESOURCE_ALLOWED_EXTENSIONS,
    REMOTE_RESOURCE_MAX_SIZE_MB,
    REMOTE_RESOURCE_RETRY_ATTEMPTS,
    REMOTE_RESOURCE_TTL_HOURS,
    get_env_int,
    get_env_string,
)

logger = logging.get_logger(__name__)


class RemoteResourceSyncTask:
    """Sync remote resource bundles to local files.

    The task is designed to run in the background during startup. Failures are
    logged and skipped per URL so one bad remote does not block the full sync.
    """

    def __init__(self, configs: list[RemoteResourceConfig]) -> None:
        """Initialize the sync task.

        Args:
            configs: Resource bundle configuration list.
        """
        self._configs = configs
        self._ttl_hours = get_env_int("REMOTE_RESOURCE_TTL_HOURS", REMOTE_RESOURCE_TTL_HOURS)
        self._max_size_bytes = (
            get_env_int("REMOTE_RESOURCE_MAX_SIZE_MB", REMOTE_RESOURCE_MAX_SIZE_MB) * 1024 * 1024
        )
        self._retry_attempts = max(
            get_env_int("REMOTE_RESOURCE_RETRY_ATTEMPTS", REMOTE_RESOURCE_RETRY_ATTEMPTS),
            0,
        )
        self._sync_interval_seconds = max(self._ttl_hours, 1) * 3600
        self._allowed_extensions = self._parse_allowed_extensions(
            get_env_string(
                "REMOTE_RESOURCE_ALLOWED_EXTENSIONS",
                REMOTE_RESOURCE_ALLOWED_EXTENSIONS,
            )
        )

    async def run(self) -> None:
        """Run startup sync and periodic re-sync based on TTL hours."""
        if not self._configs:
            return

        transport = httpx.AsyncHTTPTransport(retries=self._retry_attempts)
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=30,
            transport=transport,
        ) as client:
            while True:
                for config in self._configs:
                    await self._sync_bundle(client, config)

                await asyncio.sleep(self._sync_interval_seconds)

    async def _sync_bundle(self, client: httpx.AsyncClient, config: RemoteResourceConfig) -> None:
        """Sync all URLs from one bundle into the destination directory."""
        destination_dir = self._resolve_destination_dir(config.to_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        download_tasks = [
            self._download_one(client, url, destination_dir, config)
            for url in config.paths
        ]

        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        for url, result in zip(config.paths, results):
            if isinstance(result, Exception):
                logger.warning(
                    "Failed syncing bundle '%s' url (skipped): %s",
                    config.name,
                    type(result).__name__,
                )

    async def _download_one(
        self,
        client: httpx.AsyncClient,
        url: str,
        destination_dir: Path,
        config: RemoteResourceConfig,
    ) -> None:
        """Download one URL if it is valid and cache is stale."""
        _ = config
        # TODO: Apply config.headers in request calls for private URL authentication.

        self._validate_url(url)

        file_name = Path(urlparse(url).path).name
        if not file_name:
            raise ValueError("URL path must include a file name")

        self._validate_extension(file_name)

        destination_file = destination_dir / file_name
        if self._is_fresh(destination_file):
            logger.debug("Skipping fresh cached file: %s", destination_file)
            return

        response = await client.get(url)
        response.raise_for_status()

        if len(response.content) > self._max_size_bytes:
            raise ValueError("File exceeds maximum allowed size")

        destination_file.write_bytes(response.content)
        logger.info("Downloaded remote resource: %s", destination_file)

    def _resolve_destination_dir(self, to_dir: str) -> Path:
        """Resolve and validate destination directory under CONFIG_DIR."""
        config_root = Path(CONFIG_DIR).resolve()
        destination_dir = (config_root / to_dir).resolve()

        if not destination_dir.is_relative_to(config_root):
            raise ValueError("to_dir must resolve under FASTMCP_CONFIG_DIR")

        return destination_dir

    def _validate_url(self, url: str) -> None:
        """Validate URL scheme and basic shape."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("Only https:// URLs are allowed")
        if not parsed.netloc:
            raise ValueError("URL must include a host")

    def _validate_extension(self, file_name: str) -> None:
        """Validate file extension against allow-list."""
        extension = Path(file_name).suffix.lower()
        if extension not in self._allowed_extensions:
            raise ValueError(f"Extension '{extension}' is not allowed")

    def _is_fresh(self, path: Path) -> bool:
        """Check if an existing file is still within TTL."""
        if not path.exists():
            return False

        age_hours = (time.time() - path.stat().st_mtime) / 3600
        return age_hours < self._ttl_hours

    @staticmethod
    def _parse_allowed_extensions(raw_extensions: str) -> frozenset[str]:
        """Normalize extension env value to a set like {'.md', '.yaml'}."""
        parts = [segment.strip().lower() for segment in raw_extensions.split(",") if segment.strip()]
        normalized = [segment if segment.startswith(".") else f".{segment}" for segment in parts]
        return frozenset(normalized)
