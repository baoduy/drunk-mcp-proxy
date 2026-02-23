"""App package for MCP proxy."""

from .app_config_provider import AppConfigProvider, get_provider
from .cache_provider import CacheProvider
from .lifespan import AppLifespanManager
from .middleware_provider import (
    AuthHeaderMiddleware,
    RateLimitMiddleware,
    get_middlewares,
)
from .server import MCPProxyServer
from .starlette_app import StarletteApp
from .swagger_provider import SwaggerProvider

__all__ = [
    # app_config_provider
    "AppConfigProvider",
    "get_provider",
    # cache_provider
    "CacheProvider",
    # lifespan
    "AppLifespanManager",
    # middleware_provider
    "AuthHeaderMiddleware",
    "RateLimitMiddleware",
    "get_middlewares",
    # server
    "MCPProxyServer",
    # starlette_app
    "StarletteApp",
    # swagger_provider
    "SwaggerProvider",
]
