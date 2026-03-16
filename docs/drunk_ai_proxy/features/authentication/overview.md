# Authentication Overview

## Overview

drunk-mcp-proxy provides a sophisticated multi-layer authentication system that operates at both the MCP protocol level (client authentication) and the backend service level (service authentication). The pass-through authentication feature is particularly powerful, enabling zero-configuration token forwarding from MCP clients to backend APIs.

## Two-Layer Authentication Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Multi-Layer Authentication Architecture              │
└────────────────────────────────────────────────────────────────────────┘

Layer 1: MCP Client Authentication (Proxy Level)
┌─────────────────────────────────────────────────────────────────────┐
│ GlobalAuthProvider (Configured via config.yaml)                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Supported Providers:                                           │ │
│  │  - JWT: Token validation via JWKS_URI                          │ │
│  │  - GitHub OAuth: GitHub authentication                         │ │
│  │  - Google OAuth: Google authentication                         │ │
│  │  - Discord OAuth: Discord authentication                       │ │
│  │  - WorkOS/AuthKit: Enterprise SSO                              │ │
│  │  - Descope, Supabase, Scalekit: Other identity providers      │ │
│  │  - Custom: Any FastMCP AuthProvider subclass                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ Configuration: config.yaml                                           │
│  auth:                                                               │
│    enabled: true                                                     │
│    default_provider: jwt                                             │
│    jwt:                                                              │
│      jwks_uri: https://auth.example.com/.well-known/jwks.json       │
│      issuer: https://auth.example.com/                               │
│      audience: mcp-proxy-api                                         │
│                                                                      │
│ Result: AccessToken stored in MCP context                           │
│  - Available via get_access_token()                                  │
│  - Contains: token, claims, expiry                                   │
└─────────────────────────────────────────────────────────────────────┘

Layer 2: Backend Service Authentication (Service Level)
┌─────────────────────────────────────────────────────────────────────┐
│ Per-Service Authentication (Configured in config.yaml)              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Option 1: Pass-Through Authentication                          │ │
│  │  services:                                                     │ │
│  │    - path: /api                                                │ │
│  │      auth:                                                     │ │
│  │        pass_through: true                                      │ │
│  │  → AuthPassThrough: Forwards MCP client token to backend      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Option 2: Azure OAuth2 Client Credentials                     │ │
│  │  services:                                                     │ │
│  │    - path: /api                                                │ │
│  │      auth:                                                     │ │
│  │        azure:                                                  │ │
│  │          client_id: $AZURE_CLIENT_ID                           │ │
│  │          client_secret: $AZURE_CLIENT_SECRET                   │ │
│  │          token_url: https://login.../oauth2/v2.0/token         │ │
│  │          scopes:                                               │ │
│  │            - api://.../.default                                │ │
│  │  → AzureOauth: Fetches service token via client credentials   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Option 3: Static API Token                                     │ │
│  │  services:                                                     │ │
│  │    - path: /api                                                │ │
│  │      auth:                                                     │ │
│  │        auth_token: "Bearer sk-1234567890"                      │ │
│  │  → Static header added to all requests                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Pass-Through Authentication

Pass-through authentication is the most powerful feature, enabling zero-configuration token forwarding from MCP clients to backend services.

### Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│              Pass-Through Authentication Flow (Detailed)               │
└────────────────────────────────────────────────────────────────────────┘

