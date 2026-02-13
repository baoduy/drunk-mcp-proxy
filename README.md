# drunk-mcp-proxy

A dynamic proxy server for Model Context Protocol (MCP) built with Python and FastMCP. This service allows you to proxy and manage multiple MCP backend servers through a single unified interface.

## Features

- 🚀 **Dynamic Proxy Management**: Add and manage MCP servers on the fly
- 📝 **Static Configuration**: Define default servers in `config.json`
- 🐳 **Docker Support**: Fully containerized with Docker and Docker Compose
- 🔌 **Multiple Transports**: Support for HTTP and SSE transports
- 🔐 **Authentication**: MCP auth providers configured via environment variables
- 🌐 **DeepWiki Integration**: Pre-configured with DeepWiki MCP server for GitHub documentation access

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

2. Edit `data/*.mcp.json` to add your default MCP servers (or copy from `mcp.example.json`):
```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "https://mcp.deepwiki.com/mcp",
      "transport": "http"
    }
  }
}
```

> **Note:** The DeepWiki MCP server is pre-configured by default, providing access to GitHub repository documentation.

3. Create the data directory for persistent storage:
```bash
mkdir -p data
cp mcp.example.json data/deepwiki.mcp.json
# Edit data/*.mcp.json with your MCP servers
```

4. Start the service:
```bash
docker-compose up -d
```

5. View logs:
```bash
docker-compose logs -f
```

### Using Docker

1. Create the data directory and configuration:
```bash
mkdir -p data
cp mcp.example.json data/deepwiki.mcp.json
# Edit data/*.mcp.json with your MCP servers
```

2. Build the image:
```bash
docker build -t drunk-mcp-proxy .
```

3. Run the container:
```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --name mcp-proxy \
  drunk-mcp-proxy
```

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python src/main.py
```

## Configuration

All configuration files are validated against JSON schemas to ensure correctness.

### Server Bind and Transport

The proxy server binds to `0.0.0.0:9123` (fixed).

The server transport can be controlled with:
- `FASTMCP_SERVER_TRANSPORT` (`http`, `sse`, or `auto`)

When running, each configured MCP server is exposed as:
- `http://localhost:9123/<mcp-name>/mcp`
- `http://localhost:9123/<mcp-name>/sse`

### Static Configuration (mcp.json)

Define your default MCP servers in `data/*.mcp.json`:

```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "https://mcp.deepwiki.com/mcp",
      "transport": "http"
    },
    "server1": {
      "url": "https://api.example.com/mcp",
      "transport": "http"
    },
    "server2": {
      "url": "https://another-server.com/mcp",
      "transport": "http"
    }
  }
}
```

For local stdio-based MCP servers, set `transport` to `stdio` and supply the command in the URL field your MCP client expects (or leave the URL as a placeholder if your client launches the process directly).

```json
{
  "mcpServers": {
    "local-tool": {
      "url": "stdio://local-tool",
      "transport": "stdio"
    }
  }
}
```

**Schema:** `schemas/mcp.schema.json`

#### Namespaced Config Files

You can place multiple config files in the same directory using the naming
pattern `*.mcp.json`. Each file is mounted under a namespace equal to the file
name without the `.mcp.json` suffix.

Example:

```
data/
  deepwiki.mcp.json   -> namespace "deepwiki"
  finance.mcp.json    -> namespace "finance"
```

Set `FASTMCP_CONFIG_DIR` to the directory path (e.g. `./data`) to load all of them.


### JSON Schema Validation

All configuration files are automatically validated against their JSON schemas:

- **mcp.json**: Validated against `schemas/mcp.schema.json` (applies to each `*.mcp.json` file)
- **auth.json**: Reserved (authentication is configured via environment variables)

Validation errors are logged but non-fatal to allow the server to start. Fix validation errors to ensure proper configuration.

**Requirements:**
- Server name/proxy name: alphanumeric, hyphens, underscores (1-64 chars)
- URLs: Must be valid HTTP/HTTPS URLs
- Transport: Must be one of: `http`, `sse`, `stdio`
- API key hashes: Must be 64-character hex strings (SHA-256) if you use auth.json elsewhere

## Available Tools

The proxy server does not register any custom MCP tools by default.

## Authentication

Authentication is configured via FastMCP auth providers and environment variables. If no auth provider is configured, authentication is disabled.

