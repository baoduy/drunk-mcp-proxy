"""Unified registry for FastMCP and httpx auth handlers by auth type."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from drunk_ai_proxy.app.cache_provider import CacheProvider
from drunk_ai_proxy.utils import AuthType

if TYPE_CHECKING:
    import httpx
    from fastmcp.server.auth import AuthProvider


@dataclass(frozen=True)
class _AuthTypeEntry:
    """Registry entry containing factories for each auth integration path."""

    fastmcp_factory: Callable[[dict[str, Any]], "AuthProvider"]
    httpx_factory: Callable[[dict[str, Any]], "httpx.Auth"] | None = None


class AuthTypeRegistry:
    """Unified registry for auth provider creation across FastMCP and httpx."""

    @staticmethod
    def _create_fastmcp_basic(config: dict[str, Any]) -> "AuthProvider":
        from drunk_ai_proxy.auth.api_auth_provider import ApiKeyAuthProvider

        return ApiKeyAuthProvider(**config)

    @staticmethod
    def _create_fastmcp_jwt(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.jwt import JWTVerifier

        return JWTVerifier(**config)

    @staticmethod
    def _create_fastmcp_azure(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.azure import AzureProvider

        return AzureProvider(**config, client_storage=CacheProvider.get_oauth_store())

    @staticmethod
    def _create_fastmcp_auth0(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.auth0 import Auth0Provider

        return Auth0Provider(**config, client_storage=CacheProvider.get_oauth_store())

    @staticmethod
    def _create_fastmcp_aws(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.aws import AWSCognitoProvider

        return AWSCognitoProvider(**config, client_storage=CacheProvider.get_oauth_store())

    @staticmethod
    def _create_fastmcp_discord(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.discord import DiscordProvider

        return DiscordProvider(**config, client_storage=CacheProvider.get_oauth_store())

    @staticmethod
    def _create_fastmcp_github(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.github import GitHubProvider

        return GitHubProvider(**config, client_storage=CacheProvider.get_oauth_store())

    @staticmethod
    def _create_fastmcp_google(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.google import GoogleProvider

        return GoogleProvider(**config, client_storage=CacheProvider.get_oauth_store())

    @staticmethod
    def _create_fastmcp_in_memory(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider

        return InMemoryOAuthProvider(**config)

    @staticmethod
    def _create_fastmcp_introspection(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

        return IntrospectionTokenVerifier(**config)

    @staticmethod
    def _create_fastmcp_oci(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.oci import OCIProvider

        return OCIProvider(**config, client_storage=CacheProvider.get_oauth_store())

    @staticmethod
    def _create_fastmcp_supabase(config: dict[str, Any]) -> "AuthProvider":
        from fastmcp.server.auth.providers.supabase import SupabaseProvider

        return SupabaseProvider(**config)

    @staticmethod
    def _create_httpx_basic(config: dict[str, Any]) -> "httpx.Auth":
        from fastmcp.client.auth import BearerAuth

        return BearerAuth(**config)

    @staticmethod
    def _create_httpx_azure(config: dict[str, Any]) -> "httpx.Auth":
        from drunk_ai_proxy.auth import HttpxAzureOauth

        return HttpxAzureOauth(
            client_id=str(config["client_id"]),
            client_secret=str(config["client_secret"]),
            tenant_id=str(config["tenant_id"]),
            token_storage=CacheProvider.get_oauth_store(),
        )

    _REGISTRY: dict[AuthType, _AuthTypeEntry] = {}

    @classmethod
    def _ensure_registry(cls) -> None:
        if cls._REGISTRY:
            return
        cls._REGISTRY = {
            AuthType.BASIC: _AuthTypeEntry(
                fastmcp_factory=cls._create_fastmcp_basic,
                httpx_factory=cls._create_httpx_basic,
            ),
            AuthType.JWT: _AuthTypeEntry(fastmcp_factory=cls._create_fastmcp_jwt),
            AuthType.AZURE: _AuthTypeEntry(
                fastmcp_factory=cls._create_fastmcp_azure,
                httpx_factory=cls._create_httpx_azure,
            ),
            AuthType.AUTH0: _AuthTypeEntry(fastmcp_factory=cls._create_fastmcp_auth0),
            AuthType.AWS: _AuthTypeEntry(fastmcp_factory=cls._create_fastmcp_aws),
            AuthType.DISCORD: _AuthTypeEntry(fastmcp_factory=cls._create_fastmcp_discord),
            AuthType.GITHUB: _AuthTypeEntry(fastmcp_factory=cls._create_fastmcp_github),
            AuthType.GOOGLE: _AuthTypeEntry(fastmcp_factory=cls._create_fastmcp_google),
            AuthType.IN_MEMORY: _AuthTypeEntry(
                fastmcp_factory=cls._create_fastmcp_in_memory
            ),
            AuthType.INTROSPECTION: _AuthTypeEntry(
                fastmcp_factory=cls._create_fastmcp_introspection
            ),
            AuthType.OCI: _AuthTypeEntry(fastmcp_factory=cls._create_fastmcp_oci),
            AuthType.SUPABASE: _AuthTypeEntry(
                fastmcp_factory=cls._create_fastmcp_supabase
            ),
        }

    @classmethod
    def create_fastmcp_provider(
        cls,
        name: AuthType,
        config: dict[str, Any],
        provider_names: list[str],
    ) -> "AuthProvider":
        """Create FastMCP auth provider for the given auth type."""
        cls._ensure_registry()
        entry = cls._REGISTRY.get(name)
        if entry is None:
            raise ValueError(f"Unsupported authentication provider type: {name} in {provider_names}")
        return entry.fastmcp_factory(config)

    @classmethod
    def create_httpx_handler(
        cls,
        name: AuthType,
        config: dict[str, Any],
        provider_names: list[str],
    ) -> "httpx.Auth":
        """Create outbound httpx auth handler for the given auth type."""
        cls._ensure_registry()
        entry = cls._REGISTRY.get(name)
        if entry is None or entry.httpx_factory is None:
            raise ValueError(f"Unsupported authentication provider type: {name} in {provider_names}")
        return entry.httpx_factory(config)