Step 1: Client Request with Token
┌──────────────────────────────────────────────────────────────┐
│ MCP Client (e.g., Claude Desktop, Custom App)                │
│                                                              │
│ POST /deepsea/mcp                                            │
│ Headers:                                                     │
│   Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...     │
│   Content-Type: application/json                            │
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
Step 2: MCP Protocol Layer - Token Extraction
┌──────────────────────────────────────────────────────────────┐
│ FastMCP Server (Mounted at /deepsea)                         │
│                                                              │
│ 1. FastMCP Auth Provider (if configured):                   │
│    - Validates Authorization header                          │
│    - Extracts JWT claims                                     │
│    - Stores AccessToken in MCP context                       │
│                                                              │
│ 2. AccessToken Structure:                                    │
│    class AccessToken:                                        │
│      token: str  ← Original JWT string                       │
│      claims: dict ← Decoded JWT claims (user_id, etc.)       │
│      expires_at: datetime                                    │
│                                                              │
│ 3. Context Storage:                                          │
│    MCP request context stores AccessToken                    │
│    Available to all tool executions via dependency injection │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: Tool Execution - Pass-Through Auth Flow
┌──────────────────────────────────────────────────────────────┐
│ OpenAPI Tool Execution (getCurrencyPairs)                    │
│                                                              │
│ 1. FastMCP prepares HTTP request via httpx.AsyncClient      │
│    GET /currency-pairs?base=USD                              │
│                                                              │
│ 2. httpx client has auth=AuthPassThrough()                   │
│    → Triggers async_auth_flow()                              │
│                                                              │
│ 3. AuthPassThrough.async_auth_flow():                        │
│    ┌────────────────────────────────────────────────────┐   │
│    │ from fastmcp.server.dependencies import (          │   │
│    │     get_access_token                               │   │
│    │ )                                                  │   │
│    │                                                    │   │
│    │ def async_auth_flow(self, request: httpx.Request):│   │
│    │     # Get token from MCP context                  │   │
│    │     token = get_access_token()                     │   │
│    │                                                    │   │
│    │     if token:                                      │   │
│    │         # Forward original client token           │   │
│    │         request.headers["Authorization"] = (      │   │
│    │             f"Bearer {token.token}"                │   │
│    │         )                                          │   │
│    │     else:                                          │   │
│    │         logger.warning("No access token available")│   │
│    │                                                    │   │
│    │     yield request                                  │   │
│    └────────────────────────────────────────────────────┘   │
│                                                              │
│ 4. Modified request:                                         │
│    GET /currency-pairs?base=USD                              │
│    Headers:                                                  │
│      Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...  │
│      ↑ Same token from original MCP client request          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: Backend API Request
┌──────────────────────────────────────────────────────────────┐
│ Backend OpenAPI Service (http://host.docker.internal:5000)   │
│                                                              │
│ Receives:                                                    │
│   GET /currency-pairs?base=USD                               │
│   Headers:                                                   │
│     Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...   │
│                                                              │
│ Backend validates token:                                     │
│   - Validates JWT signature                                  │
│   - Checks issuer, audience, expiry                          │
│   - Extracts user identity (user_id, email, roles)           │
│   - Enforces authorization policies                          │
│                                                              │
│ Returns response:                                            │
│   200 OK                                                     │
│   { "pairs": [...] }                                         │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 5: Response Returned to Client
┌──────────────────────────────────────────────────────────────┐
│ Response flows back through FastMCP to MCP client            │
│   {                                                          │
│     "jsonrpc": "2.0",                                        │
│     "id": 1,                                                 │
│     "result": {                                              │
│       "content": [                                           │
│         { "type": "text", "text": "{\"pairs\": [...]}" }     │
│       ]                                                      │
│     }                                                        │
│   }                                                          │
└──────────────────────────────────────────────────────────────┘
```

### Key Benefits

1. **Zero Configuration**:
   - No need to manage service-specific credentials
   - No token exchange or translation required
   - Works with any backend that accepts JWT tokens

2. **User Context Preservation**:
   - Backend receives original user token
   - Backend can enforce user-specific policies
   - Audit logs show actual user, not service account

3. **Security**:
   - No credential storage in config files
   - No shared service accounts
   - Token never leaves secure channel (HTTPS)

4. **Flexibility**:
   - Works with any JWT issuer
   - Compatible with OAuth2, OIDC, custom auth systems
   - Backend can use token for additional API calls

### Code Implementation

**AuthPassThrough** (`src/auth_providers/auth_pass_through.py`):
```python
import httpx
import typing
import logging
from fastmcp.server.dependencies import get_access_token
from mcp.server.auth.provider import AccessToken

logger = logging.getLogger(__name__)

class AuthPassThrough(httpx.Auth):
    """
    Pass-through authentication for httpx clients.
    
    Extracts the access token from the MCP request context
    and forwards it to the backend service.
    """
    
    def _get_token(self) -> AccessToken | None:
        """Get token from MCP context."""
        token = get_access_token()
        if token:
            logger.info(f"Access token: {token}")
        else:
            logger.warning("No access token available")
        return token
    
    def auth_flow(
        self, request: httpx.Request
    ) -> typing.Generator[httpx.Request, httpx.Response, None]:
        """Sync auth flow for pass-through authentication."""
        token = self._get_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token.token}"
        yield request

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> typing.AsyncGenerator[httpx.Request, httpx.Response]:
        """Async auth flow for pass-through authentication."""
        token = self._get_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token.token}"
        yield request
