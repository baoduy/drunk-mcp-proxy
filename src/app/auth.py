"""
Authentication configuration for MCP Proxy Server.

This module handles dynamic loading of FastMCP authentication providers
from environment variables. It supports multiple auth providers and
automatically discovers configuration from environment variables.

Supported Auth Providers (Aliases):
- github: GitHub OAuth authentication
- google: Google OAuth authentication
- discord: Discord OAuth authentication
- jwt: JWT token verification
- workos: WorkOS authentication
- authkit: AuthKit (WorkOS) authentication
- descope: Descope authentication
- supabase: Supabase authentication
- scalekit: Scalekit authentication

Configuration:
    Primary: FASTMCP_SERVER_AUTH=<provider_alias_or_path>
    Provider-specific: FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAM>=<value>
    Generic fallback: <PARAM>=<value>

Example:
    FASTMCP_SERVER_AUTH=github
    FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=abc123
    FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=secret456
"""

from __future__ import annotations

import importlib
import inspect
import os
from typing import Union, TYPE_CHECKING

from tools.env import SERVER_NAME
from tools.logging_config import setup_logging

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider

logger = setup_logging(SERVER_NAME)

# Auth Provider Aliases
# =====================
# Maps short aliases to full FastMCP auth provider class paths
# This allows users to specify "github" instead of the full import path

_AUTH_ALIASES: dict[str, str] = {
    "github": "fastmcp.server.auth.providers.github.GitHubProvider",
    "google": "fastmcp.server.auth.providers.google.GoogleProvider",
    "discord": "fastmcp.server.auth.providers.discord.DiscordProvider",
    "jwt": "fastmcp.server.auth.providers.jwt.JWTVerifier",
    "workos": "fastmcp.server.auth.providers.workos.WorkOSProvider",
    "authkit": "fastmcp.server.auth.providers.workos.AuthKitProvider",
    "descope": "fastmcp.server.auth.providers.descope.DescopeProvider",
    "supabase": "fastmcp.server.auth.providers.supabase.SupabaseProvider",
    "scalekit": "fastmcp.server.auth.providers.scalekit.ScalekitProvider",
}


# Private Helper Functions
# ========================


def _resolve_auth_class_path(raw_value: str) -> str:
    """
    Resolve auth provider class path from alias or full path.

    Converts short aliases (like "github") to full Python import paths.
    If the value contains a dot, it's assumed to be a full path already.

    Args:
        raw_value: Provider alias or full class path

    Returns:
        Full Python import path to the auth provider class

    Examples:
        "github" -> "fastmcp.server.auth.providers.github.GitHubProvider"
        "com.example.MyProvider" -> "com.example.MyProvider"
    """
    if not raw_value:
        return ""
    value = raw_value.strip()
    # If contains dot, assume it's a full path
    if "." in value:
        return value
    # Otherwise look up alias (case-insensitive)
    return _AUTH_ALIASES.get(value.lower(), value)


def _import_auth_class(path: str) -> type:
    """
    Dynamically import an auth provider class from its full path.

    Uses Python's importlib to import the module and getattr to
    retrieve the class from that module.

    Args:
        path: Full Python import path (e.g., "module.submodule.ClassName")

    Returns:
        The imported class object

    Raises:
        ValueError: If path format is invalid
        ImportError: If module cannot be imported
        AttributeError: If class doesn't exist in module

    Example:
        cls = _import_auth_class("fastmcp.server.auth.providers.github.GitHubProvider")
        # cls is now the GitHubProvider class
    """
    # Split path into module and class name
    module_path, _, class_name = path.rpartition(".")
    if not module_path or not class_name:
        raise ValueError(f"Invalid auth provider path: {path}")

    # Import module and get class
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _provider_prefixes(provider_cls: type) -> list[str]:
    """
    Generate environment variable prefixes for a provider class.

    Creates two possible prefixes for provider-specific environment variables:
    1. Using full class name (e.g., FASTMCP_SERVER_AUTH_GITHUBPROVIDER_)
    2. Using base name without "Provider" suffix (e.g., FASTMCP_SERVER_AUTH_GITHUB_)

    This allows flexible environment variable naming.

    Args:
        provider_cls: Auth provider class

    Returns:
        List of possible environment variable prefixes

    Example:
        For GitHubProvider class:
        ["FASTMCP_SERVER_AUTH_GITHUBPROVIDER_", "FASTMCP_SERVER_AUTH_GITHUB_"]
    """
    name = provider_cls.__name__
    # Remove "Provider" suffix if present
    base = name[:-8] if name.endswith("Provider") else name
    return [
        f"FASTMCP_SERVER_AUTH_{name.upper()}_",
        f"FASTMCP_SERVER_AUTH_{base.upper()}_",
    ]


