# Configuration Files

Complete reference for all configuration files used by drunk-mcp-proxy.

## Configuration Files Overview

drunk-mcp-proxy uses JSON configuration files stored in the `data/` directory (configurable via `FASTMCP_CONFIG_DIR`):

| File | Purpose | Required |
|------|---------|----------|
| `config.json` | MCP and OpenAPI service definitions | Yes |
| `auth.json` | Client authentication configuration | No |
| `llm.json` | LLM provider configurations | No |

## config.json - Service Configuration

This is the main configuration file that defines which MCP and OpenAPI services to proxy.

### Structure

An array of service configuration objects:

```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null
  },
  {
    "path": "/api",
    "spec_file": "openapi/petstore.yaml",
    "spec_type": "openapi",
    "base_url": "https://api.example.com"
  }
]
```

### Field Reference

#### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `path` | string | Mount path for the service | `"/"`, `"/stock"`, `"/api"` |
| `spec_type` | enum | Type of specification | `"mcp"` or `"openapi"` |

#### Conditional Fields

| Field | Type | Required When | Description |
|-------|------|---------------|-------------|
| `spec_file` | string | Unless `mcpServers` provided | Path to specification file (relative to config dir) |
| `base_url` | string | For OpenAPI services | Base URL of the backend API |
| `mcpServers` | object | If no `spec_file` | Inline MCP server configuration (MCP only) |

#### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `tags` | array | Categorization tags | `["finance", "public"]` |
| `filters` | object | Filter OpenAPI operations | See [Filters](#filters) below |
| `auth` | object | Backend authentication config | See [Backend Auth](#backend-authentication) below |
| `skill_dir` | string | Skills directory (MCP only) | `"skills"` |

### MCP Service Configuration

#### Basic MCP Service

```json
{
  "path": "/",
  "spec_file": "mcp/mcp.json",
  "spec_type": "mcp",
  "base_url": null
}
```

#### MCP with Skills Directory

```json
{
  "path": "/",
  "spec_file": "mcp/mcp.json",
  "spec_type": "mcp",
  "base_url": null,
  "skill_dir": "skills"
}
```

The `skill_dir` points to a directory (relative to config dir) containing subdirectories with skill resources. Each subdirectory is registered with FastMCP's SkillsDirectoryProvider.

#### MCP with Inline Servers

```json
{
  "path": "/stock",
  "spec_type": "mcp",
  "mcpServers": {
    "stock-api": {
      "url": "https://mcp-stock.example.com/mcp",
      "transport": "http"
    },
    "stock-cache": {
      "command": "node",
      "args": ["stock-cache-server.js"],
      "transport": "stdio"
    }
  }
}
```

### OpenAPI Service Configuration

#### Basic OpenAPI Service

```json
{
  "path": "/petstore",
  "spec_file": "openapi/petstore.yaml",
  "spec_type": "openapi",
  "base_url": "https://petstore3.swagger.io/api/v3"
}
```

#### OpenAPI with Filters

```json
{
  "path": "/api",
  "spec_file": "openapi/api.yaml",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "filters": {
    "methods": ["GET", "POST", "PUT"],
    "tags": ["users", "posts", "comments"]
  }
}
```

#### Filters

Filter OpenAPI operations to expose only specific endpoints:

```json
"filters": {
  "methods": ["GET", "POST"],     // Only these HTTP methods
  "tags": ["users", "posts"]      // Only operations with these tags
}
```

Both filters are optional and work together (AND logic).

### Backend Authentication

Configure how the proxy authenticates to backend services (separate from client→proxy auth):

#### Pass-Through Authentication

Forward client token to backend:

```json
{
  "path": "/api",
  "spec_file": "openapi/api.yaml",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "pass_through": true
  }
}
```

#### Azure OAuth Client Credentials

Use client credentials flow for backend:

```json
{
  "path": "/api",
  "spec_file": "openapi/api.yaml",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "azure": {
      "client_id": "$AZURE_CLIENT_ID",
      "client_secret": "$AZURE_CLIENT_SECRET",
      "tenant_id": "$AZURE_TENANT_ID",
      "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
      "scopes": ["https://api.example.com/.default"],
      "issuer": "https://sts.windows.net/$AZURE_TENANT_ID/"
    }
  }
}
```

#### Combined: Pass-Through with Azure Fallback

Try pass-through first, fall back to Azure client credentials:

```json
{
  "path": "/api",
  "spec_file": "openapi/api.yaml",
  "spec_type": "openapi",
  "base_url": "https://api.example.com",
  "auth": {
    "pass_through": true,
    "azure": {
      "client_id": "$AZURE_CLIENT_ID",
      "client_secret": "$AZURE_CLIENT_SECRET",
      "tenant_id": "$AZURE_TENANT_ID",
      "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
      "scopes": ["https://api.example.com/.default"]
    }
  }
}
```

### Complete Example

```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "skill_dir": "skills",
    "tags": ["primary", "public"]
  },
  {
    "path": "/stock",
    "spec_file": "mcp/stock.mcp.json",
    "spec_type": "mcp",
    "base_url": null,
    "tags": ["finance", "internal"]
  },
  {
    "path": "/deepsea",
    "spec_file": "openapi/deepsea.openapi.json",
    "spec_type": "openapi",
    "base_url": "http://host.docker.internal:5000",
    "filters": {
      "methods": ["GET", "POST", "PUT"],
      "tags": ["CurrencyPairs", "Trading"]
    },
    "auth": {
      "pass_through": true,
      "azure": {
        "client_id": "$AZURE_CLIENT_ID",
        "client_secret": "$AZURE_CLIENT_SECRET",
        "tenant_id": "$AZURE_TENANT_ID",
        "token_url": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
        "issuer": "https://sts.windows.net/$AZURE_TENANT_ID/",
        "scopes": ["api://$AZURE_CLIENT_ID/.default"]
      }
    },
    "tags": ["finance", "trading", "internal"]
  }
]
```

## auth.json - Client Authentication

Configures how MCP clients authenticate to the proxy (not backend auth).

### Structure

```json
{
  "defaultProvider": "jwt",
  "jwt": {
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "issuer": "https://auth.example.com/",
    "audience": "mcp-proxy-api"
  }
}
```

### Supported Providers

- `auth0` - Auth0 authentication
- `aws` - AWS Cognito
- `azure` - Azure AD/Entra ID
- `debug` - Debug mode (dev only)
- `descope` - Descope CIAM
- `discord` - Discord OAuth
- `github` - GitHub OAuth
- `google` - Google OAuth
- `inMemory` - In-memory users (dev/testing)
- `introspection` - Token introspection
- `jwt` - JWT validation
- `oci` - Oracle Cloud
- `scalekit` - Scalekit SAML
- `supabase` - Supabase auth
- `workos` - WorkOS SAML
- `authkit` - AuthKit (WorkOS)

### Example Configurations

#### JWT Provider

```json
{
  "defaultProvider": "jwt",
  "jwt": {
    "jwks_uri": "https://login.microsoftonline.com/common/discovery/keys",
    "issuer": "https://sts.windows.net/$AZURE_TENANT_ID/",
    "audience": "api://your-client-id",
    "algorithm": "RS256"
  }
}
```

#### GitHub OAuth

```json
{
  "defaultProvider": "github",
  "github": {
    "client_id": "$GITHUB_CLIENT_ID",
    "client_secret": "$GITHUB_CLIENT_SECRET",
    "base_url": "https://your-proxy.example.com"
  }
}
```

#### In-Memory (Development)

```json
{
  "defaultProvider": "inMemory",
  "inMemory": {
    "users": {
      "testuser": "password123",
      "admin": "admin123"
    }
  }
}
```

See `data/auth_example.json` for all provider configurations.

## Environment Variable Resolution

Both `config.json` and `auth.json` support environment variable substitution:

### Syntax

- `$VAR_NAME` - Simple substitution
- `${VAR_NAME}` - Braced substitution (allows more complex patterns)

### Examples

```json
{
  "client_id": "$AZURE_CLIENT_ID",
  "tenant_id": "${AZURE_TENANT_ID}",
  "token_url": "https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/token",
  "base_url": "$API_BASE_URL"
}
```

Variables are resolved at startup from:
1. Environment variables
2. `.env` file (if present)
3. Docker environment

## Configuration Validation

All configurations are validated against JSON schemas in the `schemas/` directory:

- `schemas/mcp.schema.json` - MCP configuration schema
- `schemas/auth.schema.json` - Auth configuration schema

Validation happens automatically at startup. Invalid configurations will prevent the server from starting.

## Best Practices

### Security

1. **Never commit secrets** - Use environment variables for sensitive data
2. **Use `.env` for local dev** - Not committed to git
3. **Use Docker secrets** for production
4. **Validate schemas** before deployment

### Organization

1. **Group related services** - Use namespaced paths (`/stock`, `/wiki`)
2. **Use meaningful tags** - For categorization and filtering
3. **Document custom configs** - Add comments in separate docs
4. **Version control configs** - Track changes to configuration

### Performance

1. **Minimize filters** - Only filter when necessary
2. **Cache tokens** - OAuth caching enabled by default
3. **Use health checks** - Monitor service availability

## Related Documentation

- [Environment Variables](environment-variables.md)
- [Schema Validation](schema-validation.md)
- [Authentication Overview](../features/authentication/overview.md)
- [MCP Configuration](../features/mcp/proxy-management.md)
- [OpenAPI Configuration](../features/openapi/configuration.md)
