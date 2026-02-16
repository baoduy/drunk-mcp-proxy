"""
SpecConfig data models for proxy configuration.

This module provides Pydantic models for loading and validating proxy
configuration files that define MCP and OpenAPI specifications.
"""

import json
import os
from enum import Enum
from typing import Any, Optional

import jsonschema
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .env import SCHEMA_DIR
from .env_resolver import resolve_env_var


class SpecType(str, Enum):
    """Enumeration of supported specification types."""
    MCP = "mcp"
    OPENAPI = "openapi"


class Filters(BaseModel):
    """
    Optional filters for proxy specifications.

    Attributes:
        methods: List of HTTP methods to filter (e.g., ["GET", "POST"])
        tags: List of tags to filter by
    """
    methods: Optional[list[str]] = Field(default=None, alias="methods", description="List of HTTP methods to filter")
    tags: Optional[list[str]] = Field(default=None, alias="tags", description="List of tags to filter by")

    model_config = ConfigDict(
        populate_by_name=True
    )


class AzureAuthConfig(BaseModel):
    """
    OAuth configuration for API authentication.

    Attributes:
        token_url: Azure EntraID token URL for obtaining access tokens
        client_id: Azure EntraID client ID
        client_secret: Azure EntraID client secret
        tenant_id: Azure EntraID Tenant ID
        issuer: Azure EntraID Issuer ID (optional)
        scopes: List of OAuth scopes to request (supports both 'scope' and 'scopes' in JSON)
    """
    token_url: str = Field(alias="tokenUrl", description="Token URL of Azure EntraID")
    client_id: str = Field(alias="clientId", description="Azure EntraID client ID")
    client_secret: str = Field(alias="clientSecret", description="Azure EntraID client secret")
    tenant_id: str = Field(alias="tenantId", description="Azure EntraID Tenant ID")
    issuer: Optional[str] = Field(default=None, alias="issuer", description="Azure EntraID Issuer ID")
    scopes: list[str] = Field(default_factory=list, validation_alias="scope", description="Azure EntraID scopes")

    model_config = ConfigDict(
        populate_by_name=True
    )

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "AzureAuthConfig":
        """Resolve environment variable references in OAuth configuration."""
        self.token_url = resolve_env_var(self.token_url)
        self.client_id = resolve_env_var(self.client_id)
        self.client_secret = resolve_env_var(self.client_secret)
        self.tenant_id = resolve_env_var(self.tenant_id)

        if self.issuer:
            self.issuer = resolve_env_var(self.issuer)

        # Resolve environment variables in scopes list
        self.scopes = [resolve_env_var(scope) for scope in self.scopes]

        return self


class AuthField(BaseModel):
    """
    Authentication configuration for proxy specifications.

    Attributes:
        azure: Optional OAuth configuration
    """
    azure: Optional[AzureAuthConfig] = Field(default=None, description="OAuth configuration")
    auth_token: Optional[str] = Field(default=None, alias="authToken",
                                      description="Static auth token for API authentication (if applicable)")
    model_config = ConfigDict(
        populate_by_name=True
    )


