# Authentication Configuration Quick Start

## Overview

The MCP proxy supports 15 different authentication providers from the fastmcp library. The authentication system is
configured via a single `data/config.yaml` file that defines all available providers and their settings.

## Quick Start: Enable Azure Authentication

### 1. Set Environment Variables

```bash
export AZURE_CLIENT_ID="your-azure-app-id"
export AZURE_CLIENT_SECRET="your-azure-app-secret"
export AZURE_TENANT_ID="your-azure-tenant-id"
export AZURE_TOKEN_URL="https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token"
```

### 2. Update `data/config.yaml`

Change the `azure` provider from disabled to enabled:

```yaml
auth:
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
      token_url: AZURE_TOKEN_URL
    config:
      client_id: $AZURE_CLIENT_ID
      client_secret: $AZURE_CLIENT_SECRET
      tenant_id: $AZURE_TENANT_ID
      token_url: $AZURE_TOKEN_URL
      issuer: null
      scopes:
        - api://$AZURE_CLIENT_ID/.default
```

### 3. Load and Use the Configuration

```python
from src.proxies.auth_config_provider import AuthConfigProvider

# Load the configuration
auth_provider = AuthConfigProvider()
config = auth_provider.load_config()

# Get the Azure provider
azure = auth_provider.get_provider("azure")
if azure:
    print(f"Azure provider loaded: {azure.config}")
```

## Quick Start: Enable GitHub Authentication

### 1. Set Environment Variables

```bash
export GITHUB_CLIENT_ID="your-github-app-id"
export GITHUB_CLIENT_SECRET="your-github-app-secret"
```

### 2. Update `data/config.yaml`

```yaml
auth:
  github:
    enabled: true
    class: "GitHub"
    config:
      client_id: $GITHUB_CLIENT_ID
      client_secret: $GITHUB_CLIENT_SECRET
      scopes:
        - user:email
      redirect_uri: null
```

### 3. Use in Your Application

```python
github = auth_provider.get_provider("github")
if github:
    client_id = github.config['client_id']
    client_secret = github.config['client_secret']
    # Use with FastMCP
```

## Available Providers

All 15 providers are pre-configured in `data/config.yaml`. Here's the complete list:

| Provider      | Status | Purpose                       |
|---------------|--------|-------------------------------|
| azure         | ❌      | Microsoft Entra ID / Azure AD |
| aws           | ❌      | Amazon Web Services (SigV4)   |
| auth0         | ❌      | Auth0 platform                |
| github        | ❌      | GitHub OAuth2                 |
| google        | ❌      | Google OAuth2                 |
| discord       | ❌      | Discord OAuth2                |
| jwt           | ❌      | JSON Web Tokens               |
| descope       | ❌      | Descope authentication        |
| workos        | ❌      | WorkOS enterprise             |
| scalekit      | ❌      | Scalekit enterprise           |
| supabase      | ❌      | Supabase authentication       |
| oci           | ❌      | Oracle Cloud Infrastructure   |
| introspection | ❌      | OAuth token introspection     |
| debug         | ❌      | Development/testing           |
| in_memory     | ❌      | Testing with hardcoded users  |

## Configuration Structure

Each provider in `config.yaml` has this structure:

```yaml
auth:
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
      field1: $ENV_VAR_NAME_1
      field2: $ENV_VAR_NAME_2
      field3: null
```

### Fields Explained

- **enabled** - Set to `true` to activate the provider
- **description** - What the provider does
- **class** - FastMCP class name
- **required_fields** - Must be non-null when enabled
- **optional_fields** - Can be null
- **environment_variables** - Maps config fields to env var names
- **config** - Actual values (use `$VAR_NAME` syntax for env vars)

## Environment Variables

Values in the config are resolved at load time using `$VARIABLE_NAME` syntax:

```yaml
client_id: $AZURE_CLIENT_ID
token_url: https://login.microsoftonline.com/${AZURE_TENANT_ID}/oauth2/v2.0/token
```

Both `$VAR_NAME` and `${VAR_NAME}` work. The system raises an error if a referenced env var is not set when the provider
is enabled.

## Loading Configuration in Python

### Basic Loading

```python
from src.proxies.auth_config_provider import AuthConfigProvider

# Create provider
provider = AuthConfigProvider()

# Load config
config = provider.load_config()

# Get a specific provider
azure = provider.get_provider("azure")
```

### Check Provider Status

```python
# Is it enabled?
if provider.is_provider_enabled("azure"):
    print("Azure is enabled")

# Get all enabled providers
enabled = provider.get_enabled_providers()
for name, config in enabled.items():
    print(f"{name}: {config.class_}")

# List all available
all = provider.list_available_providers()
```

### Get Configuration Values

```python
# Get the config dict
azure_config = provider.get_provider_config("azure")
if azure_config:
    client_id = azure_config['client_id']
    client_secret = azure_config['client_secret']
```

## Common Tasks

### Enable a Provider

Edit `data/config.yaml` and change:

```yaml
enabled: false
```

to:

```yaml
enabled: true
```

### Set Environment Variables

For Azure:

```bash
export AZURE_CLIENT_ID="..."
export AZURE_CLIENT_SECRET="..."
export AZURE_TENANT_ID="..."
export AZURE_TOKEN_URL="https://login.microsoftonline.com/.../oauth2/v2.0/token"
```

Check what env vars you need in the `environment_variables` section of the provider.

### Add Custom Scopes

Edit the `scopes` array in the provider config:

```yaml
auth:
  azure:
    config:
      scopes:
        - api://your-app-id/.default
        - https://management.azure.com/.default
```

### Debug Configuration

Use the test script:

```bash
python test_auth_implementation.py
```

Or load directly:

```python
from src.tools.auth_config import AuthConfig

config = AuthConfig.load_from_file("data/config.yaml")
print(config.to_json(enabled_only=True))
```

## Troubleshooting

### "Environment variable not found"

```
ValueError: Environment variable 'AZURE_CLIENT_ID' referenced in configuration is not set.
```

Set the missing environment variable:

```bash
export AZURE_CLIENT_ID="your-value"
```

### "missing required fields"

```
ValueError: Provider Azure is missing required fields: client_secret
```

Ensure all required fields have non-null values in the config section.

### Provider not found

Make sure the provider name matches exactly (case-sensitive) and check that `enabled: true`.

## Next Steps

1. Choose a provider to enable
2. Set the required environment variables
3. Update `enabled: true` in `config.yaml`
4. Load the configuration and test
5. Integrate with your FastMCP server initialization

## References

- Full guide: [AUTH_CONFIG_GUIDE.md](../docs/AUTH_CONFIG_GUIDE.md)
- Examples: [examples/auth_config_examples.py](../examples/auth_config_examples.py)
- Configuration file: [data/config.yaml](../data/config.yaml)
- FastMCP docs: https://github.com/jlowin/fastmcp

