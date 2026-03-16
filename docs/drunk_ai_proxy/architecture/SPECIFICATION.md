# MCP Proxy Server - Project Specification

**Document Version:** 1.0  
**Date:** February 13, 2026  
**Status:** COMPLETED

## 1. Executive Summary

The MCP Proxy Server is a high-performance Python-based gateway that dynamically routes requests from clients to
multiple Model Context Protocol (MCP) backend servers. It provides a unified interface for managing distributed MCP
services with features including dynamic server configuration, multiple transport protocols, authentication, CORS
support, and comprehensive monitoring capabilities.

## 2. Project Overview

### 2.1 Purpose

Provide a centralized proxy solution for managing and accessing multiple MCP backend servers through a single endpoint,
enabling seamless integration of distributed MCP services.

### 2.2 Target Users

- Developers integrating multiple MCP services
- DevOps engineers managing MCP infrastructure
- Organizations running distributed MCP deployments
- MCP clients needing unified server access

### 2.3 Key Benefits

- **Single Entry Point**: One endpoint for accessing multiple MCP servers
- **Namespace Isolation**: Tool naming conflicts avoided through namespacing
- **Dynamic Configuration**: Add/remove servers without restarting
- **Multiple Transports**: Support for HTTP, SSE, and streaming protocols
- **Production-Ready**: Docker containerization, logging, monitoring, and health checks
- **Authentication-Ready**: Built-in support for multiple auth providers

## 3. Architecture & Design

### 3.1 System Architecture

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │ (HTTP/SSE)
       ▼
┌──────────────────────────────┐
│    MCP Proxy Server          │
│                              │
│  ┌────────────────────────┐  │
│  │  Health Check Endpoint │  │
│  │  (/health)             │  │
│  └────────────────────────┘  │
│                              │
│  ┌────────────────────────┐  │
│  │   Auth Middleware      │  │
│  │   CORS Middleware      │  │
│  └────────────────────────┘  │
│                              │
│  ┌────────────────────────┐  │
│  │  Proxy Manager         │  │
│  │  - Load config files   │  │
│  │  - Create proxies      │  │
│  │  - Mount to server     │  │
│  └────────────────────────┘  │
└──────┬───────────┬─────┬──────┘
       │           │     │
       ▼           ▼     ▼
   Backend MCP Servers (Namespaced)
   ├── stock (Stock Data MCP)
   ├── wiki (Wikipedia MCP)
   └── weather (Weather MCP)
```

### 3.2 Component Structure

```
src/
├── main.py                 # Entry point
├── app/                    # Application layer
│   ├── server.py          # Core server implementation
│   ├── auth.py            # Authentication configuration
│   └── middleware/        # Middleware components
│       └── cros_middleware.py  # CORS configuration
├── proxies/               # Proxy management
│   └── static_proxies.py  # Static proxy initialization
└── tools/                 # Utilities
    ├── env.py             # Environment configuration
    ├── logging_config.py  # Logging setup
    └── validation.py      # Configuration validation
