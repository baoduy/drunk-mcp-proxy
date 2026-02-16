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
from typing import Any, Optional, Dict, List, cast

from pydantic import BaseModel, Field, model_validator, ConfigDict

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


class Auth0Config(BaseModel):
    """Auth0 authentication provider configuration."""
    domain: str = Field(description="Auth0 domain")
    client_id: str = Field(description="Auth0 client ID")
    client_secret: str = Field(description="Auth0 client secret")
    audience: Optional[str] = Field(default=None, description="Auth0 audience")
    scopes: List[str] = Field(default_factory=list, description="Auth0 scopes")
    grant_type: str = Field(default="client_credentials", description="OAuth grant type")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "Auth0Config":
        """Resolve environment variable references in Auth0 configuration."""
        self.domain = resolve_env_var(self.domain)
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        if self.audience:
            self.audience = resolve_env_var(self.audience)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        return self


class AWSConfig(BaseModel):
    """AWS authentication provider configuration."""
    access_key_id: str = Field(description="AWS access key ID")
    secret_access_key: str = Field(description="AWS secret access key")
    region: str = Field(description="AWS region")
    session_token: Optional[str] = Field(default=None, description="AWS session token")
    role_arn: Optional[str] = Field(default=None, description="AWS role ARN")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "AWSConfig":
        """Resolve environment variable references in AWS configuration."""
        self.access_key_id = resolve_env_var(self.access_key_id)
        self.secret_access_key = resolve_env_var(self.secret_access_key)
        self.region = resolve_env_var(self.region)
        if self.session_token:
            self.session_token = resolve_env_var(self.session_token)
        if self.role_arn:
            self.role_arn = resolve_env_var(self.role_arn)
        return self


class AzureConfig(BaseModel):
    """Azure authentication provider configuration."""
    client_id: str = Field(description="Azure client ID")
    client_secret: str = Field(description="Azure client secret")
    tenant_id: str = Field(description="Azure tenant ID")
    token_url: Optional[str] = Field(default=None, description="Azure token URL")
    issuer: Optional[str] = Field(default=None, description="Azure issuer")
    scopes: List[str] = Field(default_factory=list, description="Azure scopes")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "AzureConfig":
        """Resolve environment variable references in Azure configuration."""
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        self.tenant_id = resolve_env_var(self.tenant_id)
        if self.token_url:
            self.token_url = resolve_env_var(self.token_url)
        if self.issuer:
            self.issuer = resolve_env_var(self.issuer)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        return self


class DescopeConfig(BaseModel):
    """Descope authentication provider configuration."""
    project_id: str = Field(description="Descope project ID")
    public_key: str = Field(description="Descope public key")
    scopes: List[str] = Field(default_factory=list, description="Descope scopes")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "DescopeConfig":
        """Resolve environment variable references in Descope configuration."""
        self.project_id = resolve_env_var(self.project_id)
        self.public_key = resolve_env_var(self.public_key)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        return self


class DiscordConfig(BaseModel):
    """Discord authentication provider configuration."""
    client_id: str = Field(description="Discord client ID")
    client_secret: str = Field(description="Discord client secret")
    bot_token: str = Field(description="Discord bot token")
    scopes: List[str] = Field(default_factory=list, description="Discord scopes")
    redirect_uri: Optional[str] = Field(default=None, description="Discord redirect URI")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "DiscordConfig":
        """Resolve environment variable references in Discord configuration."""
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        self.bot_token = resolve_env_var(self.bot_token)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        if self.redirect_uri:
            self.redirect_uri = resolve_env_var(self.redirect_uri)
        return self


class GitHubConfig(BaseModel):
    """GitHub authentication provider configuration."""
    client_id: str = Field(description="GitHub client ID")
    client_secret: str = Field(description="GitHub client secret")
    scopes: List[str] = Field(default_factory=list, description="GitHub scopes")
    redirect_uri: Optional[str] = Field(default=None, description="GitHub redirect URI")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "GitHubConfig":
        """Resolve environment variable references in GitHub configuration."""
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        if self.redirect_uri:
            self.redirect_uri = resolve_env_var(self.redirect_uri)
        return self


class GoogleConfig(BaseModel):
    """Google authentication provider configuration."""
    client_id: str = Field(description="Google client ID")
    client_secret: str = Field(description="Google client secret")
    project_id: str = Field(description="Google project ID")
    scopes: List[str] = Field(default_factory=list, description="Google scopes")
    redirect_uri: Optional[str] = Field(default=None, description="Google redirect URI")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "GoogleConfig":
        """Resolve environment variable references in Google configuration."""
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        self.project_id = resolve_env_var(self.project_id)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        if self.redirect_uri:
            self.redirect_uri = resolve_env_var(self.redirect_uri)
        return self


class InMemoryConfig(BaseModel):
    """In-memory authentication provider configuration."""
    users: Dict[str, str] = Field(default_factory=dict, description="In-memory user credentials")

    model_config = ConfigDict(populate_by_name=True)


class IntrospectionConfig(BaseModel):
    """Token introspection authentication provider configuration."""
    introspection_url: str = Field(description="Token introspection URL")
    client_id: str = Field(description="Client ID for introspection")
    client_secret: str = Field(description="Client secret for introspection")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "IntrospectionConfig":
        """Resolve environment variable references in introspection configuration."""
        self.introspection_url = resolve_env_var(self.introspection_url)
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        return self


