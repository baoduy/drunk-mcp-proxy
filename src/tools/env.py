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

    OAuth:
        FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY: Fernet encryption key for OAuth token storage (required if using OAuth)

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
# Directory containing JSON schemas (mcp.schema.json, auth.schema.json)
SCHEMA_DIR = os.environ.get("FASTMCP_SCHEMA_DIR", "schemas")

# Logging Configuration
# =====================
# Log level controls verbosity of logging output
# Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.environ.get("FASTMCP_LOG_LEVEL", "INFO").upper()

# Server Identity
# ===============
# These values identify the server in logs and health checks
SERVER_NAME = os.environ.get("FASTMCP_SERVER_NAME", "mcp-proxy-server").strip()
SERVER_VERSION = os.environ.get("FASTMCP_SERVER_VERSION", "1.0.0").strip()

# CORS Configuration
# ==================
# Cross-Origin Resource Sharing settings for web clients
# All values are comma-separated lists
CORS_ALLOW_ORIGINS = os.environ.get("FASTMCP_CORS_ALLOW_ORIGINS", "").strip()
CORS_ALLOW_METHODS = os.environ.get("FASTMCP_CORS_ALLOW_METHODS", "").strip()
CORS_ALLOW_HEADERS = os.environ.get("FASTMCP_CORS_ALLOW_HEADERS", "").strip()
CORS_EXPOSE_HEADERS = os.environ.get("FASTMCP_CORS_EXPOSE_HEADERS", "").strip()

_raw_cors_allow_credentials = os.environ.get("FASTMCP_CORS_ALLOW_CREDENTIALS", "").strip().lower()
CORS_ALLOW_CREDENTIALS = _raw_cors_allow_credentials in {"1", "true", "yes", "on"}

_raw_cors_max_age = os.environ.get("FASTMCP_CORS_MAX_AGE", "").strip()
try:
    CORS_MAX_AGE = int(_raw_cors_max_age) if _raw_cors_max_age else None
except ValueError:
    CORS_MAX_AGE = None

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

# OAuth Configuration
# ===================
# Encryption key for storing OAuth tokens securely
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
OAUTH_STORAGE_ENCRYPTION_KEY = os.environ.get("FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY", "").strip()

# OAuth Storage Type Configuration
# ==================================
# Type of storage backend for OAuth tokens (e.g., "redis", "memory", "database")
OAUTH_STORAGE_TYPE = os.environ.get("MCP_OAUTH_STORAGE_TYPE", "memory").strip()

# Redis Configuration
# ====================
# Connection string for Redis backend
# Format: redis://[user:password@]host:port/database
REDIS_CONNECTION_STRING = os.environ.get("MCP_REDIS_CONNECTION_STRING", "").strip()