```

### 3.3 Request Flow

1. **Client Request** → Arrives at proxy server endpoint
2. **Middleware Processing** → CORS, Auth validation
3. **Health Check** → Optional warmup of proxies
4. **Tool Routing** → Route to appropriate backend based on namespace
5. **Backend Call** → Forward request to MCP server
6. **Response** → Return result to client

## 4. Core Features

### 4.1 Dynamic Proxy Management

**Feature:** Load and manage multiple MCP backend servers dynamically

**Implementation:**

- Configuration files: `*.mcp.json` format in configurable directory
- Automatic discovery and loading on startup
- Namespace support for tool name prefixing
- Hot-reload capability (via container restart)

**Configuration Format:**

```json
{
  "mcpServers": {
    "server_name": {
      "command": "python",
      "args": [
        "server.py"
      ],
      "env": {
        "KEY": "value"
      }
    }
  }
}
```

### 4.2 Multiple Transport Support

**Supported Transports:**

- `http`: Standard HTTP transport (default)
- `sse`: Server-Sent Events for streaming
- `streamable-http`: HTTP with streaming capabilities

**Configuration:**

```bash
FASTMCP_SERVER_TRANSPORT=http  # or sse, streamable-http
```

### 4.3 Authentication

**Features:**

- Multiple auth provider support (GitHub, Google, JWT, etc.)
- Environment-based configuration
- Dynamic provider loading
- Parameter auto-discovery from provider signatures

**Supported Providers:**

- GitHub OAuth
- Google OAuth
- Discord OAuth
- JWT verification
- WorkOS/AuthKit
- Descope
- Supabase
- Scalekit

**Configuration:**

```bash
FASTMCP_SERVER_AUTH=github
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=xxx
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=yyy
```

### 4.4 CORS Middleware

**Features:**

- Configurable allowed origins
- Custom HTTP methods and headers
- Response header exposure
- Comma-separated configuration

**Configuration:**

```bash
FASTMCP_CORS_ALLOW_ORIGINS=https://example.com,https://app.example.com
FASTMCP_CORS_ALLOW_METHODS=GET,POST,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization
FASTMCP_CORS_EXPOSE_HEADERS=X-Request-ID
```

### 4.5 Health Monitoring

**Endpoint:** `GET /health`

**Response:**

```json
{
  "status": "healthy",
  "service": "drunk-mcp-proxy"
}
```

**Use Cases:**

- Kubernetes liveness probes
- Load balancer health checks
- Monitoring systems integration

### 4.6 Logging & Observability

**Features:**

- Structured logging with timestamps
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Component-based logger naming
- Server name in all log entries

**Configuration:**

```bash
FASTMCP_LOG_LEVEL=INFO  # or DEBUG, WARNING, ERROR, CRITICAL
```

## 5. Configuration

### 5.1 Environment Variables

| Variable                     | Default                  | Description                            |
|------------------------------|--------------------------|----------------------------------------|
| `FASTMCP_CONFIG_DIR`         | `data`                   | Directory with *.mcp.json config files |
| `FASTMCP_LOG_LEVEL`          | `INFO`                   | Logging level                          |
| `FASTMCP_SERVER_NAME`        | `drunk-mcp-proxy-server` | Server name for logging                |
| `FASTMCP_SERVER_VERSION`     | `1.0.0`                  | Server version                         |
| `FASTMCP_SERVER_TRANSPORT`   | `http`                   | Default transport protocol             |
| `FASTMCP_HOST`               | `0.0.0.0`                | Bind address                           |
| `FASTMCP_PORT`               | `9123`                   | Listen port                            |
| `FASTMCP_SERVER_AUTH`        | (none)                   | Auth provider (e.g., github, jwt)      |
| `FASTMCP_CORS_ALLOW_ORIGINS` | (none)                   | Comma-separated allowed origins        |
| `FASTMCP_CORS_ALLOW_METHODS` | (all)                    | Comma-separated allowed methods        |
| `FASTMCP_CORS_ALLOW_HEADERS` | (all)                    | Comma-separated allowed headers        |

### 5.2 File Structure

```
mcp-proxy/
├── src/
│   ├── main.py
│   ├── app/
│   ├── proxies/
│   └── tools/
├── data/                    # Configuration files
│   ├── stock.mcp.json
│   ├── wiki.mcp.json
│   └── weather.mcp.json
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 6. API Reference

### 6.1 Health Check Endpoint

**Endpoint:** `GET /health`

**Response Code:** 200 OK

**Response Body:**

```json
{
  "status": "healthy",
  "service": "drunk-mcp-proxy"
}
```

**Purpose:** Monitor server health and readiness

### 6.2 MCP Tool Access

**Pattern:** Tools are accessed via namespace prefix

**Examples:**

- Without namespace: `get_stock_price`
- With namespace: `stock.get_stock_price`
- Multiple namespaces: `wiki.search_article`, `weather.get_forecast`

## 7. Deployment

### 7.1 Local Development

```bash
# Clone repository
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy

# Run with Python
PYTHONPATH=. python -m src.main
```

### 7.2 Docker

```bash
# Build image
docker build -t mcp-proxy:latest .

# Run container
docker run -p 9123:9123 \
  -e FASTMCP_CONFIG_DIR=/mcp_proxy/data \
  -v $(pwd)/data:/mcp_proxy/data \
  mcp-proxy:latest
```

### 7.3 Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 7.4 Kubernetes

**Requirements:**

- Dockerfile (provided)
- ConfigMap for configurations
- Service for external access
- Optional: Ingress for routing

**Example Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-proxy
spec:
  replicas: 2
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
          image: mcp-proxy:latest
          ports:
            - containerPort: 9123
          livenessProbe:
            httpGet:
              path: /health
              port: 9123
            initialDelaySeconds: 10
            periodSeconds: 30
```

## 8. Development Workflow

### 8.1 Project Structure & Code Organization

**Directory Layout:**

- `src/main.py` - Application entry point
- `src/app/` - Server implementation and middleware
- `src/proxies/` - Proxy management logic
- `src/tools/` - Shared utilities (logging, env, validation)

**Naming Conventions:**

- Public functions/classes: No prefix
- Internal/private: `_` prefix
- Constants: `UPPER_SNAKE_CASE`
- Classes: `PascalCase`
- Functions: `snake_case`

### 8.2 Import Structure

**Absolute Imports (Recommended):**

```python
from src.tools.env import SERVER_NAME
from src.proxies.static_proxies import create_static_proxies
from src.app.auth import build_auth_provider
```

**Relative Imports (Within same package):**

```python
from .auth import build_auth_provider
from .middleware import build_middleware
```

### 8.3 Type Safety

**Type Hints:**

- All function parameters typed
- Return types specified
- Avoid `Any` except where necessary
- Use `Union`, `Optional` for complex types
- Type aliases for repeated patterns

**Example:**

```python
def create_static_proxies(config_dir: str) -> list[tuple[str | None, Any]]:
    """Create proxy instances from config directory."""
