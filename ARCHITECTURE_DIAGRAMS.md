# MCPProxyServer Architecture & Flow Diagrams

## Class Structure

```
MCPProxyServer
├── __init__()
│   ├── logger
│   └── auth_provider
│
├── Health Check Endpoint
│   └── _health_check_starlette(request)
│
├── Lifespan Management (Private)
│   └── _combined_lifespan(app, mcp_apps) [Async Context Manager]
│       ├── Startup Phase
│       │   ├── Log startup
│       │   ├── For each app:
│       │   │   ├── Get lifespan
│       │   │   ├── Enter context
│       │   │   └── Track or log error
│       │   └── Raise if errors
│       └── Shutdown Phase (finally)
│           ├── Log shutdown
│           ├── For each app (reversed):
│           │   ├── Exit context
│           │   └── Log error if any
│           └── Log warnings if errors
│
├── Server Execution (Private)
│   └── _run_server_async(mcp_list, middleware)
│       ├── Try block:
│       │   ├── Log app count
│       │   ├── For each app:
│       │   │   ├── Get HTTP app
│       │   │   ├── Mount to route
│       │   │   └── Add to list
│       │   ├── Create Starlette app
│       │   ├── Create uvicorn config
│       │   └── Start server
│       ├── Except ImportError:
│       │   └── Raise with helpful message
│       └── Except Exception:
│           ├── Log error
│           └── Raise
│
├── Proxy Management (Private)
│   ├── _validate_proxies(proxies)
│   │   ├── Check for None instances
│   │   ├── Check for duplicate namespaces
│   │   └── Log validation results
│   │
│   └── _mount_proxies(proxies)
│       ├── Create root FastMCP server
│       ├── For each proxy:
│       │   ├── Try:
│       │   │   ├── If no namespace: mount to root
│       │   │   ├── Else: create namespaced server
│       │   │   └── Log success
│       │   └── Except: Log error and track
│       ├── Check if all failed -> Raise RuntimeError
│       ├── Log warnings if partial failure
│       └── Return list of (name, FastMCP) servers
│
├── Configuration & Monitoring (Private)
│   ├── _get_server_config()
│   │   └── Return dict with all config values
│   │
│   └── _log_server_info()
│       ├── Get config
│       └── Log each config item
│
└── Application Entry Points (Public)
    ├── run_async()
    │   ├── Try:
    │   │   ├── Log startup
    │   │   ├── _log_server_info()
    │   │   ├── Load proxies
    │   │   ├── _validate_proxies()
    │   │   ├── _mount_proxies()
    │   │   └── _run_server_async()
    │   ├── Except KeyboardInterrupt:
    │   │   └── Log interrupt
    │   └── Except Exception:
    │       ├── Log error
    │       └── Raise
    │
    └── run()
        └── asyncio.run(run_async())
```

## Startup Flow Diagram

