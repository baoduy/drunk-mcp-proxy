"""
Centralized environment configuration for MCP proxy.

This module provides a single source of truth for all environment variables
used by the MCP proxy server. All configuration is read from environment
variables with sensible defaults.

Environment Variables:
    Configuration:
        FASTMCP_CONFIG_DIR: Directory containing *.mcp.json files (default: "data")

    Logging:
        FASTMCP_LOG_LEVEL: Log level - DEBUG, INFO, WARNING, ERROR (default: "INFO")

    Server Identity:
        FASTMCP_SERVER_NAME: Server name for logging (default: "drunk-mcp-proxy-server")
        FASTMCP_SERVER_VERSION: Server version string (default: "1.0.0")

    Transport:
        FASTMCP_SERVER_TRANSPORT: Transport protocol - http, sse, streamable-http (default: "")

    CORS (comma-separated):
        FASTMCP_CORS_ALLOW_ORIGINS: Allowed origins (e.g., "https://example.com")
        FASTMCP_CORS_ALLOW_METHODS: Allowed methods (e.g., "GET,POST")
        FASTMCP_CORS_ALLOW_HEADERS: Allowed headers (e.g., "Content-Type")
        FASTMCP_CORS_EXPOSE_HEADERS: Headers to expose (e.g., "X-Request-ID")

    Server Binding:
        FASTMCP_HOST: Host to bind to (default: "0.0.0.0")
        FASTMCP_PORT: Port to listen on (default: 9123)

Example .env file:
    FASTMCP_CONFIG_DIR=./data
    FASTMCP_LOG_LEVEL=DEBUG
    FASTMCP_SERVER_NAME=my-mcp-proxy
    FASTMCP_HOST=localhost
    FASTMCP_PORT=8080
    FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com
"""

import os

# Configuration Files
# ===================
# Directory containing MCP server configuration files (*.mcp.json)
CONFIG_DIR = os.environ.get("FASTMCP_CONFIG_DIR", "data")

# Logging Configuration
# =====================
# Log level controls verbosity of logging output
# Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.environ.get("FASTMCP_LOG_LEVEL", "INFO").upper()

# Server Identity
# ===============
# These values identify the server in logs and health checks
SERVER_NAME = os.environ.get("FASTMCP_SERVER_NAME", "drunk-mcp-proxy-server").strip()
SERVER_VERSION = os.environ.get("FASTMCP_SERVER_VERSION", "1.0.0").strip()

# Transport Configuration
# =======================
# Override transport protocol (http, sse, streamable-http)
# Empty string means use default (http)
SERVER_TRANSPORT = os.environ.get("FASTMCP_SERVER_TRANSPORT", "").strip().lower()

# CORS Configuration
# ==================
# Cross-Origin Resource Sharing settings for web clients
# All values are comma-separated lists
CORS_ALLOW_ORIGINS = os.environ.get("FASTMCP_CORS_ALLOW_ORIGINS", "").strip()
CORS_ALLOW_METHODS = os.environ.get("FASTMCP_CORS_ALLOW_METHODS", "").strip()
CORS_ALLOW_HEADERS = os.environ.get("FASTMCP_CORS_ALLOW_HEADERS", "").strip()
CORS_EXPOSE_HEADERS = os.environ.get("FASTMCP_CORS_EXPOSE_HEADERS", "").strip()

# Server Binding
# ==============
# Host and port configuration for the server
# HOST: "0.0.0.0" binds to all interfaces, "localhost" binds to local only
# PORT: Must be a valid port number (1-65535)
HOST = os.environ.get("FASTMCP_HOST", "0.0.0.0").strip()

# Port with validation - defaults to 9123 if invalid
try:
    PORT = int(os.environ.get("FASTMCP_PORT", "9123").strip())
except ValueError:
    # Invalid port value, use default
    PORT = 9123