class SpecConfig(BaseModel):
    """
    Configuration model for a single proxy specification.
    
    Attributes:
        path: Base path for the proxy (default is '/')
        spec_file: Path to the specification file (relative to config dir)
        spec_type: Type of specification ("openapi" or "mcp")
        base_url: Base URL for the API (None for MCP specs)
        tags: List of tags for categorization
        filters: Optional filters for HTTP methods and tags
        auth: Optional authentication configuration
        spec_data: Loaded JSON data from the spec_file
    """
    path: str = Field(alias="path", description="Base path for the proxy")
    spec_file: str = Field(alias="specFile", description="Path to the specification file (relative to config dir)")
    spec_type: SpecType = Field(alias="specType", description="Type of specification ('openapi' or 'mcp')")
    base_url: Optional[str] = Field(default=None, alias="baseUrl",
                                    description="Base URL for the API (None for MCP specs)")
    tags: Optional[set[str]] = Field(default=None, alias="tags", description="List of tags for categorization")
    filters: Optional[Filters] = Field(default=None, alias="filters",
                                       description="Optional filters for methods and tags")
    auth: Optional[AuthField] = Field(default=None, alias="auth", description="Optional authentication configuration")
    spec_data: Optional[dict[str, Any]] = Field(default_factory=dict, exclude=True,
                                                description="Loaded JSON data from the spec_file (not included in serialization)")

    model_config = ConfigDict(
        populate_by_name=True
    )

    @field_validator("spec_file", "path")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate that required fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field is required and cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_openapi_base_url(self) -> "SpecConfig":
        """Validate that baseUrl is required when specType is 'openapi'."""
        if (
                self.spec_type == SpecType.OPENAPI
                and not self.base_url
                and not (self.auth and self.auth.azure)
        ):
            raise ValueError("baseUrl is required when specType is 'openapi'")
        return self

    def _validate_after_load(self) -> None:
        """
        Perform validation after spec file is loaded.
        This ensures spec_data is loaded and validates its contents.
        For MCP specs, validates against the MCP JSON schema.
        """
        if self.spec_data is None:
            raise ValueError(f"Spec file '{self.spec_file}' was loaded but contains no data")

        if not self.spec_data:
            raise ValueError(f"Spec file '{self.spec_file}' contains empty data")

        # Validate MCP spec files against the JSON schema
        if self.spec_type == SpecType.MCP:
            self._validate_mcp_schema()

    def _validate_mcp_schema(self) -> None:
        """
        Validate MCP spec_data against the MCP JSON schema.
        
        Raises:
            ValueError: If the spec_data doesn't conform to the MCP schema
            FileNotFoundError: If the schema file is not found
        """
        # Use the SCHEMA_DIR from environment configuration
        schema_path = os.path.join(SCHEMA_DIR, "mcp.schema.json")

        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"MCP schema file not found at: {schema_path}")

        # Load the MCP schema
        with open(schema_path, "r") as f:
            schema = json.load(f)

        # Validate spec_data against schema
        try:
            jsonschema.validate(instance=self.spec_data, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"MCP spec file '{self.spec_file}' does not conform to MCP schema: {e.message}"
            ) from e
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid MCP schema file: {e.message}") from e

    def _load_spec_file(self, config_dir: str) -> None:
        """
        Load the specification file as JSON and store it in spec_data.
        Also validates the loaded data and performs post-load validation.
        
        Args:
            config_dir: Directory containing the configuration files
            
        Raises:
            FileNotFoundError: If the spec file doesn't exist
            json.JSONDecodeError: If the spec file contains invalid JSON
            ValueError: If validation fails after loading
        """
        spec_path = os.path.join(config_dir, self.spec_file)

        if not os.path.exists(spec_path):
            raise FileNotFoundError(f"Spec file not found: {spec_path}")

        with open(spec_path, "r") as f:
            data = json.load(f)

        # Validate that loaded data is a dictionary (JSON object)
        if not isinstance(data, dict):
            raise ValueError(f"Spec file must contain a JSON object, got {type(data).__name__}")

        self.spec_data = data

        # Perform validation after loading the spec file
        self._validate_after_load()

    @staticmethod
    def load_from_file(config_file: str) -> list["SpecConfig"]:
        """
        Load all SpecConfig entries from a configuration file.
        
        This static method reads a JSON configuration file and creates SpecConfig
        instances for each entry. Spec files are always loaded and validated.
        
        Args:
            config_file: Path to the configuration JSON file
            
        Returns:
            List of SpecConfig instances with loaded spec_data
            
        Raises:
            FileNotFoundError: If the config file or spec files don't exist
            json.JSONDecodeError: If any JSON file is invalid
            ValueError: If validation fails for any config entry
            
        Example:
            configs = SpecConfig.load_from_file("data/config.json")
            for config in configs:
                print(f"{config.name}: {config.spec_type}")
                print(f"Spec data keys: {list(config.spec_data.keys())}")
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        # Load the configuration file
        with open(config_file, "r") as f:
            config_data = json.load(f)

        if not isinstance(config_data, list):
            raise ValueError("Configuration file must contain a JSON array")

        # Get the directory containing the config file (for resolving spec_file paths)
        config_dir = os.path.dirname(os.path.abspath(config_file))

        # Parse each entry into a SpecConfig instance
        spec_configs: list[SpecConfig] = []
        for entry in config_data:  # type: ignore[misc]
            if not isinstance(entry, dict):
                continue
            config = SpecConfig.model_validate(entry)

            # Always load the spec file and validate
            config._load_spec_file(config_dir)
            spec_configs.append(config)

        return spec_configs
