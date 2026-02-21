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

    OpenAPI:
        FASTMCP_ENABLE_OPENAPI: Enable OpenAPI schema endpoint (default: false)

    Authentication:
        FASTMCP_AUTH_ENABLED: Enable request header validation (default: false)

    Rate Limiting:
        FASTMCP_RATE_LIMIT_ENABLED: Enable rate limiting (default: true)
        FASTMCP_RATE_LIMIT_REQUESTS: Max requests per window (default: 60)
        FASTMCP_RATE_LIMIT_WINDOW_SECONDS: Window size in seconds (default: 60)

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
# pyright: reportConstantRedefinition=false

import os

def getEnvString(key: str, default: str = "") -> str:
    """
    Get an environment variable as a string with a default fallback.

    Args:
        key (str): The name of the environment variable to retrieve.
        default (str): The default value to return if the environment variable is not set.

    Returns:
        str: The value of the environment variable or the default if not set.
    """
    return os.environ.get(key, default).strip()

def getEnvInt(key: str, default: int = 0) -> int:
    """
    Get an environment variable as an integer with a default fallback.

    Args:
        key (str): The name of the environment variable to retrieve.
        default (int): The default value to return if the environment variable is not set or invalid.

    Returns:
        int: The integer value of the environment variable or the default if not set or invalid.
    """
    try:
        return int(os.environ.get(key, str(default)).strip())
    except ValueError:
        return default
    
def getEnvBool(key: str, default: bool = False) -> bool:
    """
    Get an environment variable as a boolean with a default fallback.

    Args:
        key (str): The name of the environment variable to retrieve.
        default (bool): The default value to return if the environment variable is not set.

    Returns:
        bool: The boolean value of the environment variable or the default if not set.
    """
    value = os.environ.get(key, "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    elif value in {"0", "false", "no", "off"}:
        return False
    else:
        return default
    
# Configuration Files
# ===================
# Directory containing MCP server configuration files (*.mcp.json)
CONFIG_DIR = getEnvString("FASTMCP_CONFIG_DIR", "data")
# Directory containing JSON schemas (mcp.schema.json, auth.schema.json)
SCHEMA_DIR = getEnvString("FASTMCP_SCHEMA_DIR", "schemas")
# Route prefix for LLM proxy endpoints
LLM_ROUTE_PREFIX = getEnvString("FASTMCP_LLM_ROUTE_PREFIX", "/llm/v1")

# Logging Configuration
# =====================
# Log level controls verbosity of logging output
# Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = getEnvString("FASTMCP_LOG_LEVEL", "INFO").upper()

# Server Identity
# ===============
# These values identify the server in logs and health checks
SERVER_NAME = getEnvString("FASTMCP_SERVER_NAME", "mcp-proxy-server")
SERVER_VERSION = getEnvString("FASTMCP_SERVER_VERSION", "1.0.0")
SERVER_TRANSPORT = getEnvString("FASTMCP_SERVER_TRANSPORT", "http")

# CORS Configuration
# ==================
# Cross-Origin Resource Sharing settings for web clients
# All values are comma-separated lists
CORS_ALLOW_ORIGINS = getEnvString("FASTMCP_CORS_ALLOW_ORIGINS")
CORS_ALLOW_METHODS = getEnvString("FASTMCP_CORS_ALLOW_METHODS")
CORS_ALLOW_HEADERS = getEnvString("FASTMCP_CORS_ALLOW_HEADERS")
CORS_EXPOSE_HEADERS = getEnvString("FASTMCP_CORS_EXPOSE_HEADERS")
CORS_ALLOW_CREDENTIALS = getEnvBool("FASTMCP_CORS_ALLOW_CREDENTIALS", False)
CORS_MAX_AGE = getEnvInt("FASTMCP_CORS_MAX_AGE", 3600)

# Server Binding
# ==============
# Host and port configuration for the server
# HOST: "0.0.0.0" binds to all interfaces, "localhost" binds to local only
# PORT: Must be a valid port number (1-65535)
HOST = getEnvString("FASTMCP_HOST", "0.0.0.0")
PORT = getEnvInt("FASTMCP_PORT", 9123)

# OpenAPI Configuration
# =====================
# Controls whether the OpenAPI schema endpoint is enabled
OPENAPI_ENABLED = getEnvBool("FASTMCP_ENABLE_OPENAPI", False)

# Authentication Configuration
# =============================
# Enable or disable request header validation (Authorization header must not be empty)
AUTH_ENABLED = getEnvBool("FASTMCP_AUTH_ENABLED", False)

# Rate Limiting Configuration
# ===========================
# Enable/disable rate limiting and configure fixed window limits
RATE_LIMIT_ENABLED = getEnvBool("FASTMCP_RATE_LIMIT_ENABLED", False)
RATE_LIMIT_REQUESTS = getEnvInt("FASTMCP_RATE_LIMIT_REQUESTS", 60)
RATE_LIMIT_WINDOW_SECONDS = getEnvInt("FASTMCP_RATE_LIMIT_WINDOW_SECONDS", 60)

# OAuth Configuration
# ===================
# Encryption key for storing OAuth tokens securely
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
OAUTH_STORAGE_ENCRYPTION_KEY = getEnvString("FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY")

# OAuth Storage Type Configuration
# ==================================
# Type of storage backend for OAuth tokens (e.g., "redis", "memory", "database")
OAUTH_STORAGE_TYPE = getEnvString("MCP_OAUTH_STORAGE_TYPE", "memory")

# Redis Configuration
# ====================
# Connection string for Redis backend
# Format: redis://[user:password@]host:port/database
REDIS_CONNECTION_STRING = getEnvString("MCP_REDIS_CONNECTION_STRING") or None
