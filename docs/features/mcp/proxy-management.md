# MCP Proxy Management

## Overview

drunk-mcp-proxy provides comprehensive management for proxying MCP (Model Context Protocol) services. It aggregates multiple MCP servers into a unified interface, with support for namespacing to prevent tool name conflicts.

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                    MCP Service Proxy Architecture                      │
└────────────────────────────────────────────────────────────────────────┘

Configuration Loading:
┌──────────────┐         ┌──────────────────┐         ┌───────────────┐
│ config.json  │────────>│ ProxyConfig      │────────>│ SpecConfig    │
│              │         │ Provider         │         │ Instances     │
│ - MCP specs  │         │                  │         │               │
│ - Paths      │         │ Loads & validates│         │ Per-service   │
└──────────────┘         └──────────────────┘         └───────────────┘
                                  |
                                  v
                         ┌────────────────────┐
                         │ Filter by spec_type│
                         │ = "mcp"            │
                         └────────────────────┘
                                  |
                                  v
Proxy Creation:
┌──────────────────────────────────────────────────────────────────────┐
│ For each MCP config:                                                 │
│  1. Load MCP spec file (mcp.json, stock.mcp.json, etc.)             │
│  2. Create FastMCP proxy via create_proxy(spec_data, name)           │
│  3. Handle special case for root path ("/")                          │
│  4. Apply authentication provider if configured                      │
│  5. Mount at appropriate HTTP path                                   │
└──────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
FastMCP Server Structure:
┌────────────────────────────────────────────────────────────────────┐
│                     Root MCP Server (path="/")                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ FastMCP("mcp-proxy-server", version="1.0.0")                 │  │
│  │  - Auth: GlobalAuthProvider (JWT, GitHub, etc.)              │  │
│  │  - Mounted Proxies:                                           │  │
│  │    ├── Wiki MCP Proxy (from wiki.mcp.json)                   │  │
│  │    ├── Stock MCP Proxy (from stock.mcp.json)                 │  │
│  │    └── ... (other root-mounted services)                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  HTTP Endpoint: POST /mcp                                           │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│              Namespaced MCP Server (path="/stock")                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ FastMCP("mcp-proxy-server-/stock", version="1.0.0")          │  │
│  │  - Auth: GlobalAuthProvider or None                          │  │
│  │  - Proxy: create_proxy(stock.mcp.json)                       │  │
│  │  - Tools: stock_price, stock_history, etc.                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  HTTP Endpoint: POST /stock/mcp                                     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│               Namespaced MCP Server (path="/wiki")                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ FastMCP("mcp-proxy-server-/wiki", version="1.0.0")           │  │
│  │  - Auth: GlobalAuthProvider or None                          │  │
│  │  - Proxy: create_proxy(wiki.mcp.json)                        │  │
│  │  - Tools: search_wiki, get_article, etc.                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  HTTP Endpoint: POST /wiki/mcp                                      │
└────────────────────────────────────────────────────────────────────┘
```

## Request Flow

```
Step 1: Client Request
┌──────────────────────────────────────────────────────────────┐
│ MCP Client (e.g., Claude Desktop)                            │
│                                                              │
│ POST /stock/mcp                                              │
│ Headers:                                                     │
│   Authorization: Bearer <jwt-token>                          │
│ Body:                                                        │
│   {"jsonrpc": "2.0", "method": "tools/list", "id": 1}       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 2: Starlette Routing & Middleware
┌──────────────────────────────────────────────────────────────┐
│ Starlette Application                                         │
│  1. CORS Middleware: Validate origin, set CORS headers       │
│  2. Route to: /stock/mcp endpoint                            │
│  3. Invoke: FastMCP http_app for "/stock" service            │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: FastMCP Authentication
┌──────────────────────────────────────────────────────────────┐
│ FastMCP Auth Provider (if configured)                        │
│  1. Extract Authorization header                             │
│  2. Validate JWT token against JWKS_URI                      │
│  3. Extract user context (claims, scopes)                    │
│  4. Store in MCP context for downstream use                  │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: MCP Proxy Forwarding
┌──────────────────────────────────────────────────────────────┐
│ McpProxyProvider for "/stock"                                │
│  1. create_proxy(stock.mcp.json) has MCP spec:               │
│     {                                                         │
│       "mcpServers": {                                         │
│         "stock": {                                            │
│           "url": "http://stock-service.internal:8080/mcp",   │
│           "transport": "http"                                 │
│         }                                                     │
│       }                                                       │
│     }                                                         │
│  2. FastMCP routes request to backend via HTTP               │
│  3. Backend MCP server processes "tools/list" request        │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 5: Backend MCP Server
┌──────────────────────────────────────────────────────────────┐
│ Stock MCP Server (http://stock-service.internal:8080/mcp)    │
│  1. Receives JSON-RPC request                                │
│  2. Returns available tools:                                 │
│     {                                                         │
│       "tools": [                                              │
│         {"name": "stock_price", "description": "..."},        │
│         {"name": "stock_history", "description": "..."}       │
│       ]                                                       │
│     }                                                         │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 6: Response to Client
┌──────────────────────────────────────────────────────────────┐
│ Response aggregated and returned to MCP client               │
│  - Tools from all mounted services (if root path)            │
│  - Tools from specific service (if namespaced path)          │
└──────────────────────────────────────────────────────────────┘
```

## Configuration Examples

### Basic Configuration

**config.json**:
```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null
  },
  {
    "path": "/stock",
    "spec_file": "mcp/stock.mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "tags": ["finance", "internal"]
  },
  {
    "path": "/wiki",
    "spec_file": "mcp/wiki.mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "tags": ["documentation", "internal"]
  }
]
```

### MCP Specification Files

**mcp/stock.mcp.json** (HTTP Transport):
```json
{
  "mcpServers": {
    "stock": {
      "url": "http://stock-service.internal:8080/mcp",
      "transport": "http"
    }
  }
}
```

**mcp/wiki.mcp.json** (HTTP Transport):
```json
{
  "mcpServers": {
    "wiki": {
      "url": "https://mcp.deepwiki.com/mcp",
      "transport": "http"
    }
  }
}
```

**mcp/memory.mcp.json** (stdio Transport):
```json
{
  "mcpServers": {
    "memory": {
      "enabled": true,
      "timeout": 60,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "transport": "stdio"
    }
  }
}
```

## Skills Directory Provider

The Skills Directory Provider allows you to expose Markdown-based skill documentation as MCP resources. This is useful for providing LLMs with structured knowledge about code patterns, best practices, and domain-specific information.

### Configuration

Add the `skill_dir` field to your MCP configuration to enable the Skills Directory Provider:

**config.json with skill_dir**:
```json
[
  {
    "path": "/",
    "spec_type": "mcp",
    "skill_dir": "skills",
    "mcpServers": {
      "memory": {
        "enabled": true,
        "timeout": 60,
        "command": "npx",
        "args": ["@modelcontextprotocol/server-memory"],
        "transport": "stdio"
      }
    }
  }
]
```

### Directory Structure

The `skill_dir` should contain subdirectories, where each subdirectory represents a skill category. The provider automatically scans all subdirectories and makes them available as MCP resources:

```
data/
└── skills/
    ├── dknet/
    │   ├── README.md
    │   ├── efcore-repos/
    │   │   └── SKILL.md
    │   ├── slimbus-messaging/
    │   │   └── SKILL.md
    │   ├── aspcore-idempotency/
    │   │   └── SKILL.md
    │   └── dknet-overview/
    │       └── SKILL.md
    └── architecture/
        ├── patterns/
        │   └── SKILL.md
        └── guidelines/
            └── SKILL.md
