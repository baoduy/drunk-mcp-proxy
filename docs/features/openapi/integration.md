# OpenAPI Integration

## Overview

drunk-mcp-proxy can automatically convert OpenAPI 3.0 specifications into MCP tools, enabling seamless integration of RESTful APIs into the MCP ecosystem. This feature includes advanced capabilities like route filtering, Azure OAuth2 authentication, and pass-through token authentication.

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                 OpenAPI to MCP Conversion Architecture                 │
└────────────────────────────────────────────────────────────────────────┘

Configuration Loading:
┌──────────────┐         ┌──────────────────┐         ┌───────────────┐
│ config.json  │────────>│ ProxyConfig      │────────>│ SpecConfig    │
│              │         │ Provider         │         │ (OpenAPI)     │
│ - spec_type: │         │                  │         │               │
│   "openapi"  │         │ Filters by type  │         │ - spec_file   │
│ - base_url   │         │                  │         │ - base_url    │
│ - filters    │         │                  │         │ - auth        │
│ - auth       │         │                  │         │ - filters     │
└──────────────┘         └──────────────────┘         └───────────────┘
                                  |
                                  v
OpenAPI Spec Loading:
┌─────────────────────────────────────────────────────────────────────┐
│ Load OpenAPI 3.0 Spec (deepsea.openapi.json)                        │
│  {                                                                   │
│    "openapi": "3.0.0",                                               │
│    "info": { "title": "DeepSea API", "version": "1.0.0" },          │
│    "paths": {                                                        │
│      "/currency-pairs": {                                            │
│        "get": {                                                      │
│          "operationId": "getCurrencyPairs",                          │
│          "tags": ["CurrencyPairs"],                                  │
│          "responses": { ... }                                        │
│        },                                                            │
│        "post": { ... }                                               │
│      }                                                               │
│    }                                                                 │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
Route Filtering (Optional):
┌─────────────────────────────────────────────────────────────────────┐
│ Apply Filters from Config:                                          │
│  - Methods: ["GET", "POST", "PUT"] (exclude DELETE, PATCH)          │
│  - Tags: ["CurrencyPairs"] (only include tagged endpoints)          │
│                                                                      │
│ custom_route_mapper():                                               │
│   if route.method not in filters.methods:                           │
│     return MCPType.EXCLUDE                                           │
│   if route.tags not in filters.tags:                                │
│     return MCPType.EXCLUDE                                           │
│   return mcp_type                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
HTTP Client Creation:
┌─────────────────────────────────────────────────────────────────────┐
│ Create httpx.AsyncClient with Authentication:                       │
│                                                                      │
│ Option 1: Azure OAuth2 (Client Credentials Flow)                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ AzureOauth(                                                    │ │
│  │   client_id="...",                                             │ │
│  │   client_secret="...",                                         │ │
│  │   token_url="https://login.microsoftonline.com/.../token",    │ │
│  │   scope="api://.../.default"                                   │ │
│  │ )                                                              │ │
│  │ - Automatic token fetching & caching                          │ │
│  │ - Token expiry detection & refresh                            │ │
│  │ - Adds "Authorization: Bearer <token>" to requests            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ Option 2: Pass-Through Authentication                               │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ AuthPassThrough()                                              │ │
│  │ - Extracts token from MCP request context                     │ │
│  │ - Forwards token to backend API                               │ │
│  │ - No token management/caching                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ Option 3: Static Token                                              │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ headers["Authorization"] = config.auth.auth_token             │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
FastMCP Conversion:
┌─────────────────────────────────────────────────────────────────────┐
│ FastMCP.from_openapi(                                                │
│   name="mcp-proxy-server-/deepsea",                                  │
│   openapi_spec=spec_data,                                            │
│   client=httpx_client,                                               │
│   route_map_fn=custom_route_mapper,                                  │
│   tags=["finance", "api"]                                            │
│ )                                                                    │
│                                                                      │
│ Result: FastMCP server with tools for each OpenAPI endpoint:        │
│  - Tool name: operationId or auto-generated                          │
│  - Tool description: from OpenAPI operation summary/description      │
│  - Tool parameters: from OpenAPI request body & query parameters     │
│  - Tool execution: HTTP request to backend via httpx client          │
└─────────────────────────────────────────────────────────────────────┘
                                  |
                                  v
MCP Tool Mapping:
┌─────────────────────────────────────────────────────────────────────┐
│ OpenAPI Endpoint → MCP Tool                                          │
│                                                                      │
│ GET /currency-pairs?base=USD                                         │
│   → MCP Tool: getCurrencyPairs                                       │
│      Parameters: { "base": "USD" }                                   │
│      Description: "Get list of currency pairs"                      │
│                                                                      │
│ POST /currency-pairs { "base": "USD", "quote": "EUR" }              │
│   → MCP Tool: createCurrencyPair                                     │
│      Parameters: { "base": "USD", "quote": "EUR" }                   │
│      Description: "Create a new currency pair"                      │
└─────────────────────────────────────────────────────────────────────┘
```

## How OpenAPI is Converted to MCP

### Endpoint to Tool Mapping

Each OpenAPI endpoint is converted to an MCP tool following these rules:

1. **Tool Name**: Derived from `operationId` if present, otherwise auto-generated from HTTP method and path
2. **Tool Description**: Taken from `summary` or `description` field
3. **Tool Parameters**: Combined from query parameters, path parameters, and request body schema
4. **Tool Execution**: HTTP request to the backend API via httpx client

### Example Conversion

**OpenAPI Specification**:
```json
{
  "paths": {
    "/users/{userId}": {
      "get": {
        "operationId": "getUser",
        "summary": "Get user by ID",
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "includeDetails",
            "in": "query",
            "schema": { "type": "boolean", "default": false }
          }
        ],
        "responses": {
          "200": {
            "description": "User found"
          }
        }
      }
    }
  }
}
```

**Resulting MCP Tool**:
```json
{
  "name": "getUser",
  "description": "Get user by ID",
  "inputSchema": {
    "type": "object",
    "properties": {
      "userId": {
        "type": "string",
        "description": "User ID from path"
      },
      "includeDetails": {
        "type": "boolean",
        "default": false,
        "description": "Include detailed information"
      }
    },
    "required": ["userId"]
  }
}
```

## Request Flow with Authentication

```
Step 1: Client MCP Request
┌──────────────────────────────────────────────────────────────┐
│ MCP Client (e.g., Claude Desktop)                            │
│                                                              │
│ POST /deepsea/mcp                                            │
│ Headers:                                                     │
│   Authorization: Bearer <user-jwt-token>                     │
│ Body:                                                        │
│   {                                                          │
│     "jsonrpc": "2.0",                                        │
│     "method": "tools/call",                                  │
│     "params": {                                              │
│       "name": "getCurrencyPairs",                            │
│       "arguments": { "base": "USD" }                         │
│     },                                                       │
│     "id": 1                                                  │
│   }                                                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 2: FastMCP Authentication (MCP Level)
┌──────────────────────────────────────────────────────────────┐
│ FastMCP Auth Provider validates client                       │
│  1. Extract Authorization header: Bearer <user-jwt-token>    │
│  2. Validate JWT token                                       │
│  3. Store AccessToken in MCP context                         │
│     → Available via get_access_token()                       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: Tool Execution (OpenAPI Call)
┌──────────────────────────────────────────────────────────────┐
│ FastMCP invokes tool: getCurrencyPairs                       │
│  1. Construct HTTP request: GET /currency-pairs?base=USD     │
│  2. httpx.AsyncClient uses configured auth:                  │
│                                                              │
│     SCENARIO A: Pass-Through Auth                            │
│     ┌────────────────────────────────────────────────┐      │
│     │ AuthPassThrough.async_auth_flow()              │      │
│     │  1. Call get_access_token() from MCP context   │      │
│     │  2. Extract user-jwt-token                     │      │
│     │  3. Add to request:                            │      │
│     │     Authorization: Bearer <user-jwt-token>     │      │
│     └────────────────────────────────────────────────┘      │
│                                                              │
│     SCENARIO B: Azure OAuth                                  │
│     ┌────────────────────────────────────────────────┐      │
│     │ AzureOauth.async_auth_flow()                   │      │
│     │  1. Check cached token                         │      │
│     │  2. If expired, fetch new token:               │      │
│     │     POST to Azure token_url with               │      │
│     │     client credentials                         │      │
│     │  3. Cache token (in-memory + storage)          │      │
│     │  4. Add to request:                            │      │
│     │     Authorization: Bearer <azure-token>        │      │
│     └────────────────────────────────────────────────┘      │
│                                                              │
│  3. Send HTTP request to backend API                        │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: Backend OpenAPI Service
┌──────────────────────────────────────────────────────────────┐
│ DeepSea API (http://host.docker.internal:5000)               │
│                                                              │
│ GET /currency-pairs?base=USD                                 │
│ Headers:                                                     │
│   Authorization: Bearer <token>  ← From auth flow            │
│                                                              │
│ Response:                                                    │
│   {                                                          │
│     "pairs": [                                               │
│       { "base": "USD", "quote": "EUR", "rate": 0.85 },       │
│       { "base": "USD", "quote": "GBP", "rate": 0.73 }        │
│     ]                                                        │
│   }                                                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 5: Response to MCP Client
┌──────────────────────────────────────────────────────────────┐
│ FastMCP wraps response in MCP format                         │
│   {                                                          │
│     "jsonrpc": "2.0",                                        │
│     "id": 1,                                                 │
│     "result": {                                              │
│       "content": [                                           │
│         {                                                    │
│           "type": "text",                                    │
│           "text": "{\"pairs\": [...]}"                       │
│         }                                                    │
│       ]                                                      │
│     }                                                        │
│   }                                                          │
└──────────────────────────────────────────────────────────────┘
```

## Configuration Examples

### Basic OpenAPI Service

```json
{
  "path": "/api",
  "spec_file": "openapi/api.openapi.json",
  "spec_type": "openapi",
  "base_url": "https://api.example.com"
}
```

### With Pass-Through Authentication

```json
{
  "path": "/deepsea",
  "spec_file": "openapi/deepsea.openapi.json",
  "spec_type": "openapi",
  "base_url": "http://host.docker.internal:5000",
  "auth": {
    "pass_through": true
  }
}
```

### With Azure OAuth2

```json
{
  "path": "/deepsea",
  "spec_file": "openapi/deepsea.openapi.json",
  "spec_type": "openapi",
  "base_url": "http://host.docker.internal:5000",
  "auth": {
    "azure": {
      "client_id": "$AZURE_CLIENT_ID",
      "client_secret": "$AZURE_CLIENT_SECRET",
      "tenant_id": "$AZURE_TENANT_ID",
      "issuer": "https://sts.windows.net/$AZURE_TENANT_ID/",
      "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
      "scopes": ["api://$AZURE_CLIENT_ID/.default"]
    }
  }
}
```

### With Route Filters

```json
{
  "path": "/deepsea",
  "spec_file": "openapi/deepsea.openapi.json",
  "spec_type": "openapi",
  "base_url": "http://host.docker.internal:5000",
  "filters": {
    "methods": ["GET", "POST", "PUT"],
    "tags": ["CurrencyPairs", "Users"]
  },
  "auth": {
    "pass_through": true
  }
}
```

### With Static Token

```json
{
  "path": "/api",
  "spec_file": "openapi/api.openapi.json",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "auth_token": "Bearer sk-1234567890abcdef"
  }
}
```

## Filters

### Filter by HTTP Methods

Limit which HTTP methods are exposed as MCP tools:

```json
{
  "filters": {
    "methods": ["GET", "POST"]
  }
}
```

**Available methods**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`

