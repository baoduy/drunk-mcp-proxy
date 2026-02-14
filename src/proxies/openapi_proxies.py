"""
OpenAPI proxy initialization module.

This module handles loading OpenAPI specifications from .openapi.json files
and creating FastMCP servers that expose OpenAPI endpoints as MCP tools.

Key responsibilities:
- Load and validate OpenAPI configuration files from a directory
- Create FastMCP servers for each OpenAPI specification using OpenAPIProvider
- Mount OpenAPI-based MCP servers to the main server with namespacing
- Provide warm-up functionality to initialize connections

Configuration file format:
- Files must be named *.openapi.json (e.g., petstore.openapi.json, api.openapi.json)
- The filename prefix becomes the namespace for the proxy
- Each file contains a valid OpenAPI 3.0+ specification with a server URL
- No root openapi config (unlike mcp.json)

OpenAPI Integration Pattern:
- Uses FastMCP's OpenAPIProvider from fastmcp.server.providers.openapi
- Reference: https://gofastmcp.com/integrations/openapi
- Each OpenAPI spec is built into a separate FastMCP server
- Servers are mounted with namespace to avoid tool name conflicts

Required OpenAPI Structure:
- openapi: "3.0.0" or higher
- info: { title, version }
- servers: [{ url: "base_url_for_api" }]
- paths: { ... }

Example OpenAPI Config File (petstore.openapi.json):
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Swagger Petstore",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://petstore.swagger.io/v2"
    }
  ],
  "paths": {
    "/pet": {
      "post": {
        "summary": "Add a new pet"
        ...
      }
    }
  }
}
```
"""

import glob
import json
import os
from logging import Logger
from pathlib import Path
from typing import Any, TYPE_CHECKING

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import OpenAPIProvider

from src.tools.env import SERVER_NAME, SERVER_VERSION
from src.tools.logging_config import setup_logging

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider

# Type Definitions
# ================

# Type aliases for better code readability and type safety
OpenAPISpec = dict[str, Any]  # OpenAPI specification dictionary
ServerConfigDict = dict[str, OpenAPISpec]  # Maps server names to their specs

# Initialize logger with the server name from environment
logger = setup_logging(SERVER_NAME)


# OpenAPI Proxy Loader Class
# ===========================

