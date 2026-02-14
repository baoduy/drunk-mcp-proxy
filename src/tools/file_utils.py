"""
File utilities module for MCP proxy server.

This module provides utility functions for file handling, including:
- Namespace extraction from file paths
- File naming convention validation
"""

from pathlib import Path
from typing import Optional


def extract_namespace_from_path(path: str, suffix: str) -> Optional[str]:
    """
    Extract namespace from a file path based on a filename suffix.

    This function extracts a namespace by removing the specified suffix from
    the filename. For example:
    - extract_namespace_from_path("data/petstore.openapi.json", ".openapi.json") → "petstore"
    - extract_namespace_from_path("data/stock.mcp.json", ".mcp.json") → "stock"
    - extract_namespace_from_path("data/openapi.json", ".openapi.json") → None

    Args:
        path: Full or relative path to the configuration file
        suffix: File suffix to remove (e.g., ".openapi.json", ".mcp.json")

    Returns:
        Namespace string if the file follows the naming convention (has content before suffix),
        None if the file ends with the suffix but has no name prefix

    Examples:
        >>> extract_namespace_from_path("data/petstore.openapi.json", ".openapi.json")
        "petstore"

        >>> extract_namespace_from_path("data/api.mcp.json", ".mcp.json")
        "api"

        >>> extract_namespace_from_path("data/openapi.json", ".openapi.json")
        None  # No name prefix

        >>> extract_namespace_from_path("data/config.json", ".openapi.json")
        None  # File doesn't match suffix

    Note:
        This is a reusable utility function used by both StaticProxyLoader
        and OpenApiMcpProxyLoader for consistent namespace extraction.
    """
    filename = Path(path).name
    if filename.endswith(suffix):
        # Remove the suffix to get the namespace
        namespace = filename[: -len(suffix)]
        # Return None if namespace is empty (file is just the suffix)
        return namespace if namespace else None
    return None


def is_valid_namespace(namespace: Optional[str]) -> bool:
    """
    Validate if a namespace is valid (not None and not empty).

    Args:
        namespace: The namespace string to validate

    Returns:
        True if namespace is valid (not None and not empty), False otherwise

    Examples:
        >>> is_valid_namespace("petstore")
        True

        >>> is_valid_namespace(None)
        False

        >>> is_valid_namespace("")
        False
    """
    return namespace is not None and len(namespace) > 0
