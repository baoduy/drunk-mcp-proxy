"""
Static proxy initialization module.

This module handles loading MCP server configurations from .mcp.json files
and creating proxy instances that forward requests to the configured backend servers.

Key responsibilities:
- Load and validate configuration files from a directory
- Create proxy instances for each configuration
- Mount proxies to the main MCP server with optional namespacing
- Provide warm-up functionality to initialize connections

Configuration file format:
- Files must be named *.mcp.json (e.g., stock.mcp.json, wiki.mcp.json)
- The filename prefix becomes the namespace for the proxy
- Each file contains an "mcpServers" object with backend server definitions
"""

import glob
import json
import os
from pathlib import Path
from typing import Protocol, runtime_checkable, Any

from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import FastMCPProxy

from src.tools.env import SERVER_NAME
from src.tools.logging_config import setup_logging
from src.tools.validation import validate_mcp_config


# Type Definitions
# ================

@runtime_checkable
class McpProxy(Protocol):
    """
    Protocol defining the interface for MCP proxy objects.

    This protocol ensures that proxy objects have the necessary methods
    for tool listing, which is used during warm-up operations.
    """

    def list_tools(self) -> list[dict[str, str]]:
        """List available tools from the proxied server."""
        ...


# Type aliases for better code readability and type safety
ConfigDict = dict[str, object]  # Represents a configuration dictionary
ServerConfigDict = dict[str, ConfigDict]  # Maps server names to their configs

# Initialize logger with the server name from environment
logger = setup_logging(SERVER_NAME)


# Private Helper Functions
# ========================


def _namespace_from_path(path: str) -> str | None:
    """
    Extract namespace from a configuration file path.

    The namespace is derived from the filename by removing the .mcp.json extension.
    This namespace is used to prefix tool names when mounting the proxy to avoid
    naming conflicts between different proxies.

    Examples:
        - "data/stock.mcp.json" -> "stock"
        - "data/wiki.mcp.json" -> "wiki"
        - "data/config.json" -> None (not a .mcp.json file)

    Args:
        path: Full or relative path to the configuration file

    Returns:
        Namespace string if the file follows the .mcp.json convention,
        None otherwise
    """
    filename = Path(path).name
    if filename.endswith(".mcp.json"):
        # Remove the .mcp.json suffix to get the namespace
        return filename[: -len(".mcp.json")]
    return None


def _load_config_file(config_file: str) -> ConfigDict:
    """
    Load and validate a single MCP configuration file.

    This function:
    1. Reads the JSON configuration file
    2. Normalizes legacy config keys (converts "path" to "url" for backward compatibility)
    3. Validates the configuration against the JSON schema

    Legacy Support:
        Older configurations may use "path" instead of "url" for remote servers.
        This function automatically converts "path" to "url" to maintain compatibility.

    Args:
        config_file: Path to the .mcp.json configuration file

    Returns:
        Dictionary containing the parsed and normalized configuration

    Raises:
        FileNotFoundError: If the config file doesn't exist
        JSONDecodeError: If the file contains invalid JSON
    """

    # Read and parse the JSON configuration file
    with open(config_file, "r") as f:
        config: ConfigDict = json.load(f)

    # Normalize legacy config keys (path -> url) for remote servers
    # This ensures backward compatibility with older configuration formats
    servers = config.get("mcpServers", {})
    if isinstance(servers, dict):
        for _name, details in servers.items():
            if not isinstance(details, dict):
                continue
            # Convert legacy "path" key to "url" if present
            if "path" in details and "url" not in details:
                details["url"] = details.pop("path")

    # Validate configuration against schema
    # This catches configuration errors early before proxy creation
    if not validate_mcp_config(config):
        logger.warning("Configuration validation failed for '%s'", config_file)
    else:
        logger.debug("Configuration validation passed for '%s'", config_file)

    return config


