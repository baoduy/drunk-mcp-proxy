# API Endpoints Reference

This document provides a comprehensive reference for all HTTP endpoints exposed by drunk-mcp-proxy.

## Health Check Endpoint

### GET /health

Returns server health status and service information.

**Request:**
```http
GET /health HTTP/1.1
Host: localhost:9123
```

**Response:**
```json
{
  "status": "healthy",
  "service": "mcp-proxy-server"
}
```

**Status Codes:**
- `200 OK`: Service is healthy and operational
- `503 Service Unavailable`: Service is unhealthy or starting up

**Usage:**
```bash
# Basic health check
curl http://localhost:9123/health

# With Docker health check
docker inspect --format='{{.State.Health.Status}}' mcp-proxy

# Kubernetes liveness probe
kubectl get pods -l app=mcp-proxy
```

**Notes:**
- No authentication required
- Used by Docker, Kubernetes, and load balancers
- Returns immediately (no backend checks)
- Should be called periodically for monitoring

## MCP Endpoints

All MCP endpoints follow the [Model Context Protocol specification](https://spec.modelcontextprotocol.io/) and use JSON-RPC 2.0 over HTTP.

### Root MCP Endpoint

#### POST /mcp

MCP endpoint for root-mounted services (path="/").

**Request:**
```http
POST /mcp HTTP/1.1
Host: localhost:9123
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "store_memory",
        "description": "Store information in memory",
        "inputSchema": {
          "type": "object",
          "properties": {
            "key": { "type": "string" },
            "value": { "type": "string" }
          },
          "required": ["key", "value"]
        }
      }
    ]
  }
}
```

**Features:**
- Aggregates all services configured with `path: "/"`
- Single endpoint for multiple backend services
- Namespacing prevents tool name conflicts
- Shared authentication context

### Namespaced MCP Endpoints

#### POST /{namespace}/mcp

MCP endpoint for namespaced services.

**Examples:**

**GitHub Service:**
```http
POST /github/mcp HTTP/1.1
Host: localhost:9123
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Weather Service:**
```http
POST /weather/mcp HTTP/1.1
Host: localhost:9123
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "getCurrentWeather",
    "arguments": {
      "location": "London"
    }
  }
}
```

**Analytics Service:**
```http
POST /analytics/mcp HTTP/1.1
Host: localhost:9123
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "resources/list"
}
```

**Features:**
- Isolated endpoint per service
- Independent authentication and lifecycle
- Service-specific tools and resources
- No namespace conflicts

## MCP Protocol Methods

drunk-mcp-proxy supports all standard MCP methods:

### tools/list

List all available tools from the service.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "tool_name",
        "description": "Tool description",
        "inputSchema": { ... }
      }
    ]
  }
}
```

### tools/call

Execute a specific tool.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1",
      "param2": "value2"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Tool execution result"
      }
    ]
  }
}
```

### resources/list

List all available resources.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "resources/list"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "resources": [
      {
        "uri": "resource://example",
        "name": "Example Resource",
        "description": "Resource description",
        "mimeType": "text/plain"
      }
    ]
  }
}
```

### resources/read

Read a specific resource.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/read",
  "params": {
    "uri": "resource://example"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "contents": [
      {
        "uri": "resource://example",
        "mimeType": "text/plain",
        "text": "Resource content"
      }
    ]
  }
}
```

### prompts/list

List all available prompts.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "prompts/list"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "prompts": [
      {
        "name": "prompt_name",
        "description": "Prompt description",
        "arguments": [
          {
            "name": "arg1",
            "description": "Argument description",
            "required": true
          }
        ]
      }
    ]
  }
}
```

### prompts/get

Get a specific prompt with arguments.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/get",
  "params": {
    "name": "prompt_name",
    "arguments": {
      "arg1": "value1"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Generated prompt text"
        }
      }
    ]
  }
}
```

## Authentication

All MCP endpoints (except `/health`) can be protected with authentication. Authentication behavior depends on configuration in `config.yaml`.

### With Authentication Enabled

**Request:**
```http
POST /mcp HTTP/1.1
Host: localhost:9123
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Success Response (200 OK):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [...]
  }
}
```

**Unauthorized Response (401 Unauthorized):**
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

### Without Authentication

If authentication is not configured, the Authorization header is optional:

**Request:**
```http
POST /mcp HTTP/1.1
Host: localhost:9123
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

## Error Responses

All endpoints follow JSON-RPC 2.0 error format:

### Standard Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": {
      "details": "Additional error information"
    }
  }
}
```

### Common Error Codes

| Code | Message | Description |
|------|---------|-------------|
| -32700 | Parse error | Invalid JSON was received |
| -32600 | Invalid Request | JSON is not a valid request object |
| -32601 | Method not found | Method does not exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Internal JSON-RPC error |
| -32001 | Unauthorized | Authentication required or failed |
| -32002 | Forbidden | Insufficient permissions |
| -32000 | Server error | Generic server error |

### HTTP Status Codes

| Status | Meaning | Usage |
|--------|---------|-------|
| 200 OK | Success | All successful MCP requests |
| 400 Bad Request | Invalid request | Malformed JSON, invalid method |
| 401 Unauthorized | Authentication failed | Missing or invalid token |
| 403 Forbidden | Authorization failed | Valid token, insufficient permissions |
| 404 Not Found | Endpoint not found | Invalid path |
| 500 Internal Server Error | Server error | Unexpected server failure |
| 503 Service Unavailable | Service unhealthy | Server starting or unhealthy |

## CORS Headers

When CORS is enabled (via environment variables), the following headers are set:

### Preflight Request (OPTIONS)

**Request:**
```http
OPTIONS /mcp HTTP/1.1
Host: localhost:9123
Origin: https://your-app.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Authorization, Content-Type
```

**Response:**
```http
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://your-app.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 86400
```

### Actual Request

**Response Headers:**
```http
Access-Control-Allow-Origin: https://your-app.com
Access-Control-Allow-Credentials: true
Access-Control-Expose-Headers: Content-Type, Authorization
```

## Request Examples

### Using cURL

**List tools:**
```bash
curl -X POST http://localhost:9123/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**Call a tool:**
```bash
curl -X POST http://localhost:9123/weather/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "getCurrentWeather",
      "arguments": {
        "location": "London"
      }
    },
    "id": 2
  }'
```

### Using Python

```python
import requests

url = "http://localhost:9123/mcp"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_TOKEN"
}

# List tools
response = requests.post(url, json={
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
}, headers=headers)

tools = response.json()["result"]["tools"]
print(f"Available tools: {len(tools)}")

# Call a tool
response = requests.post(url, json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "store_memory",
        "arguments": {
            "key": "greeting",
            "value": "Hello, World!"
        }
    },
    "id": 2
}, headers=headers)

result = response.json()["result"]
print(f"Result: {result}")
```

### Using JavaScript/TypeScript

```typescript
const baseUrl = 'http://localhost:9123/mcp';
const headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer YOUR_TOKEN'
};

// List tools
const listTools = async () => {
  const response = await fetch(baseUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'tools/list',
      id: 1
    })
  });
  
  const data = await response.json();
  return data.result.tools;
};

// Call a tool
const callTool = async (name: string, args: any) => {
  const response = await fetch(baseUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'tools/call',
      params: {
        name,
        arguments: args
      },
      id: 2
    })
  });
  
  const data = await response.json();
  return data.result;
};

// Usage
const tools = await listTools();
console.log('Available tools:', tools.length);

const result = await callTool('getCurrentWeather', { location: 'London' });
console.log('Result:', result);
```

## Rate Limiting

Currently, drunk-mcp-proxy does not implement built-in rate limiting. Consider using:

1. **Reverse Proxy**: nginx, Traefik with rate limiting
2. **API Gateway**: Kong, AWS API Gateway
3. **Load Balancer**: Configure rate limits at LB level

## Monitoring

### Recommended Monitoring

1. **Health Check**: Poll `/health` every 30 seconds
2. **Response Time**: Track average response time per endpoint
3. **Error Rate**: Monitor 4xx and 5xx responses
4. **Authentication Failures**: Track 401/403 responses
5. **Tool Execution**: Monitor tool/call method performance

### Metrics to Track

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Health check failures | `/health` returns non-200 | > 3 consecutive failures |
| Average response time | P50, P95, P99 latencies | P95 > 1000ms |
| Error rate | 5xx responses / total | > 1% |
| Auth failures | 401/403 responses | > 5% |
| Request rate | Requests per second | Baseline ±50% |

## Best Practices

1. **Always include request ID**: Use unique IDs for correlation
2. **Handle errors gracefully**: Check for error field in response
3. **Set reasonable timeouts**: 30-60 seconds for tool execution
4. **Retry transient failures**: Use exponential backoff
5. **Cache tool lists**: Reduce unnecessary list calls
6. **Use HTTPS in production**: Protect tokens in transit
7. **Monitor health endpoint**: Detect issues proactively
8. **Log requests/responses**: Aid debugging and audit

## Related Documentation

- [First Steps](../getting-started/first-steps.md) - Getting started guide
- [MCP Proxy Management](../features/mcp/proxy-management.md) - MCP configuration
- [OpenAPI Integration](../features/openapi/integration.md) - OpenAPI configuration
- [Authentication Overview](../features/authentication/overview.md) - Authentication details
- [MCP Specification](https://spec.modelcontextprotocol.io/) - Official MCP protocol spec