```

### How It Works

1. **Directory Scanning**: The provider scans all subdirectories in the specified `skill_dir`
2. **Sorted Loading**: Subdirectories are loaded in alphabetical order for consistent behavior
3. **Resource Registration**: Each subdirectory is registered with FastMCP's `SkillsDirectoryProvider`
4. **MCP Resource Access**: Skills are exposed as MCP resources that clients can query

### Example Skills

See the example skills in `data/skills/dknet/` for a reference implementation. Each skill directory can contain any files supported by the SkillsDirectoryProvider. Common patterns include:
- **SKILL.md**: Main skill documentation with code examples and best practices
- **README.md**: Overview of the skill category
- Other markdown files with additional documentation

**Note**: The exact file naming conventions depend on the SkillsDirectoryProvider implementation in FastMCP.

### Key Features

- **Automatic Discovery**: No need to manually register each skill
- **Markdown Support**: Skills are written in markdown for easy maintenance
- **Hierarchical Organization**: Organize skills into logical subdirectories
- **Multiple Categories**: Support for multiple skill categories in a single configuration

### Notes

- If `skill_dir` is not specified, no skills will be loaded
- If the directory doesn't exist, the provider will skip loading skills without logging an error (returns silently)
- Only subdirectories are loaded; files in the root of `skill_dir` are ignored
- Hidden directories (starting with `.`) are included if present

## Key Features

### 1. Root Path Aggregation (`path="/"`)

Creates a single FastMCP server that mounts all root-path MCP services:
- Client can access all tools via single `/mcp` endpoint
- Prevents tool name conflicts via namespacing
- Unified authentication and lifecycle management

### 2. Namespaced Services

Each service gets its own FastMCP server instance:
- Isolated at HTTP endpoint level (`/stock/mcp`, `/wiki/mcp`)
- Independent authentication and lifecycle
- Prevents tool name conflicts between services

### 3. Transport Support

**HTTP/SSE Transport**:
- Direct HTTP communication to backend MCP servers
- Suitable for remote services
- Connection pooling and retry logic

**stdio Transport**:
- Local process execution
- FastMCP handles process management
- Suitable for local tools and utilities

### 4. Authentication Integration

- GlobalAuthProvider applies to root MCP server
- Validates client tokens before proxying to backend
- Supports JWT, OAuth (GitHub, Google, Discord), and custom providers
- Token context available to all downstream services

### 5. Dynamic Configuration

- JSON-based configuration with hot-reloading capability
- Environment variable substitution (`$VAR_NAME`, `${VAR_NAME}`)
- Schema validation against JSON schemas
- No code changes required to add services

## Code Implementation

**McpProxyProvider** (`src/proxies/mcp_proxy_provider.py`):
```python
class McpProxyProvider(StaticMcpProvider):
    """Provider class for creating FastMCP instances from MCP configurations."""

    def create_proxy(self) -> FastMCP:
        """Create and return a FastMCP instance based on the MCP configuration."""
        if self.config.spec_data is None:
            raise ValueError(f"spec_data is required for MCP config '{self.config.path}'")

        # Create proxy from MCP spec
        proxy = create_proxy(self.config.spec_data, name=self.config.path)
        
        # Special handling for root path
        if self.config.path == "/" and self.root_mcp is not None:
            self.root_mcp.mount(proxy)
            self.mcp = self.root_mcp
            self.mcp.auth = self._get_global_auth_provider()
            return self.mcp
        
        # Create namespaced FastMCP server
        self.mcp = FastMCP(
            f"{SERVER_NAME}-{self.config.path}",
            version=SERVER_VERSION,
        )
        self.mcp.mount(proxy)
        return self.mcp
