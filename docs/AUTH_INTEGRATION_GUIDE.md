# Integration Guide - Using AuthConfig with FastMCP

This guide explains how to integrate the authentication configuration system with your FastMCP server.

## Overview

The `AuthConfigProvider` loads and validates authentication configurations, which can then be passed to FastMCP's
authentication system during server initialization.

## Basic Integration Pattern

### 1. Import Required Modules

```python
from fastmcp import FastMCP
from src.proxies.auth_config_provider import AuthConfigProvider
```

### 2. Load Authentication Configuration

```python
# Initialize the provider
auth_provider = AuthConfigProvider()

# Load configuration (reads from data/auth.json)
try:
    config = auth_provider.load_config()
except Exception as e:
    print(f"Failed to load authentication configuration: {e}")
    # Handle error appropriately
    raise
```

### 3. Get Enabled Providers

```python
# Get all enabled providers
enabled_providers = auth_provider.get_enabled_providers()

print(f"Found {len(enabled_providers)} enabled authentication providers:")
for name, provider_config in enabled_providers.items():
    print(f"  - {name}: {provider_config.class_}")
```

### 4. Configure FastMCP with Authentication

```python
# Create FastMCP instance
mcp = FastMCP(name="my-mcp-server")

# Configure authentication based on enabled providers
if "azure" in enabled_providers:
    azure_config = auth_provider.get_provider_config("azure")
    # Use azure_config with FastMCP's Azure auth provider
    # mcp.auth = FastMCP.Auth.Azure(config=azure_config)

if "github" in enabled_providers:
    github_config = auth_provider.get_provider_config("github")
    # Use github_config with FastMCP's GitHub auth provider
    # mcp.auth = FastMCP.Auth.GitHub(config=github_config)

# Add servers, resources, tools, etc.
```

## Complete Example - MCP Server with Authentication

```python
"""
Example FastMCP server with authentication configuration.
"""

from fastmcp import FastMCP
from src.proxies.auth_config_provider import AuthConfigProvider
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Initialize auth provider
auth_provider = AuthConfigProvider()


def setup_authentication(mcp: FastMCP) -> None:
    """
    Configure FastMCP authentication based on auth.json settings.
    
    Args:
        mcp: FastMCP instance to configure
        
    Raises:
        ValueError: If authentication configuration is invalid
    """
    try:
        # Load authentication configuration
        config = auth_provider.load_config()

        # Get enabled providers
        enabled = auth_provider.get_enabled_providers()

        if not enabled:
            logger.warning("No authentication providers are enabled")
            return

        logger.info(f"Setting up {len(enabled)} authentication provider(s)")

        # Configure each enabled provider
        for name, provider_config in enabled.items():
            logger.info(f"Configuring {name} authentication ({provider_config.class_})")

            # Get the configuration dictionary
            config_dict = provider_config.config

            # Example: Handle specific providers
            if name == "azure":
                # Configure Azure auth
                setup_azure_auth(mcp, config_dict)
            elif name == "github":
                # Configure GitHub auth
                setup_github_auth(mcp, config_dict)
            elif name == "jwt":
                # Configure JWT auth
                setup_jwt_auth(mcp, config_dict)
            # Add more provider-specific setup as needed

    except Exception as e:
        logger.error(f"Failed to setup authentication: {e}")
        raise


def setup_azure_auth(mcp: FastMCP, config: dict) -> None:
    """Setup Azure authentication."""
    logger.debug(f"Azure auth config: client_id={config.get('client_id')}")
    # Implement Azure auth setup
    # from fastmcp.server.auth.providers import Azure
    # mcp.auth = Azure(**config)


def setup_github_auth(mcp: FastMCP, config: dict) -> None:
    """Setup GitHub authentication."""
    logger.debug(f"GitHub auth config: scopes={config.get('scopes')}")
    # Implement GitHub auth setup
    # from fastmcp.server.auth.providers import GitHub
    # mcp.auth = GitHub(**config)


def setup_jwt_auth(mcp: FastMCP, config: dict) -> None:
    """Setup JWT authentication."""
    logger.debug(f"JWT auth config: algorithm={config.get('algorithm')}")
    # Implement JWT auth setup
    # from fastmcp.server.auth.providers import JWT
    # mcp.auth = JWT(**config)


# Create MCP server
mcp = FastMCP(name="authenticated-mcp-server")

# Setup authentication
try:
    setup_authentication(mcp)
except Exception as e:
    logger.error(f"Authentication setup failed: {e}")
    # Decide whether to continue without auth or fail


# Add your MCP resources, tools, etc.
@mcp.resource("greeting://name")
def get_greeting(name: str) -> str:
    """Get a greeting."""
    return f"Hello, {name}!"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    # Run the server
    mcp.run()
```

## Provider-Specific Integration Examples

### Azure Authentication

```python
from src.proxies.auth_config_provider import AuthConfigProvider
from fastmcp.server.auth.providers import Azure

auth_provider = AuthConfigProvider()
azure_config = auth_provider.get_provider_config("azure")

if azure_config:
    # Create Azure auth provider
    auth = Azure(
        client_id=azure_config["client_id"],
        client_secret=azure_config["client_secret"],
        tenant_id=azure_config["tenant_id"],
        token_url=azure_config["token_url"],
        issuer=azure_config.get("issuer"),
        scopes=azure_config.get("scopes", [])
    )
    # Attach to FastMCP
    # mcp.auth = auth
```

### GitHub Authentication

