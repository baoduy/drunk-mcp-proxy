"""
AuthConfig data models for authentication provider configuration.

This module provides Pydantic models for loading and validating authentication
configuration files that define FastMCP authentication providers.
Similar to spec_config.py, it supports environment variable resolution.

The configuration file (data/auth.json) is a flat JSON object where:
- Each key is a provider name (e.g., 'azure', 'github')
- Each value is a provider configuration dictionary
- Configuration values can reference environment variables using $VAR_NAME or ${VAR_NAME} syntax
- All providers are optional - if a provider is not in the config, it's not used
"""

import json
import os
from enum import Enum
from typing import Any, Optional, cast

from pydantic import BaseModel, Field, ConfigDict, model_validator

from .env_resolver import resolve_env_var


class AuthProviderType(str, Enum):
    """Enumeration of supported authentication provider types."""
    AUTH0 = "auth0"
    AWS = "aws"
    AZURE = "azure"
    DEBUG = "debug"
    DESCOPE = "descope"
    DISCORD = "discord"
    GITHUB = "github"
    GOOGLE = "google"
    IN_MEMORY = "in_memory"
    INTROSPECTION = "introspection"
    JWT = "jwt"
    OCI = "oci"
    SCALEKIT = "scalekit"
    SUPABASE = "supabase"
    WORKOS = "workos"

class AuthConfig(BaseModel):
    """
    Root authentication configuration model.

    This model represents the entire authentication configuration with top-level
    provider configurations. Each provider field is optional - if a provider is
    not present in the configuration, it means that authentication method is not
    used by the application.

    Configuration values support environment variable resolution using $VAR_NAME or
    ${VAR_NAME} syntax. Environment variables are resolved automatically when loading
    from a file.

    Attributes:
        default_provider: Default authentication provider type
        auth0: Auth0 provider configuration
        aws: AWS provider configuration
        azure: Azure provider configuration
        descope: Descope provider configuration
        discord: Discord provider configuration
        github: GitHub provider configuration
        google: Google provider configuration
        in_memory: In-memory provider configuration
        introspection: Token introspection provider configuration
        jwt: JWT provider configuration
        oci: OCI provider configuration
        scalekit: Scalekit provider configuration
        supabase: Supabase provider configuration
        workos: WorkOS provider configuration

    Example:
        config = AuthConfig.load_from_file("data/auth.json")

        # Access specific provider config
        if config.azure:
            client_id = config.azure.get("client_id")
            
        if config.github:
            client_id = config.github.get("client_id")
            scopes = config.github.get("scopes", [])
    """
    default_provider: Optional[AuthProviderType] = Field(default=None, alias="defaultProvider", description="Default authentication provider type")
    auth0: Optional[dict[str, Any]] = Field(default=None, description="Auth0 provider configuration")
    aws: Optional[dict[str, Any]] = Field(default=None, description="AWS provider configuration")
    azure: Optional[dict[str, Any]] = Field(default=None, description="Azure provider configuration")
    descope: Optional[dict[str, Any]] = Field(default=None, description="Descope provider configuration")
    discord: Optional[dict[str, Any]] = Field(default=None, description="Discord provider configuration")
    github: Optional[dict[str, Any]] = Field(default=None, description="GitHub provider configuration")
    google: Optional[dict[str, Any]] = Field(default=None, description="Google provider configuration")
    in_memory: Optional[dict[str, Any]] = Field(default=None, alias="inMemory", description="In-memory provider configuration")
    introspection: Optional[dict[str, Any]] = Field(default=None, description="Token introspection provider configuration")
    jwt: Optional[dict[str, Any]] = Field(default=None, description="JWT provider configuration")
    oci: Optional[dict[str, Any]] = Field(default=None, description="OCI provider configuration")
    scalekit: Optional[dict[str, Any]] = Field(default=None, description="Scalekit provider configuration")
    supabase: Optional[dict[str, Any]] = Field(default=None, description="Supabase provider configuration")
    workos: Optional[dict[str, Any]] = Field(default=None, description="WorkOS provider configuration")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "AuthConfig":
        """Resolve environment variables in all provider configurations."""
        for provider_type in AuthProviderType:
            provider_config = getattr(self, provider_type.value, None)
            if provider_config is not None:
                resolved = self._resolve_env_in_dict(provider_config)
                setattr(self, provider_type.value, resolved)
        return self

    @staticmethod
    def _resolve_env_in_dict(data: Any) -> Any:
        """
        Recursively resolve environment variables in dictionary, list, or string values.
        
        Supports $VAR_NAME and ${VAR_NAME} syntax in strings.
        
        Args:
            data: Dictionary, list, string, or other value to process
            
        Returns:
            Updated data with environment variables resolved
        """
        if isinstance(data, dict):
            return {k: AuthConfig._resolve_env_in_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AuthConfig._resolve_env_in_dict(item) for item in data]
        elif isinstance(data, str):
            return resolve_env_var(data)
        else:
            return data

    def get_config(self, provider_type: AuthProviderType | None = None) -> Optional[dict[str, Any]]:
        """
        Get configuration for a specific provider.
        If provider_type is None, returns the default provider configuration if default_provider is set.

        Args:
            provider_type: The authentication provider type

        Returns:
            Configuration dictionary for the provider if it exists, None otherwise

        Example:
            azure_config = config.get_config(AuthProviderType.AZURE)
            if azure_config:
                client_id = azure_config.get("client_id")
                client_secret = azure_config.get("client_secret")
        """
        if provider_type is None and self.default_provider is not None:
            provider_type = self.default_provider
        return getattr(self, provider_type.value, None) if provider_type else None

    @staticmethod
    def load_from_file(config_file: str) -> "AuthConfig":
        """
        Load authentication configuration from a JSON file.

        This static method reads a JSON configuration file and creates an AuthConfig
        instance with resolved environment variables.

        Args:
            config_file: Path to the authentication configuration JSON file

        Returns:
            AuthConfig instance with loaded and validated provider configurations

        Raises:
            FileNotFoundError: If the config file doesn't exist
            json.JSONDecodeError: If the config file contains invalid JSON
            ValueError: If the JSON root is not an object

        Example:
            config = AuthConfig.load_from_file("data/auth.json")
            if config.azure:
                client_id = config.azure.get("client_id")
                
            if config.github:
                scopes = config.github.get("scopes")
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Authentication configuration file not found: {config_file}")

        with open(config_file, "r") as f:
            loaded_data: Any = json.load(f)

        if not isinstance(loaded_data, dict):
            raise ValueError("Authentication configuration file must contain a JSON object")

        # Validate and create config
        auth_config = AuthConfig.model_validate(cast(dict[str, Any], loaded_data))

        return auth_config
