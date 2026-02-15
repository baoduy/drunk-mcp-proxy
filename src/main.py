"""
MCP Proxy Server
A proxy server for Model Context Protocol (MCP) that dynamically routes requests to configured backend servers.
"""

from app.server import MCPProxyServer


def main() -> None:
    """
    Synchronous entry point for the MCP proxy server.

    This is the main function called when the module is executed directly.
    It wraps the async run_async() method using asyncio.run().

    Usage:
        python -m pip install -e .
        python src/main.py
    """
    server = MCPProxyServer()
    server.run()


if __name__ == "__main__":
    main()
