"""
Environment variable resolver for configuration values.

This module provides utilities to resolve environment variable references
in configuration values. Environment variables are referenced using the
syntax: $VARIABLE_NAME or ${VARIABLE_NAME}

Example:
    "clientId": "$AZURE_CLIENT_ID" -> resolves to the value of AZURE_CLIENT_ID env var
    "tokenUrl": "https://login.microsoftonline.com/${TENANT_ID}/token" -> interpolates TENANT_ID
"""

import os
import re
from typing import Any, Dict, List, Union


def resolve_env_var(value: str) -> str:
    """
    Resolve environment variable references in a string.

    Supports two formats:
    - $VAR_NAME: Replaces with environment variable value
    - ${VAR_NAME}: Alternative syntax with braces

    Args:
        value: String potentially containing environment variable references

    Returns:
        String with all environment variable references resolved

    Raises:
        ValueError: If a referenced environment variable is not set

    Example:
        >>> resolve_env_var("$AZURE_CLIENT_ID")  # Returns value of AZURE_CLIENT_ID
        >>> resolve_env_var("https://login.microsoftonline.com/${TENANT_ID}/token")
    """
    if not isinstance(value, str):
        return value

    # Pattern to match both $VAR_NAME and ${VAR_NAME}
    pattern = r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?'

    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)

        if env_value is None:
            raise ValueError(
                f"Environment variable '{var_name}' referenced in configuration is not set. "
                f"Please set: export {var_name}=<value>"
            )

        return env_value

    return re.sub(pattern, replace_var, value)


def resolve_env_vars_in_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively resolve environment variable references in a dictionary.

    Args:
        data: Dictionary potentially containing environment variable references

    Returns:
        Dictionary with all environment variable references resolved

    Raises:
        ValueError: If a referenced environment variable is not set
    """
    resolved = {}

    for key, value in data.items():
        if isinstance(value, str):
            # Resolve string values
            resolved[key] = resolve_env_var(value)
        elif isinstance(value, dict):
            # Recursively resolve nested dictionaries
            resolved[key] = resolve_env_vars_in_dict(value)
        elif isinstance(value, list):
            # Recursively resolve list items
            resolved[key] = resolve_env_vars_in_list(value)
        else:
            # Keep other types as-is (numbers, booleans, None, etc.)
            resolved[key] = value

    return resolved


def resolve_env_vars_in_list(data: List[Any]) -> List[Any]:
    """
    Recursively resolve environment variable references in a list.

    Args:
        data: List potentially containing environment variable references

    Returns:
        List with all environment variable references resolved

    Raises:
        ValueError: If a referenced environment variable is not set
    """
    resolved = []

    for item in data:
        if isinstance(item, str):
            # Resolve string values
            resolved.append(resolve_env_var(item))
        elif isinstance(item, dict):
            # Recursively resolve nested dictionaries
            resolved.append(resolve_env_vars_in_dict(item))
        elif isinstance(item, list):
            # Recursively resolve nested lists
            resolved.append(resolve_env_vars_in_list(item))
        else:
            # Keep other types as-is
            resolved.append(item)

    return resolved


def resolve_env_vars(data: Union[str, Dict[str, Any], List[Any]]) -> Union[str, Dict[str, Any], List[Any]]:
    """
    Resolve environment variable references in any data structure.

    Args:
        data: String, dictionary, or list potentially containing environment variable references

    Returns:
        Data structure with all environment variable references resolved

    Raises:
        ValueError: If a referenced environment variable is not set
    """
    if isinstance(data, str):
        return resolve_env_var(data)
    elif isinstance(data, dict):
        return resolve_env_vars_in_dict(data)
    elif isinstance(data, list):
        return resolve_env_vars_in_list(data)
    else:
        return data
