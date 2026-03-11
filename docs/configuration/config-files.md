# Configuration Files

Complete reference for configuration used by drunk-mcp-proxy.

## Configuration Overview

drunk-mcp-proxy uses a unified YAML configuration file stored in the `data/` directory (configurable via `FASTMCP_CONFIG_DIR`):

| File | Purpose | Required |
|------|---------|----------|
| `config.yaml` | Unified configuration for authentication, LLM providers, and MCP/OpenAPI services | Yes |

> **Note**: The configuration was migrated from multiple JSON files (`config.json`, `auth.json`, `llm.json`) to a single `config.yaml` file for better maintainability and clarity.

## config.yaml - Unified Configuration

This is the main configuration file that defines:
1. **Authentication** - How clients authenticate to the proxy
2. **LLM Providers** - LLM services for routing requests
3. **MCP/OpenAPI Services** - Which backend services to proxy
4. **Remote Resource Bundles** - Startup sync of HTTPS files into local folders

### Structure

```yaml
# Authentication configuration (optional)
auth:
  defaultProvider: basic
  basic:
    token: $API_KEY

# LLM providers (optional)
llm:
  - enabled: true
    provider: openai
    base_url: "https://api.openai.com/v1"
    api_key: $OPENAI_API_KEY

# MCP and OpenAPI services
mcp:
  - path: /
    spec_file: mcp/mcp.json
    spec_type: mcp

  - path: /api
    spec_file: openapi/petstore.yaml
    spec_type: openapi
    base_url: "https://api.example.com"

# Remote resource bundles (optional)
remote_resources:
  - name: dotnet_prompt
    to_dir: prompts/dotnet
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md
```

### Field Reference

