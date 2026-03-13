"""FastMCP auth provider registry and factory."""

from __future__ import annotations

from typing import Any

from drunk_ai_proxy.app.cache_provider import CacheProvider
from drunk_ai_proxy.utils import AuthType


class AuthProviderRegistry:
    """Registry for creating FastMCP auth providers by auth type."""

    @staticmethod
    def create(name: AuthType, config: dict[str, Any], provider_names: list[str]) -> object:
        """Create a FastMCP auth provider for the given auth type.

        Args:
            name: Auth provider type.
            config: Auth provider configuration.
            provider_names: Available provider names for error messages.

        Returns:
            FastMCP auth provider instance.

        Raises:
            ValueError: If provider type is unsupported.
        """
        match name:
            case AuthType.BASIC:
                from drunk_ai_proxy.auth.api_auth_provider import ApiKeyAuthProvider

                return ApiKeyAuthProvider(**config)
            case AuthType.JWT:
                from fastmcp.server.auth.providers.jwt import JWTVerifier

                return JWTVerifier(**config)
            case AuthType.AZURE:
                from fastmcp.server.auth.providers.azure import AzureProvider

                return AzureProvider(**config, client_storage=CacheProvider.get_oauth_store())
            case AuthType.AUTH0:
                from fastmcp.server.auth.providers.auth0 import Auth0Provider

                return Auth0Provider(**config, client_storage=CacheProvider.get_oauth_store())
            case AuthType.AWS:
                from fastmcp.server.auth.providers.aws import AWSCognitoProvider

                return AWSCognitoProvider(
                    **config,
                    client_storage=CacheProvider.get_oauth_store(),
                )
            case AuthType.DISCORD:
                from fastmcp.server.auth.providers.discord import DiscordProvider

                return DiscordProvider(**config, client_storage=CacheProvider.get_oauth_store())
            case AuthType.GITHUB:
                from fastmcp.server.auth.providers.github import GitHubProvider

                return GitHubProvider(**config, client_storage=CacheProvider.get_oauth_store())
            case AuthType.GOOGLE:
                from fastmcp.server.auth.providers.google import GoogleProvider

                return GoogleProvider(**config, client_storage=CacheProvider.get_oauth_store())
            case AuthType.IN_MEMORY:
                from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider

                return InMemoryOAuthProvider(**config)
            case AuthType.INTROSPECTION:
                from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

                return IntrospectionTokenVerifier(**config)
            case AuthType.OCI:
                from fastmcp.server.auth.providers.oci import OCIProvider

                return OCIProvider(**config, client_storage=CacheProvider.get_oauth_store())
            case AuthType.SUPABASE:
                from fastmcp.server.auth.providers.supabase import SupabaseProvider

                return SupabaseProvider(**config)
            case _:
                raise ValueError(
                    f"Unsupported authentication provider type: {name} in {provider_names}"
                )
