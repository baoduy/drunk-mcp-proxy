"""Unit tests for MCPProxyServer."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import src.app.server as server


class FakeStarletteApp:
    """Minimal StarletteApp stub for _async_start_server tests."""

    def __init__(self, middleware=None):
        self.middleware = middleware
        self.mounted = []
        self.built = False

    def add_mcp_services(self, services):
        self.mounted = list(services)

    def build(self):
        self.built = True
        return "fake-asgi-app"


class FakeUvicornConfig:
    """Capture config parameters for assertions."""

    def __init__(self, app, host, port, log_level):
        self.app = app
        self.host = host
        self.port = port
        self.log_level = log_level


class FakeUvicornServer:
    """Async server stub used by _async_start_server."""

    last_instance = None

    def __init__(self, config):
        self.config = config
        self.served = False
        FakeUvicornServer.last_instance = self

    async def serve(self):
        self.served = True


def test_retrieve_configuration_defaults(monkeypatch):
    """_retrieve_configuration should return defaults when HOST/PORT are unset."""
    monkeypatch.setattr(server, "SERVER_NAME", "test-server")
    monkeypatch.setattr(server, "SERVER_VERSION", "0.0.0")
    monkeypatch.setattr(server, "HOST", None)
    monkeypatch.setattr(server, "PORT", None)
    monkeypatch.setattr(server, "LOG_LEVEL", "INFO")
    monkeypatch.setattr(server, "CONFIG_DIR", "/tmp/config")

    config = server.MCPProxyServer._retrieve_configuration()

    assert config == {
        "server_name": "test-server",
        "server_version": "0.0.0",
        "host": "0.0.0.0",
        "port": 9123,
        "log_level": "INFO",
        "config_dir": "/tmp/config",
    }


def test_log_startup_configuration_logs(monkeypatch, caplog):
    """_log_startup_configuration should log all config fields."""
    monkeypatch.setattr(server, "SERVER_NAME", "test-server")
    monkeypatch.setattr(server, "SERVER_VERSION", "0.0.0")
    monkeypatch.setattr(server, "HOST", "127.0.0.1")
    monkeypatch.setattr(server, "PORT", 9123)
    monkeypatch.setattr(server, "LOG_LEVEL", "INFO")
    monkeypatch.setattr(server, "CONFIG_DIR", "/tmp/config")

    caplog.set_level("INFO")
    proxy = server.MCPProxyServer()
    proxy._log_startup_configuration()

    messages = [record.message for record in caplog.records]
    assert "MCP Proxy Server Configuration:" in messages
    assert "  Server Name: test-server" in messages
    assert "  Server Version: 0.0.0" in messages
    assert "  Host: 127.0.0.1" in messages
    assert "  Port: 9123" in messages
    assert "  Log Level: INFO" in messages
    assert "  Config Directory: /tmp/config" in messages


@pytest.mark.asyncio
async def test_async_start_server_runs_uvicorn(monkeypatch):
    """_async_start_server should create uvicorn server and call serve."""
    monkeypatch.setattr(server, "StarletteApp", FakeStarletteApp)
    monkeypatch.setattr(server, "HOST", "127.0.0.1")
    monkeypatch.setattr(server, "PORT", 9999)
    monkeypatch.setattr(server, "LOG_LEVEL", "INFO")

    fake_uvicorn = SimpleNamespace(Config=FakeUvicornConfig, Server=FakeUvicornServer)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    proxy = server.MCPProxyServer()
    await proxy._async_start_server(["svc1"], middleware=["mw1"])

    instance = FakeUvicornServer.last_instance
    assert instance is not None
    assert instance.served is True
    assert instance.config.app == "fake-asgi-app"
    assert instance.config.host == "127.0.0.1"
    assert instance.config.port == 9999
    assert instance.config.log_level == "info"


@pytest.mark.asyncio
async def test_async_start_server_import_error(monkeypatch):
    """_async_start_server should surface ImportError for uvicorn."""
    monkeypatch.setattr(server, "StarletteApp", FakeStarletteApp)

    original_import = __import__

    def import_side_effect(name, *args, **kwargs):
        if name == "uvicorn":
            raise ImportError("uvicorn not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(server, "HOST", "127.0.0.1")
    monkeypatch.setattr(server, "PORT", 9999)
    monkeypatch.setattr(server, "LOG_LEVEL", "INFO")
    monkeypatch.setattr("builtins.__import__", import_side_effect)

    proxy = server.MCPProxyServer()
    with pytest.raises(ImportError):
        await proxy._async_start_server(["svc1"], middleware=[])


@pytest.mark.asyncio
async def test_async_run_happy_path(monkeypatch):
    """async_run should load services and start the server."""
    services = ["svc1", "svc2"]

    class DummyProvider:
        def __init__(self, config_dir):
            self.config_dir = config_dir

        def get_config_services(self):
            return services

    async_start = AsyncMock()

    monkeypatch.setattr(server, "ProxyConfigProvider", DummyProvider)
    monkeypatch.setattr(server, "build_middleware", lambda: ["mw"])
    monkeypatch.setattr(server.MCPProxyServer, "_async_start_server", async_start)

    proxy = server.MCPProxyServer()
    await proxy.async_run()

    async_start.assert_called_once_with(services, ["mw"])


@pytest.mark.asyncio
async def test_async_run_keyboard_interrupt(monkeypatch):
    """KeyboardInterrupt during server start should be swallowed."""

    class DummyProvider:
        def __init__(self, config_dir):
            self.config_dir = config_dir

        def get_config_services(self):
            return ["svc1"]

    async_start = AsyncMock(side_effect=KeyboardInterrupt())

    monkeypatch.setattr(server, "ProxyConfigProvider", DummyProvider)
    monkeypatch.setattr(server, "build_middleware", lambda: [])
    monkeypatch.setattr(server.MCPProxyServer, "_async_start_server", async_start)

    proxy = server.MCPProxyServer()
    await proxy.async_run()
