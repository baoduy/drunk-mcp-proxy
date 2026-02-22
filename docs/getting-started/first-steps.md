# First Steps with drunk-mcp-proxy

Welcome to drunk-mcp-proxy! This tutorial will guide you through your first experience with the proxy, from understanding the core concepts to making your first authenticated request.

## Understanding the Proxy Concept

drunk-mcp-proxy acts as a central gateway that unifies multiple MCP (Model Context Protocol) and OpenAPI services behind a single endpoint. Think of it as a smart router that:

- **Aggregates multiple services**: Access multiple backend services through one proxy
- **Provides namespace isolation**: Prevents tool name conflicts by isolating services
- **Handles authentication**: Manages both client authentication and backend service authentication
- **Converts OpenAPI to MCP**: Automatically converts REST APIs into MCP tools
- **Enables dynamic configuration**: Add or modify services via JSON configuration

### Architecture Overview

```
MCP Client (Claude, Custom App)
         ↓
   drunk-mcp-proxy (Single Endpoint)
         ↓
   ┌────┴────┬────────┬────────┐
   ↓         ↓        ↓        ↓
MCP Service  MCP    OpenAPI  OpenAPI
(HTTP/stdio) Service  API     API
```

## Configuring Your First Service

Let's start by configuring a simple MCP service.

### Step 1: Understand the Configuration File

The proxy uses `data/config.json` to define which services to proxy. Here's the simplest configuration:

```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null
  }
]
```

**Configuration Fields Explained**:
- `path`: The HTTP path where the service will be mounted (e.g., `/`, `/wiki`, `/api`)
- `spec_file`: Path to the service specification file (relative to `data/` directory)
- `spec_type`: Type of service - either `"mcp"` or `"openapi"`
- `base_url`: Base URL for OpenAPI services (null for MCP services)

### Step 2: Create Your First MCP Service Configuration

Let's add a simple memory MCP server. Create or edit `data/config.json`:

```json
[
  {
    "path": "/memory",
    "spec_file": "mcp/memory.mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "tags": ["utility", "storage"]
  }
]
```

### Step 3: Create the MCP Specification

Create `data/mcp/memory.mcp.json`:

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

This configuration tells the proxy to:
1. Start a memory server using npx
2. Use stdio transport for communication
3. Mount it at `/memory/mcp` endpoint

### Step 4: Start the Proxy

Using Docker Compose (recommended):

```bash
# Navigate to the project directory
cd drunk-mcp-proxy

# Start the services
docker-compose up -d

# Check if it's running
curl http://localhost:9123/health
```

You should see:
```json
{
  "status": "healthy",
  "service": "mcp-proxy-server"
}
```

## Making Your First Request

Now let's interact with your MCP service using the Model Context Protocol.

### List Available Tools

```bash
curl -X POST http://localhost:9123/memory/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "store_memory",
        "description": "Store information in memory",
        "inputSchema": { ... }
      },
      {
        "name": "retrieve_memory",
        "description": "Retrieve stored information",
        "inputSchema": { ... }
      }
    ]
  }
}
```

### Call a Tool

```bash
curl -X POST http://localhost:9123/memory/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "store_memory",
      "arguments": {
        "key": "greeting",
        "value": "Hello from drunk-mcp-proxy!"
      }
    },
    "id": 2
  }'
```

## Adding Authentication

Now let's secure your proxy with JWT authentication.

### Step 1: Configure Global Authentication

Create `data/auth.json`:

```json
{
  "enabled": true,
  "defaultProvider": "jwt",
  "jwt": {
    "base_url": null,
    "jwks_uri": "https://your-auth-provider.com/.well-known/jwks.json",
    "issuer": "https://your-auth-provider.com/",
    "audience": "mcp-proxy-api",
    "algorithm": "RS256"
  }
}
```

**Note**: Replace the URLs with your actual authentication provider endpoints.

### Step 2: Set Environment Variables

Create or edit `.env` file:

```bash
# Enable authentication
FASTMCP_SERVER_AUTH=jwt

# JWT Configuration
JWKS_URI=https://your-auth-provider.com/.well-known/jwks.json
ISSUER=https://your-auth-provider.com/
AUDIENCE=mcp-proxy-api
```

### Step 3: Restart the Proxy

```bash
docker-compose restart
```

### Step 4: Make Authenticated Requests

Now all requests require an Authorization header:

```bash
curl -X POST http://localhost:9123/memory/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**Without Authentication**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Unauthorized"
  }
}
```

## Adding an OpenAPI Service

Let's add a real-world REST API to demonstrate OpenAPI integration.

### Step 1: Add OpenAPI Service Configuration

