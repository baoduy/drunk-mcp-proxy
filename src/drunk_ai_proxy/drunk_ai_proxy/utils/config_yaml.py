"""
ConfigYaml data models for YAML-based proxy configuration.

This module provides Pydantic models for loading and validating YAML
configuration files that define authentication, LLM, and MCP specifications.
"""

from __future__ import annotations

from enum import Enum
import json
import os
from collections.abc import Sequence
from typing import Any, cast

import jsonschema
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from drunk_ai_proxy.utils.env import CONFIG_DIR, SCHEMA_DIR

from .env_resolver import resolve_env_vars, resolve_env_vars_in_dict


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

    def __getitem__(self, key: str | AuthType) -> dict[str, Any] | None:
        """Access configuration fields using dict-like indexing."""
        try:
            key_value = key.value if isinstance(key, Enum) else key
            attr = getattr(self, key_value)
            if isinstance(attr, dict):
                return cast(dict[str, Any], attr)
            elif isinstance(attr, ConfigBaseModel):
                # Exclude None values and use field aliases
                return attr.model_dump(exclude_none=True)
            elif hasattr(attr, "model_dump"):
                return attr.model_dump(exclude_none=True)
            elif hasattr(attr, "__dict__"):
                return cast(dict[str, Any], vars(attr))  # Convert any object to dict
            return cast(dict[str, Any], attr)
        except AttributeError:
            return None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict):
            return self.model_dump(exclude_none=True) == other
        return super().__eq__(other)

    def _resolve_env_vars(self) -> None:
        """Resolve environment variable references in all string attributes."""
        # Resolve explicitly defined fields
        for field_name in self.__class__.model_fields.keys():
            current_value = getattr(self, field_name, None)
            if current_value is not None:
                resolved_value = resolve_env_vars(current_value)
                setattr(self, field_name, resolved_value)
        
        # Resolve extra fields (for models with extra="allow")
        if hasattr(self, "__pydantic_extra__") and self.__pydantic_extra__:
            for extra_key, extra_value in self.__pydantic_extra__.items():
                if extra_value is not None:
                    resolved_value = resolve_env_vars(extra_value)
                    self.__pydantic_extra__[extra_key] = resolved_value

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

    base_url: str | None = Field(
        default=None,
        description="Optional base URL for token introspection or auth service.",
    )
    token: str | None = Field(
        default=None,
        description="Bearer token value used for upstream authentication.",
    )


class JwtAuthConfig(ConfigBaseModel):
    """JWT authentication configuration."""

    base_url: str | None = Field(
        default=None,
        description="Optional base URL for JWT auth metadata endpoints.",
    )
    jwks_uri: str | None = Field(
        default=None,
        description="JWKS endpoint URI used to validate JWT signatures.",
    )
    issuer: str | None = Field(
        default=None,
        description="Expected JWT issuer claim value.",
    )
    audience: str | None = Field(
        default=None,
        description="Expected JWT audience claim value.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_yaml_scalars(cls, data: object) -> object:
        """Normalize single-key YAML mappings into scalar strings."""
        if not isinstance(data, dict):
            return data

        raw_data = cast(dict[str, object], data)
        normalized: dict[str, object] = {}
        for key, value in raw_data.items():
            if isinstance(value, dict):
                inner_map = cast(dict[str, object], value)
                if len(inner_map) == 1:
                    [(inner_key, inner_value)] = inner_map.items()
                    if inner_value is None:
                        normalized[key] = inner_key
                        continue
            normalized[key] = value

        return normalized


class AuthConfig(ConfigBaseModel):
    """Authentication configuration section."""
    default_provider: AuthType | None = Field(
        default=None,
        description="Default authentication provider used when not explicitly specified.",
    )
    basic: BearerAuthConfig | None = Field(
        default=None,
        description="Bearer/basic authentication provider configuration.",
    )
    jwt: JwtAuthConfig | None = Field(
        default=None,
        description="JWT authentication provider configuration.",
    )

    def _available_provider_names(self) -> list[str]:
        auth_data = self.model_dump(exclude_none=True, by_alias=True)
        auth_data.pop("default_provider", None)
        return list(auth_data.keys())

    def normalize_provider_name(
        self,
        provider_name: AuthType | str | None = None,
    ) -> AuthType:
        """Resolve and validate the authentication provider name.

        Args:
            provider_name: Optional provider name or enum. Falls back to default.

        Returns:
            Normalized provider enum.

        Raises:
            ValueError: If no provider is configured or the name is unsupported.
        """
        name = provider_name or self.default_provider
        if name is None:
            raise ValueError(
                "No provider name specified and no default provider configured"
            )

        if isinstance(name, AuthType):
            return name

        try:
            return AuthType(name)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported authentication provider type: {name} in {self._available_provider_names()}"
            ) from exc


