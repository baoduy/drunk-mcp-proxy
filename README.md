# drunk-mcp-proxy

A dynamic proxy server for Model Context Protocol (MCP) built with Python and FastMCP. This service allows you to proxy and manage multiple MCP backend servers through a single unified interface.

## Features

- 🚀 **Dynamic Proxy Management**: Add and manage MCP servers on the fly
- 📝 **Static Configuration**: Define default servers in `config.json`
- 💾 **Persistent Storage**: Dynamic proxies are saved to `proxies.json`
- 🐳 **Docker Support**: Fully containerized with Docker and Docker Compose
- 🔌 **Multiple Transports**: Support for HTTP and SSE transports
- 🛠️ **Built-in Tools**: List, add, and manage proxy servers via MCP tools
- 🔐 **Authentication**: API key-based authentication for secure access
- 🌐 **DeepWiki Integration**: Pre-configured with DeepWiki MCP server for GitHub documentation access

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

2. Edit `data/mcp.json` to add your default MCP servers (or copy from `mcp.example.json`):
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
cp mcp.example.json data/mcp.json
# Edit data/mcp.json with your MCP servers
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
cp mcp.example.json data/mcp.json
# Edit data/mcp.json with your MCP servers
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

### Static Configuration (mcp.json)

Define your default MCP servers in `data/mcp.json`:

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

**Schema:** `schemas/mcp.schema.json`

### Dynamic Proxies

Dynamic proxies are added at runtime using the `add_proxy` tool and stored in `data/proxies.json`. These persist across restarts.

**Schema:** `schemas/proxies.schema.json`

### JSON Schema Validation

All configuration files are automatically validated against their JSON schemas:

- **mcp.json**: Validated against `schemas/mcp.schema.json`
- **proxies.json**: Validated against `schemas/proxies.schema.json`
- **auth.json**: Validated against `schemas/auth.schema.json`

Validation errors are logged but non-fatal to allow the server to start. Fix validation errors to ensure proper configuration.

**Requirements:**
- Server name/proxy name: alphanumeric, hyphens, underscores (1-64 chars)
- URLs: Must be valid HTTP/HTTPS URLs
- Transport: Must be one of: `http`, `sse`, `stdio`
- API key hashes: Must be 64-character hex strings (SHA-256)

## Available Tools

The proxy server exposes the following MCP tools:

### add_proxy
Add a new MCP proxy server dynamically.

**Parameters:**
- `name` (string): Name identifier for the proxy
- `url` (string): URL of the MCP server to proxy
- `transport` (string, optional): Transport protocol (default: "http")

**Example:**
```python
add_proxy(name="my-server", url="https://my-server.com/mcp", transport="http")
```

### list_proxies
List all configured MCP proxy servers (both static and dynamic).

**Returns:** List of all configured proxies with their URLs and transport types.

### get_server_info
Get information about this MCP proxy server.

**Returns:** Server version, features, and usage information.

## Authentication

The proxy server supports API key-based authentication to secure access to your MCP backend servers. Authentication is **disabled by default** to allow easy setup and testing.

### Authentication Management

Use the `manage_auth` tool to manage authentication:

#### Enable Authentication
```python
manage_auth(action="enable")
```

#### Create an API Key
```python
manage_auth(action="create_key", client_name="my-client")
# Returns: API key (save it securely - it won't be shown again!)
```

#### Check Authentication Status
```python
manage_auth(action="status")
# Returns: Current authentication status and list of configured clients
```

#### Revoke an API Key
```python
manage_auth(action="revoke_key", client_name="my-client")
```

#### Disable Authentication
```python
manage_auth(action="disable")
```

### Authentication Model

**Important Note:** The current authentication implementation is designed for **local/trusted environments** where the proxy server manages API keys for backend MCP servers it connects to. 

For production deployments where you need to authenticate **incoming client requests**, you would need to:

1. Implement transport-layer authentication (e.g., HTTP headers, bearer tokens)
2. Use FastMCP's built-in authentication hooks if available
3. Deploy behind an API gateway that handles authentication

The `manage_auth` tool currently provides API key management infrastructure that can be extended for request-level authentication in future versions.

### Using API Keys

The authentication system stores hashed API keys that can be used to secure connections to backend services. Keys are managed through the `manage_auth` tool:

```python
# Enable authentication tracking
manage_auth(action="enable")

# Create a key for a backend service
manage_auth(action="create_key", client_name="backend-service")

# Check status
manage_auth(action="status")
```

### Security Best Practices

The authentication implementation follows MCP security best practices:

1. **Secure Token Storage**: API keys are hashed using SHA-256 before storage
2. **Per-Client Authorization**: Each client has a unique API key for tracking and revocation
3. **No Plaintext Tokens**: Raw API keys are never stored, only their hashes
4. **Persistent Configuration**: Authentication settings persist in `data/auth.json`
5. **TLS Support**: Always use HTTPS in production to protect API keys in transit

**Note:** Authentication configuration is stored in `data/auth.json` (gitignored by default).

## Environment Variables

- `MCP_CONFIG_FILE`: Path to the static configuration file
  - Local development default: `./data/mcp.json`
  - Docker default: `/app/data/mcp.json`
- `MCP_PROXIES_FILE`: Path to the dynamic proxies file
  - Local development default: `./data/proxies.json`
  - Docker default: `/app/data/proxies.json`
- `MCP_AUTH_CONFIG_FILE`: Path to the authentication configuration file
  - Local development default: `./data/auth.json`
  - Docker default: `/app/data/auth.json`
- `PYTHONPATH`: Python module search path
  - Local development: `./src`
  - Docker: `/app/src`

## Project Structure

```
drunk-mcp-proxy/
├── src/
│   ├── main.py          # Main application code
│   ├── auth.py          # Authentication module
│   └── validation.py    # JSON schema validation
├── schemas/
│   ├── mcp.schema.json      # Schema for mcp.json
│   ├── proxies.schema.json  # Schema for proxies.json
│   └── auth.schema.json     # Schema for auth.json
├── data/
│   ├── mcp.json         # Static server configuration
│   ├── proxies.json     # Dynamic proxies (created at runtime)
│   └── auth.json        # Authentication config (created at runtime)
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
- FastMCP 2.0.0+

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, modify `docker-compose.yml` to use a different port:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead
```

### Proxy Configuration Not Loading
1. Check that `data/mcp.json` exists and has valid JSON syntax
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
