"""
Authentication configuration provider module.

This module provides a centralized class for loading and managing authentication
configurations using AuthConfig from the CONFIG_DIR/auth.json file.
"""

import os
from typing import Optional, Dict, List, Any

from tools.auth_config import AuthConfig
from tools.env import CONFIG_DIR
from tools.logging_config import setup_logging


class AuthConfigProvider:
    """
    Provider class for loading and managing authentication configurations.

    This class uses AuthConfig to load authentication provider configurations from the
    auth.json file located in the CONFIG_DIR directory. It handles validation and
    resolution of environment variables for all configured providers.

    The authentication configuration is optional - any provider present in the
    configuration is considered "configured" and available for use. If a provider is not
    in the configuration, that authentication method is not used by the application.

    Attributes:
        config_dir: Directory containing configuration files
        config_file_path: Full path to the auth.json file
        auth_config: Loaded AuthConfig instance
        logger: Logger instance for this class

    Example:
        provider = AuthConfigProvider()
        provider.load_config()

        # Check if Azure is configured
        if provider.is_provider_configured("azure"):
            azure = provider.get_provider("azure")
            print(f"Azure configured: {azure}")

        # List all configured providers
        configured = provider.list_configured_providers()
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the AuthConfigProvider.

        Args:
            config_dir: Optional custom config directory. If not provided,
                       uses the CONFIG_DIR from environment variables.
        """
        self.config_dir = config_dir or CONFIG_DIR
        self.config_file_path = os.path.join(self.config_dir, "auth.json")
        self.auth_config: Optional[AuthConfig] = None
        self.logger = setup_logging(__name__)

    def _load_config(self) -> AuthConfig:
        """
        Load authentication configuration from auth.json file.

        This method uses AuthConfig.load_from_file() to load and validate
        the authentication configuration. Environment variables are resolved
        for all configured providers.

        Returns:
            Loaded and validated AuthConfig instance

        Raises:
            FileNotFoundError: If auth.json doesn't exist
            json.JSONDecodeError: If auth.json is invalid JSON
            ValueError: If validation fails for any provider configuration

        Example:
            provider = AuthConfigProvider()
            config = provider.load_config()
            print(f"Configured providers: {config.list_configured_providers()}")
        """
        self.logger.info(f"Loading authentication configuration from: {self.config_file_path}")

        if self.auth_config is not None:
            self.logger.info("Authentication configuration already loaded, returning cached config")
            return self.auth_config

        try:
            self.auth_config = AuthConfig.load_from_file(self.config_file_path)

            configured = self.auth_config.list_configured_providers()
            self.logger.info(f"Successfully loaded authentication configuration with {len(configured)} provider(s)")

            for name in configured:
                self.logger.debug(f"  - {name} provider is configured")

            return self.auth_config

        except FileNotFoundError as e:
            self.logger.error(f"Authentication configuration file not found: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"Authentication configuration validation failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load authentication configuration: {e}")
            raise

    def load_config(self) -> AuthConfig:
        """
        Public method to load authentication configuration.

        Returns:
            Loaded AuthConfig instance
        """
        return self._load_config()

    def get_config(self) -> AuthConfig:
        """
        Get the loaded authentication configuration.

        Automatically loads if not already loaded.

        Returns:
            AuthConfig instance
        """
        if self.auth_config is None:
            self._load_config()
        return self.auth_config

    def get_provider(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider (e.g., 'azure', 'github')

        Returns:
            Configuration dictionary if provider is configured, None otherwise

        Example:
            azure = provider.get_provider("azure")
            if azure:
                client_id = azure["client_id"]
        """
        config = self.get_config()
        return config.get_provider(provider_name)

    def is_provider_configured(self, provider_name: str) -> bool:
        """
        Check if a specific provider is configured.

        Args:
            provider_name: Name of the provider

        Returns:
            True if provider is configured, False otherwise

        Example:
            if provider.is_provider_configured("azure"):
                azure = provider.get_provider("azure")
                # Use azure
        """
        config = self.get_config()
        return config.is_provider_configured(provider_name)

    def list_configured_providers(self) -> List[str]:
        """
        Get list of all configured providers.

        Returns:
            List of provider names that are configured

        Example:
            providers = provider.list_configured_providers()
            print(f"Configured: {', '.join(providers)}")
        """
        config = self.get_config()
        return config.list_configured_providers()

    def get_all_providers(self) -> Dict[str, Any]:
        """
        Get all configured providers as a dictionary.

        Returns:
            Dictionary mapping provider names to their configurations

        Example:
            all_providers = provider.get_all_providers()
            for name, config in all_providers.items():
                print(f"Provider: {name}")
        """
        config = self.get_config()
        return config.to_dict()
