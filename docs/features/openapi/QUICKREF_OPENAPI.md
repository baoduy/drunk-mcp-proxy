# OpenAPI MCP Proxy Loader - Quick Reference

## Installation

No additional installation needed - uses FastMCP's built-in OpenAPI support.

## File Structure

```
drunk-mcp-proxy/
├── data/
│   ├── mcp.json                    # Root static proxy config (optional)
│   ├── stock.mcp.json              # Static proxy config
│   ├── wiki.mcp.json               # Static proxy config
│   ├── petstore.openapi.json       # OpenAPI spec (NEW)
│   └── api.openapi.json            # OpenAPI spec (NEW)
├── src/
│   ├── proxies/
│   │   ├── static_proxies.py       # StaticProxyLoader
│   │   └── openapi_proxies.py      # OpenApiMcpProxyLoader (NEW)
│   └── app/
│       └── server.py               # Updated to load both types
```

## Quick Start

### 1. Create OpenAPI File

Save as `data/myapi.openapi.json`:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "My API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.example.com"
    }
  ],
  "paths": {
    "/users": {
      "get": {
        "operationId": "getUsers",
        "responses": {
          "200": {
            "description": "List of users"
          }
        }
      }
    }
  }
}
```

### 2. Start Server

```bash
python -m src.main
```

### 3. Use the API

The server creates:

- Tools for each OpenAPI endpoint
- Mount point: `/myapi/mcp`
- Tool names: `{namespace}__{operationId}`

## API Reference

### Class: `OpenApiMcpProxyLoader`

```python
from src.proxies.openapi_proxies import OpenApiMcpProxyLoader

loader = OpenApiMcpProxyLoader("data")
servers = loader.load_all_servers()
```

#### Methods

| Method                                                 | Returns                             | Purpose                                     |
|--------------------------------------------------------|-------------------------------------|---------------------------------------------|
| `load_all_servers(auth_provider=None)`                 | `list[tuple[str, FastMCP]]`         | Load all OpenAPI servers                    |
| `build_mcp_servers(root_server, auth_provider=None)`   | `list[tuple[str \| None, FastMCP]]` | Build and return all servers including root |
| `discover_and_load_config_files()`                     | `list[tuple[str, dict]]`            | Find and load OpenAPI specs                 |
| `create_servers_from_specs(specs, auth_provider=None)` | `list[tuple[str, FastMCP]]`         | Create servers from specs                   |

### Function: `create_openapi_servers()` (Legacy API)

```python
from src.proxies.openapi_proxies import create_openapi_servers

servers = create_openapi_servers("data")
```

## OpenAPI File Format

### Minimal Valid Example

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.example.com"
    }
  ],
  "paths": {}
}
```

### Required Fields

- `openapi`: Version string
- `info.title`: API name
- `info.version`: API version
- `servers[0].url`: Base API URL
- `paths`: API endpoints object (can be empty)

## Naming Convention

| File Name               | Namespace  | Server Name            |
|-------------------------|------------|------------------------|
| `petstore.openapi.json` | `petstore` | `petstore-openapi-mcp` |
| `api.openapi.json`      | `api`      | `api-openapi-mcp`      |
| `v2-users.openapi.json` | `v2-users` | `v2-users-openapi-mcp` |

## Mount Paths

Each OpenAPI server is mounted at:

```
/{namespace}/mcp
```

### Examples

- Petstore API: `http://server:9123/petstore/mcp`
- Users API: `http://server:9123/users/mcp`
- Weather API: `http://server:9123/weather/mcp`

## Debugging

### Enable Debug Logging

```bash
export FASTMCP_LOG_LEVEL=DEBUG
python -m src.main
```

### Check Loaded Servers

Look for log messages like:

```
INFO: Loaded OpenAPI specification (namespace=petstore) from data/petstore.openapi.json
INFO: Created FastMCP server (namespace=petstore, name=petstore-openapi-mcp, base_url=...)
```

## Common Issues

### File Not Found

**Problem**: OpenAPI file not loading

**Solution**:

- Check filename ends with `.openapi.json`
- Ensure file is in the `data/` directory
- Verify the directory in config: `FASTMCP_CONFIG_DIR=data`

### Invalid OpenAPI

**Problem**: "No servers defined" error

**Solution**:

- Add `servers` array with at least one URL
- Example: `"servers": [{"url": "https://api.example.com"}]`

### No Tools Created

**Problem**: Server loads but no tools available

**Solution**:

- Add `paths` object with API endpoints
- Each endpoint becomes a tool
- Verify OpenAPI format is valid

## Examples

### Example 1: Public Weather API

File: `data/weather.openapi.json`

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Weather API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.open-meteo.com/v1"
    }
  ],
  "paths": {
    "/forecast": {
      "get": {
        "operationId": "getWeather",
        "parameters": [
          {
            "name": "latitude",
            "in": "query",
            "schema": {
              "type": "number"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Weather forecast"
          }
        }
      }
    }
  }
}
```

Access at: `http://server:9123/weather/mcp`

### Example 2: Internal Enterprise API

File: `data/internal.openapi.json`

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Internal API",
    "version": "2.0.0"
  },
  "servers": [
    {
      "url": "https://internal.company.com/api/v2"
    }
  ],
  "paths": {
    "/employees": {
      "get": {
        "operationId": "listEmployees",
        "responses": {
          "200": {
            "description": "Employee list"
          }
        }
      }
    }
  }
}
```

Access at: `http://server:9123/internal/mcp`

## Performance Tips

1. **Caching**: Servers are cached after first load
2. **Lazy Loading**: Servers only created when first accessed
3. **Reload**: Create new loader instance to force reload from disk
4. **Batching**: Load multiple APIs in one server startup

## Architecture Diagram

```
MCPProxyServer
    │
    ├── StaticProxyLoader
    │   └── Loads *.mcp.json files
    │       └── Creates proxies to remote MCP servers
    │
    └── OpenApiMcpProxyLoader (NEW)
        └── Loads *.openapi.json files
            └── Creates FastMCP servers from OpenAPI specs
                └── Each server mounted at /{namespace}/mcp

Mount Structure:
/mcp              → Root MCP server
/stock/mcp        → Static proxy
/petstore/mcp     → OpenAPI server
/api/mcp          → OpenAPI server
```

## See Also

- [OPENAPI_LOADER_GUIDE.md](OPENAPI_LOADER_GUIDE.md) - Full documentation
- [BUILD_MCP_SERVERS_QUICK_REF.md](BUILD_MCP_SERVERS_QUICK_REF.md) - StaticProxyLoader reference
- [FastMCP OpenAPI Integration](https://gofastmcp.com/integrations/openapi)