```

### Configuration Examples

**Example 1: Pass-Through Only**
```yaml
services:
  - path: /api
    spec_file: openapi/api.openapi.json
    spec_type: openapi
    base_url: https://api.example.com
    auth:
      pass_through: true
```

**Example 2: Pass-Through with Fallback to Azure OAuth**
```yaml
services:
  - path: /api
    spec_file: openapi/api.openapi.json
    spec_type: openapi
    base_url: https://api.example.com
    auth:
      pass_through: true
      azure:
        client_id: $AZURE_CLIENT_ID
        client_secret: $AZURE_CLIENT_SECRET
        token_url: https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token
        scopes:
          - api://example-api/.default
```
*Note: When both are configured, pass-through takes precedence if available.*

**Example 3: MCP Client Auth Configuration (config.yaml)**
```yaml
auth:
  enabled: true
  default_provider: jwt
  jwt:
    base_url: null
    jwks_uri: https://auth.example.com/.well-known/jwks.json
    issuer: https://auth.example.com/
    audience: mcp-proxy-api
    algorithm: RS256
```

**Note**: The field name is `default_provider` (snake_case) in config.yaml.

## Azure OAuth2 Client Credentials

For comparison, here's how Azure OAuth2 works (alternative to pass-through):

```
┌────────────────────────────────────────────────────────────────────────┐
│              Azure OAuth2 Client Credentials Flow                      │
└────────────────────────────────────────────────────────────────────────┘

Step 1: Initial Request
┌──────────────────────────────────────────────────────────────┐
│ httpx.AsyncClient makes first API request                    │
│ → Triggers AzureOauth.async_auth_flow()                       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 2: Token Fetch (if not cached)
┌──────────────────────────────────────────────────────────────┐
│ POST https://login.microsoftonline.com/TENANT/oauth2/v2.0/token│
│ Headers:                                                      │
│   Content-Type: application/x-www-form-urlencoded            │
│ Body:                                                        │
│   grant_type=client_credentials                              │
│   client_id=YOUR_CLIENT_ID                                   │
│   client_secret=YOUR_CLIENT_SECRET                           │
│   scope=api://YOUR_CLIENT_ID/.default                        │
│                                                              │
│ Response:                                                    │
│   {                                                          │
│     "token_type": "Bearer",                                  │
│     "expires_in": 3599,                                      │
│     "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJS..."       │
│   }                                                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 3: Token Caching
┌──────────────────────────────────────────────────────────────┐
│ AzureOauth stores token:                                     │
│  - In-memory cache (immediate reuse)                         │
│  - Persistent storage (optional, survives restarts)          │
│  - Expiry tracking (auto-refresh before expiration)          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        v
Step 4: Add Token to Request
┌──────────────────────────────────────────────────────────────┐
│ request.headers["Authorization"] = f"Bearer {azure_token}"   │
│ → Backend receives service account token, NOT user token    │
└──────────────────────────────────────────────────────────────┘
```

**Key Difference**: Azure OAuth uses **service account** credentials, while pass-through uses **user credentials**.

### Configuration

```yaml
services:
  - path: /api
    spec_file: openapi/api.openapi.json
    spec_type: openapi
    base_url: https://api.example.com
    auth:
      azure:
        client_id: $AZURE_CLIENT_ID
        client_secret: $AZURE_CLIENT_SECRET
        tenant_id: $AZURE_TENANT_ID
        issuer: https://sts.windows.net/$AZURE_TENANT_ID/
        token_url: https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token
        scopes:
          - api://$AZURE_CLIENT_ID/.default
