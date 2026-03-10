"""Console entry point for the Drunk MCP stdio client."""

from __future__ import annotations

from drunk_ai_client.client import run_stdio_bridge


def main() -> None:
    """Run the stdio MCP bridge client."""
    run_stdio_bridge()
