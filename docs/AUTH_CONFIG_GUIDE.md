# Authentication Configuration Implementation

## Overview

This document describes the authentication configuration system implemented for the MCP proxy server. The system
provides a centralized, validated approach to managing authentication providers from the fastmcp library.

## Architecture

### Components

1. **`src/tools/auth_config.py`** - Core authentication configuration models
    - `AuthProviderType` - Enumeration of supported auth providers
    - `AuthProviderConfig` - Individual provider configuration model
    - `AuthConfig` - Root configuration model that contains all providers

2. **`src/proxies/auth_config_provider.py`** - Configuration provider and loader
    - `AuthConfigProvider` - Loads and manages authentication configurations

3. **`data/config.yaml`** - Configuration file with all available providers

## Features

### Supported Authentication Providers

The implementation supports all 15 FastMCP authentication providers:

| Provider                | Type      | Use Case                                    |
|-------------------------|-----------|---------------------------------------------|
| **Azure**               | OAuth 2.0 | Microsoft Entra ID / Azure Active Directory |
| **AWS**                 | SigV4     | Amazon Web Services                         |
| **Auth0**               | OAuth 2.0 | Auth0 identity platform                     |
| **GitHub**              | OAuth 2.0 | GitHub OAuth authentication                 |
| **Google**              | OAuth 2.0 | Google OAuth 2.0                            |
| **Discord**             | OAuth 2.0 | Discord bot/user authentication             |
| **JWT**                 | JWT       | JSON Web Tokens                             |
| **Descope**             | OAuth 2.0 | Descope authentication                      |
| **WorkOS**              | OAuth 2.0 | WorkOS enterprise authentication            |
| **Scalekit**            | OAuth 2.0 | Scalekit enterprise                         |
| **Supabase**            | OAuth 2.0 | Supabase authentication                     |
| **OCI**                 | Key-based | Oracle Cloud Infrastructure                 |
| **Token Introspection** | OAuth 2.0 | Generic OAuth introspection                 |
| **Debug**               | None      | Development/testing (no-op)                 |
| **In-Memory**           | Password  | Testing with hardcoded users                |

### Environment Variable Resolution

The system automatically resolves environment variable references in configuration values using the `$VAR_NAME` or
`${VAR_NAME}` syntax.

**Example:**

```yaml
auth:
  config:
    client_id: "$AZURE_CLIENT_ID"
    client_secret: "$AZURE_CLIENT_SECRET"
    tenant_id: "${AZURE_TENANT_ID}"
```

When a provider is enabled, these variables are resolved by looking up the corresponding environment variables.

### Validation

The system performs multi-level validation:

1. **Schema Validation** - Validates JSON structure against Pydantic models
2. **Required Fields Validation** - Ensures all required fields are present for enabled providers
3. **Environment Variable Resolution** - Fails fast if referenced environment variables don't exist (only for enabled
   providers)
4. **Field Type Validation** - Ensures fields have correct types (string, list, dict, etc.)

## Configuration File Structure

### Example `config.yaml`

```yaml
auth:
  version: "1.0"
  description: "MCP Authentication Providers Configuration"
  providers:
    azure:
      enabled: true
      description: "Azure/Microsoft Entra ID authentication provider"
      class: "Azure"
      required_fields:
        - client_id
        - client_secret
        - tenant_id
        - token_url
      optional_fields:
        - issuer
        - scopes
      environment_variables:
        client_id: AZURE_CLIENT_ID
        client_secret: AZURE_CLIENT_SECRET
        tenant_id: AZURE_TENANT_ID
      config:
        client_id: "$AZURE_CLIENT_ID"
        client_secret: "$AZURE_CLIENT_SECRET"
        tenant_id: "$AZURE_TENANT_ID"
        token_url: "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token"
        issuer: null
        scopes:
          - "api://$AZURE_CLIENT_ID/.default"
    github:
      enabled: false
      description: "GitHub OAuth2 authentication provider"
      class: "GitHub"
      required_fields:
        - client_id
        - client_secret
      optional_fields:
        - scopes
        - redirect_uri
      environment_variables:
        client_id: GITHUB_CLIENT_ID
        client_secret: GITHUB_CLIENT_SECRET
      config:
        client_id: "$GITHUB_CLIENT_ID"
        client_secret: "$GITHUB_CLIENT_SECRET"
        scopes:
          - "user:email"
        redirect_uri: null
```

### Field Descriptions

