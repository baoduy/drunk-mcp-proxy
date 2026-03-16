"""
Centralized environment configuration for MCP proxy.

This module provides a single source of truth for all environment variables
used by the MCP proxy server. All configuration is read from environment
variables with sensible defaults.
"""
# pyright: reportConstantRedefinition=false

import os
from dataclasses import dataclass


class EnvReader:
    """Static environment variable reader helpers."""

    @staticmethod
    def string(key: str, default: str = "") -> str:
        """Get an environment variable as a string with a default fallback.

        Args:
            key: The name of the environment variable to retrieve.
            default: The default value to return if the variable is not set.

        Returns:
            The value of the environment variable or the default if not set.
        """
        return os.environ.get(key, default).strip()

    @staticmethod
    def integer(key: str, default: int = 0) -> int:
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

    @staticmethod
    def boolean(key: str, default: bool = False) -> bool:
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


get_env_string = EnvReader.string
get_env_int = EnvReader.integer
get_env_bool = EnvReader.boolean


@dataclass(frozen=True)
class EnvConfig:
    """Immutable snapshot of environment configuration values."""

    config_dir: str
    llm_route_prefix: str
    log_level: str
    server_name: str
    server_version: str
    server_transport: str
    cors_allow_origins: str
    cors_allow_methods: str
    cors_allow_headers: str
    cors_expose_headers: str
    cors_allow_credentials: bool
    cors_max_age: int
    host: str
    port: int
    swagger_enabled: bool
    auth_enabled: bool
    rate_limit_enabled: bool
    rate_limit_requests: int
    rate_limit_window_seconds: int
    remote_resource_ttl_hours: int
    remote_resource_allowed_extensions: str
    remote_resource_max_size_mb: int
    remote_resource_retry_attempts: int
    oauth_storage_encryption_key: str
    oauth_storage_type: str
    redis_connection_string: str | None

    @classmethod
    def from_environment(cls) -> "EnvConfig":
        """Capture current process environment values."""
        return cls(
            config_dir=get_env_string("FASTMCP_CONFIG_DIR", "data"),
            llm_route_prefix=get_env_string("FASTMCP_LLM_ROUTE_PREFIX", "/api/v1"),
            log_level=get_env_string("FASTMCP_LOG_LEVEL", "INFO").upper(),
            server_name=get_env_string("FASTMCP_SERVER_NAME", "drunk-ai-proxy"),
            server_version=get_env_string("FASTMCP_SERVER_VERSION", "1.0.0"),
            server_transport=get_env_string("FASTMCP_SERVER_TRANSPORT", "streamable-http"),
            cors_allow_origins=get_env_string("FASTMCP_CORS_ALLOW_ORIGINS", ""),
            cors_allow_methods=get_env_string(
                "FASTMCP_CORS_ALLOW_METHODS",
                "GET,POST,PUT,DELETE,OPTIONS",
            ),
            cors_allow_headers=get_env_string(
                "FASTMCP_CORS_ALLOW_HEADERS",
                "mcp-protocol-version,mcp-session-id,Authorization,Content-Type",
            ),
            cors_expose_headers=get_env_string("FASTMCP_CORS_EXPOSE_HEADERS", "mcp-session-id"),
            cors_allow_credentials=get_env_bool("FASTMCP_CORS_ALLOW_CREDENTIALS", True),
            cors_max_age=get_env_int("FASTMCP_CORS_MAX_AGE", 3600),
            host=get_env_string("FASTMCP_HOST", "0.0.0.0"),
            port=get_env_int("FASTMCP_PORT", 9123),
            swagger_enabled=get_env_bool("FASTMCP_SWAGGER_ENABLED", True),
            auth_enabled=get_env_bool("FASTMCP_AUTH_ENABLED", False),
            rate_limit_enabled=get_env_bool("FASTMCP_RATE_LIMIT_ENABLED", False),
            rate_limit_requests=get_env_int("FASTMCP_RATE_LIMIT_REQUESTS", 60),
            rate_limit_window_seconds=get_env_int("FASTMCP_RATE_LIMIT_WINDOW_SECONDS", 60),
            remote_resource_ttl_hours=get_env_int("REMOTE_RESOURCE_TTL_HOURS", 24),
            remote_resource_allowed_extensions=get_env_string(
                "REMOTE_RESOURCE_ALLOWED_EXTENSIONS",
                ".md,.yaml,.yml,.json,.py,.js,.ts",
            ),
            remote_resource_max_size_mb=get_env_int("REMOTE_RESOURCE_MAX_SIZE_MB", 10),
            remote_resource_retry_attempts=get_env_int("REMOTE_RESOURCE_RETRY_ATTEMPTS", 2),
            oauth_storage_encryption_key=get_env_string("FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY"),
            oauth_storage_type=get_env_string("FASTMCP_OAUTH_STORAGE_TYPE", "memory"),
            redis_connection_string=get_env_string("FASTMCP_REDIS_CONNECTION_STRING") or None,
        )


ENV_CONFIG = EnvConfig.from_environment()


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

# Backward-compatible constants from immutable environment snapshot.
CONFIG_DIR = ENV_CONFIG.config_dir
LLM_ROUTE_PREFIX = ENV_CONFIG.llm_route_prefix
LOG_LEVEL = ENV_CONFIG.log_level
SERVER_NAME = ENV_CONFIG.server_name
SERVER_VERSION = ENV_CONFIG.server_version
SERVER_TRANSPORT = ENV_CONFIG.server_transport
CORS_ALLOW_ORIGINS = ENV_CONFIG.cors_allow_origins
CORS_ALLOW_METHODS = ENV_CONFIG.cors_allow_methods
CORS_ALLOW_HEADERS = ENV_CONFIG.cors_allow_headers
CORS_EXPOSE_HEADERS = ENV_CONFIG.cors_expose_headers
CORS_ALLOW_CREDENTIALS = ENV_CONFIG.cors_allow_credentials
CORS_MAX_AGE = ENV_CONFIG.cors_max_age
HOST = ENV_CONFIG.host
PORT = ENV_CONFIG.port
SWAGGER_ENABLED = ENV_CONFIG.swagger_enabled
AUTH_ENABLED = ENV_CONFIG.auth_enabled
RATE_LIMIT_ENABLED = ENV_CONFIG.rate_limit_enabled
RATE_LIMIT_REQUESTS = ENV_CONFIG.rate_limit_requests
RATE_LIMIT_WINDOW_SECONDS = ENV_CONFIG.rate_limit_window_seconds
REMOTE_RESOURCE_TTL_HOURS = ENV_CONFIG.remote_resource_ttl_hours
REMOTE_RESOURCE_ALLOWED_EXTENSIONS = ENV_CONFIG.remote_resource_allowed_extensions
REMOTE_RESOURCE_MAX_SIZE_MB = ENV_CONFIG.remote_resource_max_size_mb
REMOTE_RESOURCE_RETRY_ATTEMPTS = ENV_CONFIG.remote_resource_retry_attempts
OAUTH_STORAGE_ENCRYPTION_KEY = ENV_CONFIG.oauth_storage_encryption_key
OAUTH_STORAGE_TYPE = ENV_CONFIG.oauth_storage_type
REDIS_CONNECTION_STRING = ENV_CONFIG.redis_connection_string