**Use cases**:
- Read-only access: `["GET"]`
- Create/Read operations: `["GET", "POST"]`
- Full CRUD: `["GET", "POST", "PUT", "DELETE"]`

### Filter by OpenAPI Tags

Only include endpoints with specific tags:

```json
{
  "filters": {
    "tags": ["Users", "Projects", "Issues"]
  }
}
```

**How it works**:
- Checks if endpoint has any of the specified tags
- Excludes endpoints with no matching tags
- Useful for large APIs with many endpoints

### Combined Filters

Use both method and tag filters:

```json
{
  "filters": {
    "methods": ["GET", "POST"],
    "tags": ["Users", "Projects"]
  }
}
```

**Result**: Only GET and POST endpoints with Users or Projects tags are exposed.

## Request Mapping

### Query Parameters

OpenAPI query parameters become MCP tool parameters:

**OpenAPI**:
```json
{
  "parameters": [
    {
      "name": "page",
      "in": "query",
      "schema": { "type": "integer", "default": 1 }
    },
    {
      "name": "limit",
      "in": "query",
      "schema": { "type": "integer", "default": 10 }
    }
  ]
}
```

**MCP Tool Call**:
```json
{
  "name": "listUsers",
  "arguments": {
    "page": 2,
    "limit": 20
  }
}
```

