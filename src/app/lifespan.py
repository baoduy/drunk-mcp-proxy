"""
Application Lifespan Management Module
"""

from contextlib import asynccontextmanager
from typing import AsyncContextManager

from fastmcp.server.http import StarletteWithLifespan

from ..tools.env import SERVER_NAME
from ..tools.logging_config import setup_logging

# Initialize logger
logger = setup_logging(SERVER_NAME)


class AppLifespanManager:
    """
    Manager for application lifecycle (startup and shutdown) of MCP apps.

    Attributes:
        logger: Logger instance for debug and error messages.
    """

    def __init__(self) -> None:
        """Initialize the AppLifespanManager."""
        self.logger = logger

    @asynccontextmanager
    async def lifespans(self, _: object, mcp_apps: list[tuple[str | None, StarletteWithLifespan]]):
        """
        Manage app lifespans to match Starlette's expected signature.

        Args:
            _: The app parameter from Starlette (unused).
            mcp_apps: List of (name, mcp_app) tuples to manage lifespans for.

        Yields:
            None - delegates to _create_app_lifespans.
        """
        async with self._create_app_lifespans(mcp_apps):
            yield

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
            self.logger.info("Starting lifespans for %d MCP apps", len(mcp_apps))

            for name, mcp_app in mcp_apps:
                lifespan = getattr(mcp_app, "lifespan", None)
                if lifespan is None:
                    self.logger.warning("MCP app missing lifespan (name=%s)", name)
                    continue

                try:
                    ctx: AsyncContextManager[None] = lifespan(mcp_app)
                    await ctx.__aenter__()
                    lifespan_contexts.append(ctx)
                    self.logger.debug("Successfully started lifespan for MCP app (name=%s)", name)
                except Exception as e:
                    self.logger.error("Failed to start lifespan for MCP app (name=%s): %s", name, str(e), exc_info=True)
                    startup_errors.append((name, e))

            if startup_errors:
                self.logger.error("Failed to start %d MCP app lifespan(s)", len(startup_errors))
                raise RuntimeError(f"MCP app startup failed: {startup_errors}")

            self.logger.info("All MCP app lifespans started successfully")
            yield

        finally:
            self.logger.info("Shutting down %d MCP app lifespan(s)", len(lifespan_contexts))
            shutdown_errors: list[tuple[int, Exception]] = []

            for idx, ctx in enumerate(reversed(lifespan_contexts)):
                try:
                    await ctx.__aexit__(None, None, None)
                    self.logger.debug("Successfully shutdown MCP app lifespan (index=%d)", idx)
                except Exception as e:
                    self.logger.error("Error during MCP app shutdown (index=%d): %s", idx, str(e), exc_info=True)
                    shutdown_errors.append((idx, e))

            if shutdown_errors:
                self.logger.warning("Encountered %d error(s) during shutdown", len(shutdown_errors))
