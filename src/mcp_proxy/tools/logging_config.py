"""
Logging configuration helpers for MCP proxy.

This module provides a centralized logging configuration setup,
ensuring consistent log formatting across all modules.

Log Format:
    %(asctime)s %(levelname)s %(name)s: %(message)s

    Example output:
    2024-02-13 10:30:45 INFO drunk-mcp-proxy-server: Starting MCP Proxy Server

Log Levels (controlled via FASTMCP_LOG_LEVEL):
    - DEBUG: Detailed diagnostic information
    - INFO: General informational messages (default)
    - WARNING: Warning messages for potentially problematic situations
    - ERROR: Error messages for serious problems
    - CRITICAL: Critical errors that may cause shutdown

Usage:
    from mcp_proxy.tools.logging_config import setup_logging
    from mcp_proxy.tools.env import SERVER_NAME

    logger = setup_logging(SERVER_NAME)
    logger.info("Server started")
"""

import logging

from .env import LOG_LEVEL


def setup_logging(name: str = "mcp-proxy") -> logging.Logger:
    """
    Configure logging and return a named logger.

    Sets up the Python logging system with a consistent format and
    log level from environment configuration. This should be called
    once per module.

    The log level is controlled by the FASTMCP_LOG_LEVEL environment
    variable, allowing runtime control of verbosity without code changes.

    Args:
        name: Logger name (typically module name or SERVER_NAME)
              This appears in log output to identify the source

    Returns:
        Configured Logger instance ready for use

    Example:
        # In a module
        from mcp_proxy.tools.env import SERVER_NAME
        logger = setup_logging(SERVER_NAME)

        logger.debug("Detailed debug info")
        logger.info("Normal operation message")
        logger.warning("Something unexpected happened")
        logger.error("An error occurred")

    Note:
        logging.basicConfig() is idempotent - subsequent calls don't
        override the initial configuration, so it's safe to call this
        multiple times.
    """
    # Configure basic logging format and level
    # This sets up the root logger with our preferred format
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),  # Get log level from env
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",  # Consistent format
    )

    # Return a named logger for this module/component
    # Using named loggers helps identify the source of log messages
    return logging.getLogger(name)
