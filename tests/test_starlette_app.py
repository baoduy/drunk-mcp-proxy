"""Unit tests for StarletteApp."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

import src.app.starlette_app as starlette_app
from src.proxies.mcp_proxy_config import McpProxyConfig


class DummyMcpServer:
    """Minimal MCP server stub returning an ASGI app."""

    def http_app(self, path: str = "/"):
        return Starlette()


def _make_config(path: str) -> McpProxyConfig:
    return McpProxyConfig.model_construct(path=path, mcp_server=DummyMcpServer())


def test_health_check_returns_service_name(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    app_factory = starlette_app.StarletteApp()
    app = app_factory.build()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "unit-test"}


def test_add_mcp_service_root_mount(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    app_factory = starlette_app.StarletteApp()
    app_factory.add_mcp_service(_make_config("/"))
    app = app_factory.build()

    mounts = [route for route in app.routes if isinstance(route, Mount)]
    assert any(route.path == "/mcp" for route in mounts)


def test_add_mcp_service_namespaced_mount(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    app_factory = starlette_app.StarletteApp()
    app_factory.add_mcp_service(_make_config("/stock"))
    app = app_factory.build()

    mounts = [route for route in app.routes if isinstance(route, Mount)]
    assert any(route.path == "/stock/mcp" for route in mounts)


def test_add_mcp_services_adds_all(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    app_factory = starlette_app.StarletteApp()
    services = [_make_config("/"), _make_config("/stock")]

    app_factory.add_mcp_services(services)

    assert len(app_factory.mcp_apps) == 2


def test_add_mcp_services_propagates_error(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    app_factory = starlette_app.StarletteApp()

    def raise_error(_service):
        raise RuntimeError("boom")

    monkeypatch.setattr(app_factory, "add_mcp_service", raise_error)

    try:
        app_factory.add_mcp_services([_make_config("/")])
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        assert False, "Expected RuntimeError to be raised"