def _load_config_files(config_dir: str) -> list[tuple[str | None, ConfigDict]]:
    """
    Load all MCP configuration files from a directory.

    This function scans the specified directory for files matching the *.mcp.json
    pattern and loads each one. Files not following this naming convention are
    ignored with a warning.

    File Naming Convention:
        - Files MUST end with .mcp.json (e.g., stock.mcp.json)
        - A root config can be named mcp.json (namespace None)
        - The filename prefix becomes the namespace (stock.mcp.json -> "stock")
        - Files ending with just .json (except mcp.json) are ignored

    Process:
        1. Check if config_dir exists and is a directory
        2. Find all *.mcp.json files in the directory
        3. Warn about any .json files that don't follow the convention
        4. Load and parse each configuration file
        5. Extract namespace from filename
        6. Return list of (namespace, config) tuples

    Args:
        config_dir: Path to the directory containing .mcp.json files

    Returns:
        List of tuples containing (namespace, config_dict) for each loaded file.
        Returns empty list if directory doesn't exist or contains no .mcp.json files.

    Exit Conditions:
        If FASTMCP_CONFIG_DIR environment variable is explicitly set but points
        to an invalid directory, the application will exit with an error message.
    """
    if not config_dir or not os.path.isdir(config_dir):
        return []

    # Find all files matching the *.mcp.json pattern plus root mcp.json
    pattern = os.path.join(config_dir, "*.mcp.json")
    files = sorted(glob.glob(pattern))
    root_config = os.path.join(config_dir, "mcp.json")
    if os.path.isfile(root_config):
        files = [root_config, *files]

    # If no .mcp.json files found, return empty list
    if not files:
        logger.info("No mcp.json or *.mcp.json files found in %s", config_dir)
        return []

    # Load each configuration file and pair it with its namespace
    results: list[tuple[str | None, ConfigDict]] = []
    for file_path in files:
        namespace = _namespace_from_path(file_path)
        results.append((namespace, _load_config_file(file_path)))
        logger.info("Loaded (namespace %s) file %s, ", namespace or "None", file_path)
    return results


def _create_proxies_from_configs(
        configs: list[tuple[str | None, ConfigDict]]
) -> list[tuple[str | None, FastMCPProxy]]:
    """
    Create proxy instances from all loaded configurations.

    This function takes a list of configuration dictionaries and creates
    a FastMCP proxy instance for each one using the create_proxy() function
    from the fastmcp library.

    Proxy Naming:
        - If namespace exists: "{namespace}-mcp-proxy" (e.g., "stock-mcp-proxy")
        - If no namespace: "mcp-proxy"

    Error Handling:
        - If a configuration has no "mcpServers" key, it's skipped with a log message
        - If proxy creation fails for any reason, the exception is logged and
          that proxy is skipped, but processing continues for remaining configs

    Args:
        configs: List of (namespace, config) tuples from _load_config_files()

    Returns:
        List of (namespace, proxy_instance) tuples for successfully created proxies.
        The namespace is preserved to enable proper mounting with namespacing.

    Note:
        The return type uses Any for the proxy because FastMCPProxy is an external
        type that we cannot directly import or define in our type system.
    """
    proxies: list[tuple[str | None, Any]] = []

    for namespace, config in configs:
        # Skip configurations that don't have any servers defined
        if not config.get("mcpServers"):
            logger.info("No static servers found in config (namespace=%s)", namespace or "none")
            continue

        try:
            # Generate a descriptive name for the proxy based on its namespace
            proxy_name = f"{namespace}-mcp-proxy" if namespace else "mcp-proxy"

            # Create the proxy instance using fastmcp's create_proxy function
            # This sets up the proxy to forward requests to the configured backend servers
            proxy = create_proxy(config, name=proxy_name)

            # Store the proxy with its namespace for later mounting
            proxies.append((namespace, proxy))
            logger.debug("Created proxy (namespace=%s, name=%s)", namespace, proxy_name)

        except Exception:
            # Log the full exception traceback but continue processing other configs
            # This ensures one bad configuration doesn't prevent other proxies from loading
            logger.exception("Failed to create proxy for namespace=%s", namespace)

    return proxies


# Public API Functions
# ====================


def create_static_proxies(config_dir: str) -> list[tuple[str | None, Any]]:
    """
    Create proxy instances from all static configuration files.

    This is the main public API function for creating static proxies.
    It orchestrates the proxy creation process in two steps:

    Process Flow:
        1. Load all *.mcp.json files from the config directory
        2. Create proxy instances for each valid configuration

    Configuration Directory:
        The config_dir should contain one or more *.mcp.json files.
        Each file represents a separate backend MCP server to proxy to.

    Example Directory Structure:
        data/
        ├── stock.mcp.json    -> Creates "stock" namespace
        ├── wiki.mcp.json     -> Creates "wiki" namespace
        └── weather.mcp.json  -> Creates "weather" namespace

    Error Handling:
        - If no config files are found, returns empty list
        - If no proxies can be created, returns empty list
        - Individual proxy failures are logged but don't stop the process

    Args:
        config_dir: Path to directory containing *.mcp.json configuration files

    Returns:
        List of (namespace, proxy_instance) tuples for successfully created proxies.
        Empty list if no proxies were created.
        The namespace can be used when mounting to the MCP server.

    Usage Example:
        proxies = create_static_proxies("data")
        print(f"Created {len(proxies)} proxies")
        # Output: Created 3 proxies

        # Mount proxies at app level
        for namespace, proxy in proxies:
            mcp_server.mount(proxy, namespace=namespace)
    """
    # Step 1: Load all config files from the directory
    configs = _load_config_files(config_dir)
    if not configs:
        logger.info("No static servers found")
        print("No static servers found")
        return []

    # Step 2: Create proxy instances from the loaded configurations
    return _create_proxies_from_configs(configs)
