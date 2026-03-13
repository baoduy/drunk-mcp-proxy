"""YAML configuration loader for proxy configuration."""

from __future__ import annotations

import os

import yaml
from pydantic import Field

from .env import CONFIG_DIR as ENV_CONFIG_DIR

from .config_yaml_models import (
    AuthConfig,
    McpAuthConfig,
    AuthType,
    BearerAuthConfig,
    ConfigBaseModel,
    JwtAuthConfig,
    LlmConfig,
    McpConfig,
    McpResourceConfig,
    McpServerConfig,
    OnDemandRemoteResourceConfig,
    OpenApiConfig,
    OpenApiFilters,
    RemoteResourceConfig,
    SpecType,
)

CONFIG_DIR = ENV_CONFIG_DIR


class ConfigYaml(ConfigBaseModel):
    """Main configuration model for YAML-based configuration."""

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
    def load_from_file(config_file: str) -> "ConfigYaml":
        """Load ConfigYaml from a YAML configuration file."""
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_file, "r") as stream:
            config_data = yaml.safe_load(stream)

        if config_data is None:
            raise ValueError("Configuration file is empty")

        if not isinstance(config_data, dict):
            raise ValueError("Configuration file must contain a YAML mapping (dict)")

        return ConfigYaml.model_validate(config_data)


__all__ = [
    "AuthType",
    "SpecType",
    "ConfigBaseModel",
    "AuthConfig",
    "McpAuthConfig",
    "BearerAuthConfig",
    "JwtAuthConfig",
    "McpConfig",
    "McpResourceConfig",
    "McpServerConfig",
    "OnDemandRemoteResourceConfig",
    "OpenApiConfig",
    "OpenApiFilters",
    "LlmConfig",
    "ConfigYaml",
    "RemoteResourceConfig",
]
