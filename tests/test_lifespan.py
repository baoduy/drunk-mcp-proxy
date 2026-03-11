"""Unit tests for AppLifespanManager."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

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
