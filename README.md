# drunk-mcp-proxy

A dynamic proxy server for Model Context Protocol (MCP) built with Python and FastMCP. This service allows you to proxy and manage multiple MCP backend servers through a single unified interface.

## Features

- 🚀 **Dynamic Proxy Management**: Add and manage MCP servers on the fly
- 📝 **Static Configuration**: Define default servers in `config.json`
- 💾 **Persistent Storage**: Dynamic proxies are saved to `proxies.json`
- 🐳 **Docker Support**: Fully containerized with Docker and Docker Compose
- 🔌 **Multiple Transports**: Support for HTTP and SSE transports
- 🛠️ **Built-in Tools**: List, add, and manage proxy servers via MCP tools

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

2. Edit `config.json` to add your default MCP servers:
```json
{
  "mcpServers": {
    "default": {
      "url": "https://example.com/mcp",
      "transport": "http"
    }
  }
}
```

3. Start the service:
```bash
docker-compose up -d
```

4. View logs:
```bash
docker-compose logs -f
```

### Using Docker

1. Build the image:
```bash
docker build -t drunk-mcp-proxy .
```

2. Run the container:
```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config.json:/app/config.json:ro \
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
python main.py
```

## Configuration

### Static Configuration (config.json)

Define your default MCP servers in `config.json`:

```json
{
  "mcpServers": {
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

### Dynamic Proxies

Dynamic proxies are added at runtime using the `add_proxy` tool and stored in `proxies.json`. These persist across restarts.

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

## Environment Variables

- `MCP_CONFIG_FILE`: Path to the static configuration file (default: `config.json`)
- `MCP_PROXIES_FILE`: Path to the dynamic proxies file (default: `proxies.json`)

## Project Structure

```
drunk-mcp-proxy/
├── main.py              # Main application code
├── config.json          # Static server configuration
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
python main.py
```

3. The server will start and display mounted proxies:
```
==================================================
Starting MCP Proxy Server
==================================================
Mounting static servers from config.json:
  ✓ Mounted 'default' at https://example.com/mcp
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
1. Check that `config.json` exists and has valid JSON syntax
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