**HTTP Request**:
```
GET /users?page=2&limit=20
```

### Path Parameters

Path parameters are extracted from the URL:

**OpenAPI**:
```json
{
  "paths": {
    "/users/{userId}/posts/{postId}": {
      "get": {
        "parameters": [
          { "name": "userId", "in": "path", "required": true },
          { "name": "postId", "in": "path", "required": true }
        ]
      }
    }
  }
}
```

**MCP Tool Call**:
```json
{
  "name": "getUserPost",
  "arguments": {
    "userId": "123",
    "postId": "456"
  }
}
```

**HTTP Request**:
```
GET /users/123/posts/456
```

### Request Body

Request body schema becomes MCP tool parameters:

**OpenAPI**:
```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "email": { "type": "string" },
            "role": { "type": "string", "enum": ["admin", "user"] }
          },
          "required": ["name", "email"]
        }
      }
    }
  }
}
```

**MCP Tool Call**:
```json
{
  "name": "createUser",
  "arguments": {
    "name": "John Doe",
    "email": "john@example.com",
    "role": "user"
  }
}
```

**HTTP Request**:
```
POST /users
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "user"
}
```

## Key Features

### 1. Automatic Tool Generation

- Each OpenAPI endpoint becomes an MCP tool
- Tool names derived from `operationId` or auto-generated
- Tool descriptions from OpenAPI `summary` or `description`
- Parameters automatically mapped from query params, path params, and request body