class LlmConfig(ConfigBaseModel):
    """LLM provider configuration."""

    enabled: bool = Field(default=True, description="Enable or disable this LLM provider.")
    websocket: bool = Field(
        default=False,
        description="Whether this LLM provider supports websocket transport.",
    )
    provider: str = Field(description="LLM provider name")
    base_url: str = Field(description="Base URL for the LLM provider")
    api_key: str | None = Field(
        default=None,
        description="API key for authenticating requests to the LLM provider.",
    )


class OpenApiFilters(ConfigBaseModel):
    """Filters for OpenAPI operation exposure."""

    methods: list[str] | None = Field(
        default=None,
        description="Allowed HTTP methods to include from the OpenAPI spec.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Allowed OpenAPI tags to include from the OpenAPI spec.",
    )


class McpAuthConfig(ConfigBaseModel):
    """Authentication configuration for MCP."""
    pass_through: bool = Field(
        default=False,
        description="Forward incoming client auth context to upstream MCP providers.",
    )
    auth_provider: AuthType | None = Field(
        default=None,
        description="Override authentication provider for this MCP entry.",
    )

class McpServerConfig(ConfigBaseModel):
    """Individual MCP server configuration."""
    enabled: bool = Field(default=True, description="Enable or disable this MCP server entry.")
    transport: str | None = Field(
        default="stdio",
        description="Transport method for MCP server (stdio, http).",
    )
    url: str | None = Field(
        default=None,
        description="URL for HTTP transport (required when transport is http).",
    )
    command: str | None = Field(
        default=None,
        description="Executable command for stdio transport (required for stdio).",
    )
    args: list[str] | None = Field(
        default=None,
        description="Optional arguments passed to the stdio command.",
    )
    env: dict[str, Any] | None = Field(
        default=None,
        description="Optional environment variables for the MCP server process.",
    )


class McpResourceConfig(ConfigBaseModel):
    """MCP resource directories configuration."""

    dirs: list[str] = Field(
        default_factory=list,
        description="Directory list containing discoverable MCP resources.",
    )


class OpenApiConfig(ConfigBaseModel):
    """OpenAPI-specific MCP configuration."""

    spec_file: str | None = Field(
        default=None,
        description="Relative path to the OpenAPI specification file.",
    )
    base_url: str | None = Field(
        default=None,
        description="Upstream API base URL used to execute mapped operations.",
    )
    filters: OpenApiFilters | None = Field(
        default=None,
        description="OpenAPI operation filters applied during route mapping.",
    )
    spec_data: dict[str, Any] | None = Field(
        default=None,
        exclude=True,
        description="Loaded OpenAPI specification document (internal runtime cache).",
    )

