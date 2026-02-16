"""Static MCP Provider abstract base class.

This module provides an abstract base class for creating MCP provider implementations.
"""
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING
from app import GlobalAuthProvider
from src.tools.auth_config import AuthProviderType
from src.tools.spec_config import AzureAuthConfig
from tools import SpecConfig
from tools import SpecConfig, AzureOauth
from src.app.cache_provider import CacheProvider

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider
    from httpx import Auth


class StaticMcpProvider(ABC):
    """Abstract base class for MCP provider implementations."""

    def __init__(self, config: SpecConfig) -> None:
        """Initialize the StaticMcpProvider.

        Args:
            config: The SpecConfig instance for this provider.
        """
        self.config = config

    def _create_auth_provider(self, provider_name: AuthProviderType | None = None) -> AuthProvider | None:
        """Create and return an authentication handler.

        Returns:
            An Authentication provider instance for the provider.
        """
        return GlobalAuthProvider.get_auth_provider(provider_name)
    
    @staticmethod
    def _scope_value(config: AzureAuthConfig) -> str | None:
        if not config.scopes:
            return None
        return " ".join(config.scopes)
    
    def _create_client_auth(self, azure_config: AzureAuthConfig) -> "Auth":
        scope_value = self._scope_value(azure_config)
        assert self.config.base_url

        auth = AzureOauth(
            client_id=azure_config.client_id,
            client_secret=azure_config.client_secret,
            token_url=azure_config.token_url,
            scope=scope_value,
            token_storage=CacheProvider.get_oauth_store()
        )

        return auth
