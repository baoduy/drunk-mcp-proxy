"""
Centralized environment configuration for MCP proxy.

This module provides a single source of truth for all environment variables
used by the MCP proxy server. All configuration is read from environment
variables with sensible defaults.
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
LLM_ROUTE_PREFIX = getEnvString("FASTMCP_LLM_ROUTE_PREFIX", "/api/v1")

# Logging Configuration
# =====================
# Log level controls verbosity of logging output
# Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = getEnvString("FASTMCP_LOG_LEVEL", "INFO").upper()

# Server Identity
# ===============
# These values identify the server in logs and health checks
SERVER_NAME = getEnvString("FASTMCP_SERVER_NAME", "drunk-ai-proxy")
SERVER_VERSION = getEnvString("FASTMCP_SERVER_VERSION", "1.0.0")
SERVER_TRANSPORT = getEnvString("FASTMCP_SERVER_TRANSPORT", "streamable-http")

# CORS Configuration
# ==================
# Cross-Origin Resource Sharing settings for web clients
# All values are comma-separated lists
CORS_ALLOW_ORIGINS = getEnvString("FASTMCP_CORS_ALLOW_ORIGINS","")
CORS_ALLOW_METHODS = getEnvString("FASTMCP_CORS_ALLOW_METHODS","GET,POST,PUT,DELETE,OPTIONS")
CORS_ALLOW_HEADERS = getEnvString("FASTMCP_CORS_ALLOW_HEADERS","mcp-protocol-version,mcp-session-id,Authorization,Content-Type")
CORS_EXPOSE_HEADERS = getEnvString("FASTMCP_CORS_EXPOSE_HEADERS","mcp-session-id")
CORS_ALLOW_CREDENTIALS = getEnvBool("FASTMCP_CORS_ALLOW_CREDENTIALS", True)
CORS_MAX_AGE = getEnvInt("FASTMCP_CORS_MAX_AGE", 3600)

# Server Binding
# ==============
# Host and port configuration for the server
# HOST: "0.0.0.0" binds to all interfaces, "localhost" binds to local only
# PORT: Must be a valid port number (1-65535)
HOST = getEnvString("FASTMCP_HOST", "0.0.0.0")
PORT = getEnvInt("FASTMCP_PORT", 9123)

SWAGGER_ENABLED = getEnvBool("FASTMCP_SWAGGER_ENABLED", True)
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
OAUTH_STORAGE_TYPE = getEnvString("FASTMCP_OAUTH_STORAGE_TYPE", "memory")

# Redis Configuration
# ====================
# Connection string for Redis backend
# Format: redis://[user:password@]host:port/database
REDIS_CONNECTION_STRING = getEnvString("FASTMCP_REDIS_CONNECTION_STRING") or None
