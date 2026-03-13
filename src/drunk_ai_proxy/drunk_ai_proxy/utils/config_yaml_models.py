"""Configuration models for YAML-backed proxy configuration."""

from __future__ import annotations

from enum import Enum
import json
import os
from collections.abc import Sequence
from typing import Any, cast

import yaml
from fastmcp.utilities import logging
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .env_resolver import resolve_env_vars, resolve_env_vars_in_dict

logger = logging.get_logger(__name__)


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
            if isinstance(attr, ConfigBaseModel):
                return attr.model_dump(exclude_none=True)
            if hasattr(attr, "model_dump"):
                return attr.model_dump(exclude_none=True)
            if hasattr(attr, "__dict__"):
                return cast(dict[str, Any], vars(attr))
            return cast(dict[str, Any], attr)
        except AttributeError:
            return None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict):
            return self.model_dump(exclude_none=True) == other
        return super().__eq__(other)

    def _resolve_env_vars(self) -> None:
        """Resolve environment variable references in all string attributes."""
        for field_name in self.__class__.model_fields.keys():
            current_value = getattr(self, field_name, None)
            if current_value is not None:
                resolved_value = resolve_env_vars(current_value)
                setattr(self, field_name, resolved_value)

        if hasattr(self, "__pydantic_extra__") and self.__pydantic_extra__:
            for extra_key, extra_value in self.__pydantic_extra__.items():
                if extra_value is not None:
                    resolved_value = resolve_env_vars(extra_value)
                    self.__pydantic_extra__[extra_key] = resolved_value

    @model_validator(mode="after")
    def after_model_validator(self) -> "ConfigBaseModel":
        """Resolve environment variable references in all string attributes."""
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
        """Resolve and validate the authentication provider name."""
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


class OnDemandRemoteResourceConfig(ConfigBaseModel):
    """Configuration for a single on-demand remote resource entry."""

    name: str = Field(description="Logical name for this remote resource entry.")
    url: str | None = Field(
        default=None,
        description="Single HTTPS URL for agents or prompts.",
    )
    urls: list[str] | None = Field(
        default=None,
        description="Multiple HTTPS URLs for skills (SKILL.md required in list).",
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional HTTP headers (e.g. Authorization) for private endpoints.",
    )

    @model_validator(mode="after")
    def validate_remote_resource(self) -> "OnDemandRemoteResourceConfig":
        """Validate URLs are HTTPS and that url/urls are not both set."""
        has_url = self.url is not None
        has_urls = self.urls is not None and len(self.urls) > 0

        if has_url and has_urls:
            raise ValueError(
                f"Remote resource '{self.name}': provide either 'url' or 'urls', not both."
            )
        if not has_url and not has_urls:
            raise ValueError(
                f"Remote resource '{self.name}': either 'url' or 'urls' must be provided."
            )

        all_urls: list[str] = []
        if self.url:
            all_urls.append(self.url)
        if self.urls:
            all_urls.extend(self.urls)

        for url in all_urls:
            if not url.startswith("https://"):
                raise ValueError(
                    f"Remote resource '{self.name}': all URLs must use HTTPS. Got: {url}"
                )

        return self