class McpConfig(ConfigBaseModel):
    """MCP server configuration."""
    enabled: bool = Field(default=True, description="Enable or disable this MCP route.")
    path: str = Field(description="Base path for the MCP proxy")
    spec_type: SpecType = Field(
        default=SpecType.MCP,
        description="Specification type: 'mcp' for MCP servers or 'openapi' for OpenAPI mapping.",
    )
    open_api: OpenApiConfig | None = Field(
        default=None,
        alias="openApi",
        description="OpenAPI-specific configuration when spec_type is openapi.",
    )
    skills: McpResourceConfig | None = Field(
        default=None,
        description="Skill resource directory configuration for this MCP route.",
    )
    prompts: McpResourceConfig | None = Field(
        default=None,
        description="Directories containing markdown prompt templates",
    )
    agents: McpResourceConfig | None = Field(
        default=None,
        description="Directories containing markdown agent definitions",
    )
    auth: McpAuthConfig | None = Field(
        default=None,
        description="Authentication behavior overrides for this MCP route.",
    )
    mcp_servers: dict[str, McpServerConfig] | None = Field(
        default=None,
        alias="mcpServers",
        description="Inline MCP server map used when spec_type is mcp.",
    )
    tags: set[str] | None = Field(
        default=None,
        description="Optional tags associated with this MCP route configuration.",
    )
    spec_data: dict[str, Any] | None = Field(
        default=None,
        exclude=True,
        description="Loaded MCP specification data (internal runtime cache).",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_no_legacy_resource_fields(cls, data: object) -> object:
        """Reject deprecated MCP resource fields.

        Args:
            data: Raw model input.

        Returns:
            Raw model input when valid.

        Raises:
            ValueError: If legacy keys are present.
        """
        if not isinstance(data, dict):
            return data

        parsed_data = cast(dict[str, object], data).copy()

        legacy_keys = ["skill_dir", "prompt_dir", "agents_dir"]
        used_legacy_keys = [key for key in legacy_keys if key in parsed_data]
        if used_legacy_keys:
            raise ValueError(
                "Legacy MCP resource keys are no longer supported: "
                f"{', '.join(used_legacy_keys)}. "
                "Use 'skills.dirs', 'prompts', and 'agents'."
            )

        spec_type = parsed_data.get("spec_type")
        if spec_type in (SpecType.OPENAPI, SpecType.OPENAPI.value, "openapi"):
            open_api_data = parsed_data.get("open_api") or parsed_data.get("openApi")
            if open_api_data is None:
                legacy_openapi: dict[str, object] = {}
                for key in ("spec_file", "base_url", "filters"):
                    value = parsed_data.get(key)
                    if value is not None:
                        legacy_openapi[key] = value
                if legacy_openapi:
                    parsed_data["open_api"] = legacy_openapi

            for key in ("spec_file", "base_url", "filters"):
                parsed_data.pop(key, None)

        return parsed_data

    @staticmethod
    def _validate_dir_list(values: Sequence[str], field_name: str) -> None:
        """Validate directory list values.

        Args:
            values: Directory values to validate.
            field_name: Field name for error reporting.

        Raises:
            ValueError: If values include empty entries.
        """
        for value in values:
            if not value or not value.strip():
                raise ValueError(f"{field_name} cannot contain empty directory values")

    def get_skill_dirs(self) -> list[str]:
        """Return configured skill directories."""
        if self.skills is None:
            return []
        return self.skills.dirs

    def get_prompt_dirs(self) -> list[str]:
        """Return configured prompt directories."""
        if self.prompts is None:
            return []
        return self.prompts.dirs

    def get_agent_dirs(self) -> list[str]:
        """Return configured agent directories."""
        if self.agents is None:
            return []
        return self.agents.dirs

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
            raise ValueError(f"MCP specification does not conform to MCP schema: {e.message}") from e
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid MCP schema file: {e.message}") from e

    @staticmethod
    def _validate_openapi_spec(spec_data: dict[str, Any]) -> None:
        """Validate basic OpenAPI document requirements."""
        if "openapi" not in spec_data:
            raise ValueError("OpenAPI spec must include 'openapi' field")
        if "info" not in spec_data:
            raise ValueError("OpenAPI spec must include 'info' field")
        if not any(key in spec_data for key in ("paths", "components", "webhooks")):
            raise ValueError(
                "OpenAPI spec must include at least one of: 'paths', 'components', or 'webhooks'"
            )

    @staticmethod
    def _load_spec_file_data(spec_file: str) -> dict[str, Any]:
        """Load specification mapping data from JSON/YAML file."""
        file = f"{CONFIG_DIR}/{spec_file}"
        if not os.path.exists(file):
            raise FileNotFoundError(f"Spec file not found: {spec_file}")

        with open(file, "r") as f:
            if file.endswith(".json"):
                data = json.load(f)
            elif file.endswith((".yaml", ".yml")):
                data = yaml.safe_load(f)
            else:
                raise ValueError(
                    f"Unsupported spec file format: {file}. Supported formats: .json, .yaml, .yml"
                )

        if not isinstance(data, dict):
            raise ValueError("Spec file must contain a mapping (dict)")

        return cast(dict[str, Any], data)

    def get_openapi_filters(self) -> OpenApiFilters | None:
        """Return effective OpenAPI filters."""
        if self.open_api is None:
            return None
        return self.open_api.filters

    def get_openapi_base_url(self) -> str | None:
        """Return effective OpenAPI base URL."""
        if self.open_api is None:
            return None
        return self.open_api.base_url

    def get_openapi_spec_data(self) -> dict[str, Any] | None:
        """Return effective OpenAPI specification data."""
        if self.open_api is None:
            return None
        return self.open_api.spec_data

    def _validate_fields(self) -> None:
        """Validate that required fields are present based on spec_type."""
        if self.spec_type == SpecType.OPENAPI:
            if self.open_api is None:
                raise ValueError("open_api is required for OpenAPI spec type")
            if not self.get_openapi_base_url():
                raise ValueError("open_api.base_url is required for OpenAPI spec type")
            if not self.open_api.spec_file:
                raise ValueError("open_api.spec_file is required for OpenAPI spec type")
        else:  # SpecType.MCP
            skill_dirs = self.get_skill_dirs()
            prompt_dirs = self.get_prompt_dirs()
            agent_dirs = self.get_agent_dirs()

            self._validate_dir_list(skill_dirs, "skills.dirs")
            self._validate_dir_list(prompt_dirs, "prompts")
            self._validate_dir_list(agent_dirs, "agents")

            if (
                not self.mcp_servers
                and not prompt_dirs
                and not agent_dirs
                and not skill_dirs
            ):
                raise ValueError(
                    "For MCP spec type, mcp_servers, prompts, agents, or skills.dirs must be provided."
                )
        
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
        if self.spec_type == SpecType.OPENAPI:
            if self.open_api is None:
                return

            if not self.open_api.spec_file:
                self.open_api.spec_data = None
                return

            data = self._load_spec_file_data(self.open_api.spec_file)
            resolved_data = resolve_env_vars_in_dict(data)
            self.open_api.spec_data = resolved_data
            self._validate_openapi_spec(resolved_data)
            return

        self.spec_data = (
            {
                "mcpServers": {
                    key: value.model_dump(exclude_none=True)
                    for key, value in self.mcp_servers.items()
                }
            }
            if self.mcp_servers
            else None
        )

        if self.spec_data is not None:
            self._validate_mcp_schema()
        
    @model_validator(mode="after")
    def after_model_validator(self) -> McpConfig:
        """After model validation, load spec data if spec_file is provided."""
        self._validate_fields()
        self._resolve_env_vars()
        self.load_spec_data()
        return self


class RemoteResourceConfig(ConfigBaseModel):
    """Configuration for a remote resource bundle.
    
    Defines a named set of HTTPS URLs to download into a local directory
    at startup without blocking the server.
    """
    
    name: str = Field(description="Logical name for the resource bundle (used in logs)")
    enabled: bool = Field(
        default=True,
        description="Enable or disable sync for this specific resource bundle",
    )
    to_dir: str = Field(
        description="Destination directory relative to data/ (e.g. 'prompts/dotnet')"
    )
    paths: list[str] = Field(
        description="List of HTTPS URLs to download to the destination directory"
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional HTTP headers for private URLs (reserved for future implementation)",
    )

class ConfigYaml(ConfigBaseModel):
    """
    Main configuration model for YAML-based configuration.

    Attributes:
        auth: Authentication configuration
        llm: List of LLM provider configurations
        mcp: List of MCP server configurations
        remote_resources: List of remote resource bundles to sync at startup
    """
    auth: AuthConfig | None = Field(
        default=None,
        description="Authentication providers and defaults.",
    )
    llm: list[LlmConfig] | None = Field(
        default=None,
        description="Configured LLM provider definitions.",
    )
    mcp: list[McpConfig] | None = Field(
        default=None,
        description="Configured MCP route and provider entries.",
    )
    remote_resources: list[RemoteResourceConfig] | None = Field(
        default=None,
        description="Remote resource bundles to synchronize at startup.",
    )

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