```

### Environment Variables

```bash
AZURE_CLIENT_ID=your-app-client-id
AZURE_CLIENT_SECRET=your-app-client-secret
AZURE_TENANT_ID=your-tenant-id
```

## All Supported Auth Providers

### Layer 1: MCP Client Authentication (Global)

These providers authenticate MCP clients connecting to the proxy.

#### 1. JWT Provider

Token validation via JWKS (JSON Web Key Set):

```yaml
auth:
  enabled: true
  default_provider: jwt
  jwt:
    base_url: null
    jwks_uri: https://auth.example.com/.well-known/jwks.json
    issuer: https://auth.example.com/
    audience: mcp-proxy-api
    algorithm: RS256
```

**Environment Variables**:
```bash
FASTMCP_SERVER_AUTH=jwt
JWKS_URI=https://auth.example.com/.well-known/jwks.json
ISSUER=https://auth.example.com/
AUDIENCE=mcp-proxy-api
```

#### 2. GitHub OAuth

```bash
FASTMCP_SERVER_AUTH=github
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=your-github-client-id
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### 3. Google OAuth

```bash
FASTMCP_SERVER_AUTH=google
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=your-google-client-id
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### 4. Discord OAuth

```bash
FASTMCP_SERVER_AUTH=discord
FASTMCP_SERVER_AUTH_DISCORD_CLIENT_ID=your-discord-client-id
FASTMCP_SERVER_AUTH_DISCORD_CLIENT_SECRET=your-discord-client-secret
```

#### 5. WorkOS / AuthKit

```bash
FASTMCP_SERVER_AUTH=workos
# or
FASTMCP_SERVER_AUTH=authkit
```

#### 6. Descope

```bash
FASTMCP_SERVER_AUTH=descope
```

#### 7. Supabase

```bash
FASTMCP_SERVER_AUTH=supabase
```

#### 8. Scalekit

```bash
FASTMCP_SERVER_AUTH=scalekit
```

#### 9. Custom Provider

```bash
FASTMCP_SERVER_AUTH=com.example.auth.CustomAuthProvider
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
```

### Layer 2: Backend Service Authentication (Per-Service)

These providers authenticate the proxy to backend services.

#### 1. Pass-Through

Forwards user token from MCP client to backend:

```yaml
services:
  - path: /api
    auth:
      pass_through: true
```

#### 2. Azure OAuth2

Client credentials flow for service-to-service auth:

```yaml
services:
  - path: /api
    auth:
      azure:
        client_id: $AZURE_CLIENT_ID
        client_secret: $AZURE_CLIENT_SECRET
        tenant_id: $AZURE_TENANT_ID
        token_url: https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token
        scopes:
          - api://$AZURE_CLIENT_ID/.default
```

#### 3. Static Token

API key or bearer token:

```yaml
services:
  - path: /api
    auth:
      auth_token: "Bearer sk-1234567890abcdef"
```

#### 4. No Authentication

Public APIs:

```yaml
services:
  - path: /api
    auth: null
