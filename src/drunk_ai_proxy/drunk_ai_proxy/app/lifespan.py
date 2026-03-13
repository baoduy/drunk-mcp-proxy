"""
Application Lifespan Management Module
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncContextManager

from fastmcp.server.http import StarletteWithLifespan

if TYPE_CHECKING:
    from drunk_ai_proxy.utils import RemoteResourceConfig

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class AppLifespanManager:
    """
    Manages application lifespan for FastMCP and other server integrations.
    
    This class handles the startup and shutdown lifecycle of all MCP applications
    mounted to the proxy server. It ensures proper initialization and cleanup of
    resources in the correct order.

    Attributes:
        logger: Logger instance for debug and error messages.
    """

    def __init__(
        self,
        mcp_apps: list[tuple[str | None, StarletteWithLifespan]] | None = None,
        remote_resources: list[RemoteResourceConfig] | None = None,
    ) -> None:
        """Initialize lifespan manager with managed app/resource references."""
        self._mcp_apps = mcp_apps or []
        self._remote_resources = remote_resources

    @asynccontextmanager
    async def lifespans(
        self,
        _: object,
        mcp_apps: list[tuple[str | None, StarletteWithLifespan]] | None = None,
        remote_resources: list[RemoteResourceConfig] | None = None,
    ):
        """
        Manage app lifespans to match Starlette's expected signature.

        Args:
            _: The app parameter from Starlette (unused).
            mcp_apps: List of (name, mcp_app) tuples to manage lifespans for.

        Yields:
            None - delegates to _create_app_lifespans.
        """
        sync_task: asyncio.Task[None] | None = None
        active_mcp_apps = mcp_apps if mcp_apps is not None else self._mcp_apps
        active_remote_resources = (
            remote_resources
            if remote_resources is not None
            else self._remote_resources
        )

        if active_remote_resources:
            from drunk_ai_proxy.app.tasks import RemoteResourceSyncTask

            enabled_remote_resources = [
                resource
                for resource in active_remote_resources
                if resource.enabled
            ]

            if enabled_remote_resources:
                sync_task = asyncio.create_task(
                    RemoteResourceSyncTask(enabled_remote_resources).run(),
                    name="remote_resource_sync",
                )
                logger.info(
                    "Scheduled remote resource sync for %d bundle(s)",
                    len(enabled_remote_resources),
                )
            else:
                logger.info("Remote resource sync skipped: no enabled bundle(s)")

        async with self._create_app_lifespans(active_mcp_apps):
            yield

        if sync_task is not None and not sync_task.done():
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                logger.debug("Remote resource sync task cancelled during shutdown")

    @asynccontextmanager
    async def _create_app_lifespans(self, mcp_apps: list[tuple[str | None, StarletteWithLifespan]]):
        """
        Manage startup and shutdown of all mounted MCP applications.

        Args:
            mcp_apps: List of (name, mcp_app) tuples to manage lifespans for.

        Yields:
            None - control returns to calling code; server runs until
            shutdown.

        Raises:
            RuntimeError: If any MCP app fails to start on init.
        """
        lifespan_contexts: list[AsyncContextManager[None]] = []
        startup_errors: list[tuple[str | None, Exception]] = []

        try:
            logger.info("Starting lifespans for %d MCP apps", len(mcp_apps))

            for name, mcp_app in mcp_apps:
                lifespan = getattr(mcp_app, "lifespan", None)
                if lifespan is None:
                    logger.warning("MCP app missing lifespan (name=%s)", name)
                    continue

                try:
                    ctx: AsyncContextManager[None] = lifespan(mcp_app)
                    await ctx.__aenter__()
                    lifespan_contexts.append(ctx)
                    logger.debug(
                        "Successfully started lifespan for MCP app (name=%s)",
                        name,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to start lifespan for MCP app (name=%s): %s",
                        name,
                        type(e).__name__,
                    )
                    startup_errors.append((name, e))

            if startup_errors:
                logger.error(
                    "Failed to start %d MCP app lifespan(s)",
                    len(startup_errors),
                )
                raise RuntimeError(f"MCP app startup failed: {startup_errors}")

            logger.info("All MCP app lifespans started successfully")
            yield

        finally:
            logger.info(
                "Shutting down %d MCP app lifespan(s)",
                len(lifespan_contexts),
            )
            shutdown_errors: list[tuple[int, Exception]] = []

            for idx, ctx in enumerate(reversed(lifespan_contexts)):
                try:
                    await ctx.__aexit__(None, None, None)
                    logger.debug(
                        "Successfully shutdown MCP app lifespan (index=%d)",
                        idx,
                    )
                except Exception as e:
                    logger.error(
                        "Error during MCP app shutdown (index=%d): %s",
                        idx,
                        type(e).__name__,
                    )
                    shutdown_errors.append((idx, e))

            if shutdown_errors:
                logger.warning(
                    "Encountered %d error(s) during shutdown",
                    len(shutdown_errors),
                )
