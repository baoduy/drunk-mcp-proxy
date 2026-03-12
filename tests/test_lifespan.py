"""Unit tests for AppLifespanManager."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from drunk_ai_proxy.app.lifespan import AppLifespanManager
from drunk_ai_proxy.utils import RemoteResourceConfig


class _FakeBackgroundTask:
    """Minimal awaitable task stub for lifecycle testing."""

    def __init__(self) -> None:
        self.cancelled = False
        self._done = False

    def done(self) -> bool:
        return self._done

    def cancel(self) -> None:
        self.cancelled = True

    def __await__(self):
        async def _wait() -> None:
            raise asyncio.CancelledError()

        return _wait().__await__()


class _CompletedBackgroundTask:
    """Task stub that is already completed (no cancellation required)."""

    def done(self) -> bool:
        return True

    def cancel(self) -> None:
        raise AssertionError("cancel should not be called for completed task")

    def __await__(self):
        raise AssertionError("completed task should not be awaited during shutdown")


@asynccontextmanager
async def _empty_context():
    yield


class TestAppLifespanManager:
    """Tests for lifecycle startup/shutdown orchestration."""

    @pytest.mark.asyncio
    async def test_lifespans_does_not_schedule_sync_without_resources(self) -> None:
        """No sync task should be created when remote_resources is absent."""
        manager = AppLifespanManager()

        with patch("drunk_ai_proxy.app.lifespan.asyncio.create_task") as create_task_mock:
            with patch.object(manager, "_create_app_lifespans", return_value=_empty_context()):
                async with manager.lifespans(None, []):
                    pass

        create_task_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_lifespans_schedules_and_cancels_sync_task(self) -> None:
        """Sync task should be created and cancelled on shutdown when still running."""
        manager = AppLifespanManager()
        fake_task = _FakeBackgroundTask()
        resources = [
            RemoteResourceConfig(
                name="bundle",
                to_dir="prompts/test",
                paths=["https://example.com/a.md"],
            )
        ]

        def _create_task_side_effect(coro, **_kwargs):
            coro.close()
            return fake_task

        with patch(
            "drunk_ai_proxy.app.lifespan.asyncio.create_task",
            side_effect=_create_task_side_effect,
        ) as create_task_mock:
            with patch("drunk_ai_proxy.app.tasks.remote_resource_sync_task.RemoteResourceSyncTask.run", new=AsyncMock()):
                with patch.object(manager, "_create_app_lifespans", return_value=_empty_context()):
                    async with manager.lifespans(None, [], remote_resources=resources):
                        pass

        create_task_mock.assert_called_once()
        assert fake_task.cancelled is True

    @pytest.mark.asyncio
    async def test_lifespans_does_not_cancel_completed_sync_task(self) -> None:
        """Completed background task should not be cancelled/awaited on shutdown."""
        manager = AppLifespanManager()
        resources = [
            RemoteResourceConfig(
                name="bundle",
                to_dir="prompts/test",
                paths=["https://example.com/a.md"],
            )
        ]

        completed_task = _CompletedBackgroundTask()

        def _create_task_side_effect(coro, **_kwargs):
            coro.close()
            return completed_task

        with patch(
            "drunk_ai_proxy.app.lifespan.asyncio.create_task",
            side_effect=_create_task_side_effect,
        ) as create_task_mock:
            with patch(
                "drunk_ai_proxy.app.tasks.remote_resource_sync_task.RemoteResourceSyncTask.run",
                new=AsyncMock(),
            ):
                with patch.object(manager, "_create_app_lifespans", return_value=_empty_context()):
                    async with manager.lifespans(None, [], remote_resources=resources):
                        pass

        create_task_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespans_schedules_sync_task_with_expected_name(self) -> None:
        """Sync task should be scheduled with the explicit task name."""
        manager = AppLifespanManager()
        fake_task = _FakeBackgroundTask()
        resources = [
            RemoteResourceConfig(
                name="bundle",
                to_dir="prompts/test",
                paths=["https://example.com/a.md"],
            )
        ]

        def _create_task_side_effect(coro, **_kwargs):
            coro.close()
            return fake_task

        with patch(
            "drunk_ai_proxy.app.lifespan.asyncio.create_task",
            side_effect=_create_task_side_effect,
        ) as create_task_mock:
            with patch("drunk_ai_proxy.app.tasks.remote_resource_sync_task.RemoteResourceSyncTask.run", new=AsyncMock()):
                with patch.object(manager, "_create_app_lifespans", return_value=_empty_context()):
                    async with manager.lifespans(None, [], remote_resources=resources):
                        pass

        assert create_task_mock.call_args.kwargs.get("name") == "remote_resource_sync"

    @pytest.mark.asyncio
    async def test_lifespans_filters_disabled_remote_resources(self) -> None:
        """Sync task should receive only enabled resource bundles."""
        manager = AppLifespanManager()
        fake_task = _FakeBackgroundTask()
        resources = [
            RemoteResourceConfig(
                name="enabled-bundle",
                enabled=True,
                to_dir="prompts/enabled",
                paths=["https://example.com/enabled.md"],
            ),
            RemoteResourceConfig(
                name="disabled-bundle",
                enabled=False,
                to_dir="prompts/disabled",
                paths=["https://example.com/disabled.md"],
            ),
        ]

        sync_instance = MagicMock()
        sync_instance.run = AsyncMock()

        def _create_task_side_effect(coro, **_kwargs):
            coro.close()
            return fake_task

        with patch(
            "drunk_ai_proxy.app.lifespan.asyncio.create_task",
            side_effect=_create_task_side_effect,
        ):
            with patch("drunk_ai_proxy.app.tasks.RemoteResourceSyncTask", return_value=sync_instance) as sync_task_cls:
                with patch.object(manager, "_create_app_lifespans", return_value=_empty_context()):
                    async with manager.lifespans(None, [], remote_resources=resources):
                        pass

        sync_task_cls.assert_called_once()
        passed_resources = sync_task_cls.call_args.args[0]
        assert len(passed_resources) == 1
        assert passed_resources[0].name == "enabled-bundle"

    @pytest.mark.asyncio
    async def test_lifespans_does_not_schedule_sync_when_all_resources_disabled(self) -> None:
        """No sync task should be created when all resource bundles are disabled."""
        manager = AppLifespanManager()
        resources = [
            RemoteResourceConfig(
                name="disabled-a",
                enabled=False,
                to_dir="prompts/a",
                paths=["https://example.com/a.md"],
            ),
            RemoteResourceConfig(
                name="disabled-b",
                enabled=False,
                to_dir="prompts/b",
                paths=["https://example.com/b.md"],
            ),
        ]

        with patch("drunk_ai_proxy.app.lifespan.asyncio.create_task") as create_task_mock:
            with patch.object(manager, "_create_app_lifespans", return_value=_empty_context()):
                async with manager.lifespans(None, [], remote_resources=resources):
                    pass

        create_task_mock.assert_not_called()
