"""App package for MCP proxy."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app_config_provider import AppConfigProvider
    from .auth_provider_registry import AuthProviderRegistry
    from .cache_provider import CacheProvider
    from .client_auth_handler_factory import ClientAuthHandlerFactory
    from .lifespan import AppLifespanManager
    from .middleware_provider import AuthHeaderMiddleware, RateLimitMiddleware
    from .server import MCPProxyServer
    from .starlette_app import StarletteApp
    from .swagger_provider import SwaggerProvider

__all__ = [
    # app_config_provider
    "AppConfigProvider",
    "AuthProviderRegistry",
    "ClientAuthHandlerFactory",
    # cache_provider
    "CacheProvider",
    # lifespan
    "AppLifespanManager",
    # middleware_provider
    "AuthHeaderMiddleware",
    "RateLimitMiddleware",
    # server
    "MCPProxyServer",
    # starlette_app
    "StarletteApp",
    # swagger_provider
    "SwaggerProvider",
]


def __getattr__(name: str) -> object:
    if name == "AppConfigProvider":
        from . import app_config_provider

        return getattr(app_config_provider, name)

    if name == "AuthProviderRegistry":
        from . import auth_provider_registry

        return auth_provider_registry.AuthProviderRegistry

    if name == "ClientAuthHandlerFactory":
        from . import client_auth_handler_factory

        return client_auth_handler_factory.ClientAuthHandlerFactory

    if name == "CacheProvider":
        from . import cache_provider

        return cache_provider.CacheProvider

    if name == "AppLifespanManager":
        from . import lifespan

        return lifespan.AppLifespanManager

    if name in {"AuthHeaderMiddleware", "RateLimitMiddleware"}:
        from . import middleware_provider

        return getattr(middleware_provider, name)

    if name == "MCPProxyServer":
        from . import server

        return server.MCPProxyServer

    if name == "StarletteApp":
        from . import starlette_app

        return starlette_app.StarletteApp

    if name == "SwaggerProvider":
        from . import swagger_provider

        return swagger_provider.SwaggerProvider

    raise AttributeError(f"module 'app' has no attribute {name!r}")
