# Environment Variable Resolution in OAuth Configuration

## Overview

The OAuth/Azure authentication configuration now supports **automatic resolution of environment variables** using the
syntax `$VARIABLE_NAME` or `${VARIABLE_NAME}`.

This allows you to reference sensitive values like client IDs, secrets, and tenant IDs from environment variables
instead of hardcoding them in the configuration file.

## Configuration Example

In your `data/config.json`:

```json
{
  "name": "deepsea",
  "specFile": "openapi/deepsea.openapi.json",
  "specType": "openapi",
  "baseUrl": "http://host.docker.internal:5000",
  "auth": {
    "azure": {
      "baseUrl": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
      "clientId": "$AZURE_CLIENT_ID",
      "clientSecret": "$AZURE_CLIENT_SECRET",
      "tenantId": "$AZURE_TENANT_ID",
      "issuer": "https://login.microsoftonline.com/$AZURE_TENANT_ID/v2.0",
      "scope": [
        "api://$AZURE_CLIENT_ID/.default"
      ]
    }
  }
}
```

## Environment Variables Setup

Set the required environment variables before running the application:

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

Or in a `.env` file (if using python-dotenv):

```env
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
```

## How It Works

1. **Loading**: When the configuration file is loaded, Pydantic parses the JSON
2. **Validation**: The `AzureAuthConfig` model validates the schema
3. **Resolution**: The `@model_validator` in `AzureAuthConfig` automatically resolves all environment variable
   references
4. **Usage**: The resolved values are available immediately as standard Python strings

### Resolution Process

```python
# Input from config.json
"clientId": "$AZURE_CLIENT_ID"

# After resolution (automatic)
auth_config.client_id = "my-actual-client-id"
```

## Supported Formats

### Format 1: Simple Reference

```json
"clientId": "$AZURE_CLIENT_ID"
```

Resolves to the value of the `AZURE_CLIENT_ID` environment variable.

### Format 2: With Braces

```json
"clientId": "${AZURE_CLIENT_ID}"
```

Same as above, alternative syntax with braces.

### Format 3: Within URLs

```json
"baseUrl": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token"
```

Resolves to: `https://login.microsoftonline.com/my-tenant-id/oauth2/v2.0/token`

### Format 4: Multiple References

```json
"scope": ["api://$AZURE_CLIENT_ID/.default"]
```

Supports lists and multiple references in the same value.

## Error Handling

If a referenced environment variable is not set, you'll get a clear error:

```
ValueError: Environment variable 'AZURE_CLIENT_ID' referenced in configuration is not set.
Please set: export AZURE_CLIENT_ID=<value>
```

## Fields That Support Resolution

All fields in the Azure authentication configuration support environment variable resolution:

- `baseUrl`: Token endpoint URL
- `clientId`: OAuth client ID
- `clientSecret`: OAuth client secret
- `tenantId`: Azure tenant ID
- `issuer`: Issuer URL (optional)
- `scope` (or `scopes`): List of OAuth scopes

## Implementation Details

### Files Modified

1. **`src/tools/env_resolver.py`** (new)
    - `resolve_env_var()`: Resolves a single string value
    - `resolve_env_vars_in_dict()`: Recursively resolves dictionaries
    - `resolve_env_vars_in_list()`: Recursively resolves lists
    - `resolve_env_vars()`: Main entry point for any data type

2. **`src/tools/spec_config.py`**
    - Added import of `resolve_env_var`
    - Added `@model_validator` to `AzureAuthConfig` that runs after the model is created

3. **`src/proxies/openapi_mcp_provider.py`**
    - Updated `create_auth()` method documentation to note automatic resolution

### JSON vs Python Naming

- **JSON config**: Uses camelCase (e.g., `"clientId"`, `"tenantId"`)
- **Python code**: Uses snake_case (e.g., `client_id`, `tenant_id`)
- Environment variable resolution works with the resolved snake_case names

## Security Best Practices

1. **Never commit secrets**: Use environment variables, not hardcoded values
2. **Use .env files**: In development, use `.env` files (don't commit them)
3. **Use secret management**: In production, use proper secret management tools
4. **Encrypt at rest**: The OAuth tokens are encrypted using Fernet encryption

Example `.env` file (add to `.gitignore`):

```env
AZURE_CLIENT_ID=your-secret-id
AZURE_CLIENT_SECRET=your-secret-key
AZURE_TENANT_ID=your-tenant-id
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=your-encryption-key
```

## Testing

You can test the resolution with:

```python
import os

os.environ['AZURE_CLIENT_ID'] = 'test-id'

from src.tools.spec_config import SpecConfig

config_data = {
    "name": "test",
    "specFile": "test.json",
    "specType": "openapi",
    "baseUrl": "http://localhost",
    "auth": {
        "azure": {
            "baseUrl": "https://login.microsoftonline.com/$AZURE_TENANT_ID/token",
            "clientId": "$AZURE_CLIENT_ID",
            "clientSecret": "$AZURE_CLIENT_SECRET",
            "tenantId": "$AZURE_TENANT_ID",
            "scope": ["api://$AZURE_CLIENT_ID/.default"]
        }
    }
}

spec = SpecConfig(**config_data)
print(spec.auth.azure.client_id)  # Outputs: test-id
```

## Troubleshooting

### Error: Environment variable not set

**Solution**: Check that you've set the environment variable before running the application

```bash
export VARIABLE_NAME=value
# or in .env file
VARIABLE_NAME=value
```

### Error: Token endpoint returns 401/403

**Solution**: Verify that the resolved credentials are correct by printing them

```python
print(spec.auth.azure.client_id)  # Make sure this matches your Azure app registration
```

### Empty baseUrl

If `baseUrl` is empty in the config, it means the URL generation is incomplete. For Azure:

```json
"baseUrl": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token"
```

## Related Configuration

Also ensure you set:

```bash
export FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY="your-encryption-key"
```

Generate a key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

