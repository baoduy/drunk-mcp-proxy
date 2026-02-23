# System Architecture

## Overview

drunk-mcp-proxy is a sophisticated proxy server built on the Model Context Protocol (MCP) that acts as a unified gateway for multiple backend MCP and OpenAPI services. The architecture is designed for scalability, flexibility, and enterprise-grade authentication.

## High-Level Architecture

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

## Architecture Layers

### Layer 1: Client Interface

**MCP Clients** (e.g., Claude Desktop, custom applications) connect via:
- **HTTP/HTTPS**: RESTful JSON-RPC over HTTP
- **SSE (Server-Sent Events)**: Real-time streaming
- **Streamable HTTP**: FastMCP's optimized transport

Clients send:
- **MCP Protocol**: JSON-RPC 2.0 requests
- **Authentication**: Bearer tokens in Authorization header
- **Context**: User context, preferences, metadata

### Layer 2: ASGI Application (Starlette)

**Starlette ASGI Application** provides:
- **HTTP Server**: High-performance async HTTP server
- **Routing**: URL-based routing to MCP services
- **Middleware**: CORS, logging, error handling
- **Health Checks**: `/health` endpoint for monitoring

**Key Components:**
- `StarletteApp`: ASGI application factory
- `MCPProxyServer`: Server orchestration and lifecycle
- `AppLifespanManager`: Startup/shutdown lifecycle

### Layer 3: Authentication & Authorization

**Two-Layer Authentication:**

#### Client → Proxy Authentication
- **FastMCP Auth Providers**: 14+ pluggable providers
- **Token Validation**: JWT, OAuth token verification
- **User Context**: Extract claims, scopes, user info
- **Session Management**: Optional session storage

#### Proxy → Backend Authentication
- **Pass-Through**: Forward client tokens to backends
- **Client Credentials**: Azure OAuth for service-to-service
- **Token Caching**: Encrypted token storage with Fernet
- **Hybrid**: Pass-through with fallback to client credentials

### Layer 4: MCP Protocol Layer

**FastMCP Framework** handles:
- **Protocol Serialization**: JSON-RPC encoding/decoding
- **Tool Registration**: Dynamic tool discovery
- **Resource Management**: MCP resource handling
- **Prompt Templates**: MCP prompt support

**Service Types:**
- **Root Service**: Aggregates tools from multiple backends
- **Namespaced Services**: Isolated service endpoints
- **Proxy Services**: Forward to backend MCP servers

### Layer 5: Service Providers

**MCP Service Providers:**
- **McpProxyProvider**: Creates proxies for MCP backends
- **OpenApiMcpProvider**: Converts OpenAPI → MCP tools
- **SkillsDirectoryProvider**: Loads skill-based resources

**Configuration:**
- **ProxyConfigProvider**: Loads `config.yaml`
- **SpecConfig**: Per-service configuration model
- **Environment Resolution**: `$VAR` substitution

### Layer 6: Backend Services

**Backend Types:**
- **MCP HTTP Servers**: Standard MCP over HTTP
- **MCP stdio Servers**: Command-line MCP servers
- **OpenAPI REST APIs**: REST APIs with OpenAPI specs
- **Custom Services**: Any HTTP-based service

## Component Architecture

### Source Code Structure

```
src/
├── main.py                          # Application entry point
├── app/
│   ├── server.py                    # MCPProxyServer - Server orchestration
│   ├── starlette_app.py             # StarletteApp - ASGI app factory
│   ├── lifespan.py                  # AppLifespanManager - Lifecycle management
│   ├── auth_provider.py             # GlobalAuthProvider - Auth factory
│   ├── cache_provider.py            # OAuth token caching
│   └── middleware/
│       └── cors_middleware.py       # CORS middleware configuration
├── proxies/
│   ├── config_provider.py           # ProxyConfigProvider - Config loader
│   ├── static_mcp_provider.py       # StaticMcpProvider - Base provider
│   ├── mcp_proxy_provider.py        # McpProxyProvider - MCP proxy creator
│   ├── openapi_mcp_provider.py      # OpenApiMcpProvider - OpenAPI converter
│   └── llm_proxies_provider.py      # LLMProxiesProvider - LLM routing
├── auth_providers/
│   ├── azure_oauth.py               # AzureOauth - Azure AD OAuth2 flow
│   └── auth_pass_through.py         # AuthPassThrough - Token forwarding
├── middleware/
│   └── auth_header_validation.py    # Auth header validation middleware
└── tools/
    ├── spec_config.py               # SpecConfig - Configuration models
    ├── auth_config.py               # AuthConfig - Auth configuration models
    ├── env.py                       # Environment variable loading
    └── env_resolver.py              # EnvResolver - Variable substitution
```

## Key Design Patterns

### 1. Provider Pattern

**Used for**: Service provisioning and plugin architecture

