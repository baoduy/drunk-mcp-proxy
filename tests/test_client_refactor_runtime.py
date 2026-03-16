"""Tests for refactored Drunk AI client runtime orchestration and sync protocol."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import cast

import pytest
from drunk_ai_client.main import StdioBridgeApplication, run_stdio_bridge
from drunk_ai_client.client_config import ClientConfig
from drunk_ai_client.resource_sync_manager import ResourceSyncManager


class _FakeResource:
    def __init__(self, uri: str, description: str = "") -> None:
        self.uri = uri
        self.description = description


class _FakeBlobContent:
    def __init__(self, blob: str) -> None:
        self.blob = blob


class _FakeResourceClient:
    def __init__(self) -> None:
        self._resources = [_FakeResource(uri="agent://demo.agent.md", description="demo")]

    async def list_resources(self) -> list[object]:
        return cast(list[object], self._resources)

    async def read_resource(self, uri: str) -> list[object]:
        if uri.endswith("/_manifest"):
            return []

        return [_FakeBlobContent(blob=base64.b64encode(b"hello").decode("utf-8"))]


def test_resource_sync_manager_supports_protocol_client(tmp_path: Path) -> None:
    """Downloads resources using a protocol-compatible fake client."""
    manager = ResourceSyncManager(
        client=_FakeResourceClient(),
        scheme="agent",
        file_suffix="agent.md",
    )

    output_file = tmp_path / "demo.agent.md"
    downloaded_path = manager.download_resource  # keep callable reference for type-check sanity
    assert callable(downloaded_path)

    import asyncio

    result_path = asyncio.run(manager.download_resource("demo.agent.md", tmp_path))

    assert result_path == output_file
    assert output_file.read_bytes() == b"hello"


def test_build_server_uses_manual_fallback_when_builtin_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falls back to manual proxy composition when from_client path returns None."""
    app = StdioBridgeApplication()
    client = object()
    config = ClientConfig(url="https://example.com/mcp", use_from_client=True)

    monkeypatch.setattr(app, "_build_transforms", lambda: [object()])
    def _fake_build_from_client(
        _client: object,
        _transforms: list[object],
    ) -> None:
        return None

    monkeypatch.setattr(app, "_build_server_from_client", _fake_build_from_client)

    manual_server = object()
    def _fake_manual_builder(
        _client: object,
        _transforms: list[object],
    ) -> object:
        return manual_server

    monkeypatch.setattr(app, "_build_server_with_manual_proxy", _fake_manual_builder)

    assert app.build_server(client, config) is manual_server


def test_build_server_uses_builtin_path_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uses FastMCP.from_client path when builder returns a server."""
    app = StdioBridgeApplication()
    client = object()
    config = ClientConfig(url="https://example.com/mcp", use_from_client=True)

    monkeypatch.setattr(app, "_build_transforms", lambda: [object()])

    builtin_server = object()
    def _fake_build_from_client(
        _client: object,
        _transforms: list[object],
    ) -> object:
        return builtin_server

    monkeypatch.setattr(app, "_build_server_from_client", _fake_build_from_client)

    assert app.build_server(client, config) is builtin_server


def test_run_stdio_bridge_adapter_invokes_application_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compatibility adapter delegates to StdioBridgeApplication.run."""
    called = {"run": 0}

    def _fake_run(self: StdioBridgeApplication) -> None:
        called["run"] += 1

    monkeypatch.setattr(StdioBridgeApplication, "run", _fake_run)

    run_stdio_bridge()

    assert called["run"] == 1