class JWTConfig(BaseModel):
    """JWT authentication provider configuration."""
    secret_key: str = Field(description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    issuer: Optional[str] = Field(default=None, description="JWT issuer")
    audience: Optional[str] = Field(default=None, description="JWT audience")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "JWTConfig":
        """Resolve environment variable references in JWT configuration."""
        self.secret_key = resolve_env_var(self.secret_key)
        if self.issuer:
            self.issuer = resolve_env_var(self.issuer)
        if self.audience:
            self.audience = resolve_env_var(self.audience)
        return self


class OCIConfig(BaseModel):
    """OCI authentication provider configuration."""
    user_ocid: str = Field(description="OCI user OCID")
    tenancy_ocid: str = Field(description="OCI tenancy OCID")
    api_key: str = Field(description="OCI API key")
    fingerprint: str = Field(description="OCI fingerprint")
    region: str = Field(default="us-phoenix-1", description="OCI region")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "OCIConfig":
        """Resolve environment variable references in OCI configuration."""
        self.user_ocid = resolve_env_var(self.user_ocid)
        self.tenancy_ocid = resolve_env_var(self.tenancy_ocid)
        self.api_key = resolve_env_var(self.api_key)
        self.fingerprint = resolve_env_var(self.fingerprint)
        self.region = resolve_env_var(self.region)
        return self


class ScalekitConfig(BaseModel):
    """Scalekit authentication provider configuration."""
    client_id: str = Field(description="Scalekit client ID")
    client_secret: str = Field(description="Scalekit client secret")
    environment_url: str = Field(description="Scalekit environment URL")
    scopes: List[str] = Field(default_factory=list, description="Scalekit scopes")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "ScalekitConfig":
        """Resolve environment variable references in Scalekit configuration."""
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        self.environment_url = resolve_env_var(self.environment_url)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        return self


class SupabaseConfig(BaseModel):
    """Supabase authentication provider configuration."""
    project_url: str = Field(description="Supabase project URL")
    api_key: str = Field(description="Supabase API key")
    scopes: List[str] = Field(default_factory=list, description="Supabase scopes")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "SupabaseConfig":
        """Resolve environment variable references in Supabase configuration."""
        self.project_url = resolve_env_var(self.project_url)
        self.api_key = resolve_env_var(self.api_key)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        return self


class WorkosConfig(BaseModel):
    """WorkOS authentication provider configuration."""
    api_key: str = Field(description="WorkOS API key")
    client_id: str = Field(description="WorkOS client ID")
    organization_id: Optional[str] = Field(default=None, description="WorkOS organization ID")
    scopes: List[str] = Field(default_factory=list, description="WorkOS scopes")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "WorkosConfig":
        """Resolve environment variable references in WorkOS configuration."""
        self.api_key = resolve_env_var(self.api_key)
        self.client_id = resolve_env_var(self.client_id)
        if self.organization_id:
            self.organization_id = resolve_env_var(self.organization_id)
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]
        return self

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
        auth0: Auth0 provider configuration
        aws: AWS provider configuration
        azure: Azure provider configuration
        descope: Descope provider configuration
        discord: Discord provider configuration
        github: GitHub provider configuration
        google: Google provider configuration
        inMemory: In-memory provider configuration
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
            client_id = config.azure.client_id
            
        if config.github:
            client_id = config.github.client_id
            scopes = config.github.scopes
    """
    default_provider: Optional[AuthProviderType] = Field(default=None, alias="defaultProvider", description="Default authentication provider type")
    auth0: Optional[Auth0Config] = Field(default=None, description="Auth0 provider configuration")
    aws: Optional[AWSConfig] = Field(default=None, description="AWS provider configuration")
    azure: Optional[AzureConfig] = Field(default=None, description="Azure provider configuration")
    descope: Optional[DescopeConfig] = Field(default=None, description="Descope provider configuration")
    discord: Optional[DiscordConfig] = Field(default=None, description="Discord provider configuration")
    github: Optional[GitHubConfig] = Field(default=None, description="GitHub provider configuration")
    google: Optional[GoogleConfig] = Field(default=None, description="Google provider configuration")
    in_memory: Optional[InMemoryConfig] = Field(default=None, alias="inMemory", description="In-memory provider configuration")
    introspection: Optional[IntrospectionConfig] = Field(default=None, description="Token introspection provider configuration")
    jwt: Optional[JWTConfig] = Field(default=None, description="JWT provider configuration")
    oci: Optional[OCIConfig] = Field(default=None, description="OCI provider configuration")
    scalekit: Optional[ScalekitConfig] = Field(default=None, description="Scalekit provider configuration")
    supabase: Optional[SupabaseConfig] = Field(default=None, description="Supabase provider configuration")
    workos: Optional[WorkosConfig] = Field(default=None, description="WorkOS provider configuration")

    model_config = ConfigDict(populate_by_name=True)

    def get_config(self, provider_type: AuthProviderType|None=None) -> Optional[BaseModel]:
        """
        Get configuration for a specific provider.
        If provider_type is None, returns the default provider configuration if default_provider is set.

        Args:
            provider_type: The authentication provider type

        Returns:
            Configuration model for the provider if it exists, None otherwise

        Example:
            azure_config = config.get_config(AuthProviderType.AZURE)
            if azure_config:
                client_id = azure_config.client_id
                client_secret = azure_config.client_secret
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
                client_id = config.azure.client_id
                
            if config.github:
                scopes = config.github.scopes
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Authentication configuration file not found: {config_file}")

        with open(config_file, "r") as f:
            loaded_data: Any = json.load(f)

        if not isinstance(loaded_data, dict):
            raise ValueError("Authentication configuration file must contain a JSON object")

        # Validate and resolve environment variables
        auth_config = AuthConfig.model_validate(cast(Dict[str, Any], loaded_data))

        return auth_config