```

## 9. Error Handling

### 9.1 Configuration Errors

- **Missing config file**: Logged, server continues
- **Invalid JSON**: Logged, server continues
- **Schema validation failure**: Logged, server continues
- **Missing directory**: Error logged, application exits if explicitly configured

### 9.2 Runtime Errors

- **Proxy creation failure**: Logged, other proxies continue
- **Proxy mounting failure**: Logged, server continues (partial success)
- **Authentication failure**: Request rejected with 401
- **Missing middleware**: Logged, server continues

### 9.3 Logging Strategy

**Log Levels:**

- `DEBUG`: Detailed proxy operations, config loading
- `INFO`: Server startup, proxy mounting, auth enabled
- `WARNING`: Configuration issues, invalid values
- `ERROR`: Proxy failures, missing critical components

## 10. Security Considerations

### 10.1 Authentication

- Multi-provider support for flexible integration
- Environment-based credential management
- Dynamic provider loading and validation

### 10.2 CORS

- Explicit origin allowlisting
- Method and header restrictions
- Configurable exposure headers

### 10.3 Data Protection

- Non-root user in Docker containers
- Environment variable-based secrets
- No hardcoded credentials

### 10.4 Network Security

- Host/port configuration
- Transport protocol selection
- Middleware support for additional security layers

## 11. Testing & Quality Assurance

### 11.1 Testing Strategy

**Unit Tests:**

- Configuration loading and validation
- Import resolution
- Auth provider initialization

**Integration Tests:**

- Proxy creation and mounting
- Full request flow
- Multi-proxy scenarios

**Docker Tests:**

- Image build validation
- Container startup verification
- Port accessibility

### 11.2 Code Quality

**Standards:**

- Type hints (PEP 484)
- Docstrings (PEP 257)
- Import organization
- 79-character line limit where practical

**Tools:**

- Python compiler for syntax checking
- Type checker for type validation
- Linting for code style

## 12. Roadmap & Future Enhancements

### 12.1 Planned Features

- [ ] Dynamic proxy reload without restart
- [ ] Metrics collection (Prometheus format)
- [ ] Rate limiting per proxy
- [ ] Request/response caching
- [ ] Load balancing across multiple backend instances
- [ ] Proxy health status endpoint
- [ ] Configuration UI dashboard

### 12.2 Performance Optimization

- [ ] Connection pooling for backend services
- [ ] Response caching strategies
- [ ] Async proxy creation
- [ ] Batch configuration loading

### 12.3 Observability

- [ ] Structured logging with JSON format
- [ ] OpenTelemetry integration
- [ ] Distributed tracing support
- [ ] Custom metrics endpoints

## 13. Troubleshooting Guide

### 13.1 Common Issues

**Issue:** "No such file or directory" for config

- **Solution:** Check `FASTMCP_CONFIG_DIR` environment variable
- **Verify:** Config files are in correct directory with `.mcp.json` extension

**Issue:** "Connection refused" to backend

- **Solution:** Verify backend servers are running and accessible
- **Check:** Network connectivity and firewall rules

**Issue:** "Attempted relative import beyond top-level package"

- **Solution:** Use `python -m src.main` or set correct `PYTHONPATH`
- **Docker:** Ensure `PYTHONPATH=/mcp_proxy` is set

**Issue:** CORS errors in browser

- **Solution:** Configure `FASTMCP_CORS_ALLOW_ORIGINS` environment variable
- **Example:** `https://example.com,https://app.example.com`

### 13.2 Debug Mode

```bash
# Enable debug logging
FASTMCP_LOG_LEVEL=DEBUG python -m src.main

# Check configuration loading
FASTMCP_LOG_LEVEL=DEBUG FASTMCP_CONFIG_DIR=./data python -m src.main
```

## 14. License & Attribution

**License:** MIT (See LICENSE file)

**Authors:** Community Contributors

**Last Updated:** February 13, 2026

---

## Appendix A: Configuration Examples

### Example 1: Basic Single Server

```json
{
  "mcpServers": {
    "wiki": {
      "url": "http://localhost:9123/mcp",
      "transport": "http"
    }
  }
}
```

### Example 2: Multiple Servers with Auth

```json
{
  "mcpServers": {
    "stock": {
      "command": "node",
      "args": [
        "server.js"
      ],
      "env": {
        "API_KEY": "stock-key"
      }
    },
    "weather": {
      "command": "python",
      "args": [
        "weather_server.py"
      ],
      "env": {
        "WEATHER_API_KEY": "weather-key"
      }
    }
  }
}
```

### Example 3: Full Environment Setup

```bash
# Core configuration
FASTMCP_CONFIG_DIR=/etc/mcp-proxy
FASTMCP_LOG_LEVEL=INFO
FASTMCP_SERVER_NAME=production-mcp-proxy
FASTMCP_SERVER_VERSION=1.0.0

# Server binding
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=9123

# Transport
FASTMCP_SERVER_TRANSPORT=http

# Authentication
FASTMCP_SERVER_AUTH=github
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=xxx
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=yyy

# CORS
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com
FASTMCP_CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization
FASTMCP_CORS_EXPOSE_HEADERS=X-Request-ID,X-Total-Count
```

---

**End of Specification Document**

