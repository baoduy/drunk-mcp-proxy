"""Unit tests for MCPProxyServer."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import drunk_ai_proxy.app.server as server


class FakeStarletteApp:
    """Minimal StarletteApp stub for _async_start_server tests."""

    def __init__(self, middleware=None):
        self.middleware = middleware
        self.mcp_services = []
        self.llm_services = []
        self.built = False

    def add_mcp_services(self, services):
        self.mcp_services = list(services)

    def add_llm_services(self, services):
        self.llm_services = list(services)

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


def test_initialization_creates_empty_services():
    """MCPProxyServer should initialize with empty service lists."""
    proxy = server.MCPProxyServer()
    
    assert proxy.mcp_services == []
    assert proxy.llm_services == []


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
    monkeypatch.setattr(server, "get_middlewares", lambda: ["mw1"])
    monkeypatch.setattr(server, "HOST", "127.0.0.1")
    monkeypatch.setattr(server, "PORT", 9999)
    monkeypatch.setattr(server, "LOG_LEVEL", "INFO")

    fake_uvicorn = SimpleNamespace(Config=FakeUvicornConfig, Server=FakeUvicornServer)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    proxy = server.MCPProxyServer()
    proxy.mcp_services = ["svc1"]
    proxy.llm_services = [("/llm/v1", "llm_svc1")]
    await proxy._async_start_server()

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
    monkeypatch.setattr(server, "get_middlewares", lambda: [])

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
    proxy.mcp_services = ["svc1"]
    with pytest.raises(ImportError):
        await proxy._async_start_server()


@pytest.mark.asyncio
async def test_async_run_happy_path(monkeypatch):
    """async_run should load MCP and LLM services and start the server."""
    mcp_services = ["svc1", "svc2"]

    class DummyMcpProvider:
        def __init__(self, config_dir):
            self.config_dir = config_dir

        def get_config_services(self):
            return mcp_services

    class DummyLlmProvider:
        def __init__(self, config_dir):
            self.config_dir = config_dir
            self.providers = ["provider1"]

    # Mock AppConfigProvider to avoid loading the actual config file
    mock_config_provider = Mock()
    mock_config_provider.get_mcp_configs.return_value = []
    mock_config_provider.get_llm_configs.return_value = []

    mock_app_config_provider = Mock()
    mock_app_config_provider.get_instance.return_value = mock_config_provider

    async_start = AsyncMock()

    monkeypatch.setattr(server, "AppConfigProvider", mock_app_config_provider)
    monkeypatch.setattr(server, "StaticProxiesProvider", DummyMcpProvider)
    monkeypatch.setattr(server, "LlmProxiesProvider", DummyLlmProvider)
    monkeypatch.setattr(server.MCPProxyServer, "_async_start_server", async_start)

    proxy = server.MCPProxyServer()
    await proxy.async_run()

    assert proxy.mcp_services == mcp_services
    assert len(proxy.llm_services) == 1
    assert proxy.llm_services[0][0] == server.LLM_ROUTE_PREFIX
    async_start.assert_called_once()


@pytest.mark.asyncio
async def test_async_run_loads_llm_providers(monkeypatch):
    """async_run should load LLM providers with correct route prefix."""
    mcp_services = []

    class DummyMcpProvider:
        def __init__(self, config_dir):
            self.config_dir = config_dir

        def get_config_services(self):
            return mcp_services

    class DummyLlmProvider:
        def __init__(self, config_dir):
            self.config_dir = config_dir
            self.providers = ["provider1"]

    # Mock AppConfigProvider to avoid loading the actual config file
    mock_config_provider = Mock()
    mock_config_provider.get_mcp_configs.return_value = []
    mock_config_provider.get_llm_configs.return_value = []

    mock_app_config_provider = Mock()
    mock_app_config_provider.get_instance.return_value = mock_config_provider

    async_start = AsyncMock()

    monkeypatch.setattr(server, "AppConfigProvider", mock_app_config_provider)
    monkeypatch.setattr(server, "StaticProxiesProvider", DummyMcpProvider)
    monkeypatch.setattr(server, "LlmProxiesProvider", DummyLlmProvider)
    monkeypatch.setattr(server, "LLM_ROUTE_PREFIX", "/llm/v1")
    monkeypatch.setattr(server.MCPProxyServer, "_async_start_server", async_start)

    proxy = server.MCPProxyServer()
    await proxy.async_run()

    assert len(proxy.llm_services) == 1
    route_prefix, llm_service = proxy.llm_services[0]
    assert route_prefix == "/llm/v1"
    assert hasattr(llm_service, "providers")
