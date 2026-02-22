# Environment Variables

Complete reference for all environment variables used by drunk-mcp-proxy.

## Overview

drunk-mcp-proxy can be configured using environment variables, which are useful for:
- **Docker deployments** - Pass config via container environment
- **CI/CD pipelines** - Configure per environment
- **Security** - Keep secrets out of config files
- **Flexibility** - Override defaults without changing files

## Configuration Priority

Configuration is loaded in this order (later sources override earlier):

1. Default values (hardcoded)
2. `.env` file (if present)
3. Environment variables
4. Configuration files (`config.json`, `auth.json`)

## Configuration Variables

### Directories and Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_CONFIG_DIR` | `data` | Directory containing `config.json` and spec files |
| `FASTMCP_SCHEMA_DIR` | `schemas` | Directory containing JSON schema files for validation |

**Example:**
```bash
FASTMCP_CONFIG_DIR=/etc/mcp-proxy/config
FASTMCP_SCHEMA_DIR=/etc/mcp-proxy/schemas
```

## Server Configuration

### Basic Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_SERVER_NAME` | `mcp-proxy-server` | Server name used in logging and health checks |
| `FASTMCP_SERVER_VERSION` | `1.0.0` | Server version string |
| `FASTMCP_HOST` | `0.0.0.0` | Host/IP to bind to (`0.0.0.0` = all interfaces) |
| `FASTMCP_PORT` | `9123` | Port to listen on |
| `FASTMCP_SERVER_TRANSPORT` | `streamable-http` | Transport protocol (`http`, `sse`, `streamable-http`, `stdio`) |

**Example:**
```bash
FASTMCP_SERVER_NAME=production-mcp-proxy
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8080
FASTMCP_SERVER_TRANSPORT=sse
```

## Logging Configuration

### Log Level

| Variable | Default | Values | Description |
|----------|---------|--------|-------------|
| `FASTMCP_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Logging verbosity |

**Example:**
```bash
# Development
FASTMCP_LOG_LEVEL=DEBUG

# Production
FASTMCP_LOG_LEVEL=WARNING
```

## CORS Configuration

### CORS Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_CORS_ALLOW_ORIGINS` | _(empty)_ | Comma-separated allowed origins. Use `*` for all (not recommended in production) |
| `FASTMCP_CORS_ALLOW_METHODS` | `*` | Comma-separated allowed HTTP methods |
| `FASTMCP_CORS_ALLOW_HEADERS` | `*` | Comma-separated allowed request headers |
| `FASTMCP_CORS_EXPOSE_HEADERS` | _(empty)_ | Comma-separated response headers to expose to browser |
| `FASTMCP_CORS_ALLOW_CREDENTIALS` | `false` | Allow cookies and credentials |
| `FASTMCP_CORS_MAX_AGE` | _(none)_ | Preflight cache duration in seconds |

**Development Example:**
```bash
# Allow all (development only!)
FASTMCP_CORS_ALLOW_ORIGINS=*
FASTMCP_CORS_ALLOW_METHODS=*
FASTMCP_CORS_ALLOW_HEADERS=*
```

**Production Example:**
```bash
# Specific origins only
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com
FASTMCP_CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Request-ID
FASTMCP_CORS_ALLOW_CREDENTIALS=true
FASTMCP_CORS_MAX_AGE=3600
```

## Authentication Configuration

### Global Authentication

| Variable | Description |
|----------|-------------|
| `FASTMCP_AUTH_ENABLED` | Enable/disable authentication (`true`/`false`) |
| `FASTMCP_SERVER_AUTH` | Default auth provider (`jwt`, `github`, `google`, etc.) |

### Provider-Specific Configuration

Generic pattern for auth providers:
```
FASTMCP_SERVER_AUTH_<PROVIDER>_<PARAMETER>=value
```

**Examples:**
```bash
# GitHub OAuth
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=your-client-id
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=your-client-secret

# JWT
FASTMCP_SERVER_AUTH_JWT_JWKS_URI=https://auth.example.com/.well-known/jwks.json
FASTMCP_SERVER_AUTH_JWT_ISSUER=https://auth.example.com/
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=mcp-proxy-api
```

### Common Auth Parameters

These variables are checked directly (without FASTMCP_SERVER_AUTH prefix):

| Variable | Description | Used By |
|----------|-------------|---------|
| `CLIENT_ID` | OAuth client ID | Most OAuth providers |
| `CLIENT_SECRET` | OAuth client secret | Most OAuth providers |
| `JWKS_URI` | JSON Web Key Set URI | JWT provider |
| `ISSUER` | Token issuer | JWT, OAuth providers |
| `AUDIENCE` | Token audience | JWT provider |
| `BASE_URL` | Application base URL | OAuth providers (redirect) |

**Example:**
```bash
CLIENT_ID=abc123
CLIENT_SECRET=xyz789
JWKS_URI=https://auth.example.com/.well-known/jwks.json
ISSUER=https://auth.example.com/
AUDIENCE=mcp-proxy-api
BASE_URL=https://proxy.example.com
```

## Rate Limiting Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |
| `FASTMCP_RATE_LIMIT_REQUESTS` | `60` | Maximum requests per window |
| `FASTMCP_RATE_LIMIT_WINDOW_SECONDS` | `60` | Time window in seconds |

**Example:**
```bash
FASTMCP_RATE_LIMIT_ENABLED=true
FASTMCP_RATE_LIMIT_REQUESTS=100
FASTMCP_RATE_LIMIT_WINDOW_SECONDS=60
```

This allows 100 requests per minute per IP address.

## OAuth Storage Configuration