```
┌─────────────────────────────────────────┐
│ MCPProxyServer()                        │
│ Create instance                         │
└─────────────────┬───────────────────────┘
                  │
                  v
┌─────────────────────────────────────────┐
│ .run() or .run_async()                  │
│ Entry point                             │
└─────────────────┬───────────────────────┘
                  │
                  v
┌─────────────────────────────────────────┐
│ Log server configuration                │
│ _log_server_info()                      │
└─────────────────┬───────────────────────┘
                  │
                  v
┌─────────────────────────────────────────┐
│ Load proxy configs from CONFIG_DIR      │
│ create_static_proxies(CONFIG_DIR)       │
│ Returns: [(namespace, proxy), ...]      │
└──┬──────────────────────────────────┬───┘
   │                                  │
   v (found proxies)                  v (no proxies)
┌─────────────────┐            ┌──────────────┐
│ Log: Loaded N   │            │ Log: Warning │
│ proxy configs   │            │ No proxies   │
└────────┬────────┘            └──────┬───────┘
         │                            │
         v (both paths merge)         │
         └────────────────┬───────────┘
                          │
                          v
┌─────────────────────────────────────────┐
│ Validate proxies                        │
│ _validate_proxies(proxies)              │
│ - Check for None instances              │
│ - Check for duplicate namespaces        │
└──┬──────────────────────────────────┬───┘
   │                                  │
   v (valid)                          v (invalid)
┌─────────────────┐            ┌──────────────┐
│ Continue        │            │ Raise        │
│                 │            │ ValueError   │
└────────┬────────┘            └──────┬───────┘
         │                            │
         v (valid path)               v (error path)
         │                       ┌────────┐
         │                       │ Except │
         │                       └────┬───┘
         │                            v
         │                       ┌─────────────┐
         │                       │ Log error   │
         │                       │ Raise       │
         │                       └─────────────┘
         │
         v
┌─────────────────────────────────────────┐
│ Mount proxies to FastMCP servers        │
│ _mount_proxies(proxies)                 │
│                                         │
│ For each (namespace, proxy):            │
│   If namespace is None:                 │
│     Mount to root server                │
│   Else:                                 │
│     Create namespaced FastMCP server    │
│     Mount proxy to it                   │
│                                         │
│ Returns: [(name, FastMCP), ...]         │
└──┬──────────────────────────────────┬───┘
   │                                  │
   v (success)                        v (all failed)
┌─────────────────┐            ┌──────────────┐
│ Log: Mounted N  │            │ Raise        │
│ MCP servers     │            │ RuntimeError │
└────────┬────────┘            └──────┬───────┘
         │                            │
         v (mount path)               v (error path)
         │                       ┌────────┐
         │                       │ Except │
         │                       └────┬───┘
         │                            v
         │                       ┌─────────────┐
         │                       │ Log error   │
         │                       │ Raise       │
         │                       └─────────────┘
         │
         v
┌─────────────────────────────────────────┐
│ Run async server                        │
│ _run_server_async(mcp_list, middleware) │
│                                         │
│ 1. For each FastMCP in mcp_list:        │
│    - Create HTTP app                    │
│    - Mount to Starlette route           │
│                                         │
│ 2. Create Starlette app with:           │
│    - All routes (health + MCP mounts)   │
│    - Middleware                         │
│    - Lifespan (_combined_lifespan)      │
│                                         │
│ 3. Create uvicorn Config                │
│ 4. Create uvicorn Server                │
│ 5. await server.serve()                 │
│                                         │
│ This blocks until server shutdown       │
└──┬──────────────────────────────────┬───┘
   │                                  │
   v (running)                        v (import error)
   │                            ┌─────────────────┐
   │                            │ Raise ImportError
   │                            │ with message    │
   │                            └────────┬────────┘
   │                                     │
   │                            (error path)
   │
   v (server running)
┌──────────────────────────┐
│ SERVER IS RUNNING        │
│                          │
│ Handles requests via:    │
│ - /health endpoint       │
│ - /mcp/* endpoints       │
│ - /{name}/mcp/* endpoints
│                          │
│ Manages lifespans via:   │
│ _combined_lifespan()     │
└──────────────────────────┘
   │
   │ (on shutdown - SIGTERM/SIGINT)
   v
┌──────────────────────────────────────┐
│ _combined_lifespan shutdown phase    │
│                                      │
│ For each MCP app (reversed order):   │
│   Try:                               │
│     Exit context                     │
│     Log success                      │
│   Except:                            │
│     Log error (don't block)          │
│                                      │
│ If any errors:                       │
│   Log warning about failures         │
│ Else:                                │
│   Clean shutdown                     │
└──────────────────────────────────────┘
   │
   v
┌──────────────────────────────────────┐
│ Server stopped                       │
│ All resources cleaned up             │
└──────────────────────────────────────┘
```

## Lifespan Context Manager Detail

```
_combined_lifespan(app, mcp_apps)
│
├─ STARTUP PHASE (try block)
│  │
│  ├─ self.logger.info("Starting lifespans for %d MCP apps", len(mcp_apps))
│  │
│  ├─ lifespan_contexts = []
│  ├─ startup_errors = []
│  │
│  └─ for name, mcp_app in mcp_apps:
│     │
│     ├─ lifespan = getattr(mcp_app, "lifespan", None)
│     │
│     ├─ if lifespan is None:
│     │  └─ self.logger.warning("MCP app missing lifespan (name=%s)", name)
│     │     continue
│     │
│     └─ try:
│        │
│        ├─ ctx = lifespan(mcp_app)
│        ├─ await ctx.__aenter__()
│        ├─ lifespan_contexts.append(ctx)
│        ├─ self.logger.debug("Successfully started...")
│        │
│        └─ except Exception as e:
│           ├─ self.logger.error("Failed to start lifespan...", exc_info=True)
│           └─ startup_errors.append((name, e))
│
│  ├─ if startup_errors:
│  │  ├─ self.logger.error("Failed to start %d MCP app lifespan(s)...")
│  │  └─ raise RuntimeError(f"MCP app startup failed: {startup_errors}")
│  │
│  └─ self.logger.info("All MCP app lifespans started successfully")
│
├─ yield  ← Returns control to calling code (server runs here)
│
└─ SHUTDOWN PHASE (finally block)
   │
   ├─ self.logger.info("Shutting down %d MCP app lifespan(s)...")
   │
   ├─ shutdown_errors = []
   │
   └─ for idx, ctx in enumerate(reversed(lifespan_contexts)):
      │
      └─ try:
         │
         ├─ await ctx.__aexit__(None, None, None)
         └─ self.logger.debug("Successfully shutdown MCP app lifespan...")
         │
         except Exception as e:
         │
         ├─ self.logger.error("Error during MCP app shutdown...", exc_info=True)
         └─ shutdown_errors.append((idx, e))
      
      ├─ if shutdown_errors:
      │  └─ self.logger.warning("Encountered %d error(s) during shutdown...")
      │
      └─ (return from context manager)
```