#### MCP Service Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `enabled` | boolean | No | Enable/disable this service | `true` (default) |
| `path` | string | Yes | Mount path for the service | `/`, `/stock`, `/api` |
| `spec_type` | enum | Yes | Type of specification | `mcp` or `openapi` |
| `spec_file` | string | Conditional | Path to spec file (relative to config dir) | `mcp/stock.json` |
| `base_url` | string | For OpenAPI | Base URL of the backend API | `https://api.example.com` |
| `mcp_servers` | object | If no spec_file | Inline MCP server configuration (MCP only) | See below |
| `skill_dir` | string | No | Skills directory (MCP only) | `skills` |
| `filters` | object | No | Filter OpenAPI operations | See [Filters](#filters) |
| `auth` | object | No | Backend authentication config | See [Backend Auth](#backend-authentication) |
| `tags` | array | No | Categorization tags | `["finance", "public"]` |

#### Authentication Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `defaultProvider` | enum | Yes | Default auth provider to use | `basic`, `jwt`, `azure` |
| `basic` | object | If using basic | Bearer token configuration | See below |
| `jwt` | object | If using JWT | JWT validation configuration | See below |

#### LLM Provider Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `enabled` | boolean | Yes | Enable/disable this provider | `true` |
| `provider` | string | Yes | Provider name | `openai`, `openrouter` |
| `base_url` | string | Yes | Provider API base URL | `https://api.openai.com/v1` |
| `api_key` | string | No | API key (supports env vars) | `$OPENAI_API_KEY` |

#### Remote Resource Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | string | Yes | Logical bundle name used in logs | `dotnet_prompt` |
| `to_dir` | string | Yes | Destination folder under `FASTMCP_CONFIG_DIR` | `prompts/dotnet` |
| `paths` | array[string] | Yes | List of source URLs (HTTPS only) | `["https://example.com/a.md"]` |

Remote resource downloads run in the background at startup and do not block server startup.
Skill and agent providers can pick up newly downloaded files at runtime via reload mode.
Prompt template runtime reload is not currently supported.

### MCP Service Configuration

#### Basic MCP Service

```yaml
mcp:
  - path: /
    spec_file: mcp/mcp.json
    spec_type: mcp
```

#### MCP with Skills Directory

```yaml
mcp:
  - path: /
    spec_file: mcp/mcp.json
    spec_type: mcp
    skill_dir: skills
```

The `skill_dir` points to a directory (relative to config dir) containing subdirectories with skill resources. Each subdirectory is registered with FastMCP's SkillsDirectoryProvider.

#### MCP with Inline Servers

```yaml
mcp:
  - path: /stock
    spec_type: mcp
    mcp_servers:
      stock-api:
        url: "https://mcp-stock.example.com/mcp"
        transport: http
      stock-cache:
        command: node
        args: ["stock-cache-server.js"]
        transport: stdio
```

### OpenAPI Service Configuration

#### Basic OpenAPI Service

```yaml
mcp:
  - path: /petstore
    spec_file: openapi/petstore.yaml
    spec_type: openapi
    base_url: "https://petstore3.swagger.io/api/v3"
```

#### OpenAPI with Filters

```yaml
mcp:
  - path: /api
    spec_file: openapi/api.yaml
    spec_type: openapi
    base_url: "https://api.example.com"
    filters:
      methods: ["GET", "POST", "PUT"]
      tags: ["users", "posts", "comments"]
```

#### Filters

Filter OpenAPI operations to expose only specific endpoints:

```yaml
filters:
  methods: ["GET", "POST"]  # Only these HTTP methods
  tags: ["users", "posts"]  # Only operations with these tags
```

Both filters are optional and work together (AND logic).

### Backend Authentication

Configure how the proxy authenticates to backend services (separate from client→proxy auth):

#### Pass-Through Authentication

Forward client token to backend:

```yaml
mcp:
  - path: /api
    spec_file: openapi/api.yaml
    spec_type: openapi
    base_url: "https://api.example.com"
    auth:
      pass_through: true
```

#### Azure OAuth Client Credentials

Use client credentials flow for backend:

```yaml
mcp:
  - path: /api
    spec_file: openapi/api.yaml
    spec_type: openapi
    base_url: "https://api.example.com"
    auth:
      azure:
        client_id: $AZURE_CLIENT_ID
        client_secret: $AZURE_CLIENT_SECRET
        tenant_id: $AZURE_TENANT_ID
        token_url: "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token"
        scopes: ["https://api.example.com/.default"]
        issuer: "https://sts.windows.net/$AZURE_TENANT_ID/"
```

#### Combined: Pass-Through with Azure Fallback

Try pass-through first, fall back to Azure client credentials:

```yaml
mcp:
  - path: /api
    spec_file: openapi/api.yaml
    spec_type: openapi
    base_url: "https://api.example.com"
    auth:
      pass_through: true
      azure:
        client_id: $AZURE_CLIENT_ID
        client_secret: $AZURE_CLIENT_SECRET
        tenant_id: $AZURE_TENANT_ID
        token_url: "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token"
        scopes: ["https://api.example.com/.default"]
```

### Complete Example

```yaml
# Complete configuration with authentication, LLM, and multiple services
auth:
  defaultProvider: azure
  basic:
    token: $API_KEY
  jwt:
    jwks_uri: "https://login.microsoftonline.com/$AZURE_TENANT_ID/discovery/keys"
    issuer: "https://sts.windows.net/$AZURE_TENANT_ID/"
    audience: "api://$AZURE_CLIENT_ID"
  azure:
    client_id: $AZURE_CLIENT_ID
    client_secret: $AZURE_CLIENT_SECRET
    tenant_id: $AZURE_TENANT_ID

llm:
  - enabled: true
    provider: openai
    base_url: "https://api.openai.com/v1"
    api_key: $OPENAI_API_KEY

mcp:
  - path: /
    spec_file: mcp/mcp.json
    spec_type: mcp
    skill_dir: skills
    tags: ["primary", "public"]

  - path: /stock
    spec_file: mcp/stock.mcp.json
    spec_type: mcp
    tags: ["finance", "internal"]

  - path: /deepsea
    spec_file: openapi/deepsea.openapi.json
    spec_type: openapi
    base_url: "http://host.docker.internal:5000"
    filters:
      methods: ["GET", "POST", "PUT"]
      tags: ["CurrencyPairs", "Trading"]
    auth:
      pass_through: true
      azure:
        client_id: $AZURE_CLIENT_ID
        client_secret: $AZURE_CLIENT_SECRET
        tenant_id: $AZURE_TENANT_ID
        token_url: "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token"
        issuer: "https://sts.windows.net/$AZURE_TENANT_ID/"
        scopes: ["api://$AZURE_CLIENT_ID/.default"]
    tags: ["finance", "trading", "internal"]
```

## Authentication Configuration

Configure how MCP clients authenticate to the proxy (client→proxy auth).

### Structure

```yaml
auth:
  defaultProvider: jwt
  jwt:
    jwks_uri: "https://auth.example.com/.well-known/jwks.json"
    issuer: "https://auth.example.com/"
    audience: "mcp-proxy-api"
```

### Supported Providers

- `basic` - Bearer token (API key) authentication
- `auth0` - Auth0 authentication
- `aws` - AWS Cognito
- `azure` - Azure AD/Entra ID
- `debug` - Debug mode (dev only)
- `descope` - Descope CIAM
- `discord` - Discord OAuth
- `github` - GitHub OAuth
- `google` - Google OAuth
- `in_memory` - In-memory users (dev/testing)
- `introspection` - Token introspection
- `jwt` - JWT validation
- `oci` - Oracle Cloud
- `scalekit` - Scalekit SAML
- `supabase` - Supabase auth
- `workos` - WorkOS SAML
- `authkit` - AuthKit (WorkOS)

### Example Configurations

#### JWT Provider

```yaml
auth:
  defaultProvider: jwt
  jwt:
    jwks_uri: "https://login.microsoftonline.com/common/discovery/keys"
    issuer: "https://sts.windows.net/$AZURE_TENANT_ID/"
    audience: "api://your-client-id"
    algorithm: "RS256"
```

#### GitHub OAuth

```yaml
auth:
  defaultProvider: github
  github:
    client_id: $GITHUB_CLIENT_ID
    client_secret: $GITHUB_CLIENT_SECRET
    base_url: "https://your-proxy.example.com"
```

#### In-Memory (Development)

```yaml
auth:
  defaultProvider: in_memory
  in_memory:
    users:
      testuser: password123
      admin: admin123
```

See `data/config.yaml` for more provider configurations.

## LLM Provider Configuration

Configure LLM providers that the proxy can route requests to.

### Structure

```yaml
llm:
  - enabled: true
    provider: openai
    base_url: "https://api.openai.com/v1"
    api_key: $OPENAI_API_KEY

  - enabled: false
    provider: openrouter
    base_url: "https://openrouter.ai/v1"
    api_key: $OPENROUTER_API_KEY
```

### Example Configurations

#### OpenAI Provider

```yaml
llm:
  - enabled: true
    provider: openai
    base_url: "https://api.openai.com/v1"
    api_key: $OPENAI_API_KEY
```

#### Multiple Providers

```yaml
llm:
  - enabled: true
    provider: openai
    base_url: "https://api.openai.com/v1"
    api_key: $OPENAI_API_KEY

  - enabled: true
    provider: anthropic
    base_url: "https://api.anthropic.com/v1"
    api_key: $ANTHROPIC_API_KEY

  - enabled: false
    provider: openrouter
    base_url: "https://openrouter.ai/v1"
    api_key: $OPENROUTER_API_KEY
```

## Environment Variable Resolution

The configuration file supports environment variable substitution:

### Syntax

- `$VAR_NAME` - Simple substitution
- `${VAR_NAME}` - Braced substitution (allows more complex patterns)

### Examples

```yaml
auth:
  basic:
    token: $API_KEY
  jwt:
    jwks_uri: "https://login.microsoftonline.com/${AZURE_TENANT_ID}/discovery/keys"
    issuer: "https://sts.windows.net/$AZURE_TENANT_ID/"

llm:
  - provider: openai
    api_key: $OPENAI_API_KEY
    base_url: $API_BASE_URL

mcp:
  - path: /api
    base_url: "https://api.example.com/${API_VERSION}"
```

Variables are resolved at startup from:
1. Environment variables
2. `.env` file (if present)
3. Docker environment

## Configuration Validation

Configuration is validated automatically at startup using Pydantic models. Invalid configurations will prevent the server from starting.

### Manual Validation

You can validate your YAML configuration manually:

```bash
# Using Python
python -c "from tools import ConfigYaml; ConfigYaml.load_from_file('data/config.yaml')"

# Using yamllint (if installed)
yamllint data/config.yaml
```

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
