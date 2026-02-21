"""Unit tests for StarletteApp."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

import src.app.starlette_app as starlette_app
from src.proxies.static_mcp_provider import McpProxyConfig


class DummyMcpServer:
    """Minimal MCP server stub returning an ASGI app."""

    def http_app(self, path: str = "/", **kwargs):
        return Starlette()


def _make_config(path: str) -> McpProxyConfig:
    return McpProxyConfig(path=path, mcp_server=DummyMcpServer())


class DummyLlmProvider:
    """Minimal LLM provider stub for testing."""
    
    def __init__(self, providers=None):
        self.providers = providers or []
        self.mounted_routes = []
    
    def mount(self, app, route_prefix="/llm/v1"):
        self.mounted_routes.append((app, route_prefix))


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


def test_add_llm_service_stores_service(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    app_factory = starlette_app.StarletteApp()
    
    llm_service = DummyLlmProvider(providers=["provider1"])
    app_factory._add_llm_service("/llm/v1", llm_service)
    
    assert len(app_factory.llm_services) == 1
    assert app_factory.llm_services[0] == ("/llm/v1", llm_service)


def test_add_llm_services_adds_all(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    app_factory = starlette_app.StarletteApp()
    
    llm_provider1 = DummyLlmProvider(providers=["provider1"])
    llm_provider2 = DummyLlmProvider(providers=["provider2"])
    services = [("prefix1", llm_provider1), ("prefix2", llm_provider2)]
    
    app_factory.add_llm_services(services)
    
    assert len(app_factory.llm_services) == 2
    assert app_factory.llm_services[0] == ("prefix1", llm_provider1)
    assert app_factory.llm_services[1] == ("prefix2", llm_provider2)


def test_build_mounts_llm_services(monkeypatch):
    monkeypatch.setattr(starlette_app, "SERVER_NAME", "unit-test")
    monkeypatch.setattr(starlette_app, "OPENAPI_ENABLED", False)
    app_factory = starlette_app.StarletteApp()
    
    llm_provider = DummyLlmProvider(providers=["provider1"])
    app_factory._add_llm_service("/llm/v1", llm_provider)
    
    app = app_factory.build()
    
    assert len(llm_provider.mounted_routes) == 1
    mounted_app, route_prefix = llm_provider.mounted_routes[0]
    assert mounted_app == app
    assert route_prefix == "/llm/v1"