class OpenApiMcpProxyLoader:
    """
    Load and create FastMCP servers from OpenAPI specification files.

    This class handles the complete workflow of discovering, loading, and instantiating
    FastMCP servers from .openapi.json configuration files in a specified directory.

    Unlike StaticProxyLoader which creates proxies to remote MCP servers, this loader
    creates FastMCP servers directly from OpenAPI specifications. Each OpenAPI spec
    is transformed into an MCP server that exposes the API endpoints as tools.

    Features:
    - Automatically caches loaded servers to avoid redundant file I/O
    - Lazy loading on first call to load_all_servers()
    - To reload: Create a new instance
    - Validates OpenAPI schema during loading

    Attributes:
        config_dir: Path to directory containing .openapi.json files
        logger: Logger instance for debug and error messages
        _loaded_servers: Cache of loaded FastMCP servers (always enabled)
    """

    def __init__(self, config_dir: str) -> None:
        """
        Initialize the OpenAPI MCP Proxy Loader.

        Args:
            config_dir: Path to directory containing .openapi.json configuration files

        Note:
            Caching is always enabled. To reload servers from disk, create a new instance.
        """
        self.config_dir: str = config_dir
        self.logger: Logger = logger
        self._loaded_servers: list[tuple[str, FastMCP]] | None = None

    # Configuration Loading Methods
    # ==============================

    @staticmethod
    def extract_namespace_from_path(path: str) -> str | None:
        """
        Extract namespace from an OpenAPI configuration file path.

        The namespace is derived from the filename by removing the .openapi.json extension.
        This namespace is used to prefix tool names when mounting the server to avoid
        naming conflicts between different OpenAPI servers.

        Unlike StaticProxyLoader, there is no root openapi config (no openapi.json file).
        All OpenAPI files must follow the *.openapi.json convention.

        Examples:
            - "data/petstore.openapi.json" -> "petstore"
            - "data/api.openapi.json" -> "api"
            - "data/openapi.json" -> None (root config not supported)
            - "data/config.json" -> None (not an .openapi.json file)

        Args:
            path: Full or relative path to the configuration file

        Returns:
            Namespace string if the file follows the .openapi.json convention,
            None otherwise

        Note:
            This is a static method as it has no dependencies on instance state.
        """
        filename = Path(path).name
        if filename.endswith(".openapi.json"):
            # Remove the .openapi.json suffix to get the namespace
            return filename[: -len(".openapi.json")]
        return None

    def load_config_file(self, config_file: str) -> OpenAPISpec:
        """
        Load and validate a single OpenAPI specification file.

        This method:
        1. Reads the JSON OpenAPI specification file
        2. Validates that it contains required OpenAPI fields (openapi, info, paths)
        3. Logs warnings for missing optional but recommended fields

        Args:
            config_file: Path to the .openapi.json configuration file

        Returns:
            Dictionary containing the parsed OpenAPI specification

        Raises:
            FileNotFoundError: If the config file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            ValueError: If required OpenAPI fields are missing
        """
        self.logger.debug("Loading OpenAPI specification file: %s", config_file)

        # Read and parse the JSON OpenAPI specification file
        with open(config_file, "r") as f:
            spec: OpenAPISpec = json.load(f)

        # Validate that this is a valid OpenAPI specification
        # Check for required top-level fields
        if "openapi" not in spec:
            raise ValueError(f"Missing required 'openapi' field in {config_file}")
        if "info" not in spec:
            raise ValueError(f"Missing required 'info' field in {config_file}")
        if "paths" not in spec:
            self.logger.warning("No 'paths' defined in OpenAPI spec: %s", config_file)

        # Log the OpenAPI version and API title
        openapi_version = spec.get("openapi", "unknown")
        api_title = spec.get("info", {}).get("title", "Unknown API")
        api_version = spec.get("info", {}).get("version", "unknown")
        self.logger.debug(
            "Loaded OpenAPI spec (version=%s, title=%s, api_version=%s) from %s",
            openapi_version,
            api_title,
            api_version,
            config_file
        )

        return spec

    def discover_and_load_config_files(self) -> list[tuple[str, OpenAPISpec]]:
        """
        Discover and load all OpenAPI configuration files from the configured directory.

        This method scans the configured directory for files matching the *.openapi.json
        pattern and loads each one. Files not following this naming convention are
        ignored with a warning.

        File Naming Convention:
            - Files MUST end with .openapi.json (e.g., petstore.openapi.json)
            - There is NO root openapi config (unlike mcp.json)
            - The filename prefix becomes the namespace (petstore.openapi.json -> "petstore")
            - Files ending with just .json are ignored

        Example Files:
            - petstore.openapi.json     -> "petstore" namespace
            - api.openapi.json          -> "api" namespace
            - weather.openapi.json      -> "weather" namespace
            - openapi.json              -> Ignored (root config not supported)
            - config.json               -> Ignored (wrong format)

        Process:
            1. Check if config_dir exists and is a directory
            2. Find all *.openapi.json files in the directory
            3. Warn about any .json files that don't follow the convention
            4. Load and parse each OpenAPI specification
            5. Extract namespace from filename
            6. Return list of (namespace, spec) tuples

        Returns:
            List of tuples containing (namespace, openapi_spec) for each loaded file.
            Returns empty list if directory doesn't exist or contains no .openapi.json files.

        Exit Conditions:
            If config_dir points to an invalid directory, logs a warning.
        """
        if not self.config_dir or not os.path.isdir(self.config_dir):
            self.logger.warning("Configuration directory not found or invalid: %s", self.config_dir)
            return []

        # Find all files matching the *.openapi.json pattern
        pattern = os.path.join(self.config_dir, "*.openapi.json")
        files = sorted(glob.glob(pattern))

        # If no .openapi.json files found, return empty list
        if not files:
            self.logger.info("No *.openapi.json files found in %s", self.config_dir)
            return []

        self.logger.info("Found %d OpenAPI configuration file(s) in %s", len(files), self.config_dir)

        # Load each configuration file and pair it with its namespace
        results: list[tuple[str, OpenAPISpec]] = []
        for file_path in files:
            try:
                namespace = self.extract_namespace_from_path(file_path)
                if namespace is None:
                    self.logger.warning("Skipping file with invalid naming convention: %s", file_path)
                    continue

                spec = self.load_config_file(file_path)
                results.append((namespace, spec))
                self.logger.info("Loaded OpenAPI specification (namespace=%s) from %s", namespace, file_path)
            except Exception as e:
                self.logger.error("Failed to load OpenAPI specification %s: %s", file_path, str(e), exc_info=True)
                continue

        return results

    # MCP Server Creation Methods
    # ===========================

    def create_servers_from_specs(
            self,
            specs: list[tuple[str, OpenAPISpec]],
            auth_provider: "AuthProvider | None" = None
    ) -> list[tuple[str, FastMCP]]:
        """
        Create FastMCP servers from all loaded OpenAPI specifications.

        This method takes a list of OpenAPI specification dictionaries and creates
        a FastMCP server for each one using the OpenAPIProvider from the fastmcp library.

        Process:
            1. Create a FastMCP server for each OpenAPI spec
            2. Set up an HTTP client with the base URL from the OpenAPI spec
            3. Create an OpenAPIProvider with the spec and client
            4. Add the provider to the FastMCP server

        Server Naming:
            - If namespace exists: "{namespace}-openapi-mcp" (e.g., "petstore-openapi-mcp")
            - Namespace ALWAYS exists for OpenAPI configs (no root config)

        Error Handling:
            - If a specification is invalid or missing required fields, it's skipped with a log message
            - If server creation fails for any reason, the exception is logged and
              that server is skipped, but processing continues for remaining specs

        Args:
            specs: List of (namespace, openapi_spec) tuples from discover_and_load_config_files()
            auth_provider: Optional authentication provider for MCP servers (default: None)

        Returns:
            List of (namespace, mcp_server) tuples for successfully created servers.
            The namespace is preserved to enable proper mounting with namespacing.
        """
        servers: list[tuple[str, FastMCP]] = []

        self.logger.info("Creating FastMCP servers from %d OpenAPI specification(s)", len(specs))

        for namespace, spec in specs:
            try:
                # Validate OpenAPI spec has required fields
                if "servers" not in spec or not spec["servers"]:
                    self.logger.warning(
                        "OpenAPI spec for namespace=%s has no servers defined. "
                        "At least one server URL is required.",
                        namespace
                    )
                    continue

                # Extract base URL from the first server in the spec
                base_url = spec["servers"][0].get("url", "")
                if not base_url:
                    self.logger.warning(
                        "OpenAPI spec for namespace=%s has empty server URL.",
                        namespace
                    )
                    continue

                # Generate a descriptive name for the server based on its namespace
                server_name = f"{namespace}-openapi-mcp"

                # Create the FastMCP server
                mcp = FastMCP(
                    name=server_name,
                    version=SERVER_VERSION,
                    auth=auth_provider
                )

                # Create an HTTP client with the base URL from the OpenAPI spec
                # This client will be used by the OpenAPIProvider to make requests
                # to the actual API endpoints
                client = httpx.AsyncClient(base_url=base_url)

                # Create OpenAPIProvider from the spec and HTTP client
                # This provider transforms OpenAPI endpoints into MCP tools
                provider = OpenAPIProvider(openapi_spec=spec, client=client)

                # Add the provider to the FastMCP server
                # This registers all endpoints as MCP tools
                mcp.add_provider(provider)

                # Store the server with its namespace for later mounting
                servers.append((namespace, mcp))
                self.logger.info(
                    "Created FastMCP server (namespace=%s, name=%s, base_url=%s)",
                    namespace,
                    server_name,
                    base_url
                )

            except Exception as e:
                # Log the error but continue processing other specs
                # This ensures one bad specification doesn't prevent others from loading
                self.logger.error("Failed to create server from OpenAPI spec (namespace=%s): %s",
                                  namespace, str(e), exc_info=True)

        return servers

    # Cache Management
    # ================

    def _is_cache_valid(self) -> bool:
        """
        Check if servers are cached in memory.

        Returns:
            True if servers have already been loaded and cached, False otherwise
        """
        return self._loaded_servers is not None

    # MCP Server Building Methods
    # ============================

    def build_mcp_servers(
            self,
            root_server: FastMCP,
            auth_provider: "AuthProvider | None" = None
    ) -> list[tuple[str | None, FastMCP]]:
        """
        Build FastMCP servers from OpenAPI specifications and mount them to the root server.

        This method orchestrates the creation and mounting of all OpenAPI-based servers,
        creating namespaced FastMCP servers for each OpenAPI specification.

        Mounting Logic:
            - Each OpenAPI server (namespace="petstore"): Creates a new FastMCP server
              named "drunk-mcp-server_petstore" and returns it for mounting to root
            - Unlike StaticProxyLoader, there are no root-level OpenAPI servers

        Process:
            1. For each OpenAPI spec in the list:
               - Create a namespaced FastMCP server
               - Build MCP tools from the OpenAPI specification
               - Add to list of servers to be mounted
            2. Track any creation errors and log them
            3. Return list of (namespace, FastMCP) tuples

        Error Handling:
            - Individual server creation failures are logged
            - Processing continues for remaining specs
            - Partial success is allowed (not all-or-nothing)

        Args:
            root_server: Root FastMCP server instance (used for reference, not directly mounted to)
            auth_provider: Optional authentication provider for OpenAPI servers (default: None)

        Returns:
            List of (namespace, FastMCP) tuples:
            - (None, root_server) for the root server
            - (namespace, mcp_server) for each OpenAPI-based server

        Raises:
            No exceptions raised - errors are logged and processing continues

        Usage Example:
            from fastmcp import FastMCP

            loader = OpenApiMcpProxyLoader("data")
            root_mcp = FastMCP("my-proxy-server", version="1.0.0")
            mcp_list = loader.build_mcp_servers(root_mcp)

            # mcp_list contains:
            # [(None, root_mcp), ("petstore", petstore_mcp), ("api", api_mcp), ...]
        """
        mcp_servers: list[tuple[str | None, FastMCP]] = [(None, root_server)]
        servers = self.load_all_servers()
        self.logger.info("Building MCP servers from %d OpenAPI specification(s)", len(servers))

        for namespace, mcp in servers:
            try:
                # Create namespaced MCP server (all OpenAPI configs are namespaced)
                self.logger.debug("Creating namespaced MCP server (namespace=%s)", namespace)
                mcp_servers.append((namespace, mcp))
                self.logger.info("Successfully added OpenAPI-based server (namespace=%s)", namespace)

            except Exception as e:
                # Log the error but continue processing other servers
                # This ensures one failed server doesn't prevent others from completing
                self.logger.error(
                    "Failed to add OpenAPI server (namespace=%s): %s",
                    namespace,
                    str(e),
                    exc_info=True
                )

        self.logger.info("MCP server building complete: %d server(s) with %d OpenAPI-based server(s) added",
                         len(mcp_servers), len(servers))
        return mcp_servers

    # Public API Methods
    # ==================

    def load_all_servers(self, auth_provider: "AuthProvider | None" = None) -> list[tuple[str, FastMCP]]:
        """
        Load and create all FastMCP servers from OpenAPI specification files.

        This is the main public method that orchestrates the complete server loading process:

        Process Flow:
            1. Check if servers are already cached (returns cached servers if available)
            2. Load all *.openapi.json files from the config directory
            3. Create FastMCP servers for each valid OpenAPI specification
            4. Cache the results in memory
            5. Return list of (namespace, mcp_server) tuples

        Caching Behavior:
            - First call: Loads all OpenAPI specification files and creates servers from disk
            - Subsequent calls: Returns cached servers (no disk I/O)
            - To reload: Create a new OpenApiMcpProxyLoader instance

        Configuration Directory:
            The config_dir should contain one or more *.openapi.json files.
            Each file represents a separate OpenAPI specification to be built into an MCP server.

        Example Directory Structure:
            data/
            ├── petstore.openapi.json   -> Creates "petstore" namespace
            ├── api.openapi.json        -> Creates "api" namespace
            └── weather.openapi.json    -> Creates "weather" namespace

        Error Handling:
            - If no config files are found, returns empty list
            - If no servers can be created, returns empty list
            - Individual server creation failures are logged but don't stop the process

        Args:
            auth_provider: Optional authentication provider for MCP servers (default: None)

        Returns:
            List of (namespace, mcp_server) tuples for successfully created servers.
            Empty list if no servers were created.
            The namespace can be used when mounting to the root MCP server.

        Usage Example:
            loader = OpenApiMcpProxyLoader("data")

            # First call - loads from disk
            servers = loader.load_all_servers()
            print(f"Created {len(servers)} servers")
            # Output: Created 2 servers

            # Second call - returns cached servers (no disk I/O)
            servers = loader.load_all_servers()
            print(f"Got {len(servers)} cached servers")
            # Output: Got 2 cached servers

            # To reload from disk, create a new instance
            loader = OpenApiMcpProxyLoader("data")  # New instance = fresh load
            servers = loader.load_all_servers()

            # Mount servers at app level
            for namespace, server in servers:
                # These are complete FastMCP servers ready to mount
                pass
        """
        # Check if servers are already cached
        if self._is_cache_valid():
            self.logger.debug("Returning %d cached OpenAPI server(s)", len(self._loaded_servers))
            return self._loaded_servers

        self.logger.info("Starting OpenAPI server load process from %s", self.config_dir)

        # Step 1: Discover and load all OpenAPI specification files from the directory
        specs = self.discover_and_load_config_files()
        if not specs:
            self.logger.info("No OpenAPI specifications found")
            # Cache empty result to prevent repeated directory scans
            self._loaded_servers = []
            return []

        # Step 2: Create FastMCP servers from the loaded specifications
        servers = self.create_servers_from_specs(specs, auth_provider=auth_provider)

        # Step 3: Cache the results in memory
        self._loaded_servers = servers
        self.logger.debug("Cached %d OpenAPI server(s) for future calls", len(servers))

        self.logger.info("OpenAPI server load process complete: %d server(s) created", len(servers))
        return servers


# Legacy Function API for Backward Compatibility
# ===============================================

def create_openapi_servers(config_dir: str, auth_provider: "AuthProvider | None" = None) -> list[tuple[str, FastMCP]]:
    """
    Create FastMCP servers from all OpenAPI specification files (Legacy API).

    This is a backward-compatible wrapper function that maintains the original
    function-based API while internally using the OpenApiMcpProxyLoader class.

    This function is maintained for backward compatibility with existing code.
    For new code, consider using OpenApiMcpProxyLoader directly for more control
    and better integration with class-based architectures.

    Args:
        config_dir: Path to directory containing *.openapi.json configuration files
        auth_provider: Optional authentication provider for MCP servers (default: None)

    Returns:
        List of (namespace, mcp_server) tuples for successfully created servers.
        Empty list if no servers were created.

    Usage Example (Legacy):
        servers = create_openapi_servers("data")
        print(f"Created {len(servers)} servers")

    Usage Example (New):
        loader = OpenApiMcpProxyLoader("data")
        servers = loader.load_all_servers()
        print(f"Created {len(servers)} servers")
    """
    loader = OpenApiMcpProxyLoader(config_dir)
    return loader.load_all_servers(auth_provider=auth_provider)