- **enabled** - Boolean indicating if this provider should be loaded and validated
- **description** - Human-readable description of the provider
- **class** - FastMCP class name for this provider
- **required_fields** - List of fields that must be present when enabled=true
- **optional_fields** - List of fields that are optional
- **environment_variables** - Mapping of field names to environment variable names (for reference)
- **config** - Actual configuration values (may reference environment variables)

## Usage Examples

### Basic Usage

```python
from src.proxies.auth_config_provider import AuthConfigProvider

# Initialize the provider
auth_provider = AuthConfigProvider()

# Load the configuration
config = auth_provider.load_config()

# Get all enabled providers
enabled = auth_provider.get_enabled_providers()
for name, provider in enabled.items():
    print(f"Provider: {name}, Class: {provider.class_}")

# Get a specific provider
github_config = auth_provider.get_provider("github")
if github_config:
    print(f"GitHub config: {github_config.config}")
```

### Loading Configuration File

```python
from src.tools.auth_config import AuthConfig

# Load from file
config = AuthConfig.load_from_file("data/config.yaml")

# Access providers
for name, provider in config.providers.items():
    if provider.enabled:
        print(f"Enabled: {name}")
```

### Checking Provider Status

```python
# Check if a provider is enabled
is_enabled = auth_provider.is_provider_enabled("azure")

# Get provider configuration
provider_config = auth_provider.get_provider_config("azure")
if provider_config:
    print(f"Azure client_id: {provider_config['client_id']}")

# List all available providers
all_providers = auth_provider.list_available_providers()
```

## Adding a New Provider

To add a new authentication provider:

1. Add an entry to the `providers` object in `data/config.yaml`:

```yaml
auth:
  providers:
    provider_name:
      enabled: false
      description: "Description of the provider"
      class: "ProviderClassName"
      required_fields:
        - field1
        - field2
      optional_fields:
        - field3
      environment_variables:
        field1: ENV_VAR_NAME_1
        field2: ENV_VAR_NAME_2
      config:
        field1: "$ENV_VAR_NAME_1"
        field2: "$ENV_VAR_NAME_2"
        field3: null
```

2. Set `enabled: true` to activate the provider
3. Ensure required environment variables are set
4. The AuthConfig will validate the configuration on load

## Environment Variables

When a provider is enabled, the configuration system looks for environment variables matching the names in the
`environment_variables` section.

**Example setup for Azure provider:**

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_TOKEN_URL="https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token"
```

## Error Handling

The system provides detailed error messages for configuration issues:

### File Not Found

```
FileNotFoundError: Authentication configuration file not found: /path/to/config.yaml
```

### Invalid YAML

```
yaml.YAMLError: Expecting value: line 1 column 1
```

### Missing Required Fields

```
ValueError: Provider Azure is missing required fields: client_id, client_secret
```

### Missing Environment Variables

```
ValueError: Environment variable 'AZURE_CLIENT_ID' referenced in configuration is not set.
```

## Testing

The implementation includes comprehensive tests in `tests/test_auth_config.py`:

```bash
# Run all auth config tests
python -m pytest tests/test_auth_config.py -v

# Run specific test
python -m pytest tests/test_auth_config.py::TestAuthConfig::test_get_enabled_providers -v
```

## Integration with FastMCP

The loaded authentication configurations can be passed to FastMCP's authentication system:

```python
from fastmcp.server import create_proxy
from src.proxies.auth_config_provider import AuthConfigProvider

# Load auth configuration
auth_provider = AuthConfigProvider()
enabled_providers = auth_provider.get_enabled_providers()

# Use with FastMCP
if "azure" in enabled_providers:
    azure_config = auth_provider.get_provider_config("azure")
    # Pass to FastMCP's auth setup
    # proxy = create_proxy(..., auth=azure_config)
```

## Similar to spec_config.py

The authentication configuration system mirrors the design of `spec_config.py`:

| Aspect          | spec_config.py      | auth_config.py     |
|-----------------|---------------------|--------------------|
| **Root file**   | config.yaml         | config.yaml        |
| **Root model**  | SpecConfig (list)   | AuthConfig (dict)  |
| **Entry model** | SpecConfig          | AuthProviderConfig |
| **Provider**    | ProxyConfigProvider | AuthConfigProvider |
| **Validation**  | Schema + custom     | Schema + custom    |
| **Env vars**    | resolve_env_var()   | resolve_env_var()  |
| **Caching**     | Yes                 | Yes                |

## Next Steps

1. **Enable providers** - Set `enabled: true` for providers you want to use
2. **Configure environment** - Set required environment variables
3. **Test loading** - Use `AuthConfigProvider` to load and validate
4. **Integrate with server** - Pass configurations to FastMCP initialization

