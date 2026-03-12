# Authentication Configuration Implementation Guide

## Overview

This document describes the authentication configuration implementation for the drunk-mcp-proxy project. The
implementation provides a simplified, flat-file approach to managing authentication providers without complex metadata
or wrapper structures.

## Architecture

### 1. Configuration File (config.yaml)

**Structure:** YAML configuration with auth section containing provider configurations

```yaml
auth:
  provider_name:
    field1: value1 or $ENV_VAR
    field2: value2 or ${ENV_VAR}
```

**Features:**

- Each provider is a key under the `auth:` section
- Configuration values support environment variable resolution using `$VAR_NAME` or `${VAR_NAME}` syntax
- All providers are optional - if not in the config, they're not used
- No metadata fields like `enabled`, `required_fields`, `optional_fields`, etc.

**Example:**

```yaml
auth:
  azure:
    client_id: $AZURE_CLIENT_ID
    client_secret: $AZURE_CLIENT_SECRET
    tenant_id: $AZURE_TENANT_ID
    scopes: []
  github:
    client_id: $GITHUB_CLIENT_ID
    client_secret: $GITHUB_CLIENT_SECRET
    scopes:
      - user:email
```

### 2. AuthConfig Class (src/tools/auth_config.py)

**Purpose:** Load and manage authentication configuration

**Key Features:**

- Flat structure with dynamic fields (any provider name allowed)
- Uses Pydantic's `extra="allow"` for dynamic fields
- Automatic environment variable resolution on load
- No validation of required/optional fields (done at provider level if needed)

**Key Methods:**

```python
# Load from file
config = AuthConfig.load_from_file("config.yaml")

# Check if provider is configured
if config.is_provider_configured("azure"):
    azure = config.get_provider("azure")
    client_id = azure["client_id"]

# List all configured providers
providers = config.list_configured_providers()  # ["azure", "github", ...]

# Convert to dict/JSON
config_dict = config.to_dict()
config_json = config.to_json(indent=2)
```

### 3. AuthConfigProvider Class (src/proxies/auth_config_provider.py)

**Purpose:** Centralized provider for loading and accessing auth configuration

**Key Features:**

- Lazy loading with caching
- Mirrors the pattern of ProxyConfigProvider
- Handles file loading and error handling
- Logging of configuration loading process

**Key Methods:**

```python
provider = AuthConfigProvider()

# Load configuration
config = provider.load_config()

# Get configured providers
azure = provider.get_provider("azure")
is_configured = provider.is_provider_configured("azure")
configured_list = provider.list_configured_providers()
all_providers = provider.get_all_providers()

# Get configuration
if azure:
    client_id = azure["client_id"]
```

### 4. AuthProviderType Enum (src/tools/auth_config.py)

**Purpose:** Define all supported authentication provider types

**Supported Providers:**

- auth0
- aws
- azure
- debug
- descope
- discord
- github
- google
- in_memory
- introspection
- jwt
- oci
- scalekit
- supabase
- workos

## Provider Configuration Reference

### Auth0

```yaml
auth:
  auth0:
    domain: https://your-tenant.auth0.com
    client_id: $AUTH0_CLIENT_ID
    client_secret: $AUTH0_CLIENT_SECRET
    audience: your-api-identifier
    scopes:
      - openid
      - profile
      - email
    grant_type: client_credentials
```

### Azure (Microsoft Entra)

```yaml
auth:
  azure:
    client_id: $AZURE_CLIENT_ID
    client_secret: $AZURE_CLIENT_SECRET
    tenant_id: $AZURE_TENANT_ID
    token_url: null
    issuer: null
    scopes:
      - api://your-app-id/read
```

### AWS Cognito

```yaml
auth:
  aws:
    access_key_id: $AWS_ACCESS_KEY_ID
    secret_access_key: $AWS_SECRET_ACCESS_KEY
    region: $AWS_REGION
    session_token: null
    role_arn: null
```

### GitHub

```yaml
auth:
  github:
    client_id: $GITHUB_CLIENT_ID
    client_secret: $GITHUB_CLIENT_SECRET
    scopes:
      - user:email
    redirect_uri: http://localhost:9123/auth/callback
```

### Google

