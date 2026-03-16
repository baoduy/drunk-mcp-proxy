"""
Environment variable resolver for configuration values.

This module provides utilities to resolve environment variable references
in configuration values. Environment variables are referenced using the
syntax: $VARIABLE_NAME or ${VARIABLE_NAME}

Example:
    "clientId": "$AZURE_CLIENT_ID" -> resolves to the value of AZURE_CLIENT_ID env var
    "tokenUrl": "https://login.microsoftonline.com/${TENANT_ID}/token" -> interpolates TENANT_ID
"""

from __future__ import annotations

import os
import re

EnvResolvable = str | dict[str, object] | list[object]


class EnvResolver:
    """Class-first environment variable resolution helpers."""

    _PATTERN = r"(?:\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*))"

    @staticmethod
    def resolve_env_var(value: object) -> object:
        """Resolve environment variable references in a string."""
        if not isinstance(value, str):
            return value

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1) or match.group(2)
            env_value = os.environ.get(var_name)

            if env_value is None:
                raise ValueError(
                    f"Environment variable '{var_name}' referenced in configuration is not set. "
                    f"Please set: export {var_name}=<value>"
                )

            return env_value

        return re.sub(EnvResolver._PATTERN, replace_var, value)

    @staticmethod
    def resolve_env_vars_in_dict(data: dict[str, object]) -> dict[str, object]:
        """Recursively resolve environment variable references in a dictionary."""
        resolved: dict[str, object] = {}

        for key, value in data.items():
            if isinstance(value, str):
                resolved[key] = EnvResolver.resolve_env_var(value)
            elif isinstance(value, dict):
                resolved[key] = EnvResolver.resolve_env_vars_in_dict(value)
            elif isinstance(value, list):
                resolved[key] = EnvResolver.resolve_env_vars_in_list(value)
            else:
                resolved[key] = value

        return resolved

    @staticmethod
    def resolve_env_vars_in_list(data: list[object]) -> list[object]:
        """Recursively resolve environment variable references in a list."""
        resolved: list[object] = []

        for item in data:
            if isinstance(item, str):
                resolved.append(EnvResolver.resolve_env_var(item))
            elif isinstance(item, dict):
                resolved.append(EnvResolver.resolve_env_vars_in_dict(item))
            elif isinstance(item, list):
                resolved.append(EnvResolver.resolve_env_vars_in_list(item))
            else:
                resolved.append(item)

        return resolved

    @staticmethod
    def resolve_env_vars(
        data: EnvResolvable,
    ) -> EnvResolvable:
        """Resolve environment variable references in any data structure."""
        if isinstance(data, str):
            return EnvResolver.resolve_env_var(data)
        if isinstance(data, dict):
            return EnvResolver.resolve_env_vars_in_dict(data)
        if isinstance(data, list):
            return EnvResolver.resolve_env_vars_in_list(data)
        return data
