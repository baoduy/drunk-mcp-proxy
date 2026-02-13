"""
Authentication configuration for MCP Proxy Server.
Loads FastMCP auth providers from environment variables.
"""

from __future__ import annotations

import importlib
import inspect
import os
from typing import Any

from ..tools.logging_config import setup_logging

logger = setup_logging("mcp-proxy")

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


def _resolve_auth_class_path(raw_value: str) -> str:
    if not raw_value:
        return ""
    value = raw_value.strip()
    if "." in value:
        return value
    return _AUTH_ALIASES.get(value.lower(), value)


def _import_auth_class(path: str) -> type:
    module_path, _, class_name = path.rpartition(".")
    if not module_path or not class_name:
        raise ValueError(f"Invalid auth provider path: {path}")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _provider_prefixes(provider_cls: type) -> list[str]:
    name = provider_cls.__name__
    base = name[:-8] if name.endswith("Provider") else name
    return [
        f"FASTMCP_SERVER_AUTH_{name.upper()}_",
        f"FASTMCP_SERVER_AUTH_{base.upper()}_",
    ]


def _coerce_value(param_name: str, raw_value: str) -> Any:
    lowered = raw_value.strip()
    if lowered.lower() in {"true", "false"}:
        return lowered.lower() == "true"
    if param_name in {"audience", "scopes"} and "," in lowered:
        return [part.strip() for part in lowered.split(",") if part.strip()]
    return raw_value


def _env_kwargs_for_provider(provider_cls: type) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}

    # Prefer the v2-style FASTMCP_SERVER_AUTH_* env vars when present.
    prefixes = _provider_prefixes(provider_cls)
    for key, value in os.environ.items():
        for prefix in prefixes:
            if key.startswith(prefix):
                param = key[len(prefix):].lower()
                kwargs[param] = _coerce_value(param, value)
                break

    # Fall back to generic env vars matching parameter names.
    try:
        signature = inspect.signature(provider_cls.__init__)
    except (TypeError, ValueError):
        return kwargs

    for param_name, param in signature.parameters.items():
        if param_name == "self" or param_name in kwargs:
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        env_key = param_name.upper()
        if env_key in os.environ:
            kwargs[param_name] = _coerce_value(param_name, os.environ[env_key])

    return kwargs


def auth_config_summary() -> str:
    """Return a short description of the auth configuration."""
    raw = os.environ.get("FASTMCP_SERVER_AUTH", "").strip()
    if not raw:
        return "disabled"
    return raw


def build_auth_provider() -> Any | None:
    """
    Build a FastMCP auth provider from environment variables.

    Uses FASTMCP_SERVER_AUTH to select the provider class path or alias.
    """
    raw = os.environ.get("FASTMCP_SERVER_AUTH", "").strip()
    if not raw:
        logger.info("No FASTMCP_SERVER_AUTH set; authentication disabled")
        return None

    class_path = _resolve_auth_class_path(raw)
    try:
        provider_cls = _import_auth_class(class_path)
    except Exception as exc:
        logger.error("Failed to import auth provider '%s': %s", class_path, exc)
        raise

    kwargs = _env_kwargs_for_provider(provider_cls)
    try:
        provider = provider_cls(**kwargs)
    except Exception as exc:
        logger.error("Failed to initialize auth provider '%s': %s", class_path, exc)
        raise

    logger.info("Authentication enabled via %s", class_path)
    return provider
