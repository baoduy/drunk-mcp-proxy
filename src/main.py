"""
MCP Proxy Server
A proxy server for Model Context Protocol (MCP) that dynamically routes requests to configured backend servers.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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
    server.run()


if __name__ == "__main__":
    main()