### Configure an Auth Provider

Set `FASTMCP_SERVER_AUTH` to a provider class path or one of the built-in aliases:

```bash
# Example: JWT verifier
export FASTMCP_SERVER_AUTH=jwt
export JWKS_URI=https://example.com/.well-known/jwks.json
export ISSUER=https://issuer.example.com/
export AUDIENCE=my-audience
```

Provider parameters can be supplied either via:
- `FASTMCP_SERVER_AUTH_<PROVIDER>_*` env vars (v2-style), or
- env vars matching the provider's constructor arguments (e.g. `CLIENT_ID`, `CLIENT_SECRET`, `BASE_URL`)

## Environment Variables

- `FASTMCP_CONFIG_DIR`: Path to the static configuration directory
  - Local development default: `./data`
  - Docker default: `/app/data`
- `FASTMCP_SERVER_AUTH`: Auth provider class path or alias (e.g. `jwt`, `github`)
- `FASTMCP_STATELESS_HTTP`: Enable stateless HTTP mode (`true`/`false`, default: `false`)
- `FASTMCP_CORS_ALLOW_ORIGINS`: Comma-separated list of allowed origins (e.g. `https://example.com`)
- `FASTMCP_CORS_ALLOW_METHODS`: Comma-separated list of allowed methods (e.g. `GET,POST,DELETE,OPTIONS`)
- `FASTMCP_CORS_ALLOW_HEADERS`: Comma-separated list of allowed headers
- `FASTMCP_CORS_EXPOSE_HEADERS`: Comma-separated list of exposed headers

Note: When CORS is enabled, the server uses `uvicorn` to serve the ASGI app with middleware.
- Provider-specific env vars (e.g. `JWKS_URI`, `ISSUER`, `AUDIENCE`, `CLIENT_ID`, `CLIENT_SECRET`)
- `PYTHONPATH`: Python module search path
  - Local development: `./src`
  - Docker: `/app/src`

## Project Structure

```
drunk-mcp-proxy/
├── src/
│   ├── main.py          # Main application code
│   └── mcp_proxy/       # Proxy implementation
├── schemas/
│   ├── mcp.schema.json      # Schema for mcp.json
│   └── auth.schema.json     # Reserved for auth.json if used elsewhere
├── data/
│   ├── *.mcp.json       # Static server configuration(s)
├── mcp.example.json     # Example MCP server configuration
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose configuration
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## Development

### Testing Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python src/main.py
```

3. The server will start and display mounted proxies:
```
==================================================
Starting MCP Proxy Server
==================================================
Mounting static servers from mcp.json:
  ✓ Mounted 'deepwiki' at https://mcp.deepwiki.com/mcp
==================================================
MCP Proxy Server is ready!
==================================================
```

## Requirements

- Python 3.11+
- FastMCP 3.0.0 or later

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, modify `docker-compose.yml` to use a different port:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead
```

### Proxy Configuration Not Loading
1. Check that `data/*.mcp.json` exists and has valid JSON syntax
2. Verify file permissions allow reading
3. Check Docker volume mounts in `docker-compose.yml`

### Container Fails to Start
1. Check logs: `docker-compose logs mcp-proxy`
2. Verify network connectivity to backend MCP servers
3. Ensure config file is properly mounted

## Examples

### Multiple Server Configuration
```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "https://mcp.deepwiki.com/mcp",
      "transport": "http"
    },
    "weather": {
      "url": "https://weather-api.example.com/mcp",
      "transport": "http"
    },
    "database": {
      "url": "https://db-api.example.com/mcp",
      "transport": "http"
    },
    "analytics": {
      "url": "https://analytics.example.com/mcp",
      "transport": "http"
    }
  }
}
```

### Using with MCP Clients
Connect to this proxy server as you would any MCP server. The proxy will route requests to the configured backend servers and aggregate their responses.

## Architecture

```
┌─────────────────┐
│   MCP Client    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  drunk-mcp-     │
│     proxy       │
│  (This Server)  │
└────────┬────────┘
         │
         ├──────────────┬──────────────┐
         v              v              v
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │Backend  │    │Backend  │    │Backend  │
   │MCP      │    │MCP      │    │MCP      │
   │Server 1 │    │Server 2 │    │Server N │
   └─────────┘    └─────────┘    └─────────┘
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/baoduy/drunk-mcp-proxy)
