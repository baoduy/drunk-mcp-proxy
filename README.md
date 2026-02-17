# drunk-mcp-proxy

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=baoduy_drunk-mcp-proxy&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=baoduy_drunk-mcp-proxy)

A powerful, production-ready dynamic proxy server for the Model Context Protocol (MCP) built with Python and FastMCP. This service enables MCP clients to seamlessly connect to multiple backend MCP servers through a unified, scalable interface with advanced features including authentication, CORS support, and environment-based configuration.

## 🎯 Overview

drunk-mcp-proxy is a sophisticated proxy server that acts as a central gateway for Model Context Protocol (MCP) services. It provides:

- **Unified Interface**: Single endpoint for multiple backend MCP servers
- **Dynamic Routing**: Automatic routing to configured backend services  
- **Namespace Isolation**: Prevent tool name conflicts with per-server namespaces
- **OpenAPI Integration**: Automatic conversion of OpenAPI specs to MCP tools
- **Enterprise Authentication**: Pluggable auth providers (JWT, OAuth, GitHub, etc.)
- **Production Ready**: Health checks, CORS, structured logging, Docker support

## ✨ Features

- 🚀 **Dynamic Proxy Management**: Configure multiple MCP and OpenAPI services via JSON
- 📝 **Flexible Configuration**: JSON-based config with environment variable resolution
- 🐳 **Docker Support**: Multi-stage production Docker image with health checks
- 🔌 **Multiple Transports**: HTTP, SSE, and stdio transport support
- 🔐 **Enterprise Auth**: JWT, GitHub, Google, Discord, and custom auth providers
- 🌐 **CORS Ready**: Full CORS middleware for web client integration
- ⚡ **Azure OAuth2**: Built-in Azure AD authentication with token caching
- 🎨 **OpenAPI Support**: Convert OpenAPI specs to MCP tools automatically
- 🔍 **Health Monitoring**: Built-in health check endpoint for monitoring
- 📊 **Structured Logging**: Configurable log levels and comprehensive logging
- 🛡️ **JSON Schema Validation**: Automatic config validation against schemas

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Python Modules Reference](#-python-modules-reference)
- [Environment Variables](#-environment-variables)
- [API Endpoints](#-api-endpoints)
- [Authentication](#-authentication)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**:
```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

2. **Configure your services** in `data/config.json`:
```json
[
  {
    "name": "github-docs",
    "specType": "mcp",
    "specFile": "mcp/github-docs.json",
    "path": "/",
    "namespace": "github"
  }
]
```

3. **Start the services**:
```bash
docker-compose up -d
```

4. **Verify it's running**:
```bash
curl http://localhost:9123/health
```

### Using Docker

```bash
# Build the image
docker build -t drunk-mcp-proxy .

# Run the container
docker run -d \
  -p 9123:9123 \
  -v $(pwd)/data:/mcp_proxy/data \
  --name mcp-proxy \
  drunk-mcp-proxy
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export FASTMCP_CONFIG_DIR=./data
export FASTMCP_LOG_LEVEL=DEBUG

# Run the server
python src/main.py
```

The server will start on `http://0.0.0.0:9123` by default.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Client                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────────┐
│               drunk-mcp-proxy Server                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Starlette Application                       │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │        CORS Middleware                    │     │    │
│  │  └──────────────────────────────────────────┘     │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │     Authentication Middleware             │     │    │
│  │  └──────────────────────────────────────────┘     │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │          Health Check (/health)           │     │    │
│  │  └──────────────────────────────────────────┘     │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │    MCP Proxy Routers                      │     │    │
│  │  │    • /mcp (root)                          │     │    │
│  │  │    • /{namespace}/mcp (namespaced)        │     │    │
│  │  └──────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬──────────────┐
        v             v             v              v
┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐
│  MCP Server  │ │  MCP Server  │ │ OpenAPI  │ │ OpenAPI  │
│   (HTTP)     │ │   (stdio)    │ │  Service │ │  Service │
│              │ │              │ │  (HTTP)  │ │  (Azure) │
└──────────────┘ └──────────────┘ └──────────┘ └──────────┘
```

### Request Flow

1. **Client Request**: MCP client sends request to proxy endpoint
2. **Middleware Processing**: CORS, authentication, and other middleware process request
3. **Route Matching**: Request is routed to appropriate backend based on path
4. **Backend Call**: Proxy forwards request to configured backend MCP/OpenAPI service
5. **Response Aggregation**: Response is collected and returned to client

### Key Components

- **MCPProxyServer**: Main server orchestrator
- **StarletteApp**: ASGI application factory
- **ProxyConfigProvider**: Configuration loader and validator
- **OpenApiMcpProvider**: OpenAPI to MCP converter
- **AzureOauth**: OAuth2 authentication handler

## 📖 Configuration

### Configuration File Structure

The main configuration file is `data/config.json`, which defines all proxy services:

```json
[
  {
    "name": "service-name",
    "specType": "mcp",
    "specFile": "mcp/service-spec.json",
    "path": "/",
    "namespace": "service",
    "tags": ["tag1", "tag2"]
  },
  {
    "name": "api-service",
    "specType": "openapi",
    "specFile": "openapi/api-spec.json",
    "baseUrl": "https://api.example.com",
    "path": "/api",
    "filters": {
      "methods": ["GET", "POST"],
      "tags": ["users", "posts"]
    },
    "auth": {
      "azure": {
        "tokenUrl": "$AZURE_TOKEN_URL",
        "clientId": "$AZURE_CLIENT_ID",
        "clientSecret": "$AZURE_CLIENT_SECRET",
        "tenantId": "$AZURE_TENANT_ID",
        "scope": ["https://api.example.com/.default"]
      }
    }
  }
]
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the service |
| `specType` | enum | Yes | Type of spec: `"mcp"` or `"openapi"` |
| `specFile` | string | Yes | Path to spec file relative to config directory |
| `path` | string | No | Mount path (default: `"/"`) |
| `namespace` | string | No | Namespace for tools (prevents conflicts) |
| `baseUrl` | string | Conditional | Required for OpenAPI specs (unless using Azure auth) |
| `tags` | array | No | Tags for categorization |
| `filters` | object | No | Filter methods/tags for OpenAPI specs |
| `auth` | object | No | Authentication configuration |

### MCP Specification File

MCP spec files (in `data/mcp/`) define MCP server endpoints:

```json
{
  "mcpServers": {
    "server-name": {
      "url": "https://mcp.example.com/mcp",
      "transport": "http"
    }
  }
}
```

### OpenAPI Specification File

OpenAPI spec files (in `data/openapi/`) are standard OpenAPI 3.0 specifications.

### Environment Variable Resolution

Configuration values support environment variable substitution:

- `$VARIABLE_NAME`: Simple substitution
- `${VARIABLE_NAME}`: Braced substitution

Example:
```json
{
  "clientId": "$AZURE_CLIENT_ID",
  "tokenUrl": "https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/token"
}
```

## 🐍 Python Modules Reference

This section provides detailed documentation of all Python files in the `src/` folder.

### Core Application Modules (`src/app/`)

#### `src/main.py`
**Purpose**: Main application entry point

- **Function**: `main()` - Synchronous entry point that initializes and runs the server
- **Usage**: Direct execution via `python src/main.py`
- **Responsibilities**:
  - Sets up Python path for module imports
  - Creates MCPProxyServer instance
  - Delegates to server.run() method

#### `src/app/server.py`
**Purpose**: Core server orchestration and lifecycle management

- **Class**: `MCPProxyServer`
  - Main server class managing the complete server lifecycle
  - Handles server initialization, configuration, and startup
  
- **Key Methods**:
  - `__init__()` - Initialize server with logger and auth provider
  - `async_run()` - Asynchronous server startup orchestration
  - `run()` - Synchronous wrapper for async_run()
  - `_async_start_server()` - Start Starlette/uvicorn server with middleware
  - `_log_startup_configuration()` - Log server configuration details
  - `_retrieve_configuration()` - Get current server configuration

- **Responsibilities**:
  - Load and build proxy configurations
  - Mount MCP services at appropriate paths
  - Configure and start uvicorn ASGI server
  - Handle graceful shutdown and error recovery

#### `src/app/auth.py`
**Purpose**: Dynamic authentication provider loading and configuration

- **Supported Auth Providers**:
  - `github`: GitHub OAuth authentication
  - `google`: Google OAuth authentication
  - `discord`: Discord OAuth authentication
  - `jwt`: JWT token verification
  - `workos`: WorkOS authentication
  - `authkit`: AuthKit (WorkOS) authentication
  - `descope`: Descope authentication
  - `supabase`: Supabase authentication
  - `scalekit`: Scalekit authentication

- **Key Functions**:
  - `build_auth_provider()` - Main function to build auth provider from environment
  - `_resolve_auth_class_path()` - Resolve alias to full class path
  - `_import_auth_class()` - Dynamically import auth provider class
  - `_env_kwargs_for_provider()` - Extract provider config from environment
  - `_coerce_value()` - Type coercion for environment variables

- **Environment Variables**:
  - `FASTMCP_SERVER_AUTH`: Provider alias or full class path
  - `FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAM>`: Provider-specific configuration
  - Generic fallback: `<PARAM>=<value>`

#### `src/app/starlette_app.py`
**Purpose**: Starlette ASGI application factory

- **Class**: `StarletteApp`
  - Factory for creating Starlette applications with MCP mounts
  - Manages health checks, middleware, and lifespan

- **Key Methods**:
  - `__init__()` - Initialize with middleware configuration
  - `add_mcp_service()` - Add single MCP service mount
  - `add_mcp_services()` - Add multiple MCP service mounts
  - `build()` - Build final Starlette application
  - `_health_check_handler()` - Health check endpoint handler

- **Mount Paths**:
  - Root service (name="root"): `/mcp`
  - Namespaced services: `/{namespace}/mcp`

#### `src/app/lifespan.py`
**Purpose**: Application lifecycle management for mounted MCP apps

- **Class**: `AppLifespanManager`
  - Manages startup and shutdown of all MCP applications
  - Ensures proper initialization order and error handling

- **Key Methods**:
  - `lifespans()` - Public entry point matching Starlette signature
  - `_create_app_lifespans()` - Core lifespan management logic

- **Responsibilities**:
  - Initialize all MCP app lifespans on startup
  - Track startup errors and fail fast if needed
  - Gracefully shutdown all apps on server stop
  - Log detailed startup/shutdown information

#### `src/app/middleware/cros_middleware.py`
**Purpose**: CORS (Cross-Origin Resource Sharing) middleware configuration

- **Key Functions**:
  - `build_cors_middleware()` - Build CORS middleware from environment
  - `_parse_csv()` - Parse comma-separated environment values

- **Environment Variables**:
  - `FASTMCP_CORS_ALLOW_ORIGINS`: Comma-separated allowed origins
  - `FASTMCP_CORS_ALLOW_METHODS`: Comma-separated allowed methods
  - `FASTMCP_CORS_ALLOW_HEADERS`: Comma-separated allowed headers
  - `FASTMCP_CORS_EXPOSE_HEADERS`: Comma-separated exposed headers
  - `FASTMCP_CORS_ALLOW_CREDENTIALS`: Allow credentials (true/false)
  - `FASTMCP_CORS_MAX_AGE`: Max age for preflight cache

- **Behavior**:
  - CORS disabled if no origins specified
  - Defaults to wildcard (*) for methods/headers if not specified

#### `src/app/middleware/__init__.py`
**Purpose**: Middleware registry and aggregation

- **Key Functions**:
  - `build_middleware()` - Build complete middleware stack

- **Middleware Order** (request flow):
  1. CORS middleware (if enabled)
  2. [Future middleware can be added]

### Proxy Configuration Modules (`src/proxies/`)

#### `src/proxies/config_provider.py`
**Purpose**: Centralized proxy configuration loading and management

- **Class**: `ProxyConfigProvider`
  - Loads and validates proxy configurations from config.json
  - Creates FastMCP server instances for all configured services

- **Key Methods**:
  - `__init__()` - Initialize with config directory
  - `_load_configs()` - Load all SpecConfig entries from config.json
  - `_get_configs_by_type()` - Filter configs by spec type (MCP/OpenAPI)
  - `_get_mcp_services()` - Create FastMCP servers for MCP configs
  - `_get_openapi_services()` - Create FastMCP servers for OpenAPI configs
  - `get_config_services()` - Get all configured services

- **Properties**:
  - `openapi_configs`: All OpenAPI configurations
  - `mcp_configs`: All MCP configurations

#### `src/proxies/mcp_proxy_config.py`
**Purpose**: Pydantic model for MCP proxy configuration

- **Class**: `McpProxyConfig`
  - Simple data model holding proxy name and FastMCP instance
  
- **Attributes**:
  - `name`: Service name identifier
  - `mcp_server`: FastMCP server instance

#### `src/proxies/openapi_mcp_provider.py`
**Purpose**: OpenAPI to MCP conversion and HTTP client creation

- **Class**: `OpenApiMcpProvider`
  - Converts OpenAPI specifications to FastMCP tool proxies
  - Handles HTTP client creation with authentication

- **Key Methods**:
  - `__init__()` - Initialize with SpecConfig
  - `create_proxy()` - Create FastMCP instance from OpenAPI spec
  - `create_client()` - Create httpx.AsyncClient with auth
  - `custom_route_mapper()` - Apply filters to routes
  - `_create_auth()` - Create Azure OAuth authentication

- **Features**:
  - Automatic OpenAPI to MCP tool conversion
  - HTTP method and tag filtering
  - Azure OAuth2 client credentials support
  - Custom route mapping for selective tool exposure

### Utility Modules (`src/tools/`)

#### `src/tools/spec_config.py`
**Purpose**: Configuration data models with validation

- **Classes**:
  - `SpecType(Enum)`: Specification type enum (MCP, OPENAPI)
  - `Filters(BaseModel)`: HTTP method and tag filters
  - `AzureAuthConfig(BaseModel)`: Azure AD OAuth configuration
  - `Auth(BaseModel)`: Authentication configuration wrapper
  - `SpecConfig(BaseModel)`: Complete proxy specification model

- **SpecConfig Key Methods**:
  - `load_spec_file()` - Load and validate spec file
  - `load_from_file()` - Static method to load all configs from file
  - `_validate_after_load()` - Post-load validation
  - `_validate_mcp_schema()` - Validate MCP specs against JSON schema

- **Features**:
  - Pydantic-based validation
  - Automatic environment variable resolution
  - JSON schema validation for MCP specs
  - Comprehensive field validation

#### `src/tools/env_resolver.py`
**Purpose**: Environment variable resolution in configuration values

- **Key Functions**:
  - `resolve_env_var()` - Resolve env vars in single string
  - `resolve_env_vars_in_dict()` - Recursive resolution in dictionaries
  - `resolve_env_vars_in_list()` - Recursive resolution in lists
  - `resolve_env_vars()` - Universal resolution dispatcher

- **Supported Formats**:
  - `$VAR_NAME`: Simple variable reference
  - `${VAR_NAME}`: Braced variable reference

- **Behavior**:
  - Raises ValueError if referenced variable not set
  - Recursively processes nested structures
  - Preserves non-string types

#### `src/tools/env.py`
**Purpose**: Centralized environment variable configuration

- **Configuration Categories**:
  - **File Paths**: `CONFIG_DIR`, `SCHEMA_DIR`
  - **Logging**: `LOG_LEVEL`
  - **Server Identity**: `SERVER_NAME`, `SERVER_VERSION`
  - **CORS**: `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_METHODS`, etc.
  - **Server Binding**: `HOST`, `PORT`
  - **OAuth**: `OAUTH_STORAGE_ENCRYPTION_KEY`

- **Default Values**:
  - CONFIG_DIR: `"data"`
  - LOG_LEVEL: `"INFO"`
  - SERVER_NAME: `"mcp-proxy-server"`
  - HOST: `"0.0.0.0"`
  - PORT: `9123`

#### `src/tools/logging_config.py`
**Purpose**: Centralized logging configuration

- **Key Functions**:
  - `setup_logging()` - Configure and return named logger

- **Log Format**:
  ```
  %(asctime)s %(levelname)s %(name)s: %(message)s
  ```

- **Log Levels**:
  - DEBUG: Detailed diagnostic information
  - INFO: General informational messages (default)
  - WARNING: Warning messages
  - ERROR: Error messages
  - CRITICAL: Critical errors

- **Behavior**:
  - Reads log level from `FASTMCP_LOG_LEVEL`
  - Creates named loggers for source identification
  - Idempotent - safe to call multiple times

#### `src/tools/azure_oauth.py`
**Purpose**: Azure AD OAuth2 client credentials authentication

- **Class**: `AzureOauth(httpx.Auth)`
  - Implements OAuth2 client credentials flow for Azure AD
  - Provides automatic token caching and refresh
  - Supports both sync and async HTTP clients

- **Key Methods**:
  - `__init__()` - Initialize with Azure AD credentials
  - `_async_fetch_token()` - Fetch new token from Azure AD
  - `_async_get_token()` - Get cached or fetch new token
  - `auth_flow()` - Synchronous auth flow for httpx.Client
  - `async_auth_flow()` - Async auth flow for httpx.AsyncClient

- **Features**:
  - Dual-layer caching (in-memory + optional storage)
  - Automatic token expiry detection (60-second buffer)
  - Pluggable token storage adapter support
  - Full sync and async support via asyncio

- **Token Storage**:
  - Uses `py-key-value-aio` for flexible storage
  - Default: in-memory storage
  - Optional: disk, keyring, encrypted storage

### Module Dependencies

```
main.py
  └── app/server.py
       ├── app/auth.py
       ├── app/starlette_app.py
       │    ├── app/lifespan.py
       │    └── proxies/mcp_proxy_config.py
       ├── app/middleware/__init__.py
       │    └── app/middleware/cros_middleware.py
       ├── proxies/config_provider.py
       │    ├── proxies/mcp_proxy_config.py
       │    ├── proxies/openapi_mcp_provider.py
       │    │    └── tools/azure_oauth.py
       │    └── tools/spec_config.py
       │         └── tools/env_resolver.py
       └── tools/
            ├── env.py
            ├── logging_config.py
            ├── env_resolver.py
            ├── spec_config.py
            └── azure_oauth.py
```

## 🔧 Environment Variables

### Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_CONFIG_DIR` | `data` | Directory containing config.json and spec files |
| `FASTMCP_SCHEMA_DIR` | `schemas` | Directory containing JSON schema files |

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_SERVER_NAME` | `mcp-proxy-server` | Server name for logging and health checks |
| `FASTMCP_SERVER_VERSION` | `1.0.0` | Server version string |
| `FASTMCP_HOST` | `0.0.0.0` | Host to bind to (0.0.0.0 = all interfaces) |
| `FASTMCP_PORT` | `9123` | Port to listen on |

### Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_LOG_LEVEL` | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |

### CORS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_CORS_ALLOW_ORIGINS` | _(empty)_ | Comma-separated allowed origins (e.g., `https://app.example.com,https://web.example.com`) |
| `FASTMCP_CORS_ALLOW_METHODS` | `*` | Comma-separated allowed methods (e.g., `GET,POST,PUT,DELETE`) |
| `FASTMCP_CORS_ALLOW_HEADERS` | `*` | Comma-separated allowed headers (e.g., `Content-Type,Authorization`) |
| `FASTMCP_CORS_EXPOSE_HEADERS` | _(empty)_ | Comma-separated headers to expose |
| `FASTMCP_CORS_ALLOW_CREDENTIALS` | `false` | Allow credentials (cookies) |
| `FASTMCP_CORS_MAX_AGE` | _(none)_ | Max age for preflight cache (seconds) |

### Authentication Configuration

| Variable | Description |
|----------|-------------|
| `FASTMCP_SERVER_AUTH` | Auth provider alias or full class path (e.g., `jwt`, `github`, `com.example.CustomProvider`) |
| `FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAM>` | Provider-specific configuration (e.g., `FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID`) |
| Generic parameters | Fallback to direct env vars (e.g., `CLIENT_ID`, `CLIENT_SECRET`, `JWKS_URI`) |

### OAuth Configuration

| Variable | Description |
|----------|-------------|
| `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY` | Fernet encryption key for OAuth token storage |

### Example .env File

```bash
# Server Configuration
FASTMCP_SERVER_NAME=my-mcp-proxy
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=INFO

# Configuration Paths
FASTMCP_CONFIG_DIR=./data
FASTMCP_SCHEMA_DIR=./schemas

# CORS Configuration
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://web.example.com
FASTMCP_CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization
FASTMCP_CORS_ALLOW_CREDENTIALS=true

# Authentication (JWT Example)
FASTMCP_SERVER_AUTH=jwt
JWKS_URI=https://auth.example.com/.well-known/jwks.json
ISSUER=https://auth.example.com/
AUDIENCE=mcp-proxy-api

# Azure OAuth (for OpenAPI services)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
AZURE_TOKEN_URL=https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/token
```

## 🌐 API Endpoints

### Health Check

```
GET /health
```

Returns server health status and service name.

**Response**:
```json
{
  "status": "healthy",
  "service": "mcp-proxy-server"
}
```

### MCP Endpoints

#### Root Service
```
POST /mcp
```

MCP endpoint for root-mounted services (path="/").

#### Namespaced Services
```
POST /{namespace}/mcp
```

MCP endpoint for namespaced services.

**Examples**:
- `POST /github/mcp` - GitHub documentation service
- `POST /weather/mcp` - Weather API service
- `POST /analytics/mcp` - Analytics service

### MCP Protocol

All MCP endpoints follow the [Model Context Protocol specification](https://spec.modelcontextprotocol.io/):

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [...]
  }
}
```

## 🔐 Authentication

Authentication is configured via FastMCP auth providers and environment variables. If no auth provider is configured, authentication is disabled.

### Supported Auth Providers

| Provider | Alias | Description |
|----------|-------|-------------|
| GitHub | `github` | GitHub OAuth authentication |
| Google | `google` | Google OAuth authentication |
| Discord | `discord` | Discord OAuth authentication |
| JWT | `jwt` | JWT token verification |
| WorkOS | `workos` | WorkOS authentication |
| AuthKit | `authkit` | AuthKit (WorkOS) authentication |
| Descope | `descope` | Descope authentication |
| Supabase | `supabase` | Supabase authentication |
| Scalekit | `scalekit` | Scalekit authentication |
| Custom | Full class path | Custom auth provider |

### Configure an Auth Provider

Set `FASTMCP_SERVER_AUTH` to a provider alias or full class path:

#### JWT Example

```bash
export FASTMCP_SERVER_AUTH=jwt
export JWKS_URI=https://example.com/.well-known/jwks.json
export ISSUER=https://issuer.example.com/
export AUDIENCE=my-audience
```

#### GitHub OAuth Example

```bash
export FASTMCP_SERVER_AUTH=github
export FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=your-github-client-id
export FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### Custom Provider Example

```bash
export FASTMCP_SERVER_AUTH=com.example.auth.CustomAuthProvider
export CLIENT_ID=your-client-id
export CLIENT_SECRET=your-client-secret
```

### Provider Configuration Priority

1. **Provider-specific env vars**: `FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAM>`
2. **Generic env vars**: Direct parameter names (e.g., `CLIENT_ID`, `CLIENT_SECRET`)

## 👨‍💻 Development

### Project Structure

```
drunk-mcp-proxy/
├── src/                          # Source code
│   ├── __init__.py
│   ├── main.py                   # Application entry point
│   ├── app/                      # Core application
│   │   ├── __init__.py
│   │   ├── server.py             # Server orchestration
│   │   ├── auth.py               # Authentication providers
│   │   ├── lifespan.py           # Lifecycle management
│   │   ├── starlette_app.py      # ASGI application factory
│   │   └── middleware/           # Middleware components
│   │       ├── __init__.py       # Middleware registry
│   │       └── cros_middleware.py # CORS middleware
│   ├── proxies/                  # Proxy configuration
│   │   ├── __init__.py
│   │   ├── config_provider.py    # Config loader
│   │   ├── mcp_proxy_config.py   # Proxy data model
│   │   └── openapi_mcp_provider.py # OpenAPI converter
│   └── tools/                    # Utility modules
│       ├── __init__.py
│       ├── env.py                # Environment config
│       ├── env_resolver.py       # Env var resolution
│       ├── logging_config.py     # Logging setup
│       ├── spec_config.py        # Config data models
│       └── azure_oauth.py        # Azure OAuth2
├── data/                         # Configuration files
│   ├── config.json               # Main config file
│   ├── mcp/                      # MCP spec files
│   └── openapi/                  # OpenAPI spec files
├── schemas/                      # JSON schemas
│   └── mcp.schema.json          # MCP validation schema
├── tests/                        # Test suite
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project metadata
├── Dockerfile                   # Docker image definition
├── docker-compose.yml           # Docker Compose config
└── README.md                    # This file
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_main.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/

# Lint code
pylint src/

# Type checking
mypy src/
```

### Adding a New Proxy Service

1. **Create spec file** in `data/mcp/` or `data/openapi/`
2. **Add to config.json**:
   ```json
   {
     "name": "my-service",
     "specType": "mcp",
     "specFile": "mcp/my-service.json",
     "namespace": "myservice"
   }
   ```
3. **Set environment variables** (if needed)
4. **Restart server**

### Adding Custom Middleware

1. **Create middleware file** in `src/app/middleware/`
2. **Implement middleware** as Starlette Middleware
3. **Register in** `src/app/middleware/__init__.py`:
   ```python
   def build_middleware() -> list[Middleware]:
       middleware = []
       middleware.extend(build_cors_middleware())
       middleware.extend(build_my_middleware())  # Add here
       return middleware
   ```

## 🧪 Testing

The project includes comprehensive test coverage:

### Test Coverage

- **15+ test files** covering all major components
- **96 tests** with **93% code coverage**
- Async testing with pytest-asyncio
- Mock support for external services

### Key Test Files

| Test File | Coverage |
|-----------|----------|
| `test_env.py` | Environment variable loading |
| `test_env_resolver.py` | Variable resolution ($VAR syntax) |
| `test_spec_config.py` | Configuration validation |
| `test_azure_oauth.py` | Azure OAuth token flow |
| `test_config_provider.py` | Config loading |
| `test_openapi_mcp_provider.py` | OpenAPI conversion |
| `test_auth.py` | Auth provider building |
| `test_middleware.py` | CORS middleware |
| `test_main.py` | Main entry point |

## 🚢 Deployment

### Docker Deployment

#### Production Image

```bash
# Build production image
docker build -t drunk-mcp-proxy:latest .

# Run container
docker run -d \
  --name mcp-proxy \
  -p 9123:9123 \
  -v $(pwd)/data:/mcp_proxy/data \
  -e FASTMCP_LOG_LEVEL=INFO \
  --health-cmd="curl -f http://localhost:9123/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  drunk-mcp-proxy:latest
```

#### Docker Compose (Recommended)

```yaml
version: '3.8'

services:
  mcp-proxy:
    build: .
    container_name: mcp-proxy
    ports:
      - "9123:9123"
    volumes:
      - ./data:/mcp_proxy/data:ro
      - mcp-pip-cache:/tmp/pip-cache
    environment:
      - FASTMCP_CONFIG_DIR=/mcp_proxy/data
      - FASTMCP_LOG_LEVEL=INFO
      - FASTMCP_SERVER_NAME=mcp-proxy-server
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9123/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - mcp-network

volumes:
  mcp-pip-cache:

networks:
  mcp-network:
    driver: bridge
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-proxy
  template:
    metadata:
      labels:
        app: mcp-proxy
    spec:
      containers:
      - name: mcp-proxy
        image: drunk-mcp-proxy:latest
        ports:
        - containerPort: 9123
        env:
        - name: FASTMCP_LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: config
          mountPath: /mcp_proxy/data
          readOnly: true
        livenessProbe:
          httpGet:
            path: /health
            port: 9123
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 9123
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: mcp-proxy-config
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-proxy
spec:
  selector:
    app: mcp-proxy
  ports:
  - port: 9123
    targetPort: 9123
  type: LoadBalancer
```

### Environment-Specific Configurations

#### Development
```bash
FASTMCP_LOG_LEVEL=DEBUG
FASTMCP_CONFIG_DIR=./data
FASTMCP_HOST=localhost
```

#### Staging
```bash
FASTMCP_LOG_LEVEL=INFO
FASTMCP_CONFIG_DIR=/app/data
FASTMCP_CORS_ALLOW_ORIGINS=https://staging.example.com
```

#### Production
```bash
FASTMCP_LOG_LEVEL=WARNING
FASTMCP_CONFIG_DIR=/app/data
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://www.example.com
FASTMCP_SERVER_AUTH=jwt
```

### Monitoring and Observability

#### Health Checks

```bash
# Basic health check
curl http://localhost:9123/health

# Docker health check
docker inspect --format='{{.State.Health.Status}}' mcp-proxy

# Kubernetes health check
kubectl get pods -l app=mcp-proxy
```

#### Logging

```bash
# Docker logs
docker logs -f mcp-proxy

# Docker Compose logs
docker-compose logs -f mcp-proxy

# Kubernetes logs
kubectl logs -f deployment/mcp-proxy
```

#### Metrics (Optional)

For production monitoring, consider adding:
- Prometheus metrics endpoint
- Grafana dashboards
- Application performance monitoring (APM)
- Distributed tracing

## 🔧 Troubleshooting

### Common Issues

#### Port Already in Use

**Error**: `Address already in use: 0.0.0.0:9123`

**Solution**:
```bash
# Find process using port
lsof -i :9123

# Kill process or use different port
export FASTMCP_PORT=9124
```

#### Configuration File Not Found

**Error**: `Configuration file not found: data/config.json`

**Solution**:
```bash
# Check config directory
ls -la data/

# Set correct path
export FASTMCP_CONFIG_DIR=/path/to/data

# Verify config.json exists
cat data/config.json
```

#### Spec File Validation Errors

**Error**: `MCP spec file 'mcp/service.json' does not conform to MCP schema`

**Solution**:
1. Validate JSON syntax: `cat data/mcp/service.json | jq`
2. Check against schema: `schemas/mcp.schema.json`
3. Ensure required fields are present
4. Review validation error message for specifics

#### Environment Variable Not Resolved

**Error**: `Environment variable 'AZURE_CLIENT_ID' referenced in configuration is not set`

**Solution**:
```bash
# Set missing variable
export AZURE_CLIENT_ID=your-client-id

# Or use .env file
echo "AZURE_CLIENT_ID=your-client-id" >> .env
```

#### CORS Errors

**Error**: `CORS policy: No 'Access-Control-Allow-Origin' header`

**Solution**:
```bash
# Enable CORS for your domain
export FASTMCP_CORS_ALLOW_ORIGINS=https://your-domain.com

# Or allow all (development only)
export FASTMCP_CORS_ALLOW_ORIGINS=*
```

#### Authentication Failures

**Error**: `Authentication failed`

**Solution**:
1. Verify `FASTMCP_SERVER_AUTH` is set correctly
2. Check provider-specific environment variables
3. Test auth endpoint directly
4. Review auth provider logs

#### OpenAPI Service Connection Issues

**Error**: `Failed to connect to OpenAPI service`

**Solution**:
1. Verify `baseUrl` is correct in config.json
2. Test endpoint directly: `curl https://api.example.com`
3. Check network connectivity
4. Verify Azure OAuth credentials (if using)

#### Memory Issues

**Error**: `MemoryError` or high memory usage

**Solution**:
1. Increase Docker memory limit
2. Review and optimize OpenAPI specs (reduce endpoints)
3. Use method/tag filters to limit exposed tools
4. Monitor with `docker stats`

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export FASTMCP_LOG_LEVEL=DEBUG
python src/main.py
```

Debug output includes:
- Configuration loading details
- Environment variable resolution
- Proxy mounting information
- Request/response details
- Authentication flow
- Error stack traces

### Getting Help

1. **Check logs**: Always check server logs first
2. **Review config**: Validate JSON configuration files
3. **Test endpoints**: Use curl to test health and MCP endpoints
4. **GitHub Issues**: Report bugs or request features
5. **Documentation**: Review MCP specification and FastMCP docs

## 📚 Additional Resources

### Related Projects

- [FastMCP](https://github.com/jlowin/fastmcp) - FastMCP framework
- [MCP Specification](https://spec.modelcontextprotocol.io/) - Model Context Protocol spec
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) - MCP debugging tool

### Documentation

- [FastMCP Documentation](https://fastmcp.com)
- [Starlette Documentation](https://www.starlette.io/)
- [uvicorn Documentation](https://www.uvicorn.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Community

- [GitHub Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)
- [Issue Tracker](https://github.com/baoduy/drunk-mcp-proxy/issues)

## 📝 Requirements

- **Python**: 3.11 or higher
- **FastMCP**: 3.0.0 or later
- **Dependencies**: See `requirements.txt`

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add docstrings to all functions and classes
- Write tests for new features
- Update documentation as needed
- Keep commits atomic and well-described

## 🙏 Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) for the excellent MCP framework
- [Starlette](https://www.starlette.io/) for the ASGI framework
- [Model Context Protocol](https://modelcontextprotocol.io/) team for the protocol specification
- All contributors and users of this project

## 📞 Support

For issues, questions, or contributions:
- **GitHub Issues**: [https://github.com/baoduy/drunk-mcp-proxy/issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
- **GitHub Discussions**: [https://github.com/baoduy/drunk-mcp-proxy/discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)
- **Repository**: [https://github.com/baoduy/drunk-mcp-proxy](https://github.com/baoduy/drunk-mcp-proxy)

---

**Made with ❤️ for the MCP community**
