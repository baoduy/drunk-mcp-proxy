# MCPProxyServer Class - Quick Reference Guide

## Usage Examples

### Basic Usage

```python
# Create and run server
server = MCPProxyServer()
await server.run_async()  # Async
server.run()  # Sync wrapper
```

### Direct Import and Use

```python
from src.app.server import MCPProxyServer


async def main():
    server = MCPProxyServer()
    await server.run_async()


# or
from src.app.server import main

main()  # Uses legacy function-based API
```

## Class Methods Overview

### Public Methods

```python
# Asynchronous entry point (recommended)
await server.run_async()

# Synchronous entry point wrapper
server.run()
```

### Private Methods (Internal Use)

#### Lifespan Management

```python
@asynccontextmanager
async def _combined_lifespan(app, mcp_apps)
# Manages startup/shutdown of all MCP apps
# - Handles errors gracefully
# - Logs all operations
# - Ensures proper cleanup order
```

#### Server Execution

```python
async def _run_server_async(mcp_list, middleware=None)
# Starts uvicorn server with Starlette app
# - Mounts all MCP apps
# - Sets up health check endpoint
# - Manages lifespan
```

#### Proxy Management

```python
def _validate_proxies(proxies)


# Validates proxy instances
# - Checks for None values
# - Detects duplicate namespaces

def _mount_proxies(proxies)
# Mounts proxies to FastMCP servers
# - Handles namespacing
# - Tracks errors separately
```

#### Configuration & Monitoring

```python
def _get_server_config()


# Returns config dict with server details

def _log_server_info()


# Logs complete server configuration

async def _health_check_starlette(request)
# Health check endpoint response
```

## Configuration Environment Variables

These are used from `src.tools.env`:

- `FASTMCP_CONFIG_DIR` - Config directory (default: "data")
- `FASTMCP_LOG_LEVEL` - Log level (default: "INFO")
- `FASTMCP_SERVER_HOST` - Server host (default: "0.0.0.0")
- `FASTMCP_SERVER_PORT` - Server port (default: 9123)
- `FASTMCP_SERVER_NAME` - Server name
- `FASTMCP_SERVER_VERSION` - Server version
- `FASTMCP_SERVER_AUTH` - Auth provider (optional)

## Startup Sequence

```
MCPProxyServer()
    ↓
.run() or .run_async()
    ↓
_log_server_info()           # Log config
    ↓
create_static_proxies()      # Load *.mcp.json files
    ↓
_validate_proxies()          # Validate loaded proxies
    ↓
_mount_proxies()             # Mount to FastMCP
    ↓
_run_server_async()          # Start uvicorn
    ↓
_combined_lifespan()         # Manage app lifespans
    ↓
Server Running...
```

## Error Handling

### Startup Errors

- Invalid proxy instances → ValueError
- Duplicate namespaces → ValueError
- Proxy mount failures → RuntimeError (partial failure ok)
- MCP app lifespan failures → RuntimeError

### Runtime Errors

- Import errors (uvicorn) → ImportError
- Server startup → Exception (logged with stack trace)

### Shutdown Errors

- Logged as warnings
- Don't prevent other apps from shutting down
- Comprehensive cleanup attempted

## Logging Output

All operations logged with timestamps and levels:

```
[INFO] Starting MCP Proxy Server
[INFO] MCP Proxy Server Configuration:
[INFO]   Server Name: drunk-mcp-server
[INFO]   Port: 9123
[INFO]   Authentication: Enabled
[INFO] Loading proxy configurations from data
[INFO] Loaded 3 proxy configuration(s)
[INFO] Mounting 3 proxy/proxies to MCP server
[DEBUG] Mounting proxy without namespace to root server
[INFO] Successfully mounted proxy to root server
[DEBUG] Creating namespaced MCP server (namespace=stock)
[INFO] Successfully mounted proxy with namespace (namespace=stock)
[INFO] Mounted 2 MCP server(s) with 3 proxy/proxies
[INFO] Mounting 2 MCP application(s)
[INFO] Mounting namespaced MCP app (name=stock) at /stock/mcp
[INFO] Creating uvicorn server (host=0.0.0.0, port=9123, log_level=info)
[INFO] Starting uvicorn server
[INFO] Starting lifespans for 2 MCP apps
[DEBUG] Successfully started lifespan for MCP app (name=None)
[DEBUG] Successfully started lifespan for MCP app (name=stock)
[INFO] All MCP app lifespans started successfully

[Ready for requests...]

[INFO] Shutting down 2 MCP app lifespan(s)
[DEBUG] Successfully shutdown MCP app lifespan (index=0)
[INFO] Server interrupted by user
```

## Endpoint Details

### Health Check

- **Path**: `/health`
- **Method**: GET
- **Response**: `{"status": "healthy", "service": "drunk-mcp-server"}`
- **Use**: Kubernetes probes, load balancer health checks

### MCP Endpoints

- **Root**: `/mcp` (if namespace is None)
- **Namespaced**: `/{namespace}/mcp`
- **Methods**: Configured by FastMCP

## Testing

```python
# Test instantiation
server = MCPProxyServer()
assert server.logger is not None
assert server.auth_provider is not None or server.auth_provider is None

# Test configuration
config = server._get_server_config()
assert "server_name" in config
assert "port" in config

# Test validation
proxies = []
server._validate_proxies(proxies)  # Should warn but not raise

# Test with mock proxies (requires FastMCPProxy instances)
# Full integration testing requires running the actual server
```

## Related Files

- `src/app/server.py` - Main implementation
- `src/tools/env.py` - Configuration loading
- `src/tools/logging_config.py` - Logging setup
- `src/app/auth.py` - Authentication provider builder
- `src/app/middleware.py` - Middleware configuration
- `src/proxies/static_proxies.py` - Proxy loader

## Version History

- **Current**: Refactored to class-based architecture with comprehensive error handling
- **Previous**: Function-based implementation (still supported via legacy API)

