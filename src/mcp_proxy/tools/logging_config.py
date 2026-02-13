"""Logging configuration helpers for MCP proxy."""

import logging
from .env import LOG_LEVEL


def setup_logging(name: str = "mcp-proxy") -> logging.Logger:
    """Configure logging and return a named logger."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger(name)