Update `data/config.json`:

```json
[
  {
    "path": "/memory",
    "spec_file": "mcp/memory.mcp.json",
    "spec_type": "mcp",
    "base_url": null
  },
  {
    "path": "/weather",
    "spec_file": "openapi/weather.openapi.json",
    "spec_type": "openapi",
    "base_url": "https://api.openweathermap.org/data/2.5",
    "auth": {
      "auth_token": "Bearer YOUR_API_KEY"
    }
  }
]
```

### Step 2: Create OpenAPI Specification

Create `data/openapi/weather.openapi.json` with a simplified OpenAPI spec:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Weather API",
    "version": "1.0.0"
  },
  "paths": {
    "/weather": {
      "get": {
        "operationId": "getCurrentWeather",
        "summary": "Get current weather for a location",
        "parameters": [
          {
            "name": "q",
            "in": "query",
            "description": "City name",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "Weather data"
          }
        }
      }
    }
  }
}
```

### Step 3: Test the OpenAPI Service

```bash
curl -X POST http://localhost:9123/weather/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "getCurrentWeather",
      "arguments": {
        "q": "London"
      }
    },
    "id": 3
  }'
```

## Common Next Steps

### 1. Add More Services

Expand your `config.json` to include multiple services:
- Internal MCP servers for documentation, databases, etc.
- External OpenAPI services (GitHub, Jira, Confluence, etc.)
- Mix of authenticated and unauthenticated services

### 2. Configure Service-Specific Authentication

Use pass-through authentication to forward user tokens:

```json
{
  "path": "/api",
  "spec_file": "openapi/api.openapi.json",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "pass_through": true
  }
}
```

Or use Azure OAuth for service-to-service authentication:

```json
{
  "path": "/api",
  "spec_file": "openapi/api.openapi.json",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "azure": {
      "client_id": "$AZURE_CLIENT_ID",
      "client_secret": "$AZURE_CLIENT_SECRET",
      "tenant_id": "$AZURE_TENANT_ID",
      "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
      "scopes": ["api://example-api/.default"]
    }
  }
}
```

### 3. Filter OpenAPI Endpoints

Reduce tool clutter by filtering OpenAPI endpoints:

```json
{
  "path": "/api",
  "spec_file": "openapi/api.openapi.json",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "filters": {
    "methods": ["GET", "POST"],
    "tags": ["Users", "Projects"]
  }
}
```

### 4. Enable CORS for Web Clients

If you need to access the proxy from a web application:

```bash
# .env file
FASTMCP_CORS_ALLOW_ORIGINS=https://your-app.com,https://localhost:3000
FASTMCP_CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=*
```

### 5. Monitor Your Proxy

Check logs:
```bash
# Docker Compose
docker-compose logs -f mcp-proxy

# Docker
docker logs -f mcp-proxy
```

Check health:
```bash
curl http://localhost:9123/health
```

### 6. Explore Skills Directory

Add markdown-based skills to provide LLMs with domain knowledge:

```json
{
  "path": "/",
  "spec_type": "mcp",
  "skill_dir": "skills",
  "mcpServers": { ... }
}
```

Create skills in `data/skills/`:
```
data/skills/
├── coding-patterns/
│   └── SKILL.md
├── api-guidelines/
│   └── SKILL.md
└── troubleshooting/
    └── SKILL.md
```

## Troubleshooting

### Service Not Starting

**Check logs**:
```bash
docker-compose logs mcp-proxy
```

**Common issues**:
- Port 9123 already in use: Change `FASTMCP_PORT` in `.env`
- Invalid JSON in config files: Validate with `jq`
- Missing environment variables: Check `.env` file

### Authentication Failures

**Check**:
- JWT token is valid and not expired
- `JWKS_URI` is accessible from the container
- `issuer` and `audience` match your token claims
- Authorization header format: `Bearer <token>`

### OpenAPI Service Not Responding

**Check**:
- `base_url` is correct and accessible
- Authentication credentials are valid
- OpenAPI spec is valid (validate with Swagger Editor)
- Network connectivity from container to backend

## Next Documentation

- [MCP Proxy Management](../features/mcp/proxy-management.md) - Deep dive into MCP service configuration
- [OpenAPI Integration](../features/openapi/integration.md) - Advanced OpenAPI features
- [Authentication Overview](../features/authentication/overview.md) - Complete authentication guide
- [Docker Deployment](../deployment/docker.md) - Production deployment guide

## Getting Help

- **GitHub Issues**: [https://github.com/baoduy/drunk-mcp-proxy/issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
- **Documentation**: Check the `docs/` directory for detailed guides
- **Examples**: Review `data/config.json` for working configurations
