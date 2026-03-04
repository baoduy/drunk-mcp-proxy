"""
ConfigYaml data models for YAML-based proxy configuration.

This module provides Pydantic models for loading and validating YAML
configuration files that define authentication, LLM, and MCP specifications.
"""

from __future__ import annotations

from enum import Enum
import json
import os
from typing import Any, Optional

import jsonschema
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tools.env import CONFIG_DIR, SCHEMA_DIR

from .env_resolver import resolve_env_var


class AuthType(str, Enum):
    """Enumeration of supported authentication provider types."""
    BASIC = "basic"
    AUTH0 = "auth0"
    AWS = "aws"
    AZURE = "azure"
    DISCORD = "discord"
    GITHUB = "github"
    GOOGLE = "google"
    IN_MEMORY = "in_memory"
    INTROSPECTION = "introspection"
    JWT = "jwt"
    OCI = "oci"
    SUPABASE = "supabase"


class SpecType(str, Enum):
    """Enumeration of supported specification types."""
    MCP = "mcp"
    OPENAPI = "openapi"


class ConfigBaseModel(BaseModel):
    """Base model with common validation logic for configuration models."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def __getitem__(self, key: AuthType) -> dict[str, Any] | None:
        """Access configuration fields using dict-like indexing."""
        try:
            attr = getattr(self, key)
            if isinstance(attr, dict):
                return attr
            elif isinstance(attr, ConfigBaseModel):
                # Exclude None values and use field aliases
                return attr.model_dump(exclude_none=True)
            elif hasattr(attr, "model_dump"):
                return attr.model_dump(exclude_none=True)
            elif hasattr(attr, "__dict__"):
                return vars(attr)  # Convert any object to dict
            return None
        except AttributeError:
            return None

    def _resolve_env_vars(self) -> None:
        """Resolve environment variable references in all string attributes."""
        for field_name in self.__class__.model_fields.keys():
            current_value = getattr(self, field_name, None)
            if current_value is not None and isinstance(current_value, str):
                resolved_value = resolve_env_var(current_value)
                setattr(self, field_name, resolved_value)

    @model_validator(mode="after")
    def after_model_validator(self) -> "ConfigBaseModel":
        """Resolve environment variable references in all string attributes.

        This method iterates through all model fields and resolves any
        environment variable references (e.g., $VAR or ${VAR}) found in
        string values.

        Returns:
            Self with resolved environment variables.
        """
        self._resolve_env_vars()
        return self


class BearerAuthConfig(ConfigBaseModel):
    """Bearer token authentication configuration."""

    base_url: Optional[str] = Field(default=None)
    token: Optional[str] = Field(default=None)


class JwtAuthConfig(ConfigBaseModel):
    """JWT authentication configuration."""

    base_url: Optional[str] = Field(default=None)
    jwks_uri: Optional[str] = Field(default=None)
    issuer: Optional[str] = Field(default=None)
    audience: Optional[str] = Field(default=None)


class AuthConfig(ConfigBaseModel):
    """Authentication configuration section."""
    default_provider: Optional[AuthType] = Field(default=None, alias="defaultProvider")
    basic: Optional[BearerAuthConfig] = Field(default=None)
    jwt: Optional[JwtAuthConfig] = Field(default=None)


class LlmConfig(ConfigBaseModel):
    """LLM provider configuration."""

    enabled: bool = Field(default=True)
    websocket: bool = Field(default=False)
    provider: str = Field(description="LLM provider name")
    base_url: str = Field(description="Base URL for the LLM provider")
    api_key: Optional[str] = Field(default=None)


class McpFilters(ConfigBaseModel):
    """Filters for MCP specifications."""

    methods: Optional[list[str]] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)


class McpAuthConfig(ConfigBaseModel):
    """Authentication configuration for MCP."""
    pass_through: bool = Field(default=False)
    auth_provider: Optional[AuthType] = Field(default=None, alias="authProvider")


class McpConfig(ConfigBaseModel):
    """MCP server configuration."""
    enabled: bool = Field(default=True)
    path: str = Field(description="Base path for the MCP proxy")
    spec_file: Optional[str] = Field(default=None)
    spec_type: SpecType = Field(default=SpecType.MCP, description="Type of specification ('mcp' or 'openapi')")
    base_url: Optional[str] = Field(default=None)
    skill_dir: Optional[str] = Field(default=None)
    filters: Optional[McpFilters] = Field(default=None)
    auth: Optional[McpAuthConfig] = Field(default=None)
    mcp_servers: Optional[dict[str, Any]] = Field(default=None, alias="mcpServers")
    tags: Optional[set[str]] = Field(default=None)
    spec_data: Optional[dict[str, Any]] = Field(default=None, exclude=True)

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

    def _validate_fields(self) -> None:
        """Validate that required fields are present based on spec_type."""
        if self.spec_type == SpecType.OPENAPI:
            if not self.base_url:
                raise ValueError("base_url is required for OpenAPI spec type")
            if not self.spec_file:
                raise ValueError("spec_file is required for OpenAPI spec type")
        else:  # SpecType.MCP
            if not self.spec_file and not self.mcp_servers:
                raise ValueError("For MCP spec type, either spec_file or mcp_servers must be provided.")
        
    def load_spec_data(self):
        """
        Load specification data from spec_file if provided.
        
        This method checks if spec_file is set and loads the configuration
        from that file. Supports both JSON and YAML formats. The loaded
        data is stored in the spec_data field.
        
        Returns:
            The loaded specification data as a dictionary, or None if no
            spec_file is provided.
            
        Raises:
            FileNotFoundError: If the spec file doesn't exist
            ValueError: If the file format is not supported or parsing fails
            
        Example:
            mcp_config = McpConfig(path="/api/mcp", spec_file="data/mcp/servers.json")
            spec_data = mcp_config.load_spec_data()
            print(f"Loaded {len(spec_data)} server configurations")
        """
        if not self.spec_file:
            self.spec_data = {"mcpServers": self.mcp_servers} if self.mcp_servers else None
            return
            
        file = f"{CONFIG_DIR}/{self.spec_file}"
        if not os.path.exists(file):
            raise FileNotFoundError(f"Spec file not found: {self.spec_file}")
        
        with open(file, "r") as f:
            if file.endswith(".json"):
                import json
                data = json.load(f)
            elif file.endswith((".yaml", ".yml")):
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported spec file format: {file}. Supported formats: .json, .yaml, .yml")
        
        # Store the loaded data first, then validate
        self.spec_data = data
        if self.spec_type == SpecType.MCP:
            # Validate data against schema/mcp.schema.json
            self._validate_mcp_schema()
        
    @model_validator(mode="after")
    def after_model_validator(self) -> McpConfig:
        """After model validation, load spec data if spec_file is provided."""
        self._validate_fields()
        self._resolve_env_vars()
        self.load_spec_data()
        return self


class ConfigYaml(ConfigBaseModel):
    """
    Main configuration model for YAML-based configuration.

    Attributes:
        auth: Authentication configuration
        llm: List of LLM provider configurations
        mcp: List of MCP server configurations
    """
    auth: Optional[AuthConfig] = Field(default=None)
    llm: Optional[list[LlmConfig]] = Field(default=None)
    mcp: Optional[list[McpConfig]] = Field(default=None)

    @staticmethod
    def load_from_file(config_file: str) -> ConfigYaml:
        """
        Load ConfigYaml from a YAML configuration file.

        Args:
            config_file: Path to the YAML configuration file

        Returns:
            ConfigYaml instance with loaded configuration

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML file is invalid
            ValueError: If configuration validation fails

        Example:
            config = ConfigYaml.load_from_file("data/config.yaml")
            print(f"Auth provider: {config.auth.default_provider}")
            for llm in config.llm:
                print(f"LLM: {llm.provider}")
            for mcp in config.mcp:
                print(f"MCP path: {mcp.path}")
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        # Load the YAML configuration file
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)

        if config_data is None:
            raise ValueError("Configuration file is empty")

        if not isinstance(config_data, dict):
            raise ValueError("Configuration file must contain a YAML mapping (dict)")

        # Validate and parse into ConfigYaml instance
        config = ConfigYaml.model_validate(config_data)

        return config