```yaml
auth:
  google:
    client_id: $GOOGLE_CLIENT_ID
    client_secret: $GOOGLE_CLIENT_SECRET
    project_id: $GOOGLE_PROJECT_ID
    scopes:
      - openid
      - email
      - profile
    redirect_uri: null
```

### Discord

```yaml
auth:
  discord:
    client_id: $DISCORD_CLIENT_ID
    client_secret: $DISCORD_CLIENT_SECRET
    bot_token: $DISCORD_BOT_TOKEN
    scopes:
      - identify
      - email
    redirect_uri: null
```

### JWT

```yaml
auth:
  jwt:
    secret_key: $JWT_SECRET_KEY
    algorithm: HS256
    issuer: null
    audience: null
```

### Introspection (OAuth 2.0 Token Introspection)

```yaml
auth:
  introspection:
    introspection_url: $TOKEN_INTROSPECTION_URL
    client_id: $TOKEN_INTROSPECTION_CLIENT_ID
    client_secret: $TOKEN_INTROSPECTION_CLIENT_SECRET
```

### Descope

```yaml
auth:
  descope:
    project_id: $DESCOPE_PROJECT_ID
    public_key: $DESCOPE_PUBLIC_KEY
    scopes: []
```

### Scalekit

```yaml
auth:
  scalekit:
    client_id: $SCALEKIT_CLIENT_ID
    client_secret: $SCALEKIT_CLIENT_SECRET
    environment_url: $SCALEKIT_ENVIRONMENT_URL
    scopes: []
```

### Supabase

```yaml
auth:
  supabase:
    project_url: $SUPABASE_PROJECT_URL
    api_key: $SUPABASE_API_KEY
    scopes: []
```

### OCI (Oracle Cloud Identity)

```yaml
auth:
  oci:
    user_ocid: $OCI_USER_OCID
    tenancy_ocid: $OCI_TENANCY_OCID
    api_key: $OCI_API_KEY
    fingerprint: $OCI_FINGERPRINT
    region: us-phoenix-1
```

### WorkOS

```yaml
auth:
  workos:
    api_key: $WORKOS_API_KEY
    client_id: $WORKOS_CLIENT_ID
    organization_id: null
    scopes: []
```

### Debug

```yaml
auth:
  debug:
    user_id: debug-user
    username: debug
```

### In-Memory

```yaml
auth:
  in_memory:
    users:
      user1: password1
      user2: password2
```

## Environment Variable Resolution

Configuration values can reference environment variables using two syntaxes:

1. **Simple format:** `$VAR_NAME`
2. **Braced format:** `${VAR_NAME}`

**Example in config.yaml:**

```yaml
auth:
  azure:
    client_id: $AZURE_CLIENT_ID
    client_secret: ${AZURE_CLIENT_SECRET}
    issuer: https://login.microsoftonline.com/${TENANT_ID}/v2.0
```

**Environment Setup:**

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export TENANT_ID="your-tenant-id"
```

The environment variables are resolved automatically when loading the configuration:

```python
config = AuthConfig.load_from_file("config.yaml")
azure = config.get_provider("azure")
print(azure["client_id"])  # Prints actual value, not "$AZURE_CLIENT_ID"
```

**Error Handling:** If a referenced environment variable is not set, a `ValueError` is raised with a clear message
indicating which variable is missing.

## Usage Examples

### Basic Loading

```python
from proxies.auth_config_provider import AuthConfigProvider

# Create provider
auth_provider = AuthConfigProvider()

# Load configuration
config = auth_provider.load_config()

# Check if Azure is configured
if auth_provider.is_provider_configured("azure"):
    azure_config = auth_provider.get_provider("azure")
    # Use azure_config with FastMCP
    # mcp = FastMCP("My App", auth=AzureProvider(**azure_config))
```

### Iterating Over Providers

```python
configured_providers = auth_provider.list_configured_providers()

for provider_name in configured_providers:
    provider_config = auth_provider.get_provider(provider_name)
    print(f"Provider: {provider_name}")
    print(f"  Config keys: {list(provider_config.keys())}")
```

### Accessing Specific Provider

```python
github = auth_provider.get_provider("github")

if github:
    print(f"GitHub Client ID: {github['client_id']}")
    print(f"GitHub Scopes: {github['scopes']}")
else:
    print("GitHub is not configured")
```

### Getting All Providers

```python
all_providers = auth_provider.get_all_providers()