class McpResourceConfig(ConfigBaseModel):
    """MCP resource directories configuration."""

    dirs: list[str] = Field(
        default_factory=list,
        description="Directory list containing discoverable MCP resources.",
    )
    remote_resources: list[str | OnDemandRemoteResourceConfig] = Field(
        default_factory=list[str | OnDemandRemoteResourceConfig],
        description=(
            "On-demand remote HTTPS resources fetched on first access and "
            "cached by TTL. Shorthand string entries are auto-normalized."
        ),
    )

    @model_validator(mode="after")
    def normalize_remote_resources(self) -> "McpResourceConfig":
        """Normalize shorthand string entries into OnDemandRemoteResourceConfig."""
        from drunk_ai_proxy.utils.config_yaml_uri import build_name_from_url  # noqa: PLC0415

        normalized: list[str | OnDemandRemoteResourceConfig] = []
        for entry in self.remote_resources:
            if isinstance(entry, str):
                if not entry.startswith("https://"):
                    raise ValueError(
                        f"Shorthand remote_resource URL must use HTTPS. Got: {entry}"
                    )
                name = build_name_from_url(entry)
                logger.warning(
                    "Shorthand remote_resource string '%s' detected. "
                    "Recommend using explicit object form with 'name' and 'urls'.",
                    entry,
                )
                if entry.endswith("SKILL.md"):
                    normalized.append(OnDemandRemoteResourceConfig(name=name, urls=[entry]))
                else:
                    normalized.append(OnDemandRemoteResourceConfig(name=name, url=entry))
                continue
            normalized.append(entry)

        self.remote_resources = normalized
        return self


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
    codemode_enabled: bool = Field(
        default=True,
        description="Enable or disable FastMCP Code Mode for this MCP route.",
    )
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
        """Reject deprecated MCP resource fields."""
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
        """Validate directory list values."""
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

    def get_skill_remote_resources(self) -> list[OnDemandRemoteResourceConfig]:
        """Return on-demand remote skill resource configs."""
        if self.skills is None:
            return []
        return [
            resource
            for resource in self.skills.remote_resources
            if isinstance(resource, OnDemandRemoteResourceConfig)
        ]

    def get_prompt_remote_resources(self) -> list[OnDemandRemoteResourceConfig]:
        """Return on-demand remote prompt resource configs."""
        if self.prompts is None:
            return []
        return [
            resource
            for resource in self.prompts.remote_resources
            if isinstance(resource, OnDemandRemoteResourceConfig)
        ]

    def get_agent_remote_resources(self) -> list[OnDemandRemoteResourceConfig]:
        """Return on-demand remote agent resource configs."""
        if self.agents is None:
            return []
        return [
            resource
            for resource in self.agents.remote_resources
            if isinstance(resource, OnDemandRemoteResourceConfig)
        ]

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
        from drunk_ai_proxy.utils import config_yaml as config_yaml_module  # noqa: PLC0415

        file = f"{config_yaml_module.CONFIG_DIR}/{spec_file}"
        if not os.path.exists(file):
            raise FileNotFoundError(f"Spec file not found: {spec_file}")

        with open(file, "r") as stream:
            if file.endswith(".json"):
                data = json.load(stream)
            elif file.endswith((".yaml", ".yml")):
                data = yaml.safe_load(stream)
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
        else:
            skill_dirs = self.get_skill_dirs()
            prompt_dirs = self.get_prompt_dirs()
            agent_dirs = self.get_agent_dirs()

            self._validate_dir_list(skill_dirs, "skills.dirs")
            self._validate_dir_list(prompt_dirs, "prompts")
            self._validate_dir_list(agent_dirs, "agents")

            has_remote_resources = (
                bool(self.get_skill_remote_resources())
                or bool(self.get_prompt_remote_resources())
                or bool(self.get_agent_remote_resources())
            )

            if (
                not self.mcp_servers
                and not prompt_dirs
                and not agent_dirs
                and not skill_dirs
                and not has_remote_resources
            ):
                raise ValueError(
                    "For MCP spec type, mcp_servers, prompts, agents, skills.dirs, "
                    "or remote_resources must be provided."
                )

    def load_spec_data(self) -> None:
        """Load specification data from spec_file if provided."""
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

    @model_validator(mode="after")
    def after_model_validator(self) -> "McpConfig":
        """After model validation, load spec data if spec_file is provided."""
        self._validate_fields()
        self._resolve_env_vars()
        self.load_spec_data()
        return self


class RemoteResourceConfig(ConfigBaseModel):
    """Configuration for a remote resource bundle."""

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


__all__ = [
    "AuthType",
    "SpecType",
    "ConfigBaseModel",
    "AuthConfig",
    "BearerAuthConfig",
    "JwtAuthConfig",
    "McpConfig",
    "McpResourceConfig",
    "OnDemandRemoteResourceConfig",
    "OpenApiFilters",
    "LlmConfig",
    "RemoteResourceConfig",
]
