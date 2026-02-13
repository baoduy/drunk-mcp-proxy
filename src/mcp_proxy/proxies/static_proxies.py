"""Static proxy initialization module."""

import glob
import json
import os
from pathlib import Path
from typing import Any

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


def load_config_files(config_path: str) -> list[tuple[str | None, dict[str, Any]]]:
    """Load one or more MCP config files. Returns (namespace, config) pairs."""
    if not config_path:
        return []

    if os.path.isdir(config_path):
        pattern = os.path.join(config_path, "*.mcp.json")
        files = sorted(glob.glob(pattern))
        if not files:
            logger.info("No *.mcp.json files found in %s", config_path)
            return []
        results: list[tuple[str | None, dict[str, Any]]] = []
        for file_path in files:
            namespace = _namespace_from_path(file_path)
            results.append((namespace, _load_config_file(file_path)))
        return results

    if not os.path.exists(config_path):
        logger.info("Config file not found at %s; using empty config", config_path)
        return [(None, {"mcpServers": {}})]

    try:
        return [(_namespace_from_path(config_path), _load_config_file(config_path))]
    except Exception as e:
        logger.exception("Error loading config file '%s'", config_path)
        import sys
        print(
            f"Error loading config file '{config_path}': {e}. Please verify the file exists and contains valid JSON.",
            file=sys.stderr,
        )
        if os.environ.get("FASTMCP_CONFIG_FILE", "").strip():
            print("Critical: Custom config file specified but failed to load. Exiting.", file=sys.stderr)
            sys.exit(1)
        return [(None, {"mcpServers": {}})]


def load_config(config_file: str) -> dict[str, Any]:
    """Load a single MCP server configuration from config file."""
    configs = load_config_files(config_file)
    return configs[0][1] if configs else {"mcpServers": {}}


def get_static_server_names(config_file: str) -> set[str]:
    """Return a set of all static server names from all loaded configs."""
    names: set[str] = set()
    for _namespace, config in load_config_files(config_file):
        servers = config.get("mcpServers", {})
        if isinstance(servers, dict):
            names.update(servers.keys())
    return names


def _try_mount_multi_server_proxy(mcp: Any, config: dict[str, Any], namespace: str | None) -> bool:
    """Try to mount a config-based proxy provider if supported by fastmcp."""
    try:
        from fastmcp.server import create_proxy
    except Exception:
        return False

    try:
        proxy = create_proxy(config, name="StaticConfigProxy")
        mcp.mount(proxy, namespace=namespace)
        logger.info("Mounted config-based proxy provider from mcp.json (namespace=%s)", namespace or "none")
        return True
    except Exception:
        logger.exception("Failed to mount config-based proxy provider; falling back")
        return False


def mount_single_proxy(mcp: Any, name: str, url: str, transport: str = "http") -> None:
    """Mount a single proxy server to the MCP instance."""
    from fastmcp.server import create_proxy

    effective_transport = (transport or "http").lower()
    logger.info("Mounting proxy '%s' at %s (transport=%s)", name, url, effective_transport)

    config = {
        "mcpServers": {
            name: {
                "url": url,
                "transport": effective_transport,
            }
        }
    }
    proxy_server = create_proxy(config, name=name)
    mcp.mount(proxy_server)


def initialize_static_proxies(mcp: Any, config_file: str, host: str, port: int) -> None:
    """Initialize and mount proxies from one or more static configuration files."""
    configs = load_config_files(config_file)
    if not configs:
        logger.info("No static servers found")
        print("No static servers found")
        return

    display_host = "localhost" if host in {"0.0.0.0", "::"} else host

    for namespace, config in configs:
        if not config.get("mcpServers"):
            logger.info("No static servers found in config (namespace=%s)", namespace or "none")
            continue

        # Try to use multi-server proxy provider first (FastMCP v3+)
        if _try_mount_multi_server_proxy(mcp, config, namespace):
            continue

        # Fallback to per-server mounting
        logger.info("Mounting static servers from mcp.json (namespace=%s)", namespace or "none")
        print(f"Mounting static servers from mcp.json (namespace={namespace or 'none'}):")
        for name, details in config["mcpServers"].items():
            url = details.get("url")
            transport = details.get("transport", "http")

            if url:
                try:
                    mount_single_proxy(mcp, name, url, transport)
                    logger.info(
                        "Static proxy '%s' loaded (transport=%s) endpoints: http://%s:%s/%s/mcp , http://%s:%s/%s/sse",
                        name,
                        transport,
                        display_host,
                        port,
                        name,
                        display_host,
                        port,
                        name,
                    )
                    print(f"  ✓ Mounted '{name}' at {url}")
                except Exception as e:
                    logger.exception("Failed to mount static server '%s'", name)
                    print(f"  ✗ Failed to mount '{name}': {e}")
