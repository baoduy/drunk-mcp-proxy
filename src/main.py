"""
MCP Proxy Server
A proxy server for Model Context Protocol (MCP) that dynamically routes requests to configured backend servers.
"""

from mcp_proxy.server.app import main

if __name__ == "__main__":
    main()
