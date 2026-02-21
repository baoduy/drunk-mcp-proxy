"""
LlmConfig data models for LLM provider configuration.

This module provides Pydantic models for loading and validating LLM
configuration files (data/llm.json).

The configuration file is a JSON array where each entry defines an LLM provider:
- provider: Provider identifier (e.g., 'openrouter')
- base_url: Provider base URL
- api_key: API key (supports $VAR_NAME or ${VAR_NAME} environment variables)
- Additional provider-specific fields are allowed
"""

import json
import os
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .env_resolver import resolve_env_var


class LlmProviderConfig(BaseModel):
    """Configuration model for a single LLM provider."""

    enabled: bool = Field(default=True, description="Whether this provider is enabled")
    provider: str = Field(description="LLM provider name")
    base_url: str = Field(description="LLM provider base URL")
    api_key: str = Field(description="LLM provider API key")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def resolve_environment_variables(self) -> "LlmProviderConfig":
        """Resolve environment variables in provider configuration."""
        resolved = self._resolve_env_in_dict(self.model_dump())
        for key, value in resolved.items():
            setattr(self, key, value)
        return self

    @staticmethod
    def _resolve_env_in_dict(data: Any) -> Any:
        """
        Recursively resolve environment variables in dictionary, list, or string values.

        Supports $VAR_NAME and ${VAR_NAME} syntax in strings.
        """
        if isinstance(data, dict):
            typed_data = cast(dict[str, Any], data)
            return {k: LlmProviderConfig._resolve_env_in_dict(v) for k, v in typed_data.items()}
        if isinstance(data, list):
            typed_data = cast(list[Any], data)
            return [LlmProviderConfig._resolve_env_in_dict(item) for item in typed_data]
        if isinstance(data, str):
            return resolve_env_var(data)
        return data


class LlmConfig(BaseModel):
    """Root LLM configuration model."""

    providers: list[Any] = Field(
        default_factory=list,
        description="List of LLM provider configurations",
    )

    @staticmethod
    def load_from_file(config_file: str) -> "LlmConfig":
        """
        Load LLM provider configuration from a JSON file.

        Args:
            config_file: Path to the LLM configuration JSON file

        Returns:
            LlmConfig instance containing provider configurations

        Raises:
            FileNotFoundError: If the config file doesn't exist
            json.JSONDecodeError: If the config file contains invalid JSON
            ValueError: If the JSON root is not an array
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"LLM configuration file not found: {config_file}")

        with open(config_file, "r") as f:
            loaded_data: Any = json.load(f)

        if not isinstance(loaded_data, list):
            raise ValueError("LLM configuration file must contain a JSON array")

        typed_data = cast(list[dict[str, Any]], loaded_data)
        providers = [LlmProviderConfig.model_validate(entry) for entry in typed_data]

        return LlmConfig.model_validate({"providers": providers})
