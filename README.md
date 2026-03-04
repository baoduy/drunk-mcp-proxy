# drunk-mcp-proxy

[![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=baoduy_drunk-mcp-proxy)](https://sonarcloud.io/summary/new_code?id=baoduy_drunk-mcp-proxy)

## Docs
- [deep-wiki](https://deepwiki.com/baoduy/drunk-mcp-proxy)
- [github-docs](https://baoduy.github.io/drunk-mcp-proxy/)
- [docker-hub](https://hub.docker.com/r/baoduy2412/mcp-proxy)

A powerful, production-ready dynamic proxy server for the Model Context Protocol (MCP) and LLM APIs, built with Python and FastMCP. This service enables MCP clients and LLM-compatible applications to seamlessly connect to multiple backend MCP servers and LLM providers through a unified, scalable interface with advanced features including authentication, CORS support, and environment-based configuration.

## 🎯 Overview

drunk-mcp-proxy acts as a central gateway for both Model Context Protocol (MCP) services and LLM providers, providing:

- **Unified Interface**: Single endpoint for multiple backend MCP servers and LLM providers
- **Dynamic Routing**: Automatic routing to configured backend services  
- **Namespace Isolation**: Prevent tool name conflicts with per-server namespaces
- **OpenAPI Integration**: Automatic conversion of OpenAPI specs to MCP tools
- **LLM Proxy**: Multi-provider LLM API gateway with OpenAI-compatible endpoints
- **Anthropic Compatibility**: Proxy Anthropic Messages API requests through OpenAI-compatible backends
- **WebSocket Responses API**: Native WebSocket support for OpenAI Responses API streaming
- **Enterprise Authentication**: 14+ pluggable auth providers (JWT, OAuth, GitHub, Azure, etc.)
- **Production Ready**: Health checks, CORS, structured logging, Docker support

## ✨ Key Features

- 🚀 **Dynamic Proxy Management**: Configure multiple MCP and OpenAPI services via YAML
- 🤖 **LLM Gateway**: Route requests to multiple LLM providers (OpenAI, Ollama, LM Studio, etc.)
- 🔄 **Anthropic API Compatibility**: Use Anthropic/Claude clients with any OpenAI-compatible backend
- 🔌 **WebSocket Responses API**: Full WebSocket support for OpenAI Responses API
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

#### `data/config.yaml` - Unified Configuration

Define authentication, LLM providers, and MCP/OpenAPI services in a single file:

```yaml
# Authentication configuration (optional)
auth:
  defaultProvider: basic
  basic:
    base_url: null
    token: $API_KEY
  jwt:
    base_url: null
    jwks_uri: "https://login.microsoftonline.com/common/discovery/keys"
    issuer: "https://sts.windows.net/$AZURE_TENANT_ID/"
    audience: "api://your-client-id"

# LLM provider configuration (optional)
llm:
  - enabled: true
    websocket: true
    provider: openai
    base_url: "https://api.openai.com/v1"
    api_key: $OPENAI_API_KEY

# MCP and OpenAPI service configuration
mcp:
  - path: /
    spec_type: mcp
    skill_dir: skills
    mcp_servers:
      my-server:
        enabled: true
        command: npx
        args: ["@playwright/mcp@0.0.64"]
        transport: stdio

  - path: /api
    spec_file: openapi/petstore.yaml
    spec_type: openapi
    base_url: "https://api.example.com"
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
├── config.yaml       # Unified configuration (auth, LLM, and MCP/OpenAPI services)
├── mcp/              # MCP server specifications (optional, for external spec files)
│   ├── stock.mcp.json
│   └── wiki.mcp.json
├── openapi/          # OpenAPI specifications
│   └── petstore.yaml
└── skills/           # Skill directories (optional)
```

### Configuration (`config.yaml`)

The proxy uses a unified YAML configuration file to define authentication, LLM providers, and MCP/OpenAPI services:

```yaml
# Authentication configuration
auth:
  defaultProvider: basic
  basic:
    token: $API_KEY

# MCP service configuration
mcp:
  - path: /stock
    spec_file: mcp/stock.mcp.json
    spec_type: mcp

  - path: /api
    spec_file: openapi/petstore.yaml
    spec_type: openapi
    base_url: "https://api.example.com"
    filters:
      methods: ["GET", "POST"]
      tags: ["public"]
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
MCP Client / LLM Client / Anthropic Client
        ↓ (HTTP/SSE/WebSocket + Authorization)
        ↓
┌──────────────────────────────────────────────┐
│  drunk-mcp-proxy Server                      │
│ ┌────────────────────────────────────────┐  │
│ │ Starlette ASGI Application             │  │
│ │ • CORS Middleware                      │  │
│ │ • Auth Validation                      │  │
│ │ • Rate Limiting                        │  │
│ │ • Health Check: /health                │  │
│ │ • Root FastMCP Server (/)              │  │
│ │ • MCP Sub-services:                    │  │
│ │   - /stock (MCP)                       │  │
│ │   - /wiki (MCP)                        │  │
│ │   - /api (OpenAPI)                     │  │
│ │ • LLM Proxy (/api/v1):                │  │
│ │   - POST /chat/completions             │  │
│ │   - POST /messages (Anthropic API)     │  │
│ │   - WS   /responses (WebSocket)        │  │
│ │   - POST /embeddings                   │  │
│ │   - POST /images/generations           │  │
│ │   - POST /audio/transcriptions         │  │
│ │   - POST /audio/translations           │  │
│ │   - GET  /models                       │  │
│ │   - GET  /providers                    │  │
│ └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
        ↓ ↓ ↓
   [Backend MCP/OpenAPI/LLM Services]
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

```yaml
auth:
  defaultProvider: basic
  basic:
    token: $API_KEY
```

Set the `API_KEY` environment variable in your `.env` file.

### OAuth 2.0 Authentication (Azure AD Example)

```yaml
auth:
  defaultProvider: azure
  azure:
    client_id: $AZURE_CLIENT_ID
    client_secret: $AZURE_CLIENT_SECRET
    tenant_id: $AZURE_TENANT_ID
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

## 🤖 LLM Proxy

When LLM providers are configured, drunk-mcp-proxy exposes a full OpenAI-compatible LLM gateway at `/api/v1`. All endpoints use the model ID format `provider_modelname` (e.g., `openai_gpt-4o`, `lms_llama3.2`) to route requests to the appropriate backend.

### LLM Provider Configuration

Add providers to the `llm` section of `config.yaml`:

```yaml
llm:
  - enabled: true
    websocket: true       # Enable for providers that support native WebSocket Responses API
                          # When false, HTTP Responses API is used as fallback
    provider: openai      # Short provider name used as prefix in model IDs
    base_url: "https://api.openai.com/v1"
    api_key: $OPENAI_API_KEY

  - enabled: true
    websocket: false
    provider: lms         # LM Studio
    base_url: "http://host.docker.internal:1234/v1"

  - enabled: false
    provider: oll         # Ollama
    base_url: "http://host.docker.internal:11434/v1"
```

### Model ID Format

All LLM endpoints expect the model ID to include a provider prefix separated by an underscore:

```
{provider}_{model_name}
```

Examples:
- `openai_gpt-4o` → routes to the `openai` provider, model `gpt-4o`
- `lms_llama3.2` → routes to the `lms` (LM Studio) provider, model `llama3.2`
- `ort_claude-3-5-sonnet` → routes to the `ort` (OpenRouter) provider, model `claude-3-5-sonnet`

### Available Endpoints

All endpoints are mounted at `/api/v1` (configurable via `FASTMCP_LLM_ROUTE_PREFIX`):

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat/completions` | OpenAI-compatible chat completions |
| `POST` | `/api/v1/messages` | Anthropic Messages API (see below) |
| `WS`   | `/api/v1/responses` | OpenAI WebSocket Responses API |
| `POST` | `/api/v1/embeddings` | Text embeddings |
| `POST` | `/api/v1/images/generations` | Image generation |
| `POST` | `/api/v1/audio/transcriptions` | Audio transcription (Whisper) |
| `POST` | `/api/v1/audio/translations` | Audio translation |
| `GET`  | `/api/v1/models` | List all available models across providers |
| `GET`  | `/api/v1/providers` | List all configured providers |

### Chat Completions

Standard OpenAI-compatible chat completions:

```bash
curl -X POST http://localhost:9123/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "openai_gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### Anthropic Messages API Compatibility

The `/messages` endpoint accepts Anthropic Messages API format and transparently converts to/from the OpenAI format, letting Anthropic/Claude clients use any OpenAI-compatible backend:

```bash
curl -X POST http://localhost:9123/api/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "lms_llama3.2",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 1024
  }'
```

**Supported conversions:**
- System prompts (string and block array)
- Multimodal content (text, base64 images, URL images)
- Tool use and tool results
- Streaming SSE events in Anthropic format
- `stop_sequences` → `stop`, `metadata.user_id` → `user`, finish reason mapping

#### Use with Claude Code CLI

Point the Claude Code CLI at the proxy to use any backend model with the Anthropic-compatible endpoint:

```bash
export ANTHROPIC_BASE_URL=http://localhost:9123/api/v1
export ANTHROPIC_AUTH_TOKEN=YOUR_API_KEY_HERE
claude --model lms_llama3.2
```

### WebSocket Responses API

The `/responses` WebSocket endpoint provides OpenAI Responses API streaming. Clients connect via WebSocket and exchange JSON messages using the OpenAI Responses API protocol.

**Connection URL:** `ws://localhost:9123/api/v1/responses`

**Message flow:**
1. Client connects with `Authorization: Bearer <token>` header
2. Client sends a `response.create` event with `model: "provider_modelname"`
3. Proxy routes to the configured backend and streams response events back
4. For providers with `websocket: true`, native WebSocket is used for lowest latency
5. For other providers, the HTTP Responses API is used as fallback

```javascript
const ws = new WebSocket("ws://localhost:9123/api/v1/responses", {
  headers: { "Authorization": "Bearer YOUR_API_KEY" }
});

ws.send(JSON.stringify({
  type: "response.create",
  response: {
    model: "openai_gpt-4o",
    instructions: "You are a helpful assistant.",
    input: [{ type: "message", role: "user", content: "Hello!" }]
  }
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data);  // response.created, response.output_text.delta, response.done, etc.
};
```

**Provider WebSocket support:** Set `websocket: true` in the provider config for providers that natively support the `/responses` WebSocket endpoint (e.g., OpenAI). For all other providers, the HTTP Responses API is used as a fallback.

> **Note:** The `previous_response_id` continuation feature is only supported for providers with native WebSocket (`websocket: true`). Using it with HTTP fallback providers returns an error.

### List Models and Providers

```bash
# List all models across all configured providers
curl http://localhost:9123/api/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# Filter by provider
curl "http://localhost:9123/api/v1/models?provider=openai" \
  -H "Authorization: Bearer YOUR_API_KEY"

# List configured providers
curl http://localhost:9123/api/v1/providers \
  -H "Authorization: Bearer YOUR_API_KEY"
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
