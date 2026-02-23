# OpenAPI MCP Proxy Loader

## Overview

The `OpenApiMcpProxyLoader` is a new loader class that transforms OpenAPI specifications into FastMCP servers. Unlike
`StaticProxyLoader` which creates proxies to remote MCP servers, this loader directly builds MCP servers from OpenAPI
API definitions.

## Key Features

- **Automatic Discovery**: Loads all `*.openapi.json` files from a configured directory
- **Namespace Support**: Each OpenAPI spec becomes a namespaced server to avoid tool name conflicts
- **Standard OpenAPI 3.0+**: Works with any valid OpenAPI 3.0 or higher specification
- **Caching**: Automatically caches loaded servers to avoid redundant file I/O
- **Error Resilience**: Continues processing remaining specs if one fails

## File Naming Convention

Files must follow the naming pattern: `{name}.openapi.json`

### Valid Examples

- `petstore.openapi.json` → namespace: `"petstore"`
- `api.openapi.json` → namespace: `"api"`
- `weather.openapi.json` → namespace: `"weather"`

### Invalid Examples

- `openapi.json` → Ignored (no root OpenAPI config)
- `config.json` → Ignored (wrong extension)
- `.openapi.json` → Ignored (no name prefix)

## OpenAPI Specification Requirements

Each `.openapi.json` file must contain a valid OpenAPI 3.0+ specification with:

### Required Fields

1. **openapi**: Version string (e.g., `"3.0.0"`, `"3.1.0"`)
2. **info**: Object containing:
    - `title`: API name
    - `version`: API version
3. **servers**: Array with at least one server object containing:
    - `url`: Base URL for the API (e.g., `"https://api.example.com/v1"`)
4. **paths**: Object containing API endpoints

