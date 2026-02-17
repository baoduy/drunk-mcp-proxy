"""Global Authentication Provider module.

This module provides a factory class for creating authentication providers
from configuration files.
"""
from __future__ import annotations

import os
from typing import Any, Optional, TYPE_CHECKING
from .cache_provider import CacheProvider
from tools import AuthConfig, AuthProviderType
from tools.env import CONFIG_DIR
from tools.logging_config import setup_logging

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


logger = setup_logging(__name__)


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
            logger.info("Loading authentication configuration from: %s", auth_config_path)
            cls._auth_config = AuthConfig.load_from_file(auth_config_path)
            logger.debug("Authentication configuration loaded successfully")
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
            logger.debug("Returning cached provider for: %s", provider_name)
            return GlobalAuthProvider._provider_cache[provider_name]

        config = GlobalAuthProvider._load_config()
        provider_config = config.get_config(provider_name)

        if provider_config is None:
            logger.warning("Provider configuration not found for: %s", provider_name)
            GlobalAuthProvider._provider_cache[provider_name] = None
            return None

        # Determine which provider type to use
        resolved_provider_type = provider_name or config.default_provider
        if resolved_provider_type is None:
            logger.warning("No provider type specified and no default provider configured")
            GlobalAuthProvider._provider_cache[provider_name] = None
            return None

        # Map provider type to FastMCP provider class
        provider_class_info = GlobalAuthProvider._get_provider_class(resolved_provider_type)

        if provider_class_info is None:
            logger.warning("Could not find provider class for type: %s", resolved_provider_type)
            GlobalAuthProvider._provider_cache[provider_name] = None
            return None

        provider_class, needs_client_storage = provider_class_info

        # Create provider instance from configuration
        logger.info("Creating authentication provider of type: %s", resolved_provider_type)
        provider_instance = GlobalAuthProvider._create_provider_instance(provider_class, provider_config, needs_client_storage)

        # Cache the provider instance
        GlobalAuthProvider._provider_cache[provider_name] = provider_instance

        if provider_instance is not None:
            logger.info("Successfully created and cached authentication provider: %s", resolved_provider_type)
        else:
            logger.warning("Failed to create authentication provider instance for: %s", resolved_provider_type)

        return provider_instance

    @staticmethod
    def _get_provider_class(provider_type: AuthProviderType) -> Optional[tuple[type, bool]]:
        """Get the FastMCP provider class for the given provider type.

        Args:
            provider_type: The authentication provider type.

        Returns:
            A tuple of (provider_class, needs_client_storage) if found, None otherwise.
        """
        provider_mapping = {
            AuthProviderType.AUTH0: ("fastmcp.server.auth.providers.auth0", "Auth0Provider", False),
            AuthProviderType.AWS: ("fastmcp.server.auth.providers.aws", "AWSProvider", False),
            AuthProviderType.AZURE: ("fastmcp.server.auth.providers.azure", "AzureProvider", True),
            AuthProviderType.DISCORD: ("fastmcp.server.auth.providers.discord", "DiscordProvider", True),
            AuthProviderType.GITHUB: ("fastmcp.server.auth.providers.github", "GitHubProvider", True),
            AuthProviderType.GOOGLE: ("fastmcp.server.auth.providers.google", "GoogleProvider", True),
            AuthProviderType.JWT: ("fastmcp.server.auth.providers.jwt", "JWTVerifier", False),
            AuthProviderType.INTROSPECTION: ("fastmcp.server.auth.providers.introspection", "IntrospectionProvider", False),
            AuthProviderType.SUPABASE: ("fastmcp.server.auth.providers.supabase", "SupabaseProvider", True),
        }

        if provider_type not in provider_mapping:
            return None

        module_name, class_name, needs_client_storage = provider_mapping[provider_type]

        try:
            module = __import__(module_name, fromlist=[class_name])
            provider_class = getattr(module, class_name)
            return (provider_class, needs_client_storage)
        except (ImportError, AttributeError) as e:
            logger.error("Failed to import provider class %s from %s: %s", class_name, module_name, str(e))
            return None

    @staticmethod
    def _create_provider_instance(provider_class: type, config: dict[str,Any], needs_client_storage: bool = False) -> "AuthProvider | None":
        """Create an instance of a provider from its configuration.

        Args:
            provider_class: The provider class to instantiate.
            config: The configuration model for the provider.
            needs_client_storage: Whether this provider needs OAuth client storage for token caching.

        Returns:
            An instance of the provider, or None if creation fails.
            
        Raises:
            TypeError: If provider initialization fails with invalid arguments.
            Exception: If config dict manipulation fails.
        """
        # Make a copy to avoid mutating the original config
        config_dict = config.copy()
        
        # Inject client_storage only for providers that need it (OAuth providers)
        if needs_client_storage:
            config_dict['client_storage'] = CacheProvider.get_oauth_store()
    
        return provider_class(**config_dict)
        