### 2. Route Filtering

- **By HTTP Method**: Include only specific methods (GET, POST, PUT, DELETE, PATCH)
- **By Tags**: Include only endpoints with specific tags
- Reduces tool clutter and improves security

### 3. Flexible Authentication

- **Pass-Through**: Forward client token to backend (zero configuration)
- **Azure OAuth2**: Automatic client credentials flow with token caching
- **Static Token**: Use a pre-configured API key
- **No Auth**: Public APIs

### 4. HTTP Client Management

- Automatic base URL handling
- Request/response serialization
- Error handling and retries
- Connection pooling via httpx

## Code Implementation

**OpenApiMcpProvider** (`src/proxies/openapi_mcp_provider.py`):
```python
class OpenApiMcpProvider(StaticMcpProvider):
    """Provider class for creating FastMCP instances from OpenAPI specs."""

    def custom_route_mapper(self, route: HTTPRoute, mcp_type: MCPType) -> MCPType | None:
        """Filter routes based on configured filters."""
        if self.config.filters is not None:
            if self.config.filters.methods:
                if route.method not in self.config.filters.methods:
                    return MCPType.EXCLUDE
            if self.config.filters.tags:
                if not any(tag in route.tags for tag in self.config.filters.tags):
                    return MCPType.EXCLUDE
        return mcp_type

    def create_client(self) -> httpx.AsyncClient:
        """Return an appropriate HTTP client for the configured service."""
        if not self.config.base_url:
            raise ValueError("base_url is required for OpenAPI clients")

        auth: Auth | None = None
        headers: dict[str, str] = {}
        
        if self.config.auth and self.config.auth.azure:
            # Azure OAuth2 client credentials flow
            auth = self._create_client_auth(self.config.auth.azure)
        elif self.config.auth and self.config.auth.auth_token:
            # Static token
            headers["Authorization"] = self.config.auth.auth_token

        return httpx.AsyncClient(base_url=self.config.base_url, auth=auth, headers=headers)

    def create_proxy(self) -> FastMCP:
        """Create and return a FastMCP instance based on the loaded configurations."""
        client = self.create_client()
        
        self.mcp = FastMCP.from_openapi(
            name=f"{SERVER_NAME}-{self.config.path}",
            openapi_spec=self.config.spec_data,
            client=client,
            route_map_fn=self.custom_route_mapper,
            tags=self.config.tags
        )
        
        return self.mcp
```

