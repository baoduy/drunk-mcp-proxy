#!/usr/bin/env python3
"""
Test script to verify environment variable resolution in OAuth configuration.

This script tests that environment variables in the auth configuration
are properly resolved when loading the SpecConfig.
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment variables
os.environ['AZURE_CLIENT_ID'] = 'test-client-id-12345'
os.environ['AZURE_CLIENT_SECRET'] = 'test-secret-key-67890'
os.environ['AZURE_TENANT_ID'] = 'test-tenant-id-abc123'


def test_env_resolver():
    """Test the basic environment variable resolver."""
    from src.tools.env_resolver import resolve_env_var

    print("=" * 60)
    print("Test 1: Basic Environment Variable Resolver")
    print("=" * 60)

    # Test 1a: Simple variable reference
    result = resolve_env_var("$AZURE_CLIENT_ID")
    assert result == "test-client-id-12345", f"Expected 'test-client-id-12345', got '{result}'"
    print("✓ Simple variable reference: $AZURE_CLIENT_ID")

    # Test 1b: Variable with braces
    result = resolve_env_var("${AZURE_TENANT_ID}")
    assert result == "test-tenant-id-abc123", f"Expected 'test-tenant-id-abc123', got '{result}'"
    print("✓ Variable with braces: ${AZURE_TENANT_ID}")

    # Test 1c: Variable in URL
    result = resolve_env_var("https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token")
    expected = "https://login.microsoftonline.com/test-tenant-id-abc123/oauth2/v2.0/token"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ Variable in URL: https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token")

    # Test 1d: Multiple variables
    result = resolve_env_var("api://$AZURE_CLIENT_ID/.default")
    expected = "api://test-client-id-12345/.default"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ Multiple variable references: api://$AZURE_CLIENT_ID/.default")

    print()


def test_spec_config():
    """Test SpecConfig with environment variable resolution."""
    from src.tools.spec_config import SpecConfig

    print("=" * 60)
    print("Test 2: SpecConfig with Environment Variables")
    print("=" * 60)

    # Create test configuration with environment variable references
    config_data = {
        "name": "deepsea",
        "namespace": None,
        "specFile": "openapi/deepsea.openapi.json",
        "specType": "openapi",
        "baseUrl": "http://host.docker.internal:5000",
        "filters": {
            "methods": ["GET", "POST", "PUT"],
            "tags": ["CurrencyPairs"]
        },
        "auth": {
            "azure": {
                "tokenUrl": "https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token",
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

    # Load and validate the configuration
    spec = SpecConfig(**config_data)

    print(f"Config name: {spec.name}")
    print(f"Spec type: {spec.spec_type}")
    print(f"Base URL: {spec.base_url}")
    print()

    # Verify environment variables are resolved
    auth = spec.auth.azure

    print("Auth Configuration (with resolved environment variables):")
    print("-" * 60)

    assert auth.client_id == "test-client-id-12345", f"client_id not resolved correctly"
    print(f"✓ client_id: {auth.client_id}")

    assert auth.client_secret == "test-secret-key-67890", f"client_secret not resolved correctly"
    print(f"✓ client_secret: {auth.client_secret}")

    assert auth.tenant_id == "test-tenant-id-abc123", f"tenant_id not resolved correctly"
    print(f"✓ tenant_id: {auth.tenant_id}")

    expected_token_url = "https://login.microsoftonline.com/test-tenant-id-abc123/oauth2/v2.0/token"
    assert auth.token_url == expected_token_url, f"base_url not resolved correctly"
    print(f"✓ base_url: {auth.token_url}")

    expected_issuer = "https://login.microsoftonline.com/test-tenant-id-abc123/v2.0"
    assert auth.issuer == expected_issuer, f"issuer not resolved correctly"
    print(f"✓ issuer: {auth.issuer}")

    expected_scopes = ["api://test-client-id-12345/.default"]
    assert auth.scopes == expected_scopes, f"scopes not resolved correctly"
    print(f"✓ scopes: {auth.scopes}")

    print()


def test_missing_env_var():
    """Test error handling for missing environment variables."""
    from src.tools.env_resolver import resolve_env_var

    print("=" * 60)
    print("Test 3: Error Handling for Missing Environment Variables")
    print("=" * 60)

    # Remove a variable to test error handling
    original_value = os.environ.pop('MISSING_VAR', None)

    try:
        result = resolve_env_var("$MISSING_VAR")
        print("✗ Should have raised ValueError for missing variable")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Correctly raised error for missing variable:")
        print(f"  {str(e)[:80]}...")
    finally:
        # Restore environment
        if original_value:
            os.environ['MISSING_VAR'] = original_value

    print()


def main():
    """Run all tests."""
    try:
        print("\n" + "=" * 60)
        print("Environment Variable Resolution Tests")
        print("=" * 60)
        print()

        test_env_resolver()
        test_spec_config()
        test_missing_env_var()

        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        print()
        print("Summary:")
        print("✓ Environment variable resolver works correctly")
        print("✓ SpecConfig loads and resolves environment variables")
        print("✓ Error handling for missing variables is proper")
        print()

        return 0

    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
