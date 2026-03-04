"""
MCP Proxy Server
A proxy server for Model Context Protocol (MCP) that dynamically routes requests to configured backend servers.
"""

import sys
from pathlib import Path

# Ensure the src directory is on sys.path when running as a script
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app import MCPProxyServer  # type: ignore[import-not-found]  # noqa: E402


def main() -> None:
    """
    Synchronous entry point for the MCP proxy server.

    This is the main function called when the module is executed directly.
    It wraps the async run_async() method using asyncio.run().

    Usage:
        python -m pip install -e .
        python -m main
    """
    server = MCPProxyServer()
    server.run()


if __name__ == "__main__":
    main()
