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
- [Feature 1: Proxy MCP Management for MCP Services](#-feature-1-proxy-mcp-management-for-mcp-services)
- [Feature 2: Proxy MCP Management for OpenAPI Services](#-feature-2-proxy-mcp-management-for-openapi-services)
- [Feature 3: Authentication Configuration (Pass-Through Token Focus)](#-feature-3-authentication-configuration-pass-through-token-focus)
- [Configuration Reference](#-configuration-reference)
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

drunk-mcp-proxy is a sophisticated proxy server that unifies multiple MCP and OpenAPI services behind a single endpoint. The architecture is designed for scalability, flexibility, and enterprise-grade authentication.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP Client (e.g., Claude Desktop)             │
│                    HTTP/SSE Request with Authorization Header           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 v
┌─────────────────────────────────────────────────────────────────────────┐
│                        drunk-mcp-proxy Server                           │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │              Starlette ASGI Application                         │    │
│  │  ┌──────────────────────────────────────────────────────┐     │    │
│  │  │           CORS Middleware (Optional)                  │     │    │
│  │  │     - Allow Origins, Methods, Headers                 │     │    │
│  │  │     - Configured via ENV variables                    │     │    │
│  │  └──────────────────────────────────────────────────────┘     │    │
│  │  ┌──────────────────────────────────────────────────────┐     │    │
│  │  │            Health Check Endpoint                      │     │    │
│  │  │              GET /health                              │     │    │
│  │  └──────────────────────────────────────────────────────┘     │    │
│  │  ┌──────────────────────────────────────────────────────┐     │    │
│  │  │           Root MCP Server (/)                         │     │    │
│  │  │         POST /mcp (Mounted Services)                  │     │    │
│  │  │    ┌──────────────────────────────────┐              │     │    │
│  │  │    │  FastMCP Auth Provider           │              │     │    │
│  │  │    │  (JWT, GitHub, Google, etc.)     │              │     │    │
│  │  │    └──────────────────────────────────┘              │     │    │
│  │  └──────────────────────────────────────────────────────┘     │    │
│  │  ┌──────────────────────────────────────────────────────┐     │    │
│  │  │      Namespaced MCP Services                          │     │    │
│  │  │      POST /stock/mcp                                  │     │    │
│  │  │      POST /wiki/mcp                                   │     │    │
│  │  │      POST /deepsea/mcp (OpenAPI)                      │     │    │
│  │  └──────────────────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────┬──────────────────────────────┘
                       │                  │
        ┌──────────────┼──────────────────┼────────────────┐
        v              v                  v                v
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  MCP Server  │ │  MCP Server  │ │   OpenAPI    │ │   OpenAPI    │
│   (HTTP)     │ │   (stdio)    │ │   Service    │ │   Service    │
│              │ │              │ │  + Azure     │ │  + Pass-     │
│  Stock API   │ │  Wiki Docs   │ │    OAuth     │ │    Through   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### Component Architecture

```
src/
├── main.py                          # Application entry point
├── app/
│   ├── server.py                    # MCPProxyServer - Server orchestration
│   ├── starlette_app.py             # StarletteApp - ASGI app factory
│   ├── lifespan.py                  # Lifecycle management for MCP apps
│   ├── auth_provider.py             # GlobalAuthProvider - Auth factory
│   ├── cache_provider.py            # OAuth token caching
│   └── middleware/
│       └── cros_middleware.py       # CORS middleware configuration
├── proxies/
│   ├── config_provider.py           # ProxyConfigProvider - Config loader
│   ├── static_mcp_provider.py       # StaticMcpProvider - Base provider
│   ├── mcp_proxy_provider.py        # McpProxyProvider - MCP proxy creator
│   └── openapi_mcp_provider.py      # OpenApiMcpProvider - OpenAPI converter
├── auth_providers/
│   ├── azure_oauth.py               # AzureOauth - Azure AD OAuth2 flow
│   └── auth_pass_through.py         # AuthPassThrough - Token forwarding
└── tools/
    ├── spec_config.py               # Configuration models
    ├── auth_config.py               # Auth configuration models
    ├── env.py                       # Environment variable loading
    └── env_resolver.py              # Environment variable substitution
```

---

## 🎯 Feature 1: Proxy MCP Management for MCP Services

### Overview

drunk-mcp-proxy provides comprehensive management for proxying MCP (Model Context Protocol) services. It aggregates multiple MCP servers into a unified interface, with support for namespacing to prevent tool name conflicts.

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                    MCP Service Proxy Architecture                      │
└────────────────────────────────────────────────────────────────────────┘

Configuration Loading:
┌──────────────┐         ┌──────────────────┐         ┌───────────────┐
│ config.json  │────────>│ ProxyConfig      │────────>│ SpecConfig    │
│              │         │ Provider         │         │ Instances     │
│ - MCP specs  │         │                  │         │               │
│ - Paths      │         │ Loads & validates│         │ Per-service   │
└──────────────┘         └──────────────────┘         └───────────────┘
                                  |
                                  v
                         ┌────────────────────┐
                         │ Filter by spec_type│
                         │ = "mcp"            │
                         └────────────────────┘
                                  |
                                  v
Proxy Creation:
┌──────────────────────────────────────────────────────────────────────┐
│ For each MCP config:                                                 │
│  1. Load MCP spec file (mcp.json, stock.mcp.json, etc.)             │
│  2. Create FastMCP proxy via create_proxy(spec_data, name)           │
│  3. Handle special case for root path ("/")                          │
│  4. Apply authentication provider if configured                      │
│  5. Mount at appropriate HTTP path                                   │
└──────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
FastMCP Server Structure:
┌────────────────────────────────────────────────────────────────────┐
│                     Root MCP Server (path="/")                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ FastMCP("mcp-proxy-server", version="1.0.0")                 │  │
│  │  - Auth: GlobalAuthProvider (JWT, GitHub, etc.)              │  │
│  │  - Mounted Proxies:                                           │  │
│  │    ├── Wiki MCP Proxy (from wiki.mcp.json)                   │  │
│  │    ├── Stock MCP Proxy (from stock.mcp.json)                 │  │
│  │    └── ... (other root-mounted services)                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  HTTP Endpoint: POST /mcp                                           │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│              Namespaced MCP Server (path="/stock")                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ FastMCP("mcp-proxy-server-/stock", version="1.0.0")          │  │
│  │  - Auth: GlobalAuthProvider or None                          │  │
│  │  - Proxy: create_proxy(stock.mcp.json)                       │  │
│  │  - Tools: stock_price, stock_history, etc.                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  HTTP Endpoint: POST /stock/mcp                                     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│               Namespaced MCP Server (path="/wiki")                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ FastMCP("mcp-proxy-server-/wiki", version="1.0.0")           │  │
│  │  - Auth: GlobalAuthProvider or None                          │  │
│  │  - Proxy: create_proxy(wiki.mcp.json)                        │  │
│  │  - Tools: search_wiki, get_article, etc.                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  HTTP Endpoint: POST /wiki/mcp                                      │
└────────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
Step 1: Client Request
┌──────────────────────────────────────────────────────────────┐
│ MCP Client (e.g., Claude Desktop)                            │
│                                                              │
│ POST /stock/mcp                                              │
│ Headers:                                                     │
│   Authorization: Bearer <jwt-token>                          │
│ Body:                                                        │
│   {"jsonrpc": "2.0", "method": "tools/list", "id": 1}       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 2: Starlette Routing & Middleware
┌──────────────────────────────────────────────────────────────┐
│ Starlette Application                                         │
│  1. CORS Middleware: Validate origin, set CORS headers       │
│  2. Route to: /stock/mcp endpoint                            │
│  3. Invoke: FastMCP http_app for "/stock" service            │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: FastMCP Authentication
┌──────────────────────────────────────────────────────────────┐
│ FastMCP Auth Provider (if configured)                        │
│  1. Extract Authorization header                             │
│  2. Validate JWT token against JWKS_URI                      │
│  3. Extract user context (claims, scopes)                    │
│  4. Store in MCP context for downstream use                  │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: MCP Proxy Forwarding
┌──────────────────────────────────────────────────────────────┐
│ McpProxyProvider for "/stock"                                │
│  1. create_proxy(stock.mcp.json) has MCP spec:               │
│     {                                                         │
│       "mcpServers": {                                         │
│         "stock": {                                            │
│           "url": "http://stock-service.internal:8080/mcp",   │
│           "transport": "http"                                 │
│         }                                                     │
│       }                                                       │
│     }                                                         │
│  2. FastMCP routes request to backend via HTTP               │
│  3. Backend MCP server processes "tools/list" request        │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 5: Backend MCP Server
┌──────────────────────────────────────────────────────────────┐
│ Stock MCP Server (http://stock-service.internal:8080/mcp)    │
│  1. Receives JSON-RPC request                                │
│  2. Returns available tools:                                 │
│     {                                                         │
│       "tools": [                                              │
│         {"name": "stock_price", "description": "..."},        │
│         {"name": "stock_history", "description": "..."}       │
│       ]                                                       │
│     }                                                         │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 6: Response to Client
┌──────────────────────────────────────────────────────────────┐
│ Response aggregated and returned to MCP client               │
│  - Tools from all mounted services (if root path)            │
│  - Tools from specific service (if namespaced path)          │
└──────────────────────────────────────────────────────────────┘
```

### Configuration Example

**config.json**:
```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null
  },
  {
    "path": "/stock",
    "spec_file": "mcp/stock.mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "tags": ["finance", "internal"]
  },
  {
    "path": "/wiki",
    "spec_file": "mcp/wiki.mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "tags": ["documentation", "internal"]
  }
]
```

**mcp/stock.mcp.json**:
```json
{
  "mcpServers": {
    "stock": {
      "url": "http://stock-service.internal:8080/mcp",
      "transport": "http"
    }
  }
}
```

**mcp/wiki.mcp.json**:
```json
{
  "mcpServers": {
    "wiki": {
      "url": "https://mcp.deepwiki.com/mcp",
      "transport": "http"
    }
  }
}
```

### Key Features

1. **Root Path Aggregation (`path="/"`)**: 
   - Creates a single FastMCP server that mounts all root-path MCP services
   - Client can access all tools via single `/mcp` endpoint
   - Prevents tool name conflicts via namespacing

2. **Namespaced Services (`path="/stock"`, `path="/wiki"`)**: 
   - Each service gets its own FastMCP server instance
   - Isolated at HTTP endpoint level (`/stock/mcp`, `/wiki/mcp`)
   - Independent authentication and lifecycle

3. **Transport Support**:
   - HTTP/SSE: Direct HTTP communication to backend MCP servers
   - stdio: Local process execution (FastMCP handles process management)

4. **Authentication Integration**:
   - GlobalAuthProvider applies to root MCP server
   - Validates client tokens before proxying to backend
   - Supports JWT, OAuth (GitHub, Google, Discord), and custom providers

5. **Dynamic Configuration**:
   - JSON-based configuration with hot-reloading capability
   - Environment variable substitution (`$VAR_NAME`, `${VAR_NAME}`)
   - Schema validation against JSON schemas

### Code Implementation

**McpProxyProvider (src/proxies/mcp_proxy_provider.py)**:
```python
class McpProxyProvider(StaticMcpProvider):
    """Provider class for creating FastMCP instances from MCP configurations."""

    def create_proxy(self) -> FastMCP:
        """Create and return a FastMCP instance based on the MCP configuration."""
        if self.config.spec_data is None:
            raise ValueError(f"spec_data is required for MCP config '{self.config.path}'")

        # Create proxy from MCP spec
        proxy = create_proxy(self.config.spec_data, name=self.config.path)
        
        # Special handling for root path
        if self.config.path == "/" and self.root_mcp is not None:
            self.root_mcp.mount(proxy)
            self.mcp = self.root_mcp
            self.mcp.auth = self._get_global_auth_provider()
            return self.mcp
        
        # Create namespaced FastMCP server
        self.mcp = FastMCP(
            f"{SERVER_NAME}-{self.config.path}",
            version=SERVER_VERSION,
        )
        self.mcp.mount(proxy)
        return self.mcp
```

---

## 🌐 Feature 2: Proxy MCP Management for OpenAPI Services

### Overview

drunk-mcp-proxy can automatically convert OpenAPI 3.0 specifications into MCP tools, enabling seamless integration of RESTful APIs into the MCP ecosystem. This feature includes advanced capabilities like route filtering, Azure OAuth2 authentication, and pass-through token authentication.

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                 OpenAPI to MCP Conversion Architecture                 │
└────────────────────────────────────────────────────────────────────────┘

Configuration Loading:
┌──────────────┐         ┌──────────────────┐         ┌───────────────┐
│ config.json  │────────>│ ProxyConfig      │────────>│ SpecConfig    │
│              │         │ Provider         │         │ (OpenAPI)     │
│ - spec_type: │         │                  │         │               │
│   "openapi"  │         │ Filters by type  │         │ - spec_file   │
│ - base_url   │         │                  │         │ - base_url    │
│ - filters    │         │                  │         │ - auth        │
│ - auth       │         │                  │         │ - filters     │
└──────────────┘         └──────────────────┘         └───────────────┘
                                  |
                                  v
OpenAPI Spec Loading:
┌─────────────────────────────────────────────────────────────────────┐
│ Load OpenAPI 3.0 Spec (deepsea.openapi.json)                        │
│  {                                                                   │
│    "openapi": "3.0.0",                                               │
│    "info": { "title": "DeepSea API", "version": "1.0.0" },          │
│    "paths": {                                                        │
│      "/currency-pairs": {                                            │
│        "get": {                                                      │
│          "operationId": "getCurrencyPairs",                          │
│          "tags": ["CurrencyPairs"],                                  │
│          "responses": { ... }                                        │
│        },                                                            │
│        "post": { ... }                                               │
│      }                                                               │
│    }                                                                 │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
Route Filtering (Optional):
┌─────────────────────────────────────────────────────────────────────┐
│ Apply Filters from Config:                                          │
│  - Methods: ["GET", "POST", "PUT"] (exclude DELETE, PATCH)          │
│  - Tags: ["CurrencyPairs"] (only include tagged endpoints)          │
│                                                                      │
│ custom_route_mapper():                                               │
│   if route.method not in filters.methods:                           │
│     return MCPType.EXCLUDE                                           │
│   if route.tags not in filters.tags:                                │
│     return MCPType.EXCLUDE                                           │
│   return mcp_type                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
HTTP Client Creation:
┌─────────────────────────────────────────────────────────────────────┐
│ Create httpx.AsyncClient with Authentication:                       │
│                                                                      │
│ Option 1: Azure OAuth2 (Client Credentials Flow)                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ AzureOauth(                                                    │ │
│  │   client_id="...",                                             │ │
│  │   client_secret="...",                                         │ │
│  │   token_url="https://login.microsoftonline.com/.../token",    │ │
│  │   scope="api://.../.default"                                   │ │
│  │ )                                                              │ │
│  │ - Automatic token fetching & caching                          │ │
│  │ - Token expiry detection & refresh                            │ │
│  │ - Adds "Authorization: Bearer <token>" to requests            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ Option 2: Pass-Through Authentication                               │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ AuthPassThrough()                                              │ │
│  │ - Extracts token from MCP request context                     │ │
│  │ - Forwards token to backend API                               │ │
│  │ - No token management/caching                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ Option 3: Static Token                                              │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ headers["Authorization"] = config.auth.auth_token             │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
FastMCP Conversion:
┌─────────────────────────────────────────────────────────────────────┐
│ FastMCP.from_openapi(                                                │
│   name="mcp-proxy-server-/deepsea",                                  │
│   openapi_spec=spec_data,                                            │
│   client=httpx_client,                                               │
│   route_map_fn=custom_route_mapper,                                  │
│   tags=["finance", "api"]                                            │
│ )                                                                    │
│                                                                      │
│ Result: FastMCP server with tools for each OpenAPI endpoint:        │
│  - Tool name: operationId or auto-generated                          │
│  - Tool description: from OpenAPI operation summary/description      │
│  - Tool parameters: from OpenAPI request body & query parameters     │
│  - Tool execution: HTTP request to backend via httpx client          │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
MCP Tool Mapping:
┌─────────────────────────────────────────────────────────────────────┐
│ OpenAPI Endpoint → MCP Tool                                          │
│                                                                      │
│ GET /currency-pairs?base=USD                                         │
│   → MCP Tool: getCurrencyPairs                                       │
│      Parameters: { "base": "USD" }                                   │
│      Description: "Get list of currency pairs"                      │
│                                                                      │
│ POST /currency-pairs { "base": "USD", "quote": "EUR" }              │
│   → MCP Tool: createCurrencyPair                                     │
│      Parameters: { "base": "USD", "quote": "EUR" }                   │
│      Description: "Create a new currency pair"                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Request Flow with Authentication

```
Step 1: Client MCP Request
┌──────────────────────────────────────────────────────────────┐
│ MCP Client (e.g., Claude Desktop)                            │
│                                                              │
│ POST /deepsea/mcp                                            │
│ Headers:                                                     │
│   Authorization: Bearer <user-jwt-token>                     │
│ Body:                                                        │
│   {                                                          │
│     "jsonrpc": "2.0",                                        │
│     "method": "tools/call",                                  │
│     "params": {                                              │
│       "name": "getCurrencyPairs",                            │
│       "arguments": { "base": "USD" }                         │
│     },                                                       │
│     "id": 1                                                  │
│   }                                                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 2: FastMCP Authentication (MCP Level)
┌──────────────────────────────────────────────────────────────┐
│ FastMCP Auth Provider validates client                       │
│  1. Extract Authorization header: Bearer <user-jwt-token>    │
│  2. Validate JWT token                                       │
│  3. Store AccessToken in MCP context                         │
│     → Available via get_access_token()                       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: Tool Execution (OpenAPI Call)
┌──────────────────────────────────────────────────────────────┐
│ FastMCP invokes tool: getCurrencyPairs                       │
│  1. Construct HTTP request: GET /currency-pairs?base=USD     │
│  2. httpx.AsyncClient uses configured auth:                  │
│                                                              │
│     SCENARIO A: Pass-Through Auth                            │
│     ┌────────────────────────────────────────────────┐      │
│     │ AuthPassThrough.async_auth_flow()              │      │
│     │  1. Call get_access_token() from MCP context   │      │
│     │  2. Extract user-jwt-token                     │      │
│     │  3. Add to request:                            │      │
│     │     Authorization: Bearer <user-jwt-token>     │      │
│     └────────────────────────────────────────────────┘      │
│                                                              │
│     SCENARIO B: Azure OAuth                                  │
│     ┌────────────────────────────────────────────────┐      │
│     │ AzureOauth.async_auth_flow()                   │      │
│     │  1. Check cached token                         │      │
│     │  2. If expired, fetch new token:               │      │
│     │     POST to Azure token_url with               │      │
│     │     client credentials                         │      │
│     │  3. Cache token (in-memory + storage)          │      │
│     │  4. Add to request:                            │      │
│     │     Authorization: Bearer <azure-token>        │      │
│     └────────────────────────────────────────────────┘      │
│                                                              │
│  3. Send HTTP request to backend API                        │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: Backend OpenAPI Service
┌──────────────────────────────────────────────────────────────┐
│ DeepSea API (http://host.docker.internal:5000)               │
│                                                              │
│ GET /currency-pairs?base=USD                                 │
│ Headers:                                                     │
│   Authorization: Bearer <token>  ← From auth flow            │
│                                                              │
│ Response:                                                    │
│   {                                                          │
│     "pairs": [                                               │
│       { "base": "USD", "quote": "EUR", "rate": 0.85 },       │
│       { "base": "USD", "quote": "GBP", "rate": 0.73 }        │
│     ]                                                        │
│   }                                                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 5: Response to MCP Client
┌──────────────────────────────────────────────────────────────┐
│ FastMCP wraps response in MCP format                         │
│   {                                                          │
│     "jsonrpc": "2.0",                                        │
│     "id": 1,                                                 │
│     "result": {                                              │
│       "content": [                                           │
│         {                                                    │
│           "type": "text",                                    │
│           "text": "{\"pairs\": [...]}"                       │
│         }                                                    │
│       ]                                                      │
│     }                                                        │
│   }                                                          │
└──────────────────────────────────────────────────────────────┘
```

### Configuration Example

**config.json**:
```json
[
  {
    "path": "/deepsea",
    "spec_file": "openapi/deepsea.openapi.json",
    "spec_type": "openapi",
    "base_url": "http://host.docker.internal:5000",
    "filters": {
      "methods": ["GET", "POST", "PUT"],
      "tags": ["CurrencyPairs"]
    },
    "auth": {
      "pass_through": true,
      "azure": {
        "client_id": "$AZURE_CLIENT_ID",
        "client_secret": "$AZURE_CLIENT_SECRET",
        "tenant_id": "$AZURE_TENANT_ID",
        "issuer": "https://sts.windows.net/$AZURE_TENANT_ID/",
        "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
        "scopes": ["api://$AZURE_CLIENT_ID/.default"]
      }
    }
  }
]
```

### Key Features

1. **Automatic Tool Generation**:
   - Each OpenAPI endpoint becomes an MCP tool
   - Tool names derived from `operationId` or auto-generated
   - Tool descriptions from OpenAPI `summary` or `description`
   - Parameters automatically mapped from query params, path params, and request body

2. **Route Filtering**:
   - **By HTTP Method**: Include only specific methods (GET, POST, PUT, DELETE, PATCH)
   - **By Tags**: Include only endpoints with specific tags
   - Reduces tool clutter and improves security

3. **Flexible Authentication**:
   - **Pass-Through**: Forward client token to backend (zero configuration)
   - **Azure OAuth2**: Automatic client credentials flow with token caching
   - **Static Token**: Use a pre-configured API key
   - **No Auth**: Public APIs

4. **HTTP Client Management**:
   - Automatic base URL handling
   - Request/response serialization
   - Error handling and retries
   - Connection pooling via httpx

### Code Implementation

**OpenApiMcpProvider (src/proxies/openapi_mcp_provider.py)**:
```python
class OpenApiMcpProvider(StaticMcpProvider):
    """Provider class for creating FastMCP instances from OpenAPI specs."""

    def custom_route_mapper(self, route: HTTPRoute, mcp_type: MCPType) -> MCPType | None:
        """Filter routes based on configured filters."""
        if self.config.filters is not None:
            if self.config.filters.methods:
                if route.method not in self.config.filters.methods:
                    return MCPType.EXCLUDE
            if self.config.filters.tags:
                if not any(tag in route.tags for tag in self.config.filters.tags):
                    return MCPType.EXCLUDE
        return mcp_type

    def create_client(self) -> httpx.AsyncClient:
        """Return an appropriate HTTP client for the configured service."""
        if not self.config.base_url:
            raise ValueError("base_url is required for OpenAPI clients")

        auth: Auth | None = None
        headers: dict[str, str] = {}
        
        if self.config.auth and self.config.auth.azure:
            # Azure OAuth2 client credentials flow
            auth = self._create_client_auth(self.config.auth.azure)
        elif self.config.auth and self.config.auth.auth_token:
            # Static token
            headers["Authorization"] = self.config.auth.auth_token

        return httpx.AsyncClient(base_url=self.config.base_url, auth=auth, headers=headers)

    def create_proxy(self) -> FastMCP:
        """Create and return a FastMCP instance based on the loaded configurations."""
        client = self.create_client()
        
        self.mcp = FastMCP.from_openapi(
            name=f"{SERVER_NAME}-{self.config.path}",
            openapi_spec=self.config.spec_data,
            client=client,
            route_map_fn=self.custom_route_mapper,
            tags=self.config.tags
        )
        
        return self.mcp
```

---

## 🔐 Feature 3: Authentication Configuration (Pass-Through Token Focus)

### Overview

drunk-mcp-proxy provides a sophisticated multi-layer authentication system that operates at both the MCP protocol level (client authentication) and the backend service level (service authentication). The pass-through authentication feature is particularly powerful, enabling zero-configuration token forwarding from MCP clients to backend APIs.

### Authentication Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Multi-Layer Authentication Architecture              │
└────────────────────────────────────────────────────────────────────────┘

Layer 1: MCP Client Authentication (Proxy Level)
┌─────────────────────────────────────────────────────────────────────┐
│ GlobalAuthProvider (Configured via auth.json)                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Supported Providers:                                           │ │
│  │  - JWT: Token validation via JWKS_URI                          │ │
│  │  - GitHub OAuth: GitHub authentication                         │ │
│  │  - Google OAuth: Google authentication                         │ │
│  │  - Discord OAuth: Discord authentication                       │ │
│  │  - WorkOS/AuthKit: Enterprise SSO                              │ │
│  │  - Descope, Supabase, Scalekit: Other identity providers      │ │
│  │  - Custom: Any FastMCP AuthProvider subclass                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ Configuration: data/auth.json                                        │
│  {                                                                   │
│    "enabled": true,                                                  │
│    "default_provider": "jwt",                                        │
│    "jwt": {                                                          │
│      "jwks_uri": "https://auth.example.com/.well-known/jwks.json",  │
│      "issuer": "https://auth.example.com/",                          │
│      "audience": "mcp-proxy-api"                                     │
│    }                                                                 │
│  }                                                                   │
│                                                                      │
│ Result: AccessToken stored in MCP context                           │
│  - Available via get_access_token()                                  │
│  - Contains: token, claims, expiry                                   │
└─────────────────────────────────────────────────────────────────────┘

Layer 2: Backend Service Authentication (Service Level)
┌─────────────────────────────────────────────────────────────────────┐
│ Per-Service Authentication (Configured in config.json)              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Option 1: Pass-Through Authentication                          │ │
│  │  {                                                             │ │
│  │    "auth": {                                                   │ │
│  │      "pass_through": true                                      │ │
│  │    }                                                           │ │
│  │  }                                                             │ │
│  │  → AuthPassThrough: Forwards MCP client token to backend      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Option 2: Azure OAuth2 Client Credentials                     │ │
│  │  {                                                             │ │
│  │    "auth": {                                                   │ │
│  │      "azure": {                                                │ │
│  │        "client_id": "$AZURE_CLIENT_ID",                        │ │
│  │        "client_secret": "$AZURE_CLIENT_SECRET",                │ │
│  │        "token_url": "https://login.../oauth2/v2.0/token",      │ │
│  │        "scopes": ["api://.../.default"]                        │ │
│  │      }                                                          │ │
│  │    }                                                           │ │
│  │  }                                                             │ │
│  │  → AzureOauth: Fetches service token via client credentials   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Option 3: Static API Token                                     │ │
│  │  {                                                             │ │
│  │    "auth": {                                                   │ │
│  │      "auth_token": "Bearer sk-1234567890"                      │ │
│  │    }                                                           │ │
│  │  }                                                             │ │
│  │  → Static header added to all requests                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Pass-Through Authentication Deep Dive

#### Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│              Pass-Through Authentication Flow (Detailed)               │
└────────────────────────────────────────────────────────────────────────┘

Step 1: Client Request with Token
┌──────────────────────────────────────────────────────────────┐
│ MCP Client (e.g., Claude Desktop, Custom App)                │
│                                                              │
│ POST /deepsea/mcp                                            │
│ Headers:                                                     │
│   Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...     │
│   Content-Type: application/json                            │
│ Body:                                                        │
│   {                                                          │
│     "jsonrpc": "2.0",                                        │
│     "method": "tools/call",                                  │
│     "params": {                                              │
│       "name": "getCurrencyPairs",                            │
│       "arguments": { "base": "USD" }                         │
│     },                                                       │
│     "id": 1                                                  │
│   }                                                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 2: MCP Protocol Layer - Token Extraction
┌──────────────────────────────────────────────────────────────┐
│ FastMCP Server (Mounted at /deepsea)                         │
│                                                              │
│ 1. FastMCP Auth Provider (if configured):                   │
│    - Validates Authorization header                          │
│    - Extracts JWT claims                                     │
│    - Stores AccessToken in MCP context                       │
│                                                              │
│ 2. AccessToken Structure:                                    │
│    class AccessToken:                                        │
│      token: str  ← Original JWT string                       │
│      claims: dict ← Decoded JWT claims (user_id, etc.)       │
│      expires_at: datetime                                    │
│                                                              │
│ 3. Context Storage:                                          │
│    MCP request context stores AccessToken                    │
│    Available to all tool executions via dependency injection │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: Tool Execution - Pass-Through Auth Flow
┌──────────────────────────────────────────────────────────────┐
│ OpenAPI Tool Execution (getCurrencyPairs)                    │
│                                                              │
│ 1. FastMCP prepares HTTP request via httpx.AsyncClient      │
│    GET /currency-pairs?base=USD                              │
│                                                              │
│ 2. httpx client has auth=AuthPassThrough()                   │
│    → Triggers async_auth_flow()                              │
│                                                              │
│ 3. AuthPassThrough.async_auth_flow():                        │
│    ┌────────────────────────────────────────────────────┐   │
│    │ from fastmcp.server.dependencies import (          │   │
│    │     get_access_token                               │   │
│    │ )                                                  │   │
│    │                                                    │   │
│    │ def async_auth_flow(self, request: httpx.Request):│   │
│    │     # Get token from MCP context                  │   │
│    │     token = get_access_token()                     │   │
│    │                                                    │   │
│    │     if token:                                      │   │
│    │         # Forward original client token           │   │
│    │         request.headers["Authorization"] = (      │   │
│    │             f"Bearer {token.token}"                │   │
│    │         )                                          │   │
│    │     else:                                          │   │
│    │         logger.warning("No access token available")│   │
│    │                                                    │   │
│    │     yield request                                  │   │
│    └────────────────────────────────────────────────────┘   │
│                                                              │
│ 4. Modified request:                                         │
│    GET /currency-pairs?base=USD                              │
│    Headers:                                                  │
│      Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...  │
│      ↑ Same token from original MCP client request          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: Backend API Request
┌──────────────────────────────────────────────────────────────┐
│ Backend OpenAPI Service (http://host.docker.internal:5000)   │
│                                                              │
│ Receives:                                                    │
│   GET /currency-pairs?base=USD                               │
│   Headers:                                                   │
│     Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...   │
│                                                              │
│ Backend validates token:                                     │
│   - Validates JWT signature                                  │
│   - Checks issuer, audience, expiry                          │
│   - Extracts user identity (user_id, email, roles)           │
│   - Enforces authorization policies                          │
│                                                              │
│ Returns response:                                            │
│   200 OK                                                     │
│   { "pairs": [...] }                                         │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 5: Response Returned to Client
┌──────────────────────────────────────────────────────────────┐
│ Response flows back through FastMCP to MCP client            │
│   {                                                          │
│     "jsonrpc": "2.0",                                        │
│     "id": 1,                                                 │
│     "result": {                                              │
│       "content": [                                           │
│         { "type": "text", "text": "{\"pairs\": [...]}" }     │
│       ]                                                      │
│     }                                                        │
│   }                                                          │
└──────────────────────────────────────────────────────────────┘
```

#### Key Benefits

1. **Zero Configuration**:
   - No need to manage service-specific credentials
   - No token exchange or translation required
   - Works with any backend that accepts JWT tokens

2. **User Context Preservation**:
   - Backend receives original user token
   - Backend can enforce user-specific policies
   - Audit logs show actual user, not service account

3. **Security**:
   - No credential storage in config files
   - No shared service accounts
   - Token never leaves secure channel (HTTPS)

4. **Flexibility**:
   - Works with any JWT issuer
   - Compatible with OAuth2, OIDC, custom auth systems
   - Backend can use token for additional API calls

#### Code Implementation

**AuthPassThrough (src/auth_providers/auth_pass_through.py)**:
```python
import httpx
import typing
import logging
from fastmcp.server.dependencies import get_access_token
from mcp.server.auth.provider import AccessToken

logger = logging.getLogger(__name__)

class AuthPassThrough(httpx.Auth):
    """
    Pass-through authentication for httpx clients.
    
    Extracts the access token from the MCP request context
    and forwards it to the backend service.
    """
    
    def _get_token(self) -> AccessToken | None:
        """Get token from MCP context."""
        token = get_access_token()
        if token:
            logger.info(f"Access token: {token}")
        else:
            logger.warning("No access token available")
        return token
    
    def auth_flow(
        self, request: httpx.Request
    ) -> typing.Generator[httpx.Request, httpx.Response, None]:
        """Sync auth flow for pass-through authentication."""
        token = self._get_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token.token}"
        yield request

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> typing.AsyncGenerator[httpx.Request, httpx.Response]:
        """Async auth flow for pass-through authentication."""
        token = self._get_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token.token}"
        yield request
```

#### Configuration Examples

**Example 1: Pass-Through Only**
```json
{
  "path": "/api",
  "spec_file": "openapi/api.openapi.json",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "pass_through": true
  }
}
```

**Example 2: Pass-Through with Fallback to Azure OAuth**
```json
{
  "path": "/api",
  "spec_file": "openapi/api.openapi.json",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "pass_through": true,
    "azure": {
      "client_id": "$AZURE_CLIENT_ID",
      "client_secret": "$AZURE_CLIENT_SECRET",
      "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
      "scopes": ["api://example-api/.default"]
    }
  }
}
```
*Note: When both are configured, pass-through takes precedence if available.*

**Example 3: MCP Client Auth Configuration (auth.json)**
```json
{
  "enabled": true,
  "default_provider": "jwt",
  "jwt": {
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "issuer": "https://auth.example.com/",
    "audience": "mcp-proxy-api",
    "algorithms": ["RS256"]
  }
}
```

### Azure OAuth2 Client Credentials

For comparison, here's how Azure OAuth2 works (alternative to pass-through):

```
┌────────────────────────────────────────────────────────────────────────┐
│              Azure OAuth2 Client Credentials Flow                      │
└────────────────────────────────────────────────────────────────────────┘

Step 1: Initial Request
┌──────────────────────────────────────────────────────────────┐
│ httpx.AsyncClient makes first API request                    │
│ → Triggers AzureOauth.async_auth_flow()                       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 2: Token Fetch (if not cached)
┌──────────────────────────────────────────────────────────────┐
│ POST https://login.microsoftonline.com/TENANT/oauth2/v2.0/token│
│ Headers:                                                      │
│   Content-Type: application/x-www-form-urlencoded            │
│ Body:                                                        │
│   grant_type=client_credentials                              │
│   client_id=YOUR_CLIENT_ID                                   │
│   client_secret=YOUR_CLIENT_SECRET                           │
│   scope=api://YOUR_CLIENT_ID/.default                        │
│                                                              │
│ Response:                                                    │
│   {                                                          │
│     "token_type": "Bearer",                                  │
│     "expires_in": 3599,                                      │
│     "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJS..."       │
│   }                                                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: Token Caching
┌──────────────────────────────────────────────────────────────┐
│ AzureOauth stores token:                                     │
│  - In-memory cache (immediate reuse)                         │
│  - Persistent storage (optional, survives restarts)          │
│  - Expiry tracking (auto-refresh before expiration)          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: Add Token to Request
┌──────────────────────────────────────────────────────────────┐
│ request.headers["Authorization"] = f"Bearer {azure_token}"   │
│ → Backend receives service account token, NOT user token    │
└──────────────────────────────────────────────────────────────┘
```

**Key Difference**: Azure OAuth uses **service account** credentials, while pass-through uses **user credentials**.

### Authentication Decision Matrix

| Scenario | Recommended Auth | Reason |
|----------|------------------|---------|
| User-specific actions (e.g., CRUD on user data) | **Pass-Through** | Backend needs user identity for authorization |
| Service-to-service (e.g., read shared resources) | **Azure OAuth** | Service account sufficient, better for caching |
| Public API (no auth) | **None** | No authentication required |
| API Key based | **Static Token** | Simple, no OAuth overhead |
| Multi-tenant with user context | **Pass-Through** | Each user needs their own token |
| High-volume background jobs | **Azure OAuth** | Minimize token validations, better performance |

### Environment Variables for Authentication

**MCP Client Authentication (Global)**:
```bash
# JWT Provider
FASTMCP_SERVER_AUTH=jwt
JWKS_URI=https://auth.example.com/.well-known/jwks.json
ISSUER=https://auth.example.com/
AUDIENCE=mcp-proxy-api

# GitHub OAuth Provider
FASTMCP_SERVER_AUTH=github
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=your-github-client-id
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=your-github-client-secret

# Google OAuth Provider
FASTMCP_SERVER_AUTH=google
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=your-google-client-id
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**Backend Service Authentication (Per-Service in config.json)**:
```bash
# Azure OAuth
AZURE_CLIENT_ID=your-app-client-id
AZURE_CLIENT_SECRET=your-app-client-secret
AZURE_TENANT_ID=your-tenant-id
```

### Best Practices

1. **Use Pass-Through When**:
   - Backend enforces user-level permissions
   - Audit logs require user identity
   - Backend makes downstream API calls on behalf of user

2. **Use Azure OAuth When**:
   - Backend doesn't require user context
   - High request volume (token caching reduces overhead)
   - Service-to-service communication

3. **Security Considerations**:
   - Always use HTTPS in production
   - Rotate client secrets regularly (Azure OAuth)
   - Configure appropriate token expiry times
   - Validate tokens on backend (don't trust proxy alone)
   - Use minimum required scopes

4. **Monitoring**:
   - Log authentication failures
   - Track token refresh rates (Azure OAuth)
   - Monitor pass-through availability
   - Alert on expired credentials

---

## 📖 Configuration Reference

### Complete config.json Example

```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null
  },
  {
    "path": "/stock",
    "spec_file": "mcp/stock.mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "tags": ["finance", "internal"]
  },
  {
    "path": "/deepsea",
    "spec_file": "openapi/deepsea.openapi.json",
    "spec_type": "openapi",
    "base_url": "http://host.docker.internal:5000",
    "filters": {
      "methods": ["GET", "POST", "PUT"],
      "tags": ["CurrencyPairs", "Trading"]
    },
    "auth": {
      "pass_through": true,
      "azure": {
        "client_id": "$AZURE_CLIENT_ID",
        "client_secret": "$AZURE_CLIENT_SECRET",
        "tenant_id": "$AZURE_TENANT_ID",
        "issuer": "https://sts.windows.net/$AZURE_TENANT_ID/",
        "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
        "scopes": ["api://$AZURE_CLIENT_ID/.default"]
      }
    }
  }
]
```

### Complete auth.json Example

```json
{
  "enabled": true,
  "default_provider": "jwt",
  "jwt": {
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "issuer": "https://auth.example.com/",
    "audience": "mcp-proxy-api",
    "algorithms": ["RS256", "ES256"]
  },
  "github": {
    "client_id": "$GITHUB_CLIENT_ID",
    "client_secret": "$GITHUB_CLIENT_SECRET"
  },
  "azure": {
    "client_id": "$AZURE_AUTH_CLIENT_ID",
    "tenant_id": "$AZURE_AUTH_TENANT_ID",
    "client_secret": "$AZURE_AUTH_CLIENT_SECRET"
  }
}
```

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
