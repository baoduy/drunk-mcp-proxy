"""
MCP Proxy Server
A proxy server for Model Context Protocol (MCP) that dynamically routes requests to configured backend servers.
"""

import json
import os
import sys
import asyncio
from typing import Any
from fastmcp import FastMCP
from fastmcp.server.proxy import ProxyClient, FastMCPProxy

# Configuration file paths
CONFIG_FILE = os.environ.get("MCP_CONFIG_FILE", "config.json")
PROXIES_FILE = os.environ.get("MCP_PROXIES_FILE", "proxies.json")

# Lock for file operations to prevent race conditions
_proxies_lock = asyncio.Lock()

# Initialize FastMCP server
mcp = FastMCP("MCP Proxy Server", version="1.0.0")


def load_config() -> dict[str, Any]:
    """Load the MCP server configuration from config file."""
    if not os.path.exists(CONFIG_FILE):
        return {"mcpServers": {}}
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file '{CONFIG_FILE}': {e}. Please verify the file exists and contains valid JSON.", file=sys.stderr)
        # Exit on critical config error in production/Docker environments
        if os.environ.get("MCP_CONFIG_FILE"):
            print(f"Critical: Custom config file specified but failed to load. Exiting.", file=sys.stderr)
            sys.exit(1)
        return {"mcpServers": {}}


def load_proxies() -> list[dict[str, str]]:
    """Load dynamically added proxies from proxies file."""
    if not os.path.exists(PROXIES_FILE):
        return []
    
    try:
        with open(PROXIES_FILE, 'r') as f:
            data = json.load(f)
            return data.get("proxies", [])
    except Exception as e:
        print(f"Error loading proxies file '{PROXIES_FILE}': {e}. Please verify the file contains valid JSON.", file=sys.stderr)
        return []


async def save_proxy_async(name: str, url: str, transport: str = "http") -> None:
    """Save a proxy configuration to the proxies file asynchronously."""
    async with _proxies_lock:  # Prevent race conditions on concurrent writes
        def _save():
            proxies = load_proxies()
            
            # Update existing or add new proxy
            for p in proxies:
                if p.get("name") == name:
                    p["url"] = url
                    p["transport"] = transport
                    break
            else:
                proxies.append({"name": name, "url": url, "transport": transport})
            
            with open(PROXIES_FILE, 'w') as f:
                json.dump({"proxies": proxies}, f, indent=2)
        
        # Run file I/O in thread pool to avoid blocking event loop
        await asyncio.to_thread(_save)


def mount_proxy(name: str, url: str, transport: str = "http") -> None:
    """Mount a proxy server to the MCP instance.
    
    Note: Currently the transport parameter is stored in configuration but not used
    by ProxyClient, which automatically determines the transport from the URL.
    """
    def client_factory():
        return ProxyClient(url)
    
    proxy_server = FastMCPProxy(client_factory=client_factory, name=name)
    mcp.mount(proxy_server)


@mcp.tool()
async def add_proxy(name: str, url: str, transport: str = "http") -> str:
    """
    Add a new MCP proxy server dynamically.
    
    Args:
        name: Name identifier for the proxy
        url: URL of the MCP server to proxy
        transport: Transport protocol (default: http)
    
    Returns:
        Success or error message
    """
    # Prevent conflicts with statically configured servers
    config = load_config()
    static_servers = config.get("mcpServers", {}) or {}
    if name in static_servers:
        return (
            f"✗ Cannot add proxy '{name}': a static server with this name is already "
            f"defined in {CONFIG_FILE}."
        )
    
    # Prevent conflicts with existing dynamic proxies
    existing_proxies = load_proxies()
    if any(p.get("name") == name for p in existing_proxies):
        return (
            f"✗ Cannot add proxy '{name}': a dynamic proxy with this name is already "
            f"defined in {PROXIES_FILE}."
        )
    
    # Mount first, only save if mount succeeds
    try:
        mount_proxy(name, url, transport)
    except Exception as e:
        return f"✗ Failed to mount proxy '{name}' at {url}: {e}"
    
    # Save only after successful mount
    await save_proxy_async(name, url, transport)
    return f"✓ Added and mounted proxy '{name}' at {url}"


@mcp.tool()
def list_proxies() -> str:
    """
    List all configured MCP proxy servers.
    
    Returns:
        List of configured proxies
    """
    # Load both static config and dynamic proxies
    config = load_config()
    proxies = load_proxies()
    
    result = []
    
    # Add static servers from config
    if config.get("mcpServers"):
        result.append("Static Servers (from config.json):")
        for name, details in config["mcpServers"].items():
            url = details.get("url", "N/A")
            transport = details.get("transport", "http")
            result.append(f"  - {name}: {url} ({transport})")
    
    # Add dynamic proxies
    if proxies:
        result.append("\nDynamic Proxies (from proxies.json):")
        for p in proxies:
            result.append(f"  - {p.get('name', 'Unknown')}: {p.get('url', 'N/A')} ({p.get('transport', 'http')})")
    
    if not result:
        return "No proxies configured"
    
    return "\n".join(result)


@mcp.tool()
def get_server_info() -> str:
    """
    Get information about this MCP proxy server.
    
    Returns:
        Server information
    """
    return """
MCP Proxy Server v1.0.0
-----------------------
A dynamic proxy server for Model Context Protocol.

Features:
- Dynamic proxy management
- HTTP/SSE transport support
- Persistent configuration
- Multiple backend servers

Use 'add_proxy' to add new backend servers.
Use 'list_proxies' to view all configured servers.
"""


def initialize_static_proxies():
    """Initialize and mount proxies from the static configuration file."""
    config = load_config()
    
    if not config.get("mcpServers"):
        print("No static servers found in config.json")
        return
    
    print("Mounting static servers from config.json:")
    for name, details in config["mcpServers"].items():
        url = details.get("url")
        transport = details.get("transport", "http")
        
        if url:
            try:
                mount_proxy(name, url, transport)
                print(f"  ✓ Mounted '{name}' at {url}")
            except Exception as e:
                print(f"  ✗ Failed to mount '{name}': {e}")


def initialize_dynamic_proxies():
    """Initialize and mount dynamically added proxies."""
    proxies = load_proxies()
    
    if not proxies:
        print("No dynamic proxies found in proxies.json")
        return
    
    print("Mounting dynamic proxies from proxies.json:")
    for proxy in proxies:
        name = proxy.get("name")
        url = proxy.get("url")
        transport = proxy.get("transport", "http")
        
        if name and url:
            try:
                mount_proxy(name, url, transport)
                print(f"  ✓ Mounted '{name}' at {url}")
            except Exception as e:
                print(f"  ✗ Failed to mount '{name}': {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Starting MCP Proxy Server")
    print("=" * 50)
    
    # Initialize proxies from configuration files
    initialize_static_proxies()
    initialize_dynamic_proxies()
    
    print("=" * 50)
    print("MCP Proxy Server is ready!")
    print("=" * 50)
    
    # Run the MCP server
    mcp.run()