### Example Structure

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "My API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.example.com/v1"
    }
  ],
  "paths": {
    "/users": {
      "get": {
        "summary": "List users",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  }
}
```

## Integration with MCP Proxy Server

### Automatic Integration

When the MCPProxyServer starts, it automatically:

1. Loads all static proxy configurations (`.mcp.json` files)
2. Loads all OpenAPI specifications (`.openapi.json` files)
3. Mounts them all to the root server with proper namespacing

### Mount Paths

- Static proxies: `/{namespace}/mcp` (e.g., `/stock/mcp`)
- OpenAPI servers: `/{namespace}/mcp` (e.g., `/petstore/mcp`)

## Usage Example

### 1. Create an OpenAPI File

Save as `data/petstore.openapi.json`:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Swagger Petstore",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "http://petstore.swagger.io/v1"
    }
  ],
  "paths": {
    "/pets": {
      "get": {
        "summary": "List all pets",
        "operationId": "listPets",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "schema": {
              "type": "integer"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "A list of pets"
          }
        }
      }
    }
  }
}
```

### 2. Start the Server

```bash
python -m src.main
```

The server will:

- Load the petstore.openapi.json file
- Create a FastMCP server named `petstore-openapi-mcp`
- Mount it at `/petstore/mcp`

### 3. Using the OpenAPI Tools

The OpenAPI tools are now available through the MCP protocol:

```python
# List available tools
GET / petstore / mcp / tools

# Call the listPets tool
POST / petstore / mcp / tools / petstore__listPets / call
{
    "arguments": {
        "limit": 10
    }
}
```

## Programmatic Usage

### Using the Loader Class

```python
from fastmcp import FastMCP
from src.proxies.openapi_proxies import OpenApiMcpProxyLoader

# Create loader
loader = OpenApiMcpProxyLoader("data")

# Load all OpenAPI servers
servers = loader.load_all_servers()

# Create root MCP server
root_mcp = FastMCP("my-server", version="1.0.0")

# Build servers (returns list of (namespace, mcp_server) tuples)
mcp_list = loader.build_mcp_servers(root_mcp)

# Mount to your server
for namespace, server in mcp_list:
    if namespace:
        # Mount namespaced server
        pass
    else:
        # Mount root server
        pass
```

### Using the Legacy Function API

```python
from src.proxies.openapi_proxies import create_openapi_servers

# Create servers from all OpenAPI files
servers = create_openapi_servers("data")

for namespace, mcp_server in servers:
    print(f"Created server: {namespace}")
```

## How It Works

### Processing Flow

1. **Discovery**: Scans config directory for `*.openapi.json` files
2. **Loading**: Reads and validates each OpenAPI specification
3. **Validation**: Checks for required fields (openapi, info, servers, paths)
4. **Server Creation**: Creates a FastMCP server for each spec
5. **Provider Setup**: Adds OpenAPIProvider to each server
6. **Caching**: Stores created servers in memory
7. **Mounting**: Adds servers to the root server for serving

### HTTP Client Management

Each OpenAPI server gets an `httpx.AsyncClient` configured with:

- **Base URL**: Extracted from the OpenAPI spec's `servers[0].url`
- **Async Support**: Uses AsyncClient for non-blocking API calls
- **Automatic Cleanup**: FastMCP manages the client lifecycle

## Error Handling

### Graceful Degradation

If an OpenAPI spec has issues, the loader:

- Logs the error with details
- Skips that spec
- Continues processing remaining specs
- Returns a partial list of successfully created servers

### Common Issues

| Issue                   | Solution                                    |
|-------------------------|---------------------------------------------|
| Missing `servers` field | Add at least one server object with a `url` |
| Empty server URL        | Provide a valid base URL for the API        |
| Invalid JSON            | Check JSON syntax with a JSON validator     |
| Missing required fields | Ensure `openapi`, `info`, and `paths` exist |

## Caching Behavior

### First Load

```python
loader = OpenApiMcpProxyLoader("data")
servers = loader.load_all_servers()  # Loads from disk
```

### Subsequent Calls

```python
servers = loader.load_all_servers()  # Returns cached servers (no disk I/O)
```

### Force Reload

```python
loader = OpenApiMcpProxyLoader("data")  # Create new instance
servers = loader.load_all_servers()  # Fresh load from disk
```

## Configuration Examples

### Example 1: Simple REST API

File: `data/jsonplaceholder.openapi.json`

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "JSONPlaceholder API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://jsonplaceholder.typicode.com"
    }
  ],
  "paths": {
    "/posts": {
      "get": {
        "operationId": "getPosts",
        "responses": {
          "200": {
            "description": "List of posts"
          }
        }
      }
    }
  }
}
```

### Example 2: API with Authentication

File: `data/secure-api.openapi.json`

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Secure API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.example.com/v1"
    }
  ],
  "components": {
    "securitySchemes": {
      "bearerAuth": {
        "type": "http",
        "scheme": "bearer"
      }
    }
  },
  "security": [
    {
      "bearerAuth": []
    }
  ],
  "paths": {
    "/protected": {
      "get": {
        "operationId": "getProtected",
        "responses": {
          "200": {
            "description": "Protected resource"
          }
        }
      }
    }
  }
}
```

## Logging

The loader provides detailed logging at each step:

```
INFO: Loading OpenAPI specification file: data/petstore.openapi.json
DEBUG: Loaded OpenAPI spec (version=3.0.0, title=Swagger Petstore, api_version=1.0.0)
INFO: Creating FastMCP servers from 1 OpenAPI specification(s)
INFO: Created FastMCP server (namespace=petstore, name=petstore-openapi-mcp, base_url=http://petstore.swagger.io/v1)
DEBUG: Cached 1 OpenAPI server(s) for future calls
INFO: OpenAPI server load process complete: 1 server(s) created
```

## Differences from StaticProxyLoader

| Feature      | StaticProxyLoader           | OpenApiMcpProxyLoader        |
|--------------|-----------------------------|------------------------------|
| Config Files | `*.mcp.yaml`                | `*.openapi.json`             |
| Root Config  | `mcp.yaml` (optional)       | Not supported                |
| Purpose      | Proxy to remote MCP servers | Build MCP from OpenAPI specs |
| Creation     | Uses `create_proxy()`       | Uses `OpenAPIProvider`       |
| Tools        | Proxied from remote MCP     | Generated from OpenAPI       |
| HTTP Client  | Managed by proxy            | Created per server           |

## Reference

- [FastMCP OpenAPI Integration](https://gofastmcp.com/integrations/openapi)
- [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.3)
- [FastMCP Documentation](https://github.com/jaidyn-ai/FastMCP)

