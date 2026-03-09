"""STDIO MCP bridge client for remote Drunk AI Proxy servers.

This module creates a local FastMCP server in stdio mode that proxies all
operations to a remote MCP endpoint with optional Bearer authentication.

Environment variables:
    API_URL: Remote MCP endpoint URL (required).
    API_KEY: Bearer token for authentication (optional).
    SKILL_DIR: Local directory where remote skills are synced at startup (required).

Example:
    export API_URL="https://example.com/mcp"
    export API_KEY="your-token-here"
    python client.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.server import create_proxy
from fastmcp.utilities.skills import sync_skills  # pyright: ignore[reportUnknownVariableType]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


@dataclass
class ClientConfig:
    """Configuration for remote MCP connection."""

    url: str
    api_key: str | None = None
    skill_dir: Path | None = None

    @classmethod
    def from_env(cls) -> "ClientConfig":
        """Load configuration from environment variables and CLI arguments.

        Returns:
            ClientConfig: Validated configuration.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        parser = argparse.ArgumentParser(
            description="FastMCP stdio bridge to remote MCP endpoint"
        )
        parser.add_argument("--url", help="Remote MCP endpoint URL")
        parser.add_argument("--api-key", help="Bearer token for authentication")
        args = parser.parse_args()

        # Prefer CLI args, fallback to env vars
        url = args.url or os.getenv("API_URL")
        if not url:
            raise ValueError("API_URL environment variable or --url argument required")

        # Validate URL format
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url} (must be http:// or https://)")

        api_key = args.api_key or os.getenv("API_KEY")
        skill_dir_value = os.getenv("SKILL_DIR")
        if not skill_dir_value:
            raise ValueError("SKILL_DIR environment variable required")

        skill_dir = Path(skill_dir_value).expanduser()
        skill_dir.mkdir(parents=True, exist_ok=True)

        return cls(url=url, api_key=api_key, skill_dir=skill_dir)


def create_authenticated_client(config: ClientConfig) -> Client[Any]:
    """Create FastMCP Client with optional authentication.

    Args:
        config: Client configuration with URL and optional API key.

    Returns:
        Client: Configured FastMCP Client instance.
    """
    if config.api_key:
        LOGGER.info(
            "Creating authenticated client for %s (api_key=...%s)",
            config.url,
            config.api_key[-4:],
        )
        return Client(config.url, auth=BearerAuth(config.api_key))

    LOGGER.info("Creating unauthenticated client for %s", config.url)
    return Client(config.url)


async def sync_remote_skills_on_start(config: ClientConfig) -> None:
    """Sync all remote skills to local SKILL_DIR once at startup.

    Args:
        config: Client configuration containing remote endpoint and skill directory.
    """
    if config.skill_dir is None:
        raise ValueError("SKILL_DIR must be configured")

    sync_client = create_authenticated_client(config)
    async with sync_client:
        paths = await sync_skills(sync_client, config.skill_dir)

    LOGGER.info("Synced %d skills into %s", len(paths), config.skill_dir)

# https://gofastmcp.com/clients/client#creating-a-client
def run_stdio_bridge() -> None:
    """Run FastMCP stdio bridge server.

    This creates a local stdio MCP server that proxies all operations
    to the configured remote endpoint.
    """
    config = ClientConfig.from_env()

    # Sync skills from remote server once before exposing stdio proxy.
    asyncio.run(sync_remote_skills_on_start(config))

    # Create authenticated client
    client = create_authenticated_client(config)

    # Create proxy from client (automatically handles connection lifecycle)
    proxy = create_proxy(client)

    # Create local stdio server and mount the remote proxy
    server = FastMCP(name="drunk-ai-client-stdio")
    server.mount(proxy)

    LOGGER.info("Starting stdio bridge to %s", config.url)
    server.run(transport="stdio")


if __name__ == "__main__":
    try:
        run_stdio_bridge()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down")
    except Exception as exc:
        LOGGER.error("Fatal error: %s", exc, exc_info=True)
        raise
