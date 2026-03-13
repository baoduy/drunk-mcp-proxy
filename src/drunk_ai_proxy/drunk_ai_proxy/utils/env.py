"""
Centralized environment configuration for MCP proxy.

This module provides a single source of truth for all environment variables
used by the MCP proxy server. All configuration is read from environment
variables with sensible defaults.
"""
# pyright: reportConstantRedefinition=false

import os


def get_env_string(key: str, default: str = "") -> str:
    """Get an environment variable as a string with a default fallback.

    Args:
        key: The name of the environment variable to retrieve.
        default: The default value to return if the variable is not set.

    Returns:
        The value of the environment variable or the default if not set.
    """
    return os.environ.get(key, default).strip()


def get_env_int(key: str, default: int = 0) -> int:
    """Get an environment variable as an integer with a default fallback.

    Args:
        key: The name of the environment variable to retrieve.
        default: The default value to return if not set or invalid.

    Returns:
        The integer value of the environment variable or the default.
    """
    try:
        return int(os.environ.get(key, str(default)).strip())
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get an environment variable as a boolean with a default fallback.

    Args:
        key: The name of the environment variable to retrieve.
        default: The default value to return if the variable is not set.

    Returns:
        The boolean value of the environment variable or the default.
    """
    value = os.environ.get(key, "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


# Configuration Files
# ===================
# Directory containing MCP server configuration files (*.mcp.json)
CONFIG_DIR = get_env_string("FASTMCP_CONFIG_DIR", "data")
# Route prefix for LLM proxy endpoints
LLM_ROUTE_PREFIX = get_env_string("FASTMCP_LLM_ROUTE_PREFIX", "/api/v1")

# Logging Configuration
# =====================
# Log level controls verbosity of logging output
# Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = get_env_string("FASTMCP_LOG_LEVEL", "INFO").upper()

# Server Identity
# ===============
# These values identify the server in logs and health checks
SERVER_NAME = get_env_string("FASTMCP_SERVER_NAME", "drunk-ai-proxy")
SERVER_VERSION = get_env_string("FASTMCP_SERVER_VERSION", "1.0.0")
SERVER_TRANSPORT = get_env_string("FASTMCP_SERVER_TRANSPORT", "streamable-http")

# CORS Configuration
# ==================
# Cross-Origin Resource Sharing settings for web clients
# All values are comma-separated lists
CORS_ALLOW_ORIGINS = get_env_string("FASTMCP_CORS_ALLOW_ORIGINS", "")
CORS_ALLOW_METHODS = get_env_string("FASTMCP_CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
CORS_ALLOW_HEADERS = get_env_string(
    "FASTMCP_CORS_ALLOW_HEADERS",
    "mcp-protocol-version,mcp-session-id,Authorization,Content-Type",
)
CORS_EXPOSE_HEADERS = get_env_string("FASTMCP_CORS_EXPOSE_HEADERS", "mcp-session-id")
CORS_ALLOW_CREDENTIALS = get_env_bool("FASTMCP_CORS_ALLOW_CREDENTIALS", True)
CORS_MAX_AGE = get_env_int("FASTMCP_CORS_MAX_AGE", 3600)

# Server Binding
# ==============
# Host and port configuration for the server
# HOST: "0.0.0.0" binds to all interfaces, "localhost" binds to local only
# PORT: Must be a valid port number (1-65535)
HOST = get_env_string("FASTMCP_HOST", "0.0.0.0")
PORT = get_env_int("FASTMCP_PORT", 9123)

SWAGGER_ENABLED = get_env_bool("FASTMCP_SWAGGER_ENABLED", True)

# Authentication Configuration
# =============================
# Enable or disable request header validation (Authorization header must not be empty)
AUTH_ENABLED = get_env_bool("FASTMCP_AUTH_ENABLED", False)

# Code Mode Configuration
# ========================
# Enable or disable FastMCP Code Mode transforms
CODEMODE_ENABLED = get_env_bool("FASTMCP_CODEMODE_ENABLED", True)

# Rate Limiting Configuration
# ===========================
# Enable/disable rate limiting and configure fixed window limits
RATE_LIMIT_ENABLED = get_env_bool("FASTMCP_RATE_LIMIT_ENABLED", False)
RATE_LIMIT_REQUESTS = get_env_int("FASTMCP_RATE_LIMIT_REQUESTS", 60)
RATE_LIMIT_WINDOW_SECONDS = get_env_int("FASTMCP_RATE_LIMIT_WINDOW_SECONDS", 60)

# Remote Resource Sync Configuration
# ==================================
# Controls startup and periodic synchronization for top-level remote_resources.
REMOTE_RESOURCE_TTL_HOURS = get_env_int("REMOTE_RESOURCE_TTL_HOURS", 24)
REMOTE_RESOURCE_ALLOWED_EXTENSIONS = get_env_string(
    "REMOTE_RESOURCE_ALLOWED_EXTENSIONS",
    ".md,.yaml,.yml,.json,.py,.js,.ts",
)
REMOTE_RESOURCE_MAX_SIZE_MB = get_env_int("REMOTE_RESOURCE_MAX_SIZE_MB", 10)
# Number of transport-level retries for failed downloads.
REMOTE_RESOURCE_RETRY_ATTEMPTS = get_env_int("REMOTE_RESOURCE_RETRY_ATTEMPTS", 2)

# OAuth Configuration
# ===================
# Encryption key for storing OAuth tokens securely
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
OAUTH_STORAGE_ENCRYPTION_KEY = get_env_string("FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY")

# OAuth Storage Type Configuration
# ==================================
# Type of storage backend for OAuth tokens (e.g., "redis", "memory", "database")
OAUTH_STORAGE_TYPE = get_env_string("FASTMCP_OAUTH_STORAGE_TYPE", "memory")

# Redis Configuration
# ====================
# Connection string for Redis backend
# Format: redis://[user:password@]host:port/database
REDIS_CONNECTION_STRING = get_env_string("FASTMCP_REDIS_CONNECTION_STRING") or None