```python
from src.proxies.auth_config_provider import AuthConfigProvider
from fastmcp.server.auth.providers import GitHub

auth_provider = AuthConfigProvider()
github_config = auth_provider.get_provider_config("github")

if github_config:
    auth = GitHub(
        client_id=github_config["client_id"],
        client_secret=github_config["client_secret"],
        scopes=github_config.get("scopes", []),
        redirect_uri=github_config.get("redirect_uri")
    )
    # mcp.auth = auth
```

### JWT Authentication

```python
from src.proxies.auth_config_provider import AuthConfigProvider
from fastmcp.server.auth.providers import JWT

auth_provider = AuthConfigProvider()
jwt_config = auth_provider.get_provider_config("jwt")

if jwt_config:
    auth = JWT(
        secret_key=jwt_config["secret_key"],
        algorithm=jwt_config.get("algorithm", "HS256"),
        issuer=jwt_config.get("issuer"),
        audience=jwt_config.get("audience")
    )
    # mcp.auth = auth
```

## Middleware Integration

If your FastMCP server uses Starlette for HTTP handling, you can integrate authentication into middleware:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from src.proxies.auth_config_provider import AuthConfigProvider


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.auth_provider = AuthConfigProvider()
        self.enabled_providers = self.auth_provider.get_enabled_providers()

    async def dispatch(self, request, call_next):
        # Check authorization header
        auth_header = request.headers.get("Authorization", "")

        # Validate based on enabled providers
        if not self.validate_auth(auth_header):
            return JSONResponse(
                {"error": "Unauthorized"},
                status_code=401
            )

        return await call_next(request)

    def validate_auth(self, auth_header: str) -> bool:
        # Implement authentication validation
        # using enabled provider configurations
        return bool(auth_header)
```

## Configuration Checking

Before starting your server, verify authentication setup:

```python
def check_auth_configuration() -> bool:
    """
    Check if authentication is properly configured.
    
    Returns:
        True if all enabled providers are valid, False otherwise
    """
    auth_provider = AuthConfigProvider()

    try:
        config = auth_provider.load_config()
    except Exception as e:
        logger.error(f"Failed to load auth configuration: {e}")
        return False

    enabled = auth_provider.get_enabled_providers()

    if not enabled:
        logger.warning("No authentication providers enabled")
        return True  # OK - optional auth

    # Validate enabled providers
    try:
        config.validate_enabled_providers()
        logger.info(f"Authentication configuration valid - {len(enabled)} provider(s) enabled")
        return True
    except ValueError as e:
        logger.error(f"Authentication validation failed: {e}")
        return False


# Use in your startup code
if not check_auth_configuration():
    # Handle configuration error
    pass
```

## Environment Setup

Before running your server, ensure environment variables are set:

```bash
#!/bin/bash

# For Azure authentication
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_TOKEN_URL="https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token"

# For GitHub authentication
export GITHUB_CLIENT_ID="your-client-id"
export GITHUB_CLIENT_SECRET="your-client-secret"

# For JWT authentication
export JWT_SECRET_KEY="your-secret-key"
export JWT_ALGORITHM="HS256"

# Run your server
python src/main.py
```

## Error Handling

Implement proper error handling:

```python
def setup_server_with_auth():
    """Setup FastMCP server with error handling."""
    try:
        # Initialize
        mcp = FastMCP(name="my-server")
        auth_provider = AuthConfigProvider()

        # Load configuration
        try:
            config = auth_provider.load_config()
        except FileNotFoundError:
            logger.warning("auth.json not found - running without authentication")
            return mcp
        except ValueError as e:
            logger.error(f"Invalid authentication configuration: {e}")
            raise

        # Setup authentication
        enabled = auth_provider.get_enabled_providers()
        for name, provider_config in enabled.items():
            try:
                # Setup provider
                logger.info(f"Setting up {name} authentication")
            except Exception as e:
                logger.error(f"Failed to setup {name}: {e}")
                # Decide: fail hard or continue with other providers
                raise

        return mcp

    except Exception as e:
        logger.critical(f"Server setup failed: {e}")
        raise
```

## Testing Authentication Setup

```python
import unittest
from unittest.mock import patch
from src.proxies.auth_config_provider import AuthConfigProvider


class TestAuthenticationSetup(unittest.TestCase):

    def test_azure_auth_enabled(self):
        """Test Azure authentication setup."""
        with patch.dict('os.environ', {
            'AZURE_CLIENT_ID': 'test-id',
            'AZURE_CLIENT_SECRET': 'test-secret',
            'AZURE_TENANT_ID': 'test-tenant',
            'AZURE_TOKEN_URL': 'https://test'
        }):
            provider = AuthConfigProvider()
            config = provider.load_config()
            # Enable Azure in auth.json for testing
            azure = provider.get_provider("azure")
            self.assertIsNotNone(azure)

    def test_github_auth_enabled(self):
        """Test GitHub authentication setup."""
        with patch.dict('os.environ', {
            'GITHUB_CLIENT_ID': 'test-id',
            'GITHUB_CLIENT_SECRET': 'test-secret'
        }):
            provider = AuthConfigProvider()
            config = provider.load_config()
            github = provider.get_provider("github")
            self.assertIsNotNone(github)
```

## Summary

To integrate authentication with FastMCP:

1. **Load configuration** - Use `AuthConfigProvider.load_config()`
2. **Check enabled providers** - Use `get_enabled_providers()`
3. **Get provider configs** - Use `get_provider_config(name)`
4. **Configure FastMCP** - Pass configs to FastMCP auth providers
5. **Handle errors** - Implement proper exception handling
6. **Set environment variables** - Ensure all required vars are set
7. **Test** - Verify authentication setup before deployment

See `examples/auth_config_examples.py` for more code samples.

