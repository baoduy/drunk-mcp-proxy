# drunk-mcp-proxy

[![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=baoduy_drunk-mcp-proxy)](https://sonarcloud.io/summary/new_code?id=baoduy_drunk-mcp-proxy)

## Docs
- [deep-wiki](https://deepwiki.com/baoduy/drunk-mcp-proxy)
- [github-docs](https://baoduy.github.io/drunk-mcp-proxy/)
- [docker-hub](https://hub.docker.com/r/baoduy2412/mcp-proxy)

A powerful, production-ready dynamic proxy server for the Model Context Protocol (MCP) built with Python and FastMCP. This service enables MCP clients to seamlessly connect to multiple backend MCP servers through a unified, scalable interface with advanced features including authentication, CORS support, and environment-based configuration.

## 🎯 Overview

drunk-mcp-proxy acts as a central gateway for Model Context Protocol (MCP) services, providing:

- **Unified Interface**: Single endpoint for multiple backend MCP servers
- **Dynamic Routing**: Automatic routing to configured backend services  
- **Namespace Isolation**: Prevent tool name conflicts with per-server namespaces
- **OpenAPI Integration**: Automatic conversion of OpenAPI specs to MCP tools
- **Enterprise Authentication**: 14+ pluggable auth providers (JWT, OAuth, GitHub, Azure, etc.)
- **Production Ready**: Health checks, CORS, structured logging, Docker support

## ✨ Key Features

- 🚀 **Dynamic Proxy Management**: Configure multiple MCP and OpenAPI services via JSON
- 🐳 **Docker Support**: Multi-stage production Docker image with health checks
- 🔐 **Enterprise Auth**: JWT, GitHub, Google, Discord, Azure OAuth, and custom auth providers
- 🌐 **CORS Ready**: Full CORS middleware for web client integration
- 🎨 **OpenAPI Support**: Convert OpenAPI specs to MCP tools automatically
- 🔍 **Health Monitoring**: Built-in health check endpoint
- 📊 **Structured Logging**: Configurable log levels
- 🛡️ **JSON Schema Validation**: Automatic config validation

## 🚀 Quick Start

Get up and running with drunk-mcp-proxy using the pre-built Docker image from Docker Hub.

### Step 1: Prepare Configuration Files

Create a `data/` directory with the required configuration files:

```bash
mkdir -p data/mcp data/openapi data/skills
```

#### `data/config.json` - Service Configuration

Define your MCP and OpenAPI services:

```json
[
  {
    "path": "/",
    "spec_type": "mcp",
    "skill_dir": "skills",
    "mcpServers": {
      "my-server": {
        "enabled": true,
        "command": "npx",
        "args": ["@playwright/mcp@0.0.64"],
        "transport": "stdio"
      }
    }
  },
  {
    "path": "/api",
    "spec_file": "openapi/petstore.yaml",
    "spec_type": "openapi",
    "base_url": "https://api.example.com"
  }
]
```

#### `data/auth.json` - Authentication Configuration

Configure authentication providers (optional):

```json
{
  "defaultProvider": "bearer",
  "bearer": {
    "token": "$API_KEY"
  },
  "azure": {
    "clientId": "$AZURE_CLIENT_ID",
    "clientSecret": "$AZURE_CLIENT_SECRET",
    "tenantId": "$AZURE_TENANT_ID"
  }
}
```

> **Note**: 
> - **Bearer auth** (`defaultProvider: "bearer"`) is the simplest option for API key authentication, commonly used by API proxies and gateways.
> - Environment variables like `$API_KEY` or `$AZURE_CLIENT_ID` are automatically resolved when the config is loaded.

See the [samples in the repository](data/) for more configuration examples.

### Step 2: Prepare Docker Compose

Create a `docker-compose.yml` file:

```yaml
services:
  mcp-proxy:
    image: baoduy2412/mcp-proxy:latest
    container_name: mcp-proxy-server
    ports:
      - "${FASTMCP_PORT:-9123}:${FASTMCP_PORT:-9123}"
    volumes:
      - ./data:/drunk-proxy/data
    env_file:
      - .env
    environment:
      - FASTMCP_HOST=0.0.0.0
      - FASTMCP_PORT=${FASTMCP_PORT:-9123}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9123/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

> **Note**: The `./data` directory is mounted to `/drunk-proxy/data` in the container. All configuration files should be placed in this directory.

### Step 3: Configure Environment & Run

Create a `.env` file from the sample:

```bash
cp .env.sample .env
```

Edit `.env` with your settings. Key environment variables:

```bash
# Server Configuration
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=INFO
FASTMCP_AUTH_ENABLED=false

# Bearer Authentication (API Key)
API_KEY=your-api-key-here

# OAuth Storage (required if using OAuth)
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=your-44-character-encryption-key

# Azure Authentication (if using Azure OAuth)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
```

> **Tip**: See [.env.sample](.env.sample) for the complete list of available environment variables.

Now start the server:

```bash
docker-compose up -d
```

Verify it's running:

```bash
curl http://localhost:9123/health
```

### Additional Services (Optional)

The full [docker-compose.yml](docker-compose.yml) in the repository includes optional services:
- **MCP Inspector** - Debug and inspect MCP servers
- **OpenWebUI** - Web interface for LLM interactions

---

## 🛠️ Local Development

### Using Docker (Build from Source)

```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy

docker build -t drunk-mcp-proxy .
docker run -d -p 9123:9123 -v $(pwd)/data:/drunk-proxy/data drunk-mcp-proxy
```

### Running Locally

```bash
# Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Run the server
python src/main.py
```

The server will start on `http://0.0.0.0:9123` by default.

## 📖 Configuration

### Configuration Directory Structure

```text
data/
├── config.json       # Main service configuration
├── auth.json         # Authentication provider configuration
├── llm.json          # LLM proxy configuration (optional)
├── mcp/              # MCP server specifications
│   ├── stock.mcp.json
│   └── wiki.mcp.json
├── openapi/          # OpenAPI specifications
│   └── petstore.yaml
└── skills/           # Skill directories (optional)
```

### Service Configuration (`config.json`)

Configure MCP and OpenAPI services:

```json
[
  {
    "path": "/stock",
    "spec_file": "mcp/stock.mcp.json",
    "spec_type": "mcp"
  },
  {
    "path": "/api",
    "spec_file": "openapi/petstore.yaml",
    "spec_type": "openapi",
    "base_url": "https://api.example.com",
    "filters": {
      "methods": ["GET", "POST"],
      "tags": ["public"]
    }
  }
]
```

### Authentication Configuration (`auth.json`)

Configure authentication providers:

```json
{
  "defaultProvider": "azure",
  "azure": {
    "clientId": "$AZURE_CLIENT_ID",
    "clientSecret": "$AZURE_CLIENT_SECRET",
    "tenantId": "$AZURE_TENANT_ID"
  }
}
```

### Environment Variables

Key environment variables (see [.env.sample](.env.sample) for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `FASTMCP_PORT` | Server port | `9123` |
| `FASTMCP_HOST` | Server host | `0.0.0.0` |
| `FASTMCP_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `FASTMCP_AUTH_ENABLED` | Enable authentication | `false` |
| `FASTMCP_CONFIG_DIR` | Configuration directory | `data` |
| `FASTMCP_CORS_ALLOW_ORIGINS` | CORS allowed origins | `*` |
| `API_KEY` | API key for bearer authentication | - |
| `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY` | Fernet key for OAuth token encryption | - |

See [Environment Variables](docs/configuration/environment-variables.md) for complete list.

## 📚 Documentation

- **Getting Started**
  - [Installation Guide](docs/getting-started/installation.md)
  - [Quick Start Guide](docs/getting-started/quick-start.md)
  - [First Steps](docs/getting-started/first-steps.md)

- **Configuration**
  - [Configuration Files](docs/configuration/config-files.md)
  - [Environment Variables](docs/configuration/environment-variables.md)
  - [Schema Validation](docs/configuration/schema-validation.md)

- **Features**
  - [MCP Proxy Management](docs/features/mcp/proxy-management.md)
  - [OpenAPI Integration](docs/features/openapi/integration.md)
  - [Authentication](docs/features/authentication/overview.md)
  - [Pass-Through Authentication](docs/features/authentication/pass-through.md)

- **Architecture**
  - [System Architecture](docs/architecture/system-architecture.md)
  - [Component Overview](docs/architecture/components.md)
  - [Request Flow](docs/architecture/request-flow.md)

- **API Reference**
  - [REST API Endpoints](docs/api-reference/endpoints.md)
  - [Python Modules](docs/api-reference/modules.md)

- **Deployment**
  - [Docker Deployment](docs/deployment/docker.md)
  - [Production Setup](docs/deployment/production.md)
  - [Health Checks & Monitoring](docs/deployment/monitoring.md)

- **Development**
  - [Development Guide](docs/development/guide.md)
  - [Testing](docs/development/testing.md)
  - [Troubleshooting](docs/development/troubleshooting.md)

For comprehensive documentation, see the [Documentation Index](docs/INDEX.md).

## 🏗️ Architecture Overview

```
MCP Client (e.g., Claude Desktop)
        ↓ (HTTP/SSE + Authorization)
        ↓
┌─────────────────────────────────────┐
│  drunk-mcp-proxy Server             │
│ ┌───────────────────────────────┐  │
│ │ Starlette ASGI Application    │  │
│ │ • CORS Middleware             │  │
│ │ • Auth Validation             │  │
│ │ • Rate Limiting               │  │
│ │ • Health Check: /health       │  │
│ │ • Root FastMCP Server (/)     │  │
│ │ • Sub-services:               │  │
│ │   - /stock (MCP)              │  │
│ │   - /wiki (MCP)               │  │
│ │   - /api (OpenAPI)            │  │
│ └───────────────────────────────┘  │
└─────────────────────────────────────┘
        ↓ ↓ ↓
   [Backend MCP/OpenAPI Services]
```

See [System Architecture](docs/architecture/system-architecture.md) for detailed diagrams.

## 🔐 Authentication

drunk-mcp-proxy supports 14+ authentication providers:

- **Token-based**: Bearer (API Keys), JWT
- **OAuth 2.0**: Azure AD, GitHub, Google, Discord, Auth0
- **Enterprise**: WorkOS, Scalekit, Descope
- **Custom**: Pass-through, Introspection

### Bearer Authentication (API Key)

The simplest option for API key authentication, commonly used by API proxies and gateways:

```json
{
  "defaultProvider": "bearer",
  "bearer": {
    "token": "$API_KEY"
  }
}
```

Set the `API_KEY` environment variable in your `.env` file.

### OAuth 2.0 Authentication (Azure AD Example)

```json
{
  "defaultProvider": "azure",
  "azure": {
    "clientId": "$AZURE_CLIENT_ID",
    "clientSecret": "$AZURE_CLIENT_SECRET",
    "tenantId": "$AZURE_TENANT_ID"
  }
}
```

See [Authentication Guide](docs/features/authentication/overview.md) for details.

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_server.py

# Run with coverage
python -m pytest --cov=src --cov-report=html
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) framework
- Powered by [Starlette](https://www.starlette.io/) ASGI framework
- Authentication via FastMCP's pluggable auth system

## 📞 Support

- 📖 [Documentation](docs/INDEX.md)
- 🐛 [Issue Tracker](https://github.com/baoduy/drunk-mcp-proxy/issues)
- 💬 [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)

---

**Note**: For detailed technical documentation, API references, and advanced configuration, please refer to the [comprehensive documentation](docs/INDEX.md).