```

## Usage Examples

### Example 1: Single Root Service

Simple configuration with one service at the root path:

```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp"
  }
]
```

Access via: `POST http://localhost:9123/mcp`

### Example 2: Multiple Namespaced Services

Multiple services with their own namespaces:

```json
[
  {
    "path": "/github",
    "spec_file": "mcp/github.mcp.json",
    "spec_type": "mcp",
    "tags": ["version-control", "documentation"]
  },
  {
    "path": "/database",
    "spec_file": "mcp/database.mcp.json",
    "spec_type": "mcp",
    "tags": ["storage", "internal"]
  }
]
```

Access via:
- `POST http://localhost:9123/github/mcp`
- `POST http://localhost:9123/database/mcp`

### Example 3: Mixed Root and Namespaced

Combination of root-aggregated and namespaced services:

```json
[
  {
    "path": "/",
    "spec_file": "mcp/common.mcp.json",
    "spec_type": "mcp"
  },
  {
    "path": "/specialized",
    "spec_file": "mcp/specialized.mcp.json",
    "spec_type": "mcp"
  }
]
```

- Root services: `POST http://localhost:9123/mcp`
- Specialized service: `POST http://localhost:9123/specialized/mcp`

### Example 4: With Skills Directory

Include markdown-based skills for domain knowledge:

```json
[
  {
    "path": "/",
    "spec_type": "mcp",
    "skill_dir": "skills",
    "mcpServers": {
      "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "transport": "stdio"
      }
    }
  }
]
```

## Best Practices

### Path Organization

1. **Use root path (`/`)** for:
   - Common utilities (memory, filesystem, etc.)
   - Services that should be available everywhere
   - Internal tools

2. **Use namespaced paths** for:
   - External services (APIs, databases)
   - Service-specific tools
   - When you need independent authentication

### Transport Selection

1. **Use HTTP transport** for:
   - Remote services
   - Services behind load balancers
   - Services requiring connection pooling

2. **Use stdio transport** for:
   - Local utilities
   - NPM/NPX packages
   - Python/Node.js scripts

### Configuration Management

1. **Use environment variables** for:
   - Sensitive data (credentials, tokens)
   - Environment-specific values (URLs, ports)
   - Dynamic configuration

2. **Use JSON files** for:
   - Static configuration
   - Service specifications
   - Tool definitions

### Tagging

Use tags to categorize services:
```json
{
  "path": "/api",
  "tags": ["external", "production", "finance"]
}
```

Benefits:
- Filter services in client applications
- Organize service documentation
- Implement tag-based access control

## Troubleshooting

### Service Not Starting

**Check logs**:
```bash
docker-compose logs mcp-proxy
```

**Common issues**:
- Invalid MCP specification JSON
- Missing `mcpServers` key in spec file
- Invalid transport type (must be "http" or "stdio")

### Tools Not Appearing

**Verify**:
1. MCP specification is correctly formatted
2. Backend service is accessible
3. No network connectivity issues
4. Authentication is properly configured

**Test backend directly**:
```bash
curl -X POST http://backend-service:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### stdio Services Failing

**Check**:
- Command is available in PATH
- Arguments are correct
- Process has required permissions
- Timeout is sufficient for service startup

### Root vs Namespaced Confusion

**Remember**:
- Root path (`/`) aggregates ALL root-path services
- Namespaced paths are independent
- Tools from root and namespaced services are separate

## Related Documentation

- [First Steps](../../getting-started/first-steps.md) - Getting started guide
- [OpenAPI Integration](../openapi/integration.md) - OpenAPI service configuration
- [Authentication Overview](../authentication/overview.md) - Authentication configuration
- [API Reference](../../api-reference/endpoints.md) - API endpoint documentation
