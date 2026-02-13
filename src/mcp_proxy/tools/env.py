"""Centralized environment configuration for MCP proxy."""

import os

# Configuration files
CONFIG_DIR = os.environ.get("FASTMCP_CONFIG_DIR", "data")

# Logging
LOG_LEVEL = os.environ.get("FASTMCP_LOG_LEVEL", "INFO").upper()

# Server identity
SERVER_NAME = os.environ.get("FASTMCP_SERVER_NAME", "drunk-mcp-proxy-server").strip()
SERVER_VERSION = os.environ.get("FASTMCP_SERVER_VERSION", "1.0.0").strip()

# Transport overrides
SERVER_TRANSPORT = os.environ.get("FASTMCP_SERVER_TRANSPORT", "").strip().lower()

# CORS configuration (comma-separated lists)
CORS_ALLOW_ORIGINS = os.environ.get("FASTMCP_CORS_ALLOW_ORIGINS", "").strip()
CORS_ALLOW_METHODS = os.environ.get("FASTMCP_CORS_ALLOW_METHODS", "").strip()
CORS_ALLOW_HEADERS = os.environ.get("FASTMCP_CORS_ALLOW_HEADERS", "").strip()
CORS_EXPOSE_HEADERS = os.environ.get("FASTMCP_CORS_EXPOSE_HEADERS", "").strip()


# Server bind (fixed defaults, override via env if needed)
HOST = os.environ.get("FASTMCP_HOST", "0.0.0.0").strip()
try:
    PORT = int(os.environ.get("FASTMCP_PORT", "9123").strip())
except ValueError:
    PORT = 9123