for provider_name, provider_config in all_providers.items():
    print(f"{provider_name}: {type(provider_config).__name__}")
```

## Key Design Decisions

### 1. Flat Structure

- **Why:** Simpler than nested `providers: {}` wrapper
- **Benefit:** Direct provider name to config mapping
- **Tradeoff:** Less metadata space, but validation is done in provider classes

### 2. Optional Providers

- **Why:** Applications may not use all providers
- **Benefit:** Only configured providers are loaded and validated
- **Tradeoff:** Must check `is_provider_configured()` before accessing

### 3. Environment Variable Resolution at Load Time

- **Why:** Simplifies provider usage code
- **Benefit:** Resolved values are immediately available
- **Tradeoff:** All env vars must be set before loading config

### 4. No Validation Metadata in Config

- **Why:** Each provider has different validation needs
- **Benefit:** Config file is lean and focused on actual configuration
- **Tradeoff:** Validation is done in provider classes or at usage time

## Migration from Old Format

If you had the old format with `enabled`, `required_fields`, etc.:

**Old Format:**

```json
{
  "providers": {
    "azure": {
      "enabled": true,
      "required_fields": [
        "client_id",
        "client_secret"
      ],
      "config": {
        "client_id": "$AZURE_CLIENT_ID"
      }
    }
  }
}
```

**New Format:**

```yaml
auth:
  azure:
    client_id: $AZURE_CLIENT_ID
```

1. Remove `providers` wrapper
2. Remove `enabled` flag (presence = configured)
3. Remove `required_fields` / `optional_fields` (done at provider level)
4. Remove `config` wrapper
5. Move all fields to root level of provider object

## Error Handling

### FileNotFoundError

Raised when `config.yaml` doesn't exist.

```python
try:
    config = AuthConfig.load_from_file("config.yaml")
except FileNotFoundError:
    print("Auth config file not found")
```

### ValueError

Raised when environment variables referenced in config are not set.

```python
try:
    config = AuthConfig.load_from_file("config.yaml")
except ValueError as e:
    print(f"Failed to resolve env vars: {e}")
    # Error message will indicate which variable is missing
```

### YAML Parse Error

Raised when config.yaml contains invalid YAML.

```python
try:
    config = AuthConfig.load_from_file("config.yaml")
except yaml.YAMLError:
    print("Auth config file contains invalid YAML")
```

## Testing

### Unit Tests

See `tests/test_auth_config.py` for comprehensive test coverage.

### Manual Testing

```python
# Test 1: Load and list providers
from proxies.auth_config_provider import AuthConfigProvider

provider = AuthConfigProvider()
print(provider.list_configured_providers())

# Test 2: Get specific provider
azure = provider.get_provider("azure")
print(azure)

# Test 3: Check if configured
print(provider.is_provider_configured("github"))
```

## Files Involved

- `config.yaml` - Configuration file with all providers (under `auth:` section)
- `src/tools/auth_config.py` - AuthConfig and AuthProviderType
- `src/proxies/auth_config_provider.py` - AuthConfigProvider
- `src/tools/env_resolver.py` - Environment variable resolution
- `tests/test_auth_config.py` - Unit tests

## Related Documentation

- [FastMCP Authentication](https://github.com/jlowin/fastmcp) - Upstream auth provider documentation
- [Environment Variable Guide](docs/guides/environment-variables.md) - How to set environment variables
- [Security Best Practices](docs/guides/security.md) - Securing authentication credentials

## Troubleshooting

### Issue: "Environment variable X not set"

**Solution:** Set the missing environment variable before loading the config.

```bash
export MISSING_VAR="value"
```

### Issue: Provider not found when getting config

**Solution:** Use `is_provider_configured()` to check first.

```python
if provider.is_provider_configured("azure"):
    azure = provider.get_provider("azure")
```

### Issue: None values in provider config

**Solution:** This is normal - optional fields may be omitted or set to `null` in config.yaml. Check for None in your code.

```python
redirect_uri = azure.get("redirect_uri")  # May be None
```

## Support

For issues or questions about authentication configuration, please refer to:

1. This documentation
2. Inline code comments in auth_config.py and auth_config_provider.py
3. Test files for usage examples
4. FastMCP upstream documentation for provider-specific details