### Token Storage and Encryption

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_OAUTH_STORAGE_TYPE` | `in-memory` | Storage backend: `in-memory`, `disk`, `redis`, `keyring` |
| `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY` | _(none)_ | Fernet encryption key (44 chars) for token encryption |

**Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Example:**
```bash
MCP_OAUTH_STORAGE_TYPE=disk
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=your-44-char-fernet-key-here
```

### Redis Configuration (if using Redis storage)

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis connection URL |
| `REDIS_HOST` | Redis host (if not using URL) |
| `REDIS_PORT` | Redis port (if not using URL) |
| `REDIS_PASSWORD` | Redis password |
| `REDIS_DB` | Redis database number |

**Example:**
```bash
# Using URL
REDIS_URL=redis://:password@localhost:6379/0

# Or individual params
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-password
REDIS_DB=0
```

## Azure OAuth Configuration

For backend services using Azure OAuth:

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Azure AD application client ID |
| `AZURE_CLIENT_SECRET` | Azure AD application client secret |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_TOKEN_URL` | Token endpoint URL |

**Example:**
```bash
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789abc
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=87654321-4321-4321-4321-cba987654321
AZURE_TOKEN_URL=https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/token
```

## Complete Example Files

### Development .env

```bash
# Server
FASTMCP_SERVER_NAME=dev-mcp-proxy
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=DEBUG

# Paths
FASTMCP_CONFIG_DIR=./data
FASTMCP_SCHEMA_DIR=./schemas

# CORS (Allow all for dev)
FASTMCP_CORS_ALLOW_ORIGINS=*
FASTMCP_CORS_ALLOW_METHODS=*
FASTMCP_CORS_ALLOW_HEADERS=*

# Auth (Disabled for dev)
FASTMCP_AUTH_ENABLED=false

# Rate Limiting (Disabled for dev)
FASTMCP_RATE_LIMIT_ENABLED=false
```

### Production .env

```bash
# Server
FASTMCP_SERVER_NAME=production-mcp-proxy
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=WARNING
FASTMCP_SERVER_TRANSPORT=streamable-http

# Paths
FASTMCP_CONFIG_DIR=/etc/mcp-proxy/config
FASTMCP_SCHEMA_DIR=/etc/mcp-proxy/schemas

# CORS (Specific origins)
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com
FASTMCP_CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Request-ID
FASTMCP_CORS_ALLOW_CREDENTIALS=true
FASTMCP_CORS_MAX_AGE=3600

# Authentication (JWT)
FASTMCP_AUTH_ENABLED=true
FASTMCP_SERVER_AUTH=jwt
JWKS_URI=https://auth.example.com/.well-known/jwks.json
ISSUER=https://auth.example.com/
AUDIENCE=mcp-proxy-api

# Rate Limiting
FASTMCP_RATE_LIMIT_ENABLED=true
FASTMCP_RATE_LIMIT_REQUESTS=100
FASTMCP_RATE_LIMIT_WINDOW_SECONDS=60

# OAuth Storage
MCP_OAUTH_STORAGE_TYPE=redis
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=<44-char-fernet-key>
REDIS_URL=redis://:password@redis:6379/0

# Azure OAuth (for backend services)
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_TENANT_ID=<your-tenant-id>
```

### Docker Compose Environment

```yaml
environment:
  - FASTMCP_HOST=0.0.0.0
  - FASTMCP_PORT=9123
  - FASTMCP_LOG_LEVEL=INFO
  - FASTMCP_CONFIG_DIR=/mcp_proxy/data
  - FASTMCP_CORS_ALLOW_ORIGINS=*
  - FASTMCP_AUTH_ENABLED=false
```

## Variable Substitution in Config Files

Environment variables can be used in `config.json` and `auth.json`:

```json
{
  "client_id": "$AZURE_CLIENT_ID",
  "client_secret": "$AZURE_CLIENT_SECRET",
  "tenant_id": "${AZURE_TENANT_ID}",
  "token_url": "https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/token"
}
```

Syntax:
- `$VAR_NAME` - Simple substitution
- `${VAR_NAME}` - Braced substitution (recommended)

## Security Best Practices

### Do's

✅ **Use environment variables for secrets**
```bash
AZURE_CLIENT_SECRET=your-secret  # Good
```

✅ **Use `.env` file for local development** (add to `.gitignore`)

✅ **Use Docker secrets in production**

✅ **Use separate values per environment**

✅ **Rotate secrets regularly**

### Don'ts

❌ **Don't commit secrets to git**
```json
{"client_secret": "actual-secret"}  // Bad
```

❌ **Don't use weak encryption keys**

❌ **Don't share `.env` files**

❌ **Don't log secret values**

❌ **Don't use default values in production**

## Troubleshooting

### Variables Not Loading

```bash
# Check if variable is set
echo $FASTMCP_PORT

# Check Docker container variables
docker exec mcp-proxy env | grep FASTMCP

# Check file is being read
docker exec mcp-proxy cat /mcp_proxy/.env
```

### Substitution Not Working

Variables in JSON files:
- Must use `$VAR` or `${VAR}` syntax
- Variable must be set in environment
- Check logs for substitution errors

### Permission Denied

```bash
# Check file ownership
ls -la .env

# Fix permissions
chmod 600 .env
```

## Related Documentation

- [Configuration Files](config-files.md) - JSON configuration reference
- [Authentication Overview](../features/authentication/overview.md) - Auth configuration details
- [Production Setup](../deployment/production.md) - Production environment setup
- [Docker Deployment](../deployment/docker.md) - Docker-specific configuration
