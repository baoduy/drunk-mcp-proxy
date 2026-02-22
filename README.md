# drunk-mcp-proxy

[![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=baoduy_drunk-mcp-proxy)](https://sonarcloud.io/summary/new_code?id=baoduy_drunk-mcp-proxy)

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

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy

# Start the services
docker-compose up -d

# Verify it's running
curl http://localhost:9123/health
```

### Using Docker

```bash
# Build and run
docker build -t drunk-mcp-proxy .
docker run -d -p 9123:9123 -v $(pwd)/data:/mcp_proxy/data drunk-mcp-proxy
```

### Local Development

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

### Basic Configuration

Configure your services in `data/config.json`:

```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null
  },
  {
    "path": "/api",
    "spec_file": "openapi/petstore.yaml",
    "spec_type": "openapi",
    "base_url": "https://api.example.com"
  }
]
```

### Environment Variables

Key environment variables:

```bash
FASTMCP_HOST=0.0.0.0              # Server host
FASTMCP_PORT=9123                  # Server port
FASTMCP_CONFIG_DIR=data            # Configuration directory
FASTMCP_LOG_LEVEL=INFO             # Log level (DEBUG, INFO, WARNING, ERROR)
FASTMCP_AUTH_ENABLED=false         # Enable authentication
FASTMCP_CORS_ALLOW_ORIGINS=*       # CORS allowed origins
```

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

- **OAuth 2.0**: Azure AD, GitHub, Google, Discord, Auth0
- **Token-based**: JWT, API Keys
- **Enterprise**: WorkOS, Scalekit, Descope
- **Custom**: Pass-through, Introspection

Configuration example:

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
pytest

# Run specific test file
pytest tests/test_server.py

# Run with coverage
pytest --cov=src --cov-report=html
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