## Error Handling Flow

```
START
 │
 ├─ Validation Error
 │  └─ ValueError → Propagate immediately
 │
 ├─ Proxy Load Error
 │  └─ Exception → Log & Propagate
 │
 ├─ Proxy Mount Error
 │  ├─ Some fail: Log warning, continue
 │  └─ All fail: RuntimeError → Propagate
 │
 ├─ Startup Error
 │  ├─ MCP lifespan fails:
 │  │  ├─ Tracked in startup_errors[]
 │  │  ├─ RuntimeError raised
 │  │  └─ Cleanup triggered
 │  │
 │  ├─ Uvicorn import fails:
 │  │  ├─ ImportError raised
 │  │  └─ Helpful message provided
 │  │
 │  └─ Server startup fails:
 │     ├─ Exception logged with trace
 │     └─ Propagated
 │
 ├─ Runtime Error
 │  └─ Handled by uvicorn/Starlette
 │
 ├─ Shutdown Error
 │  ├─ Logged (not fatal)
 │  ├─ Tracked in shutdown_errors[]
 │  └─ Shutdown continues
 │
 ├─ KeyboardInterrupt
 │  ├─ Caught in run_async()
 │  ├─ Logged: "Server interrupted by user"
 │  └─ Graceful shutdown triggered
 │
 └─ Cleanup & Exit
```

## Method Call Sequence

```
User code
    │
    v
MCPProxyServer()  ← Instantiate
    │
    v
.run() or .run_async()  ← Call entry point
    │
    v
_log_server_info()  ← Log configuration
    │
    v
create_static_proxies()  ← Load proxies (external)
    │
    v
_validate_proxies()  ← Validate
    │
    v
_mount_proxies()  ← Mount to FastMCP
    │
    v
_run_server_async()  ← Start server
    │
    ├─ Create Starlette app
    │
    └─ Pass _combined_lifespan to Starlette lifespan
        │
        v
    Starlette startup
        │
        v
    _combined_lifespan.__aenter__()  ← Server calls this on startup
        │
        v
    For each MCP app:
        │
        └─ app.lifespan.__aenter__()  ← Start each app
            │
            v
    yield  ← Server is now running
        │
        v
    [Server handles requests]
        │
        v
    KeyboardInterrupt or signal
        │
        v
    Starlette shutdown
        │
        v
    _combined_lifespan.__aexit__()  ← Server calls this on shutdown
        │
        v
    For each MCP app (reversed):
        │
        └─ app.lifespan.__aexit__()  ← Stop each app
            │
            v
    Return from context
        │
        v
    Server stopped
        │
        v
    return from run_async()
        │
        v
    Program exits
```

## Configuration Data Flow

```
Environment Variables
    │
    ├─ FASTMCP_CONFIG_DIR
    ├─ FASTMCP_LOG_LEVEL
    ├─ FASTMCP_SERVER_HOST
    ├─ FASTMCP_SERVER_PORT
    ├─ FASTMCP_SERVER_NAME
    ├─ FASTMCP_SERVER_VERSION
    └─ FASTMCP_SERVER_AUTH (optional)
    │
    v
src.tools.env  ← Load environment
    │
    ├─ CONFIG_DIR
    ├─ LOG_LEVEL
    ├─ HOST
    ├─ PORT
    ├─ SERVER_NAME
    ├─ SERVER_VERSION
    └─ _auth_provider
    │
    v
MCPProxyServer.__init__()
    │
    ├─ self.logger = logger  (from env)
    └─ self.auth_provider = _auth_provider  (from env)
    │
    v
_get_server_config()
    │
    └─ Returns dict:
       ├─ server_name
       ├─ server_version
       ├─ host
       ├─ port
       ├─ log_level
       ├─ config_dir
       └─ auth_enabled
    │
    v
_log_server_info()
    │
    └─ Logs each config item
```

## Endpoint Routing

```
Client Request
    │
    v
Starlette Router
    │
    ├─ GET /health
    │  │
    │  v
    │  _health_check_starlette(request)
    │  │
    │  └─ → {"status": "healthy", "service": "drunk-mcp-server"}
    │
    ├─ /mcp/*  (root proxy)
    │  │
    │  v
    │  Mount("/mcp", app=root_mcp_app)
    │  │
    │  └─ → Root MCP server
    │
    ├─ /{namespace}/mcp/*  (namespaced proxies)
    │  │
    │  v
    │  Mount("/{namespace}/mcp", app=namespaced_mcp_app)
    │  │
    │  └─ → Namespaced MCP server
    │
    └─ * (unknown)
       │
       v
       404 Not Found

Each MCP endpoint:
    │
    ├─ List tools
    ├─ Call tool
    ├─ SSE support
    └─ HTTP streaming
```


