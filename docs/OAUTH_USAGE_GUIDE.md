# OAuth2 Client Credentials Usage Guide

## FastMCP-Compatible Entra ID OAuth Provider

This guide demonstrates how to use the refactored `EntraClientCredentialsOAuth` class for OAuth2 authentication with
Entra ID (Azure AD).

## Quick Start

### Basic Usage (No Storage)

```python
from src.tools.oauth_client import EntraClientCredentialsOAuth
import httpx

# Create OAuth provider
oauth = EntraClientCredentialsOAuth(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://login.microsoftonline.com/YOUR-TENANT-ID/oauth2/v2.0/token",
    scope="https://graph.microsoft.com/.default",
    base_url="https://graph.microsoft.com",
)

# Use as httpx auth
client = httpx.AsyncClient(auth=oauth)

# Make authenticated requests
async with client:
    response = await client.get("/v1.0/users")
    users = response.json()
```

## Advanced Usage

### With Token Storage

```python
from src.tools.oauth_client import EntraClientCredentialsOAuth
from your_storage_module import EncryptedTokenStorage
import httpx

# Create storage adapter
storage = EncryptedTokenStorage(
    key_file="~/.oauth-tokens/encryption-key",
    token_file="~/.oauth-tokens/tokens.db",
)

# Create OAuth provider with persistence
oauth = EntraClientCredentialsOAuth(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://login.microsoftonline.com/YOUR-TENANT-ID/oauth2/v2.0/token",
    scope="https://graph.microsoft.com/.default",
    storage=storage,  # Enable persistent caching
    base_url="https://graph.microsoft.com",
    timeout=30.0,
)

# Use as before
client = httpx.AsyncClient(auth=oauth)

async with client:
    response = await client.get("/v1.0/users")
```

### With Multiple Scopes

```python
oauth = EntraClientCredentialsOAuth(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://login.microsoftonline.com/YOUR-TENANT-ID/oauth2/v2.0/token",
    scope="https://graph.microsoft.com/.default https://management.azure.com/.default",
    base_url="https://graph.microsoft.com",
)
```

### As Context Manager

```python
async with EntraClientCredentialsOAuth(
        client_id="your-client-id",
        client_secret="your-client-secret",
        token_url="https://login.microsoftonline.com/YOUR-TENANT-ID/oauth2/v2.0/token",
        scope="https://graph.microsoft.com/.default",
        base_url="https://graph.microsoft.com",
) as oauth:
    client = httpx.AsyncClient(auth=oauth)
    async with client:
        response = await client.get("/v1.0/me")
        profile = response.json()
```

## Token Lifecycle

### Automatic Token Management

The OAuth provider handles token lifecycle automatically:

1. **First Request**: Fetches fresh token from Entra ID
2. **Subsequent Requests**: Uses cached token (if not expired)
3. **Token Expiry**: Automatically refreshes 60 seconds before expiry
4. **Storage**: Optionally persists tokens across restarts

### Manual Token Access

```python
# Get current token (will fetch if needed)
token = await oauth._get_token()
print(f"Access Token: {token['access_token']}")
print(f"Expires In: {token['expires_in']} seconds")

# Check if current token is expired
is_expired = oauth._is_token_expired()
```

## Backward Compatibility

Existing code using `OauthAsyncClient` continues to work:

```python
# Still works!
from src.tools.oauth_client import OauthAsyncClient

client = OauthAsyncClient(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://login.microsoftonline.com/YOUR-TENANT-ID/oauth2/v2.0/token",
    base_url="https://graph.microsoft.com",
)

# Use original API
response = await client.get("/v1.0/users")
```

## Implementation Details

### Supported HTTP Methods

All standard HTTP methods are supported with automatic OAuth injection:

```python
await oauth.get("/v1.0/users")
await oauth.post("/v1.0/users", json={"displayName": "New User"})
await oauth.put("/v1.0/users/{id}", json={"displayName": "Updated"})
await oauth.patch("/v1.0/users/{id}", json={"givenName": "Updated"})
await oauth.delete("/v1.0/users/{id}")
```

### Request Building

Build requests without automatic sending:

```python
request = oauth.build_request("GET", "/v1.0/users")
# Modify request as needed
request.headers["X-Custom"] = "value"

# Send with auth
response = await oauth.send(request)
```

### Storage Adapter Interface

If implementing custom token storage:

```python
class MyTokenStorage:
    async def get_tokens(self) -> dict | None:
        """Load tokens from storage"""
        # Return token dict or None if not found
        pass

    async def set_tokens(self, tokens: dict) -> None:
        """Save tokens to storage"""
        # Persist token dict securely
        pass


storage = MyTokenStorage()
oauth = EntraClientCredentialsOAuth(
    # ... other params ...
    storage=storage,
)
```

## Common Scenarios

### OpenAPI Integration

```python
from src.proxies.openapi_mcp_provider import OpenApiMcpProvider

oauth = EntraClientCredentialsOAuth(
    client_id="client-id",
    client_secret="client-secret",
    token_url="https://login.microsoftonline.com/tenant/oauth2/v2.0/token",
    scope="https://graph.microsoft.com/.default",
    base_url="https://graph.microsoft.com",
)

client = httpx.AsyncClient(auth=oauth)
# Pass to OpenApiMcpProvider
```

### FastMCP Integration

```python
from fastmcp import FastMCP

oauth = EntraClientCredentialsOAuth(
    # ... configuration ...
)

client = httpx.AsyncClient(auth=oauth)

mcp = FastMCP.from_openapi(
    name="my-api",
    openapi_spec=spec,
    client=client,  # Uses OAuth automatically
)
```

### Error Handling

```python
try:
    response = await oauth.get("/v1.0/users")
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    print(f"API Error: {e.response.status_code}")
except httpx.RequestError as e:
    print(f"Request Error: {e}")
```

## Configuration Reference

### Required Parameters

- `client_id`: OAuth2 client ID from Entra ID
- `client_secret`: OAuth2 client secret
- `token_url`: Entra ID token endpoint
- `base_url`: Base URL for API requests

### Optional Parameters

- `scope`: OAuth2 scopes (space-separated if multiple)
- `storage`: Token storage adapter for persistence
- `timeout`: HTTP timeout in seconds (default: 30.0)

## Performance Tips

1. **Reuse OAuth Instance**: Create once, use multiple times
2. **Connection Pooling**: httpx.AsyncClient maintains connection pools automatically
3. **Token Caching**: Tokens are cached in-memory (no refetch until expiry)
4. **Storage Benefits**: Persistent storage avoids token fetching on restart

## Troubleshooting

### "Invalid client" Error

- Verify `client_id` and `client_secret` are correct
- Check client is registered in Entra ID

### "Invalid scope" Error

- Verify scope format: `https://resource/.default`
- Check scope is configured for the client in Entra ID

### Token Not Persisting

- Verify `storage` adapter is properly initialized
- Check file system permissions for storage location

### Slow First Request

- First request includes token fetch (expected)
- Subsequent requests are fast (token cached)
- Consider warming up with a dummy request on startup

## References

- [OAuth2 Client Credentials Flow (RFC 6749)](https://tools.ietf.org/html/rfc6749#section-4.4)
- [Microsoft Entra ID OAuth Endpoints](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols)
- [httpx Documentation](https://www.python-httpx.org/)
- [FastMCP Documentation](https://alPrice.github.io/fastmcp/)

---

**Last Updated**: February 15, 2026  
**Status**: Production Ready