```python
# Base provider interface
class StaticMcpProvider:
    def create_services(self, configs: List[SpecConfig]) -> Dict[str, FastMCP]
        # Create MCP services from configuration

# Specific implementations
class McpProxyProvider(StaticMcpProvider):
    # Creates proxies for MCP backends

class OpenApiMcpProvider(StaticMcpProvider):
    # Converts OpenAPI specs to MCP tools
```

### 2. Factory Pattern

**Used for**: Authentication provider creation

```python
class GlobalAuthProvider:
    @staticmethod
    def create_provider(config: AuthConfig) -> Auth:
        # Factory method to create auth providers
        provider_class = _get_provider_class(config.provider_name)
        return provider_class(**config.provider_config)
```

### 3. Proxy Pattern

**Used for**: Forwarding MCP requests to backends

```python
# FastMCP's create_proxy creates transparent proxies
proxy = await create_proxy(mcp_spec, name="backend-service")
# Proxy forwards all MCP protocol calls to backend
```

### 4. Middleware Pattern

**Used for**: Request/response processing pipeline

```python
# Starlette middleware stack
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(AuthValidationMiddleware, ...)
app.add_middleware(RateLimitMiddleware, ...)
```

## Data Flow

### Startup Sequence

```
1. Load environment variables (.env, ENV)
2. Load configuration file (config.yaml)
3. Create GlobalAuthProvider (if auth enabled)
4. Create ProxyConfigProvider
5. For each service config:
   a. Filter by spec_type (mcp/openapi)
   b. Create service provider (McpProxyProvider/OpenApiMcpProvider)
   c. Create FastMCP service
   d. Mount at configured path
6. Create StarletteApp with all services
7. Add middleware (CORS, health check)
8. Start ASGI server (Uvicorn)
```

### Request Flow

```
1. Client sends HTTP POST to /service/mcp
   ├─ Headers: Authorization: Bearer <token>
   └─ Body: {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

2. Starlette routes request
   ├─ CORS middleware: Validate origin, add headers
   ├─ Route to FastMCP service at /service
   └─ Invoke FastMCP http_app

3. FastMCP authentication (if configured)
   ├─ Extract Authorization header
   ├─ Validate token (JWT/OAuth)
   ├─ Extract user context
   └─ Store in MCP context

4. FastMCP protocol handling
   ├─ Deserialize JSON-RPC request
   ├─ Route to appropriate handler (tools/list, tools/call, etc.)
   └─ For proxied services: forward to backend

5. Backend service processing
   ├─ MCP backend: Forward via HTTP or stdio
   ├─ OpenAPI backend: Convert MCP call to REST API call
   └─ Apply backend authentication (pass-through or OAuth)

6. Response processing
   ├─ Backend returns result
   ├─ FastMCP serializes to JSON-RPC response
   └─ Starlette returns HTTP response to client
```

## Scalability Considerations

### Horizontal Scaling

- **Stateless Design**: No server-side session state
- **Load Balancing**: Multiple proxy instances behind load balancer
- **Token Caching**: Shared Redis cache for OAuth tokens
- **Health Checks**: Kubernetes/Docker health probe support

### Performance Optimization

- **Async I/O**: Full async/await throughout
- **Connection Pooling**: HTTP client connection reuse
- **Token Caching**: Avoid repeated OAuth flows
- **Lazy Loading**: Services loaded only when needed

### Resource Management

- **Memory**: Minimal per-request memory
- **Connections**: Configurable connection limits
- **Timeouts**: Configurable request timeouts
- **Rate Limiting**: Per-IP request throttling

## Security Architecture

### Defense in Depth

1. **Transport Security**: HTTPS/TLS encryption
2. **Authentication**: Token validation at proxy
3. **Authorization**: Scope/claim verification
4. **Backend Auth**: Separate backend authentication
5. **Token Encryption**: Fernet encryption for cached tokens
6. **CORS**: Origin validation for web clients
7. **Rate Limiting**: DDoS protection

### Secret Management

- **Environment Variables**: All secrets via ENV
- **Docker Secrets**: Production secret injection
- **Token Rotation**: Support for key rotation
- **Audit Logging**: Security event logging

## Monitoring & Observability

### Health Checks

```
GET /health
Response: {"status": "healthy"}
```

### Logging

- **Structured Logging**: JSON log format
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Request Tracing**: Request ID propagation
- **Error Tracking**: Exception logging

### Metrics (Future)

- Request rate
- Response latency
- Error rates
- Backend health
- Token cache hit rate

## Related Documentation

- [Component Overview](components.md) - Detailed component docs
- [Request Flow](request-flow.md) - Request processing details
- [Module Structure](module-structure.md) - Python module organization
- [Configuration](../configuration/config-files.md) - Configuration reference
- [Authentication](../features/authentication/overview.md) - Auth architecture