def _coerce_value(param_name: str, raw_value: str) -> Union[bool, list[str], str]:
    """
    Convert string environment variable values to appropriate Python types.

    Handles type coercion for common parameter types:
    - Boolean: "true"/"false" strings -> bool
    - List: comma-separated values -> list[str] (for audience, scopes)
    - String: everything else -> str

    Args:
        param_name: Name of the parameter (used to detect list types)
        raw_value: Raw string value from environment variable

    Returns:
        Coerced value as bool, list[str], or str

    Examples:
        _coerce_value("enabled", "true") -> True
        _coerce_value("scopes", "read,write") -> ["read", "write"]
        _coerce_value("client_id", "abc123") -> "abc123"
    """
    lowered = raw_value.strip()

    # Boolean coercion
    if lowered.lower() in {"true", "false"}:
        return lowered.lower() == "true"

    # List coercion for specific parameters
    if param_name in {"audience", "scopes"} and "," in lowered:
        return [part.strip() for part in lowered.split(",") if part.strip()]

    # Default: return as string
    return raw_value


def _env_kwargs_for_provider(provider_cls: type) -> dict[str, Union[bool, list[str], str]]:
    """
    Extract provider configuration from environment variables.

    Builds a kwargs dictionary for the provider class constructor by:
    1. Looking for provider-specific env vars (FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAM>)
    2. Falling back to generic env vars matching parameter names
    3. Coercing values to appropriate types (bool, list, str)

    This allows flexible configuration without hardcoding parameter names.

    Configuration Priority:
        1. FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID (provider-specific)
        2. CLIENT_ID (generic fallback)

    Args:
        provider_cls: Auth provider class to get configuration for

    Returns:
        Dictionary of parameter names to coerced values

    Example:
        For GitHubProvider with:
            FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=abc123
            FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=secret
        Returns:
            {"client_id": "abc123", "client_secret": "secret"}
    """
    kwargs: dict[str, Union[bool, list[str], str]] = {}

    # Step 1: Look for provider-specific environment variables
    # These take the form: FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAM>
    prefixes = _provider_prefixes(provider_cls)
    for key, value in os.environ.items():
        for prefix in prefixes:
            if key.startswith(prefix):
                # Extract parameter name from env var name
                param = key[len(prefix):].lower()
                kwargs[param] = _coerce_value(param, value)
                break

    # Step 2: Fall back to generic environment variables
    # Look at the class __init__ signature to find parameter names
    try:
        signature = inspect.signature(provider_cls.__init__)
    except (TypeError, ValueError):
        # Can't inspect signature, return what we have
        return kwargs

    for param_name, param in signature.parameters.items():
        # Skip self and parameters we already found
        if param_name == "self" or param_name in kwargs:
            continue
        # Skip *args and **kwargs
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        # Check for generic env var matching parameter name
        env_key = param_name.upper()
        if env_key in os.environ:
            kwargs[param_name] = _coerce_value(param_name, os.environ[env_key])

    return kwargs


# Public API Functions
# ====================


def build_auth_provider() -> "AuthProvider | None":
    """
    Build a FastMCP auth provider from environment variables.

    This is the main public function for authentication setup. It:
    1. Reads the FASTMCP_SERVER_AUTH environment variable
    2. Resolves the provider alias to a full class path
    3. Dynamically imports the provider class
    4. Extracts configuration from environment variables
    5. Instantiates and returns the provider

    Authentication Flow:
        Environment → Resolve Alias → Import Class → Extract Config → Create Instance

    Configuration:
        FASTMCP_SERVER_AUTH: Provider alias or full class path
            - If empty: authentication is disabled (returns None)
            - If alias: resolved via _AUTH_ALIASES
            - If contains dot: used as full class path

        Provider-specific variables:
            FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAM>=value

        Generic fallback variables:
            <PARAM>=value

    Returns:
        Configured auth provider instance, or None if authentication is disabled

    Raises:
        ImportError: If provider class cannot be imported
        Exception: If provider initialization fails

    Example:
        # Disable authentication
        FASTMCP_SERVER_AUTH=

        # Use GitHub OAuth
        FASTMCP_SERVER_AUTH=github
        FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=abc123
        FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=secret456

        # Use custom provider
        FASTMCP_SERVER_AUTH=com.example.CustomProvider
        CLIENT_ID=xyz789
    """
    # Check if authentication is enabled
    raw = os.environ.get("FASTMCP_SERVER_AUTH", "").strip()
    if not raw:
        logger.info("No FASTMCP_SERVER_AUTH set; authentication disabled")
        return None

    # Step 1: Resolve provider alias to full class path
    class_path = _resolve_auth_class_path(raw)

    # Step 2: Import the provider class
    try:
        provider_cls = _import_auth_class(class_path)
    except Exception as exc:
        logger.error("Failed to import auth provider '%s': %s", class_path, exc)
        raise

    # Step 3: Extract configuration from environment variables
    kwargs = _env_kwargs_for_provider(provider_cls)

    # Step 4: Instantiate the provider
    try:
        provider = provider_cls(**kwargs)
    except Exception as exc:
        logger.error("Failed to initialize auth provider '%s': %s", class_path, exc)
        raise

    logger.info("Authentication enabled via %s", class_path)
    return provider
