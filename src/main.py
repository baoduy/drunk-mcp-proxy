"""
MCP Proxy Server
A proxy server for Model Context Protocol (MCP) that dynamically routes requests to configured backend servers.
"""

import asyncio

from src.app.server import MCPProxyServer


def main() -> None:
    """
    Synchronous entry point for the MCP proxy server.

    This is the main function called when the module is executed directly.
    It wraps the async run_async() method using asyncio.run().

    Usage:
        python -m src.main
        # or
        python src/main.py
    """
    server = MCPProxyServer()
    asyncio.run(server.run_async())


if __name__ == "__main__":
    main()
