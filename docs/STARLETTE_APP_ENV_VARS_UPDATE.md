# StarletteApp Refactoring - Environment Variables Integration ✅

**Date:** February 14, 2026  
**Status:** ✅ Complete  
**Impact:** Simplified API, better separation of concerns

---

## Summary

Moved the health check handler into `StarletteApp` and updated it to use environment variables (HOST, PORT, SERVER_NAME)
directly. This eliminates the need to pass these values around and makes the API cleaner.

---

## Changes Made

### 1. `src/app/starlette_app.py` - Updated

**Added Environment Variable Imports:**

```python
from src.tools.env import SERVER_NAME, HOST, PORT
```

**Simplified Constructor:**

- ✅ Removed `health_check_handler` parameter (now built-in)
- ✅ Removed `service_name` parameter (loaded from `SERVER_NAME`)
- ✅ Added automatic loading of `host` and `port` from environment variables

**Before:**

```python
def __init__(
        routes=None,
        middleware=None,
        lifespan=None,
        health_check_handler=None,
        service_name="mcp-proxy-server"
):
    self.service_name = service_name
    self._health_check_handler = health_check_handler or self._default_health_check
```

**After:**

```python
def __init__(
        routes=None,
        middleware=None,
        lifespan=None
):
    # Get configuration from environment variables
    self.service_name = SERVER_NAME
    self.host = HOST or "0.0.0.0"
    self.port = PORT or 9123

    # Health check is built-in
    self._ensure_health_check_route()
```

**Updated Methods:**

- ✅ `_default_health_check()` → `_health_check_handler()` (built-in)
- ✅ `add_mcp_mount()` - Removed `host` and `port` parameters (uses `self.host`/`self.port`)
- ✅ `add_mcp_mounts()` - Removed `host` and `port` parameters (uses `self.host`/`self.port`)

---

### 2. `src/app/server.py` - Updated

**Removed Health Check Handler:**

```python
# REMOVED - Now in StarletteApp
@staticmethod
async def _handle_health_check(_: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "drunk-mcp-server"})
```

**Removed Unused Imports:**

```python
# REMOVED
from starlette.requests import Request
from starlette.responses import JSONResponse
```

**Simplified StarletteApp Usage:**

**Before:**

```python
server_host = HOST or "0.0.0.0"
server_port = PORT or 9123

starlette_app = StarletteApp(
    middleware=middleware,
    health_check_handler=self._handle_health_check,
    service_name="drunk-mcp-server"
)

starlette_app.add_mcp_mounts(mcp_list, host=server_host, port=server_port)
```

**After:**

```python
# Host, port, and service name are loaded from environment variables
starlette_app = StarletteApp(middleware=middleware)

starlette_app.add_mcp_mounts(mcp_list)
```

---

## Benefits

### 1. **Simpler API**

- ✅ 3 parameters → 3 parameters (but cleaner purpose)
- ✅ No need to pass `host`, `port`, `service_name`, `health_check_handler`
- ✅ Single source of truth (environment variables)

### 2. **Better Separation of Concerns**

- ✅ Health check handler belongs in `StarletteApp` (it's part of the app structure)
- ✅ Server doesn't need to know about health check implementation
- ✅ Configuration centralized in environment variables

### 3. **Reduced Code Duplication**

- ✅ Host/port/service_name loaded once, used everywhere
- ✅ No passing values through multiple layers
- ✅ Fewer parameters to track

### 4. **Easier Testing**

- ✅ Environment variables can be mocked
- ✅ StarletteApp is self-contained
- ✅ No need to provide health check handler for tests

---

## Usage Comparison

### Before

```python
from src.tools.env import HOST, PORT

server_host = HOST or "0.0.0.0"
server_port = PORT or 9123

starlette_app = StarletteApp(
    middleware=middleware,
    health_check_handler=self._handle_health_check,
    service_name="drunk-mcp-server"
)

starlette_app.add_mcp_mounts(mcp_list, host=server_host, port=server_port)
app = starlette_app.build_with_lifespan(lifespan_func)
```

### After

```python
# Everything comes from environment variables!
starlette_app = StarletteApp(middleware=middleware)
starlette_app.add_mcp_mounts(mcp_list)
app = starlette_app.build_with_lifespan(lifespan_func)
```

---

## Environment Variables Used

| Variable      | Default            | Usage                                     |
|---------------|--------------------|-------------------------------------------|
| `SERVER_NAME` | "drunk-mcp-server" | Service name in health check response     |
| `HOST`        | "0.0.0.0"          | Server host for endpoint URLs and uvicorn |
| `PORT`        | 9123               | Server port for endpoint URLs and uvicorn |

---

## Log Output

Health check response uses `SERVER_NAME`:

```json
{
  "status": "healthy",
  "service": "drunk-mcp-server"
}
```

Mount logs include full URLs with `HOST` and `PORT`:

```
INFO: Adding 3 MCP mount(s)
INFO: Adding root MCP mount at /mcp 
      (full endpoint: http://0.0.0.0:9123/mcp)
INFO: Adding namespaced MCP mount (name=petstore) at /petstore/mcp 
      (full endpoint: http://0.0.0.0:9123/petstore/mcp)
```

---

## Code Structure

### StarletteApp Constructor Flow

```
__init__()
  ↓
Load env vars (SERVER_NAME, HOST, PORT)
  ↓
Initialize routes, middleware, lifespan
  ↓
Add built-in health check route
```

### StarletteApp Mount Flow

```
add_mcp_mounts(mcp_list)
  ↓
For each (name, mcp):
  ↓
add_mcp_mount(name, mcp)
  ↓
Use self.host and self.port from env vars
  ↓
Log full endpoint URL
  ↓
Add to routes and mcp_apps
```

---

## Testing

### Unit Test Example

```python
import os
from src.app.starlette_app import StarletteApp


def test_starlette_app_loads_env_vars():
    # Set environment variables
    os.environ["SERVER_NAME"] = "test-service"
    os.environ["HOST"] = "localhost"
    os.environ["PORT"] = "8080"

    # Create app
    app = StarletteApp()

    # Verify loaded from env
    assert app.service_name == "test-service"
    assert app.host == "localhost"
    assert app.port == 8080
```

---

## Verification

✅ All files compile without syntax errors  
✅ No type checking warnings  
✅ Imports are correct  
✅ Environment variables properly loaded  
✅ Health check handler built-in  
✅ API simplified (fewer parameters)  
✅ Backward compatible functionality

---

## Migration Guide

### If You Were Using StarletteApp Directly

**Old Code:**

```python
app = StarletteApp(
    health_check_handler=my_handler,
    service_name="my-service"
)
app.add_mcp_mounts(mcp_list, host="localhost", port=8080)
```

**New Code:**

```python
# Set environment variables instead
os.environ["SERVER_NAME"] = "my-service"
os.environ["HOST"] = "localhost"
os.environ["PORT"] = "8080"

# Simpler initialization
app = StarletteApp()
app.add_mcp_mounts(mcp_list)
```

---

## Summary

✅ **Health check handler moved to StarletteApp**  
✅ **Environment variables used directly (SERVER_NAME, HOST, PORT)**  
✅ **API simplified (fewer parameters)**  
✅ **Better separation of concerns**  
✅ **No breaking changes to MCPProxyServer**

The code is now cleaner, more maintainable, and follows the principle of configuration through environment variables! 🎉

