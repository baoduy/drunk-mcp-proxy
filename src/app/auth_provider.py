"""Global Authentication Provider module.

This module provides a factory class for creating authentication providers
from configuration files.
"""
from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

from tools import AuthConfig, AuthProviderType
from tools.env import CONFIG_DIR

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


class GlobalAuthProvider:
    """Factory class for creating authentication providers from configuration."""

    _auth_config: Optional[AuthConfig] = None
    _provider_cache: dict[Optional[AuthProviderType], "AuthProvider | None"] = {}

    @classmethod
    def _load_config(cls) -> "AuthConfig":
        """Load and cache the authentication configuration.

        Returns:
            AuthConfig instance with all provider configurations.
        """
        if cls._auth_config is None:
            auth_config_path = os.path.join(CONFIG_DIR, "auth.json")
            cls._auth_config = AuthConfig.load_from_file(auth_config_path)
        assert cls._auth_config is not None
        return cls._auth_config

    @staticmethod
    def get_auth_provider(provider_name: AuthProviderType | None = None) -> "AuthProvider | None":
        """Get an authentication provider based on the provider name.

        If provider_name is None, uses the default provider from configuration.
        If the provider is not configured, returns None.
        
        Providers are cached after creation and reused on subsequent calls.

        Args:
            provider_name: The provider type to get. If None, uses default provider.

        Returns:
            An AuthProvider instance if the provider is available, None otherwise.

        Example:
            # Get Azure provider
            azure_provider = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)

            # Get default provider
            default_provider = GlobalAuthProvider.get_auth_provider()

            # Get GitHub provider
            github_provider = GlobalAuthProvider.get_auth_provider(AuthProviderType.GITHUB)
        """
        # Check if provider is already cached
        if provider_name in GlobalAuthProvider._provider_cache:
            return GlobalAuthProvider._provider_cache[provider_name]

        try:
            config = GlobalAuthProvider._load_config()
            provider_config = config.get_config(provider_name)

            if provider_config is None:
                GlobalAuthProvider._provider_cache[provider_name] = None
                return None

            # Determine which provider type to use
            resolved_provider_type = provider_name or config.default_provider
            if resolved_provider_type is None:
                GlobalAuthProvider._provider_cache[provider_name] = None
                return None

            # Map provider type to FastMCP provider class
            provider_class = GlobalAuthProvider._get_provider_class(resolved_provider_type)

            if provider_class is None:
                GlobalAuthProvider._provider_cache[provider_name] = None
                return None

            # Create provider instance from configuration
            provider_instance = GlobalAuthProvider._create_provider_instance(provider_class, provider_config)

            # Cache the provider instance
            GlobalAuthProvider._provider_cache[provider_name] = provider_instance

            return provider_instance

        except Exception:
            GlobalAuthProvider._provider_cache[provider_name] = None
            return None

    @staticmethod
    def _get_provider_class(provider_type: AuthProviderType) -> Optional[type]:
        """Get the FastMCP provider class for the given provider type.

        Args:
            provider_type: The authentication provider type.

        Returns:
            The provider class if found, None otherwise.
        """
        provider_mapping = {
            AuthProviderType.AUTH0: ("fastmcp.server.auth.providers.auth0", "Auth0Provider"),
            AuthProviderType.AWS: ("fastmcp.server.auth.providers.aws", "AWSProvider"),
            AuthProviderType.AZURE: ("fastmcp.server.auth.providers.azure", "AzureProvider"),
            AuthProviderType.DISCORD: ("fastmcp.server.auth.providers.discord", "DiscordProvider"),
            AuthProviderType.GITHUB: ("fastmcp.server.auth.providers.github", "GitHubProvider"),
            AuthProviderType.GOOGLE: ("fastmcp.server.auth.providers.google", "GoogleProvider"),
            AuthProviderType.JWT: ("fastmcp.server.auth.providers.jwt", "JWTVerifier"),
            AuthProviderType.INTROSPECTION: ("fastmcp.server.auth.providers.introspection", "IntrospectionProvider"),
            AuthProviderType.SUPABASE: ("fastmcp.server.auth.providers.supabase", "SupabaseProvider"),
        }

        if provider_type not in provider_mapping:
            return None

        module_name, class_name = provider_mapping[provider_type]

        try:
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)
        except (ImportError, AttributeError):
            return None

    @staticmethod
    def _create_provider_instance(provider_class: type, config: object) -> "AuthProvider | None":
        """Create an instance of a provider from its configuration.

        Args:
            provider_class: The provider class to instantiate.
            config: The configuration model for the provider.

        Returns:
            An instance of the provider, or None if creation fails.
        """
        try:
            # Convert config model to dictionary
            config_dict = config.model_dump(exclude_none=True)  # type: ignore
            return provider_class(**config_dict)
        except Exception:
            return None
