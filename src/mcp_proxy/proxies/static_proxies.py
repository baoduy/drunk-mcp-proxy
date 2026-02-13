"""Static proxy initialization module."""

import glob
import inspect
import json
import os
from pathlib import Path
from typing import Any

from fastmcp.server import create_proxy

from ..tools.logging_config import setup_logging
from ..tools.validation import validate_mcp_config

logger = setup_logging("mcp-proxy")


def _namespace_from_path(path: str) -> str | None:
    filename = Path(path).name
    if filename.endswith(".mcp.json"):
        return filename[: -len(".mcp.json")]
    return None


def _load_config_file(config_file: str) -> dict[str, Any]:
    logger.debug("Loading MCP config from %s", config_file)
    with open(config_file, "r") as f:
        config = json.load(f)

    # Normalize legacy config keys (path -> url) for remote servers
    servers = config.get("mcpServers", {})
    if isinstance(servers, dict):
        for _name, details in servers.items():
            if not isinstance(details, dict):
                continue
            if "path" in details and "url" not in details:
                details["url"] = details.pop("path")

    # Validate configuration against schema
    if not validate_mcp_config(config):
        logger.warning("Configuration validation failed for '%s'", config_file)
    else:
        logger.debug("Configuration validation passed for '%s'", config_file)

    return config


def _load_config_files(config_dir: str) -> list[tuple[str | None, dict[str, Any]]]:
    """Load one or more MCP config files from a directory."""
    if not config_dir:
        return []

    if os.path.isdir(config_dir):
        pattern = os.path.join(config_dir, "*.mcp.json")
        files = sorted(glob.glob(pattern))
        # Warn about json files that don't follow the *.mcp.json convention.
        for other_path in sorted(glob.glob(os.path.join(config_dir, "*.json"))):
            if not other_path.endswith(".mcp.json"):
                logger.warning("Ignoring non-conforming config file (expected *.mcp.json): %s", other_path)
        if not files:
            logger.info("No *.mcp.json files found in %s", config_dir)
            return []
        results: list[tuple[str | None, dict[str, Any]]] = []
        for file_path in files:
            namespace = _namespace_from_path(file_path)
            results.append((namespace, _load_config_file(file_path)))
        return results

    logger.error("Config directory not found or not a directory: %s", config_dir)
    if os.environ.get("FASTMCP_CONFIG_DIR", "").strip():
        import sys
        print("Critical: FASTMCP_CONFIG_DIR must point to a directory. Exiting.", file=sys.stderr)
        sys.exit(1)
    return []


def _load_config(config_dir: str) -> dict[str, Any]:
    """Load the first MCP server configuration from a directory."""
    configs = _load_config_files(config_dir)
    return configs[0][1] if configs else {"mcpServers": {}}


def _get_static_server_names(config_dir: str) -> set[str]:
    """Return a set of all static server names from all loaded configs."""
    names: set[str] = set()
    for _namespace, config in _load_config_files(config_dir):
        servers = config.get("mcpServers", {})
        if isinstance(servers, dict):
            names.update(servers.keys())
    return names


def _create_proxies_from_configs(
        configs: list[tuple[str | None, dict[str, Any]]]
) -> list[tuple[str | None, Any]]:
    """Create proxy instances from all loaded configurations.

    Args:
        configs: List of (namespace, config) tuples

    Returns:
        List of (namespace, proxy) tuples
    """
    proxies: list[tuple[str, Any]] = []

    for namespace, config in configs:
        if not config.get("mcpServers"):
            logger.info("No static servers found in config (namespace=%s)", namespace or "none")
            continue

        try:
            proxy_name = f"{namespace}-mcp-proxy" if namespace else "mcp-proxy"
            proxy = create_proxy(config, name=proxy_name)
            proxies.append((namespace, proxy))
            logger.debug("Created proxy (namespace=%s, name=%s)", namespace, proxy_name)
        except Exception:
            logger.exception("Failed to create proxy for namespace=%s", namespace)

    return proxies


def _mount_proxies(mcp: Any, proxies: list[tuple[str, Any]]) -> None:
    """Mount all proxy instances to the MCP server.

    Args:
        mcp: MCP server instance
        proxies: List of (namespace, proxy) tuples
    """
    for namespace, proxy in proxies:
        try:
            mcp.mount(proxy, namespace=namespace)
            logger.info("Mounted proxy to MCP server (namespace=%s)", namespace)
        except Exception:
            logger.exception("Failed to mount proxy (namespace=%s)", namespace)


def setup_static_proxies(mcp: Any, config_dir: str) -> list[Any]:
    """Initialize and mount proxies from all static configuration files.

    Process:
    1. Load all config files from directory
    2. Create proxy instances for each config
    3. Mount all proxies to the MCP server
    """
    # Step 1: Load all config files
    configs = _load_config_files(config_dir)
    if not configs:
        logger.info("No static servers found")
        print("No static servers found")
        return []

    # Step 2: Create proxy instances
    proxies = _create_proxies_from_configs(configs)
    if not proxies:
        logger.warning("No proxies could be created from configs")
        return []

    # Step 3: Mount proxies to MCP server
    _mount_proxies(mcp, proxies)

    # Return list of proxy instances (without namespaces)
    return [proxy for _, proxy in proxies]


async def warm_up_proxies(proxies: list[Any]) -> None:
    """Warm up proxied servers by listing tools once."""
    for proxy in proxies:
        list_tools = getattr(proxy, "list_tools", None)
        if list_tools is None:
            continue
        try:
            if inspect.iscoroutinefunction(list_tools):
                await list_tools()
            else:
                list_tools()
        except Exception:
            logger.exception("Proxy warm-up failed")