```

## Authentication Decision Matrix

| Scenario | Recommended Auth | Reason |
|----------|------------------|---------|
| User-specific actions (e.g., CRUD on user data) | **Pass-Through** | Backend needs user identity for authorization |
| Service-to-service (e.g., read shared resources) | **Azure OAuth** | Service account sufficient, better for caching |
| Public API (no auth) | **None** | No authentication required |
| API Key based | **Static Token** | Simple, no OAuth overhead |
| Multi-tenant with user context | **Pass-Through** | Each user needs their own token |
| High-volume background jobs | **Azure OAuth** | Minimize token validations, better performance |

## Best Practices

### When to Use Pass-Through

1. **Backend enforces user-level permissions**: Users can only access their own data
2. **Audit logs require user identity**: Track who did what
3. **Backend makes downstream API calls on behalf of user**: Token needs to work for multiple services
4. **Multi-tenant systems**: Each user has different access rights

### When to Use Azure OAuth

1. **Backend doesn't require user context**: Service account has access to all data
2. **High request volume**: Token caching reduces overhead
3. **Service-to-service communication**: No user involved
4. **Internal APIs**: Backend trusts the service account

### When to Use Static Token

1. **Simple API key authentication**: No OAuth2 infrastructure
2. **Testing and development**: Quick setup
3. **Public APIs with rate limiting**: API key for tracking
4. **No token expiry**: Long-lived credentials

### Security Considerations

1. **Always use HTTPS in production**: Protect tokens in transit
2. **Rotate client secrets regularly**: Azure OAuth credentials
3. **Configure appropriate token expiry times**: Balance security and user experience
4. **Validate tokens on backend**: Don't trust proxy alone
5. **Use minimum required scopes**: Principle of least privilege
6. **Store secrets in environment variables**: Never commit to source control
7. **Enable audit logging**: Track authentication events
8. **Monitor for suspicious activity**: Failed auth attempts, unusual patterns

### Configuration Management

1. **Use environment variables for secrets**: `$AZURE_CLIENT_SECRET`
2. **Use YAML files for non-sensitive config**: Service URLs, scopes
3. **Validate configuration on startup**: Catch errors early
4. **Document authentication requirements**: Help users configure correctly

### Monitoring and Logging

1. **Log authentication failures**: Help diagnose issues
2. **Track token refresh rates**: Azure OAuth performance
3. **Monitor pass-through availability**: Alert if tokens missing
4. **Alert on expired credentials**: Before users affected
5. **Measure authentication latency**: Identify bottlenecks

## Troubleshooting

### Pass-Through Authentication Issues

**Problem**: Backend receives no Authorization header

**Solutions**:
1. Verify MCP client auth is configured (Layer 1)
2. Check that client sends Authorization header
3. Confirm `pass_through: true` in config.yaml
4. Check logs for "No access token available"

**Problem**: Backend rejects token

**Solutions**:
1. Verify token format matches backend expectations
2. Check token expiry
3. Confirm issuer and audience match
4. Test token directly with backend API

### Azure OAuth Issues

**Problem**: Token fetch fails

**Solutions**:
1. Verify client credentials are correct
2. Check token URL is accessible from proxy
3. Confirm scopes are correct for target API
4. Review Azure AD app registration

**Problem**: Token expires too quickly

**Solutions**:
1. Check token lifetime in Azure AD
2. Verify token refresh logic
3. Monitor token cache hit rate
4. Consider increasing token lifetime

### MCP Client Authentication Issues

**Problem**: Client authentication fails

**Solutions**:
1. Verify JWKS_URI is accessible
2. Check issuer and audience claims
3. Confirm algorithm matches (RS256, etc.)
4. Validate token with jwt.io
5. Check auth provider configuration

### Configuration Errors

**Problem**: Invalid auth configuration

**Solutions**:
1. Validate YAML syntax
2. Check required fields are present
3. Verify environment variables are set
4. Review error messages in logs

## Environment Variables Reference

### Global Auth (Layer 1)

```bash
# JWT Provider
FASTMCP_SERVER_AUTH=jwt
JWKS_URI=https://auth.example.com/.well-known/jwks.json
ISSUER=https://auth.example.com/
AUDIENCE=mcp-proxy-api

# GitHub OAuth
FASTMCP_SERVER_AUTH=github
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=your-client-id
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=your-client-secret

# Google OAuth
FASTMCP_SERVER_AUTH=google
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=your-client-id
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=your-client-secret

# Discord OAuth
FASTMCP_SERVER_AUTH=discord
FASTMCP_SERVER_AUTH_DISCORD_CLIENT_ID=your-client-id
FASTMCP_SERVER_AUTH_DISCORD_CLIENT_SECRET=your-client-secret
```

### Service Auth (Layer 2)

```bash
# Azure OAuth
AZURE_CLIENT_ID=your-app-client-id
AZURE_CLIENT_SECRET=your-app-client-secret
AZURE_TENANT_ID=your-tenant-id

# OAuth Token Storage Encryption
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=your-encryption-key
```

## Related Documentation

- [First Steps](../../getting-started/first-steps.md) - Authentication setup guide
- [MCP Proxy Management](../mcp/proxy-management.md) - MCP service configuration
- [OpenAPI Integration](../openapi/integration.md) - OpenAPI auth configuration
- [API Reference](../../api-reference/endpoints.md) - API endpoints

## Additional Resources

- [FastMCP Authentication Docs](https://github.com/modelcontextprotocol/fastmcp)
- [Azure AD OAuth2 Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-client-creds-grant-flow)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
