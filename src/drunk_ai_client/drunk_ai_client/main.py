"""Application orchestration and CLI entry point for the Drunk MCP stdio client.

This module intentionally keeps runtime orchestration and compatibility adapters
in one place for a single-module client surface.
"""

from __future__ import annotations

import asyncio
import os
from typing import cast

from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.server import create_proxy
from fastmcp.server.transforms import Transform
from fastmcp.utilities import logging, skills

from drunk_ai_client.client_config import ClientConfig, ClientConfigLoader
from drunk_ai_client.resource_sync_manager import ResourceSyncManager

logger = logging.get_logger(__name__)


class StdioBridgeApplication:
    """Orchestrates stdio bridge startup, sync, and FastMCP server composition."""

    def __init__(self, config_loader: type[ClientConfigLoader] = ClientConfigLoader) -> None:
        """Initialize runtime application dependencies.

        Args:
            config_loader: Loader class used to build runtime config.
        """
        self._config_loader = config_loader

    def bootstrap_runtime_env(self) -> None:
        """Initialize runtime environment defaults required before FastMCP use."""
        os.environ.setdefault("FASTMCP_LOG_LEVEL", "INFO")

    def load_config(self) -> ClientConfig:
        """Load runtime configuration from CLI arguments and environment variables."""
        return self._config_loader.load()

    def create_authenticated_client(self, config: ClientConfig) -> object:
        """Create a FastMCP client with optional Bearer authentication.

        Args:
            config: Runtime client configuration.

        Returns:
            A FastMCP client configured for the remote endpoint.
        """
        if config.api_key:
            logger.info(
                "Creating authenticated client for %s (api_key=...%s)",
                config.url,
                config.api_key[-4:],
            )
            return Client(config.url, auth=BearerAuth(config.api_key))

        logger.info("Creating unauthenticated client for %s", config.url)
        return Client(config.url)

    async def sync_resources_on_startup(self, config: ClientConfig) -> None:
        """Sync configured remote resources into local directories at startup.

        Args:
            config: Runtime client configuration.
        """
        if config.skill_dir is None and config.agents_dir is None:
            return

        sync_client = self.create_authenticated_client(config)
        async with sync_client:  # pyright: ignore[reportGeneralTypeIssues]
            if config.skill_dir is not None:
                skill_paths = await skills.sync_skills(  # pyright: ignore[reportUnknownMemberType, reportArgumentType]
                    sync_client,  # pyright: ignore[reportArgumentType]
                    config.skill_dir,
                    overwrite=config.allows_overwrite,
                )
                logger.info("Synced %d skills into %s", len(skill_paths), config.skill_dir)

            if config.agents_dir is not None:
                agent_manager = ResourceSyncManager(
                    client=sync_client,  # pyright: ignore[reportArgumentType]
                    scheme="agent",
                    file_suffix="agent.md",
                )
                agent_paths = await agent_manager.sync(
                    config.agents_dir,
                    overwrite=config.allows_overwrite,
                )
                logger.info("Synced %d agents into %s", len(agent_paths), config.agents_dir)

    def _build_transforms(self) -> list[Transform]:
        """Build search transform pipeline for the local stdio proxy."""
        from fastmcp.server.transforms.search import BM25SearchTransform, RegexSearchTransform

        return [
            RegexSearchTransform(max_results=10),
            BM25SearchTransform(max_results=3),
        ]

    def _build_server_from_client(
        self,
        client: object,
        transforms: list[Transform],
    ) -> FastMCP | None:
        """Try FastMCP built-in `from_client` composition with graceful fallback."""
        from_client = getattr(FastMCP, "from_client", None)
        if not callable(from_client):
            return None

        try:
            server = from_client(
                client=client,
                name="drunk-ai-client-stdio",
                transforms=transforms,
            )
            if isinstance(server, FastMCP):
                logger.info("Using FastMCP.from_client composition")
                return cast(FastMCP, server)
            return None
        except (AttributeError, TypeError, ValueError) as exc:
            logger.error("FastMCP.from_client fallback: %s", type(exc).__name__)
            return None

    def _build_server_with_manual_proxy(
        self,
        client: object,
        transforms: list[Transform],
    ) -> FastMCP:
        """Build server using explicit proxy creation and mount."""
        proxy = create_proxy(client)  # pyright: ignore[reportArgumentType]
        server = FastMCP(name="drunk-ai-client-stdio", transforms=transforms)
        server.mount(proxy)
        return server

    def build_server(self, client: object, config: ClientConfig) -> FastMCP:
        """Build the local FastMCP stdio server with compatibility fallback.

        Args:
            client: Remote FastMCP client.
            config: Runtime configuration used to decide composition strategy.

        Returns:
            A FastMCP server ready to run in stdio mode.
        """
        transforms = self._build_transforms()

        if config.use_from_client:
            server = self._build_server_from_client(client, transforms)
            if server is not None:
                return server

        logger.info("Using manual create_proxy + mount composition")
        return self._build_server_with_manual_proxy(client, transforms)

    def run(self) -> None:
        """Run the local stdio bridge to the configured remote endpoint."""
        self.bootstrap_runtime_env()
        config = self.load_config()

        if config.sync_enabled and (
            config.skill_dir is not None or config.agents_dir is not None
        ):
            asyncio.run(self.sync_resources_on_startup(config))

        client = self.create_authenticated_client(config)
        server = self.build_server(client, config)

        logger.info("Starting stdio bridge to %s", config.url)
        server.run(transport="stdio")


def create_authenticated_client(config: ClientConfig) -> object:
    """Backward-compatible adapter for authenticated client creation."""
    return StdioBridgeApplication().create_authenticated_client(config)


async def sync_remove_resources(config: ClientConfig) -> None:
    """Backward-compatible adapter for startup resource sync."""
    await StdioBridgeApplication().sync_resources_on_startup(config)


def run_stdio_bridge() -> None:
    """Backward-compatible adapter for running the stdio bridge."""
    StdioBridgeApplication().run()


class ClientCliEntrypoint:
    """CLI entrypoint orchestrator for the Drunk AI stdio client."""

    def run(self) -> None:
        """Run the stdio MCP bridge client."""
        run_stdio_bridge()


def main() -> None:
    """Compatibility adapter used by console script entrypoints."""
    ClientCliEntrypoint().run()


if __name__ == "__main__":
    try:
        run_stdio_bridge()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    except Exception as exc:
        logger.error("Fatal error: %s", type(exc).__name__)
        raise
