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
from logging import Logger
from pathlib import Path
from typing import Protocol, runtime_checkable

from fastmcp import FastMCP
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import FastMCPProxy

from src.tools.env import SERVER_NAME, SERVER_VERSION
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
ConfigDict = dict[str, str | int | float | bool | None | dict | list]  # Configuration dictionary
ServerConfigDict = dict[str, ConfigDict]  # Maps server names to their configs

# Initialize logger with the server name from environment
logger = setup_logging(SERVER_NAME)


# Static Proxy Loader Class
# =========================

class StaticProxyLoader:
    """
    Load and create MCP proxy instances from static configuration files.

    This class handles the complete workflow of discovering, loading, and instantiating
    proxy servers from .mcp.json configuration files in a specified directory.

    Features:
    - Automatically caches loaded proxies to avoid redundant file I/O
    - Lazy loading on first call to load_all_proxies()
    - To reload: Create a new instance

    Attributes:
        config_dir: Path to directory containing .mcp.json files
        logger: Logger instance for debug and error messages
        _loaded_proxies: Cache of loaded proxies (always enabled)
    """

    def __init__(self, config_dir: str) -> None:
        """
        Initialize the Static Proxy Loader.

        Args:
            config_dir: Path to directory containing .mcp.json configuration files

        Note:
            Caching is always enabled. To reload proxies from disk, create a new instance.
        """
        self.config_dir: str = config_dir
        self.logger: Logger = logger
        self._loaded_proxies: list[tuple[str | None, FastMCPProxy]] | None = None

    # Configuration Loading Methods
    # ==============================

    @staticmethod
    def extract_namespace_from_path(path: str) -> str | None:
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

        Note:
            This is a static method as it has no dependencies on instance state.
        """
        filename = Path(path).name
        if filename.endswith(".mcp.json"):
            # Remove the .mcp.json suffix to get the namespace
            return filename[: -len(".mcp.json")]
        return None

    def load_config_file(self, config_file: str) -> ConfigDict:
        """
        Load and validate a single MCP configuration file.

        This method:
        1. Reads the JSON configuration file
        2. Normalizes legacy config keys (converts "path" to "url" for backward compatibility)
        3. Validates the configuration against the JSON schema

        Legacy Support:
            Older configurations may use "path" instead of "url" for remote servers.
            This method automatically converts "path" to "url" to maintain compatibility.

        Args:
            config_file: Path to the .mcp.json configuration file

        Returns:
            Dictionary containing the parsed and normalized configuration

        Raises:
            FileNotFoundError: If the config file doesn't exist
            JSONDecodeError: If the file contains invalid JSON
        """
        self.logger.debug("Loading configuration file: %s", config_file)

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
                    self.logger.debug("Normalized legacy 'path' key to 'url' in config")

        # Validate configuration against schema
        # This catches configuration errors early before proxy creation
        if not validate_mcp_config(config):
            self.logger.warning("Configuration validation failed for '%s'", config_file)
        else:
            self.logger.debug("Configuration validation passed for '%s'", config_file)

        return config

    def discover_and_load_config_files(self) -> list[tuple[str | None, ConfigDict]]:
        """
        Discover and load all MCP configuration files from the configured directory.

        This method scans the configured directory for files matching the *.mcp.json
        pattern and loads each one. Files not following this naming convention are
        ignored with a warning.

        File Naming Convention:
            - Files MUST end with .mcp.json (e.g., stock.mcp.json)
            - A root config can be named mcp.json (namespace None - root namespace)
            - The filename prefix becomes the namespace (stock.mcp.json -> "stock")
            - Files ending with just .json (except mcp.json) are ignored

        Example Files:
            - mcp.json              -> Root namespace (None)
            - stock.mcp.json        -> "stock" namespace
            - wiki.mcp.json         -> "wiki" namespace
            - weather.mcp.json      -> "weather" namespace
            - config.json           -> Ignored (wrong format)

        Process:
            1. Check if config_dir exists and is a directory
            2. Find all *.mcp.json files in the directory
            3. Warn about any .json files that don't follow the convention
            4. Load and parse each configuration file
            5. Extract namespace from filename
            6. Return list of (namespace, config) tuples

        Returns:
            List of tuples containing (namespace, config_dict) for each loaded file.
            Returns empty list if directory doesn't exist or contains no .mcp.json files.

        Exit Conditions:
            If config_dir points to an invalid directory, logs a warning.
        """
        if not self.config_dir or not os.path.isdir(self.config_dir):
            self.logger.warning("Configuration directory not found or invalid: %s", self.config_dir)
            return []

        # Find all files matching the *.mcp.json pattern plus root mcp.json
        pattern = os.path.join(self.config_dir, "*.mcp.json")
        files = sorted(glob.glob(pattern))
        root_config = os.path.join(self.config_dir, "mcp.json")
        if os.path.isfile(root_config):
            files = [root_config, *files]

        # If no .mcp.json files found, return empty list
        if not files:
            self.logger.info("No mcp.json or *.mcp.json files found in %s", self.config_dir)
            return []

        self.logger.info("Found %d configuration file(s) in %s", len(files), self.config_dir)

        # Load each configuration file and pair it with its namespace
        results: list[tuple[str | None, ConfigDict]] = []
        for file_path in files:
            try:
                namespace = self.extract_namespace_from_path(file_path)
                config = self.load_config_file(file_path)
                results.append((namespace, config))
                self.logger.info("Loaded configuration (namespace=%s) from %s", namespace or "None", file_path)
            except Exception as e:
                self.logger.error("Failed to load configuration file %s: %s", file_path, str(e), exc_info=True)
                continue

        return results

    # Proxy Creation Methods
    # ======================

    def create_proxies_from_configs(
            self,
            configs: list[tuple[str | None, ConfigDict]]
    ) -> list[tuple[str | None, FastMCPProxy]]:
        """
        Create proxy instances from all loaded configurations.

        This method takes a list of configuration dictionaries and creates
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
            configs: List of (namespace, config) tuples from discover_and_load_config_files()

        Returns:
            List of (namespace, proxy_instance) tuples for successfully created proxies.
            The namespace is preserved to enable proper mounting with namespacing.
        """
        proxies: list[tuple[str | None, FastMCPProxy]] = []

        self.logger.info("Creating proxies from %d configuration(s)", len(configs))

        for namespace, config in configs:
            # Skip configurations that don't have any servers defined
            if not config.get("mcpServers"):
                self.logger.debug("No static servers found in config (namespace=%s)", namespace or "none")
                continue

            try:
                # Generate a descriptive name for the proxy based on its namespace
                proxy_name = f"{namespace}-mcp-proxy" if namespace else "mcp-proxy"

                # Create the proxy instance using fastmcp's create_proxy function
                # This sets up the proxy to forward requests to the configured backend servers
                proxy = create_proxy(config, name=proxy_name)

                # Store the proxy with its namespace for later mounting
                proxies.append((namespace, proxy))
                self.logger.info("Created proxy (namespace=%s, name=%s)", namespace or "none", proxy_name)

            except Exception as e:
                # Log the error but continue processing other configs
                # This ensures one bad configuration doesn't prevent other proxies from loading
                self.logger.error("Failed to create proxy (namespace=%s): %s", namespace or "none", str(e),
                                  exc_info=True)

        return proxies

    # Cache Management
    # ================

    def _is_cache_valid(self) -> bool:
        """
        Check if proxies are cached in memory.

        Returns:
            True if proxies have already been loaded and cached, False otherwise
        """
        return self._loaded_proxies is not None

    # MCP Server Building Methods
    # ============================

    def build_mcp_servers(
            self,
            root_server: FastMCP,
            auth_provider: object | None = None
    ) -> list[tuple[str | None, FastMCP]]:
        """
        Build FastMCP servers and mount all proxies with namespace handling.

        This method orchestrates the mounting of all proxies to FastMCP servers,
        handling both root-level proxies (no namespace) and namespaced proxies.

        Mounting Logic:
            - Root proxy (namespace=None): Mounted directly to the provided root_server
            - Namespaced proxy (namespace="stock"): Creates a new FastMCP server named
              "drunk-mcp-server_stock" and mounts the proxy to it

        Process:
            1. For each proxy in the list:
               - If namespace is None: Mount to root_server
               - If namespace exists: Create new FastMCP server, mount proxy, add to list
            2. Track any mounting errors and log them
            3. Return list of (namespace, FastMCP) tuples

        Error Handling:
            - Individual mount failures are logged
            - Processing continues for remaining proxies
            - Partial success is allowed (not all-or-nothing)

        Args:
            root_server: Root FastMCP server instance to mount root proxies to
            auth_provider: Optional authentication provider for namespaced servers (default: None)

        Returns:
            List of (namespace, FastMCP) tuples:
            - (None, root_server) for the root server
            - (namespace, mcp_server) for each namespaced server

        Raises:
            No exceptions raised - errors are logged and processing continues

        Usage Example:
            from fastmcp import FastMCP

            loader = StaticProxyLoader("data")
            proxies = loader.load_all_proxies()

            root_mcp = FastMCP("my-proxy-server", version="1.0.0")
            mcp_list = loader.build_mcp_servers(root_mcp)

            # mcp_list contains:
            # [(None, root_mcp), ("stock", stock_mcp), ("wiki", wiki_mcp), ...]
        """
        mcp_servers: list[tuple[str | None, FastMCP]] = [(None, root_server)]
        proxies = self.load_all_proxies()
        self.logger.info("Building MCP servers from %d proxy/proxies", len(proxies))

        for namespace, proxy in proxies:
            try:
                if namespace is None:
                    # Mount proxy without namespace to root server
                    self.logger.debug("Mounting proxy without namespace to root server")
                    root_server.mount(proxy)
                    self.logger.info("Successfully mounted proxy to root server")

                else:
                    # Create namespaced MCP server and mount proxy
                    self.logger.debug("Creating namespaced MCP server (namespace=%s)", namespace)
                    mcp = FastMCP(
                        f"{SERVER_NAME}_{namespace}",
                        version=SERVER_VERSION,
                        auth=auth_provider
                    )
                    mcp.mount(proxy)
                    mcp_servers.append((namespace, mcp))
                    self.logger.info("Successfully mounted proxy with namespace (namespace=%s)", namespace)

            except Exception as e:
                # Log the error but continue processing other proxies
                # This ensures one failed mount doesn't prevent others from completing
                self.logger.error(
                    "Failed to mount proxy (namespace=%s): %s",
                    namespace or "none",
                    str(e),
                    exc_info=True
                )

        self.logger.info("MCP server building complete: %d server(s) with %d proxy/proxies mounted",
                         len(mcp_servers), len(proxies))
        return mcp_servers

    # Public API Methods
    # ==================

    def load_all_proxies(self) -> list[tuple[str | None, FastMCPProxy]]:
        """
        Load and create all proxy instances from configuration files.

        This is the main public method that orchestrates the complete proxy loading process:

        Process Flow:
            1. Check if proxies are already cached (returns cached proxies if available)
            2. Load all *.mcp.json files from the config directory
            3. Create proxy instances for each valid configuration
            4. Cache the results in memory
            5. Return list of (namespace, proxy) tuples

        Caching Behavior:
            - First call: Loads all configuration files and creates proxies from disk
            - Subsequent calls: Returns cached proxies (no disk I/O)
            - To reload: Create a new StaticProxyLoader instance

        Configuration Directory:
            The config_dir should contain one or more *.mcp.json files.
            Each file represents a separate backend MCP server to proxy to.

        Example Directory Structure:
            data/
            ├── mcp.json              -> Creates "None" namespace (root namespace)
            ├── stock.mcp.json        -> Creates "stock" namespace
            ├── wiki.mcp.json         -> Creates "wiki" namespace
            └── weather.mcp.json      -> Creates "weather" namespace

        Error Handling:
            - If no config files are found, returns empty list
            - If no proxies can be created, returns empty list
            - Individual proxy failures are logged but don't stop the process

        Returns:
            List of (namespace, proxy_instance) tuples for successfully created proxies.
            Empty list if no proxies were created.
            The namespace can be used when mounting to the MCP server.

        Usage Example:
            loader = StaticProxyLoader("data")

            # First call - loads from disk
            proxies = loader.load_all_proxies()
            print(f"Created {len(proxies)} proxies")
            # Output: Created 3 proxies

            # Second call - returns cached proxies (no disk I/O)
            proxies = loader.load_all_proxies()
            print(f"Got {len(proxies)} cached proxies")
            # Output: Got 3 cached proxies

            # To reload from disk, create a new instance
            loader = StaticProxyLoader("data")  # New instance = fresh load
            proxies = loader.load_all_proxies()

            # Mount proxies at app level
            for namespace, proxy in proxies:
                mcp_server.mount(proxy, namespace=namespace)
        """
        # Check if proxies are already cached
        if self._is_cache_valid():
            self.logger.debug("Returning %d cached proxy/proxies", len(self._loaded_proxies))
            return self._loaded_proxies

        self.logger.info("Starting proxy load process from %s", self.config_dir)

        # Step 1: Discover and load all config files from the directory
        configs = self.discover_and_load_config_files()
        if not configs:
            self.logger.info("No static server configurations found")
            # Cache empty result to prevent repeated directory scans
            self._loaded_proxies = []
            return []

        # Step 2: Create proxy instances from the loaded configurations
        proxies = self.create_proxies_from_configs(configs)

        # Step 3: Cache the results in memory
        self._loaded_proxies = proxies
        self.logger.debug("Cached %d proxy/proxies for future calls", len(proxies))

        self.logger.info("Proxy load process complete: %d proxy/proxies created", len(proxies))
        return proxies


# Legacy Function API for Backward Compatibility
# ===============================================

def create_static_proxies(config_dir: str) -> list[tuple[str | None, FastMCPProxy]]:
    """
    Create proxy instances from all static configuration files (Legacy API).

    This is a backward-compatible wrapper function that maintains the original
    function-based API while internally using the StaticProxyLoader class.

    This function is maintained for backward compatibility with existing code.
    For new code, consider using StaticProxyLoader directly for more control
    and better integration with class-based architectures.

    Args:
        config_dir: Path to directory containing *.mcp.json configuration files

    Returns:
        List of (namespace, proxy_instance) tuples for successfully created proxies.
        Empty list if no proxies were created.

    Usage Example (Legacy):
        proxies = create_static_proxies("data")
        print(f"Created {len(proxies)} proxies")

    Usage Example (New):
        loader = StaticProxyLoader("data")
        proxies = loader.load_all_proxies()
        print(f"Created {len(proxies)} proxies")
    """
    loader = StaticProxyLoader(config_dir)
    return loader.load_all_proxies()