## Best Practices

### OpenAPI Specification Quality

1. **Use operationId**: Provide meaningful operation IDs for better tool names
2. **Add descriptions**: Include summary and description for each endpoint
3. **Define schemas**: Use proper JSON Schema for request/response bodies
4. **Tag endpoints**: Organize endpoints with tags for easy filtering

### Authentication Strategy

1. **Use Pass-Through** when:
   - Backend needs user identity
   - User-specific authorization is required
   - Audit logging needs user context

2. **Use Azure OAuth** when:
   - Service-to-service communication
   - Backend doesn't need user context
   - High request volume (benefits from caching)

3. **Use Static Token** when:
   - Simple API key authentication
   - Testing and development
   - No token expiry concerns

### Filtering Strategy

1. **Filter by methods** to:
   - Provide read-only access (`["GET"]`)
   - Restrict dangerous operations (exclude `["DELETE"]`)
   - Simplify tool list

2. **Filter by tags** to:
   - Expose only relevant endpoints
   - Create domain-specific proxies
   - Reduce security surface area

### Error Handling

1. **Handle backend errors**: OpenAPI errors are passed through to MCP client
2. **Monitor failures**: Log authentication and connection errors
3. **Set appropriate timeouts**: Configure httpx client timeouts
4. **Implement retries**: Use httpx retry logic for transient failures

## Troubleshooting

### Tools Not Appearing

**Check**:
- OpenAPI spec is valid (use Swagger Editor)
- `base_url` is accessible from proxy
- Filters aren't excluding all endpoints
- OpenAPI version is 3.0.x (2.0 not supported)

**Validate**:
```bash
# Check if spec loads
cat data/openapi/api.openapi.json | jq .

# Test base_url
curl -v https://api.example.com
```

### Authentication Failures

**Pass-Through Issues**:
- Verify MCP client auth is configured
- Check that token is being passed
- Confirm backend accepts the token format

**Azure OAuth Issues**:
- Verify client credentials are correct
- Check token URL is accessible
- Confirm scopes are correct
- Review cache storage permissions

### Filter Not Working

**Debug**:
1. Remove filters temporarily
2. Check if tools appear without filters
3. Verify tag names match OpenAPI spec exactly (case-sensitive)
4. Check HTTP method names are uppercase

### Request Mapping Issues

**Parameter Problems**:
- Verify parameter names match OpenAPI spec
- Check required vs optional parameters
- Validate parameter types (string, integer, boolean)

**Body Issues**:
- Confirm `Content-Type: application/json`
- Validate JSON schema
- Check for nested object support

## Related Documentation

- [First Steps](../../getting-started/first-steps.md) - Getting started guide
- [MCP Proxy Management](../mcp/proxy-management.md) - MCP service configuration
- [Authentication Overview](../authentication/overview.md) - Authentication details
- [API Reference](../../api-reference/endpoints.md) - API endpoints
