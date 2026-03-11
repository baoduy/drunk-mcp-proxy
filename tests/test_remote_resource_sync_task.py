"""Tests for RemoteResourceSyncTask."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from drunk_ai_proxy.app.tasks.remote_resource_sync_task import RemoteResourceSyncTask
from drunk_ai_proxy.utils import RemoteResourceConfig


class TestRemoteResourceSyncTaskValidation:
    """Validation behavior for URLs and extensions."""

    def test_validate_url_accepts_https(self) -> None:
        """HTTPS URL should be accepted."""
        task = RemoteResourceSyncTask([])
        task._validate_url("https://example.com/file.md")

    @pytest.mark.parametrize("url", ["http://example.com/file.md", "ftp://example.com/file.md", "file:///tmp/file.md"])
    def test_validate_url_rejects_non_https(self, url: str) -> None:
        """Non-HTTPS schemes should be rejected."""
        task = RemoteResourceSyncTask([])
        with pytest.raises(ValueError, match="Only https:// URLs are allowed"):
            task._validate_url(url)

    def test_validate_extension_accepts_allowed_extension(self) -> None:
        """Allowed extension should pass validation."""
        with patch.dict("os.environ", {"REMOTE_RESOURCE_ALLOWED_EXTENSIONS": ".md,.yaml"}):
            task = RemoteResourceSyncTask([])
        task._validate_extension("README.md")

    def test_validate_extension_rejects_disallowed_extension(self) -> None:
        """Disallowed extension should raise ValueError."""
        with patch.dict("os.environ", {"REMOTE_RESOURCE_ALLOWED_EXTENSIONS": ".md,.yaml"}):
            task = RemoteResourceSyncTask([])
        with pytest.raises(ValueError, match="not allowed"):
            task._validate_extension("payload.exe")


class TestRemoteResourceSyncTaskTTL:
    """TTL cache behavior."""

    def test_is_fresh_returns_true_for_recent_file(self, tmp_path: Path) -> None:
        """A recently modified file should be treated as fresh."""
        with patch.dict("os.environ", {"REMOTE_RESOURCE_TTL_HOURS": "24"}):
            task = RemoteResourceSyncTask([])

        file_path = tmp_path / "recent.md"
        file_path.write_text("content")

        assert task._is_fresh(file_path) is True

    def test_is_fresh_returns_false_for_stale_file(self, tmp_path: Path) -> None:
        """A stale file should not be treated as fresh."""
        with patch.dict("os.environ", {"REMOTE_RESOURCE_TTL_HOURS": "1"}):
            task = RemoteResourceSyncTask([])

        file_path = tmp_path / "stale.md"
        file_path.write_text("content")

        stale_timestamp = time.time() - 3 * 3600
        file_path.touch()
        file_path.chmod(0o644)
        import os
        os.utime(file_path, (stale_timestamp, stale_timestamp))

        assert task._is_fresh(file_path) is False


class TestRemoteResourceSyncTaskDownload:
    """Download and per-URL error handling behavior."""

    @pytest.mark.asyncio
    async def test_download_one_writes_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Valid download should write destination file."""
        monkeypatch.setattr(
            "drunk_ai_proxy.app.tasks.remote_resource_sync_task.CONFIG_DIR",
            str(tmp_path),
        )
        task = RemoteResourceSyncTask([])

        destination_dir = task._resolve_destination_dir("prompts/test")
        destination_dir.mkdir(parents=True, exist_ok=True)

        response = Mock()
        response.content = b"hello"
        response.raise_for_status = Mock()

        client = AsyncMock()
        client.get.return_value = response

        await task._download_one(
            client,
            "https://example.com/file.md",
            destination_dir,
            RemoteResourceConfig(name="bundle", to_dir="prompts/test", paths=[]),
        )

        output_file = destination_dir / "file.md"
        assert output_file.exists()
        assert output_file.read_bytes() == b"hello"

    @pytest.mark.asyncio
    async def test_download_one_skips_when_fresh(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fresh cached file should skip network call."""
        monkeypatch.setattr(
            "drunk_ai_proxy.app.tasks.remote_resource_sync_task.CONFIG_DIR",
            str(tmp_path),
        )
        task = RemoteResourceSyncTask([])

        destination_dir = task._resolve_destination_dir("prompts/test")
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_file = destination_dir / "file.md"
        output_file.write_text("cached")

        client = AsyncMock()
        await task._download_one(
            client,
            "https://example.com/file.md",
            destination_dir,
            RemoteResourceConfig(name="bundle", to_dir="prompts/test", paths=[]),
        )

        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_one_raises_for_size_limit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Oversized responses should be rejected."""
        monkeypatch.setattr(
            "drunk_ai_proxy.app.tasks.remote_resource_sync_task.CONFIG_DIR",
            str(tmp_path),
        )
        with patch.dict("os.environ", {"REMOTE_RESOURCE_MAX_SIZE_MB": "0"}):
            task = RemoteResourceSyncTask([])

        destination_dir = task._resolve_destination_dir("prompts/test")
        destination_dir.mkdir(parents=True, exist_ok=True)

        response = Mock()
        response.content = b"non-empty"
        response.raise_for_status = Mock()

        client = AsyncMock()
        client.get.return_value = response

        with pytest.raises(ValueError, match="maximum allowed size"):
            await task._download_one(
                client,
                "https://example.com/file.md",
                destination_dir,
                RemoteResourceConfig(name="bundle", to_dir="prompts/test", paths=[]),
            )

    @pytest.mark.asyncio
    async def test_sync_bundle_continues_after_url_failures(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """One URL failure should not stop other bundle URLs."""
        monkeypatch.setattr(
            "drunk_ai_proxy.app.tasks.remote_resource_sync_task.CONFIG_DIR",
            str(tmp_path),
        )

        config = RemoteResourceConfig(
            name="test-bundle",
            to_dir="prompts/test",
            paths=["https://example.com/1.md", "https://example.com/2.md"],
        )
        task = RemoteResourceSyncTask([config])

        with patch.object(task, "_download_one", new=AsyncMock(side_effect=[httpx.TimeoutException("x"), None])) as download_mock:
            await task._sync_bundle(AsyncMock(), config)

        assert download_mock.await_count == 2


class TestRemoteResourceSyncTaskRun:
    """Task run orchestration behavior."""

    @pytest.mark.asyncio
    async def test_run_syncs_all_bundles_then_waits_for_next_interval(self) -> None:
        """run should sync all bundles, then sleep for periodic re-sync."""
        configs = [
            RemoteResourceConfig(name="a", to_dir="prompts/a", paths=["https://example.com/a.md"]),
            RemoteResourceConfig(name="b", to_dir="prompts/b", paths=["https://example.com/b.md"]),
        ]
        task = RemoteResourceSyncTask(configs)

        mock_client = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("drunk_ai_proxy.app.tasks.remote_resource_sync_task.httpx.AsyncClient", return_value=mock_context):
            with patch.object(task, "_sync_bundle", new=AsyncMock()) as sync_bundle_mock:
                with patch("drunk_ai_proxy.app.tasks.remote_resource_sync_task.asyncio.sleep", new=AsyncMock(side_effect=asyncio.CancelledError)) as sleep_mock:
                    with pytest.raises(asyncio.CancelledError):
                        await task.run()

        assert sync_bundle_mock.await_count == 2
        sleep_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_uses_configured_retry_attempts(self) -> None:
        """run should create httpx transport with configured retry attempts."""
        configs = [
            RemoteResourceConfig(name="a", to_dir="prompts/a", paths=["https://example.com/a.md"]),
        ]

        with patch.dict("os.environ", {"REMOTE_RESOURCE_RETRY_ATTEMPTS": "3"}):
            task = RemoteResourceSyncTask(configs)

        with patch("drunk_ai_proxy.app.tasks.remote_resource_sync_task.httpx.AsyncHTTPTransport") as transport_cls:
            with patch("drunk_ai_proxy.app.tasks.remote_resource_sync_task.httpx.AsyncClient") as client_cls:
                client_cm = AsyncMock()
                client_cm.__aenter__.return_value = AsyncMock()
                client_cm.__aexit__.return_value = None
                client_cls.return_value = client_cm

                with patch.object(task, "_sync_bundle", new=AsyncMock()):
                    with patch("drunk_ai_proxy.app.tasks.remote_resource_sync_task.asyncio.sleep", new=AsyncMock(side_effect=asyncio.CancelledError)):
                        with pytest.raises(asyncio.CancelledError):
                            await task.run()

        transport_cls.assert_called_once_with(retries=3)
