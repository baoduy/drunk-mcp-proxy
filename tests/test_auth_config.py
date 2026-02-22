"""
Tests for authentication configuration loading and validation.

This test suite covers the AuthConfig structure with dictionary-based provider configurations:
- Each provider is a dictionary with configuration values
- Configuration values support environment variable references
- Providers are accessed via typed fields or get_config() method
- All providers are optional (presence = enabled)
"""

import json

import pytest

from src.tools.auth_config import (
    AuthConfig,
    AuthProviderType,
)


class TestAuthConfigBasicCreation:
    """Test basic AuthConfig model creation."""

    def test_auth_config_empty_creation(self):
        """Test creating an empty AuthConfig instance."""
        config = AuthConfig()
        assert config.auth0 is None
        assert config.aws is None
        assert config.azure is None
        assert config.github is None
        assert config.default_provider is None

    def test_auth_config_with_azure_provider(self):
        """Test creating AuthConfig with Azure provider."""
        data = {
            "azure": {
                "client_id": "test-id",
                "client_secret": "test-secret",
                "tenant_id": "test-tenant"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.azure is not None
        assert isinstance(config.azure, dict)
        assert config.azure["client_id"] == "test-id"
        assert config.azure["client_secret"] == "test-secret"

    def test_auth_config_with_default_provider(self):
        """Test creating AuthConfig with default provider."""
        data = {
            "defaultProvider": "azure",
            "azure": {
                "client_id": "test-id",
                "client_secret": "test-secret",
                "tenant_id": "test-tenant"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.default_provider == AuthProviderType.AZURE
        assert config.azure is not None

    def test_auth_config_with_multiple_providers(self):
        """Test creating AuthConfig with multiple providers."""
        data = {
            "defaultProvider": "github",
            "azure": {
                "client_id": "azure-id",
                "client_secret": "azure-secret",
                "tenant_id": "tenant-id"
            },
            "github": {
                "client_id": "github-id",
                "client_secret": "github-secret",
                "scopes": ["user:email"]
            },
            "jwt": {
                "secret_key": "jwt-secret"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.default_provider == AuthProviderType.GITHUB
        assert config.azure is not None
        assert config.github is not None
        assert config.jwt is not None
        assert config.google is None

    def test_get_config_with_provider_type(self):
        """Test get_config() method with AuthProviderType enum."""
        data = {
            "enabled": True,
            "azure": {
                "client_id": "test-id",
                "client_secret": "test-secret",
                "tenant_id": "tenant"
            }
        }
        config = AuthConfig.model_validate(data)
        
        azure_config = config.get_config(AuthProviderType.AZURE)
        assert azure_config is not None
        assert isinstance(azure_config, dict)
        assert azure_config["client_id"] == "test-id"

    def test_get_config_nonexistent_provider(self):
        """Test get_config() returns None for nonexistent provider."""
        config = AuthConfig()
        result = config.get_config(AuthProviderType.AZURE)
        assert result is None

    def test_direct_property_access(self):
        """Test accessing provider configuration via direct property."""
        data = {
            "github": {
                "client_id": "gh-id",
                "client_secret": "gh-secret",
                "scopes": ["repo"]
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.github["client_id"] == "gh-id"
        assert config.github["scopes"] == ["repo"]
        assert config.default_provider is None

    def test_get_config_for_default_provider(self):
        """Test retrieving the default provider using get_config()."""
        data = {
            "enabled": True,
            "defaultProvider": "jwt",
            "jwt": {
                "secret_key": "secret"
            }
        }
        config = AuthConfig.model_validate(data)
        
        # Get the default provider
        default = config.get_config(config.default_provider)
        assert default is not None
        assert isinstance(default, dict)


class TestAuthConfigProviders:
    """Test individual provider configuration types."""

    def test_auth0_config(self):
        """Test Auth0 configuration."""
        data = {
            "auth0": {
                "domain": "example.auth0.com",
                "client_id": "auth0-id",
                "client_secret": "auth0-secret",
                "audience": "https://api.example.com",
                "scopes": ["openid", "profile"]
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.auth0["domain"] == "example.auth0.com"
        assert config.auth0.get("grant_type", "client_credentials") == "client_credentials"

    def test_aws_config(self):
        """Test AWS configuration."""
        data = {
            "aws": {
                "access_key_id": "aws-key",
                "secret_access_key": "aws-secret",
                "region": "us-east-1"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.aws["access_key_id"] == "aws-key"
        assert config.aws["region"] == "us-east-1"

    def test_azure_config_with_scopes(self):
        """Test Azure configuration with scopes."""
        data = {
            "azure": {
                "client_id": "azure-id",
                "client_secret": "azure-secret",
                "tenant_id": "tenant",
                "scopes": ["api://app/.default"]
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.azure["scopes"] == ["api://app/.default"]

    def test_github_config(self):
        """Test GitHub configuration."""
        data = {
            "github": {
                "client_id": "gh-id",
                "client_secret": "gh-secret",
                "scopes": ["user:email", "read:user"]
            }
        }
        config = AuthConfig.model_validate(data)
        assert len(config.github["scopes"]) == 2

    def test_google_config(self):
        """Test Google configuration."""
        data = {
            "google": {
                "client_id": "google-id",
                "client_secret": "google-secret",
                "project_id": "project-123",
                "scopes": ["openid", "email", "profile"]
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.google["project_id"] == "project-123"

    def test_jwt_config(self):
        """Test JWT configuration."""
        data = {
            "jwt": {
                "secret_key": "jwt-secret",
                "algorithm": "HS256",
                "issuer": "issuer-name"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.jwt["algorithm"] == "HS256"
        assert config.jwt["issuer"] == "issuer-name"

    def test_in_memory_config(self):
        """Test In-Memory configuration."""
        data = {
            "inMemory": {
                "users": {
                    "user1": "password1",
                    "user2": "password2"
                }
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.in_memory["users"]["user1"] == "password1"

    def test_oci_config(self):
        """Test OCI configuration."""
        data = {
            "oci": {
                "user_ocid": "user-ocid",
                "tenancy_ocid": "tenancy-ocid",
                "api_key": "api-key",
                "fingerprint": "fingerprint",
                "region": "us-phoenix-1"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.oci["region"] == "us-phoenix-1"


class TestAuthConfigLoadFromFile:
    """Test AuthConfig.load_from_file() method."""

    def test_load_from_file_nonexistent(self):
        """Test loading from nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            AuthConfig.load_from_file("/nonexistent/path/auth.json")

    def test_load_from_file_empty_config(self, tmp_path):
        """Test loading an empty config file."""
        auth_file = tmp_path / "auth.json"
        auth_file.write_text("{}")

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure is None
        assert config.github is None

    def test_load_from_file_single_provider(self, tmp_path):
        """Test loading config with a single provider."""
        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "test-id",
                "client_secret": "test-secret",
                "tenant_id": "tenant"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure is not None
        assert config.azure["client_id"] == "test-id"

    def test_load_from_file_multiple_providers(self, tmp_path):
        """Test loading config with multiple providers."""
        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "azure-id",
                "client_secret": "azure-secret",
                "tenant_id": "tenant"
            },
            "github": {
                "client_id": "github-id",
                "client_secret": "github-secret"
            },
            "jwt": {
                "secret_key": "jwt-secret"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure is not None
        assert config.github is not None
        assert config.jwt is not None

    def test_load_from_file_invalid_json(self, tmp_path):
        """Test loading file with invalid JSON raises error."""
        auth_file = tmp_path / "auth.json"
        auth_file.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            AuthConfig.load_from_file(str(auth_file))

    def test_load_from_file_not_dict(self, tmp_path):
        """Test loading file that contains JSON array instead of object."""
        auth_file = tmp_path / "auth.json"
        auth_file.write_text("[]")

        with pytest.raises(ValueError, match="must contain a JSON object"):
            AuthConfig.load_from_file(str(auth_file))

    def test_load_from_file_with_null_optional_fields(self, tmp_path):
        """Test loading config with null values for optional fields."""
        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "test-id",
                "client_secret": "test-secret",
                "tenant_id": "tenant",
                "token_url": None,
                "issuer": None
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure.get("token_url") is None
        assert config.azure.get("issuer") is None

    def test_load_from_file_with_nested_objects(self, tmp_path):
        """Test loading config with nested objects."""
        auth_file = tmp_path / "auth.json"
        data = {
            "inMemory": {
                "users": {
                    "user1": "password1",
                    "user2": "password2"
                }
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.in_memory["users"]["user1"] == "password1"

    def test_load_from_file_with_default_provider(self, tmp_path):
        """Test loading config with default provider specified."""
        auth_file = tmp_path / "auth.json"
        data = {
            "defaultProvider": "azure",
            "azure": {
                "client_id": "test-id",
                "client_secret": "test-secret",
                "tenant_id": "tenant"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.default_provider == AuthProviderType.AZURE
        assert config.azure is not None

    def test_load_from_file_without_default_provider(self, tmp_path):
        """Test loading config without default provider."""
        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "test-id",
                "client_secret": "test-secret",
                "tenant_id": "tenant"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.default_provider is None
        assert config.azure is not None


class TestAuthConfigEnvironmentVariables:
    """Test environment variable resolution in AuthConfig."""

    def test_resolve_env_var_simple(self, tmp_path, monkeypatch):
        """Test resolving simple environment variable."""
        monkeypatch.setenv("TEST_CLIENT_ID", "resolved-id")

        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "$TEST_CLIENT_ID",
                "client_secret": "secret",
                "tenant_id": "tenant"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure["client_id"] == "resolved-id"

    def test_resolve_env_var_braced(self, tmp_path, monkeypatch):
        """Test resolving environment variable with braces."""
        monkeypatch.setenv("TEST_TENANT_ID", "tenant-123")

        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "id",
                "client_secret": "secret",
                "tenant_id": "${TEST_TENANT_ID}"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure["tenant_id"] == "tenant-123"

    def test_resolve_env_var_in_url(self, tmp_path, monkeypatch):
        """Test resolving environment variable within a URL."""
        monkeypatch.setenv("TENANT_ID", "abc123")

        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "id",
                "client_secret": "secret",
                "tenant_id": "tenant",
                "issuer": "https://login.microsoftonline.com/${TENANT_ID}/v2.0"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure["issuer"] == "https://login.microsoftonline.com/abc123/v2.0"

    def test_resolve_multiple_env_vars(self, tmp_path, monkeypatch):
        """Test resolving multiple environment variables in same provider."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "client-123")
        monkeypatch.setenv("AZURE_SECRET", "secret-456")
        monkeypatch.setenv("AZURE_TENANT", "tenant-789")

        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "$AZURE_CLIENT_ID",
                "client_secret": "$AZURE_SECRET",
                "tenant_id": "$AZURE_TENANT"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.azure["client_id"] == "client-123"
        assert config.azure["client_secret"] == "secret-456"
        assert config.azure["tenant_id"] == "tenant-789"

    def test_missing_env_var_raises_error(self, tmp_path):
        """Test that missing environment variable raises ValueError."""
        auth_file = tmp_path / "auth.json"
        data = {
            "azure": {
                "client_id": "$MISSING_VAR",
                "client_secret": "secret",
                "tenant_id": "tenant"
            }
        }
        auth_file.write_text(json.dumps(data))

        with pytest.raises(ValueError, match="Environment variable"):
            AuthConfig.load_from_file(str(auth_file))

    def test_env_var_in_array(self, tmp_path, monkeypatch):
        """Test that environment variables in arrays are also resolved."""
        monkeypatch.setenv("GITHUB_SCOPE", "user:email")

        auth_file = tmp_path / "auth.json"
        data = {
            "github": {
                "client_id": "id",
                "client_secret": "secret",
                "scopes": ["$GITHUB_SCOPE", "read:user"]
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.github["scopes"][0] == "user:email"
        assert config.github["scopes"][1] == "read:user"

    def test_env_var_missing_in_array_raises_error(self, tmp_path):
        """Test that missing environment variables in arrays raises error."""
        auth_file = tmp_path / "auth.json"
        data = {
            "github": {
                "client_id": "id",
                "client_secret": "secret",
                "scopes": ["$UNRESOLVED", "read:user"]
            }
        }
        auth_file.write_text(json.dumps(data))

        with pytest.raises(ValueError, match="Environment variable"):
            AuthConfig.load_from_file(str(auth_file))


class TestAuthProviderTypeEnum:
    """Test AuthProviderType enumeration."""

    def test_all_providers_defined(self):
        """Test that all 16 providers are defined."""
        providers = list(AuthProviderType)
        assert len(providers) == 16

    def test_auth0_defined(self):
        """Test Auth0 provider is defined."""
        assert AuthProviderType.AUTH0.value == "auth0"

    def test_azure_defined(self):
        """Test Azure provider is defined."""
        assert AuthProviderType.AZURE.value == "azure"

    def test_github_defined(self):
        """Test GitHub provider is defined."""
        assert AuthProviderType.GITHUB.value == "github"

    def test_in_memory_defined(self):
        """Test In-Memory provider is defined."""
        assert AuthProviderType.IN_MEMORY.value == "in_memory"

    def test_all_provider_values(self):
        """Test all provider values are correct."""
        expected_providers = {
            "auth0", "aws", "azure", "debug", "descope",
            "discord", "github", "google", "in_memory",
            "introspection", "jwt", "oci", "scalekit",
            "supabase", "workos", "bearer"
        }
        actual_providers = {p.value for p in AuthProviderType}
        assert actual_providers == expected_providers

    def test_get_config_with_all_provider_types(self):
        """Test get_config() works with all provider types."""
        data = {
            "enabled": True,
            "azure": {
                "client_id": "id",
                "client_secret": "secret",
                "tenant_id": "tenant"
            }
        }
        config = AuthConfig.model_validate(data)
        
        # Test with each provider type
        for provider_type in AuthProviderType:
            result = config.get_config(provider_type)
            # Only azure should be not None
            if provider_type == AuthProviderType.AZURE:
                assert result is not None
            else:
                assert result is None


class TestDefaultProvider:
    """Test default_provider field functionality."""

    def test_default_provider_none_by_default(self):
        """Test that default_provider is None by default."""
        config = AuthConfig()
        assert config.default_provider is None

    def test_default_provider_with_enum_value(self):
        """Test default_provider with AuthProviderType enum."""
        data = {
            "defaultProvider": "azure",
            "azure": {
                "client_id": "id",
                "client_secret": "secret",
                "tenant_id": "tenant"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.default_provider == AuthProviderType.AZURE

    def test_default_provider_json_alias(self):
        """Test that defaultProvider JSON key is properly aliased."""
        data = {
            "defaultProvider": "github",
            "github": {
                "client_id": "id",
                "client_secret": "secret"
            }
        }
        config = AuthConfig.model_validate(data)
        assert config.default_provider == AuthProviderType.GITHUB

    def test_default_provider_all_enum_values(self):
        """Test default_provider with all AuthProviderType values."""
        for provider_type in AuthProviderType:
            data = {"defaultProvider": provider_type.value}
            config = AuthConfig.model_validate(data)
            assert config.default_provider == provider_type

    def test_get_default_provider_config(self):
        """Test getting configuration of the default provider."""
        data = {
            "enabled": True,
            "defaultProvider": "jwt",
            "jwt": {
                "secret_key": "my-secret",
                "algorithm": "HS256"
            }
        }
        config = AuthConfig.model_validate(data)
        
        # Get default provider config
        default_config = config.get_config(config.default_provider)
        assert default_config is not None
        assert isinstance(default_config, dict)
        assert default_config["secret_key"] == "my-secret"

    def test_default_provider_without_config(self):
        """Test default_provider set but provider config missing."""
        data = {
            "defaultProvider": "azure"
            # azure config not provided
        }
        config = AuthConfig.model_validate(data)
        assert config.default_provider == AuthProviderType.AZURE
        assert config.azure is None
        assert config.get_config(AuthProviderType.AZURE) is None

    def test_default_provider_load_from_file(self, tmp_path):
        """Test loading default_provider from file."""
        auth_file = tmp_path / "auth.json"
        data = {
            "defaultProvider": "discord",
            "discord": {
                "client_id": "discord-id",
                "client_secret": "discord-secret",
                "bot_token": "bot-token"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.default_provider == AuthProviderType.DISCORD
        assert config.discord is not None

    def test_default_provider_with_env_vars(self, tmp_path, monkeypatch):
        """Test default_provider config with environment variables."""
        monkeypatch.setenv("OAUTH_SECRET", "secret123")
        
        auth_file = tmp_path / "auth.json"
        data = {
            "defaultProvider": "google",
            "google": {
                "client_id": "client-123",
                "client_secret": "$OAUTH_SECRET",
                "project_id": "project-456"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.default_provider == AuthProviderType.GOOGLE
        assert config.google["client_secret"] == "secret123"

    def test_multiple_providers_with_default(self):
        """Test multiple providers configured with one as default."""
        data = {
            "enabled": True,
            "defaultProvider": "scalekit",
            "azure": {
                "client_id": "azure-id",
                "client_secret": "azure-secret",
                "tenant_id": "tenant"
            },
            "scalekit": {
                "client_id": "scalekit-id",
                "client_secret": "scalekit-secret",
                "environment_url": "https://api.scalekit.com"
            },
            "jwt": {
                "secret_key": "jwt-secret"
            }
        }
        config = AuthConfig.model_validate(data)
        
        # Verify default provider
        assert config.default_provider == AuthProviderType.SCALEKIT
        
        # Verify all providers are available
        assert config.azure is not None
        assert config.scalekit is not None
        assert config.jwt is not None
        
        # Verify default provider can be retrieved
        default = config.get_config(config.default_provider)
        assert default == config.scalekit
        assert default["client_id"] == "scalekit-id"


class TestAuthConfigIntegration:
    """Integration tests for AuthConfig."""

    def test_full_workflow_single_provider(self, tmp_path, monkeypatch):
        """Test complete workflow with single provider."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
        monkeypatch.setenv("AZURE_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT", "tenant")

        auth_file = tmp_path / "auth.json"
        data = {
            "enabled": True,
            "defaultProvider": "azure",
            "azure": {
                "client_id": "$AZURE_CLIENT_ID",
                "client_secret": "$AZURE_SECRET",
                "tenant_id": "$AZURE_TENANT",
                "scopes": ["api://app-id/read"]
            }
        }
        auth_file.write_text(json.dumps(data))

        # Load config
        config = AuthConfig.load_from_file(str(auth_file))

        # Verify default provider
        assert config.default_provider == AuthProviderType.AZURE

        # Verify via direct property
        assert config.azure is not None
        assert config.azure["client_id"] == "client-id"
        assert config.azure["client_secret"] == "secret"
        assert config.azure["tenant_id"] == "tenant"
        assert config.azure["scopes"] == ["api://app-id/read"]

        # Get the default provider config
        default_config = config.get_config(config.default_provider)
        assert default_config is not None
        assert default_config["client_id"] == "client-id"

        # Verify other providers are None
        assert config.github is None
        assert config.get_config(AuthProviderType.GITHUB) is None

    def test_full_workflow_multiple_providers(self, tmp_path, monkeypatch):
        """Test complete workflow with multiple providers."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "azure-id")
        monkeypatch.setenv("GITHUB_CLIENT_ID", "github-id")
        monkeypatch.setenv("JWT_SECRET", "jwt-secret")

        auth_file = tmp_path / "auth.json"
        data = {
            "enabled": True,
            "defaultProvider": "github",
            "azure": {
                "client_id": "$AZURE_CLIENT_ID",
                "client_secret": "azure-secret",
                "tenant_id": "tenant"
            },
            "github": {
                "client_id": "$GITHUB_CLIENT_ID",
                "client_secret": "github-secret"
            },
            "jwt": {
                "secret_key": "$JWT_SECRET"
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))

        # Check default provider
        assert config.default_provider == AuthProviderType.GITHUB
        
        # Check all providers
        assert config.azure is not None
        assert config.github is not None
        assert config.jwt is not None
        assert config.google is None

        # Verify data
        assert config.azure["client_id"] == "azure-id"
        assert config.github["client_id"] == "github-id"
        assert config.jwt["secret_key"] == "jwt-secret"

        # Get default provider
        default = config.get_config(config.default_provider)
        assert default == config.github

    def test_mixed_env_vars_and_literals(self, tmp_path, monkeypatch):
        """Test config with mix of environment variables and literal values."""
        monkeypatch.setenv("GITHUB_SECRET", "gh-secret")

        auth_file = tmp_path / "auth.json"
        data = {
            "defaultProvider": "github",
            "github": {
                "client_id": "github-static-id",
                "client_secret": "$GITHUB_SECRET",
                "scopes": ["user:email", "read:user"]
            }
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.default_provider == AuthProviderType.GITHUB
        assert config.github["client_id"] == "github-static-id"
        assert config.github["client_secret"] == "gh-secret"
        assert config.github["scopes"] == ["user:email", "read:user"]

    def test_all_provider_types_creation(self, tmp_path):
        """Test creating config with all provider types."""
        auth_file = tmp_path / "auth.json"
        data = {
            "enabled": True,
            "defaultProvider": "aws",
            "auth0": {"domain": "x.auth0.com", "client_id": "id", "client_secret": "secret"},
            "aws": {"access_key_id": "key", "secret_access_key": "secret", "region": "us-east-1"},
            "azure": {"client_id": "id", "client_secret": "secret", "tenant_id": "tenant"},
            "descope": {"project_id": "id", "public_key": "key"},
            "discord": {"client_id": "id", "client_secret": "secret", "bot_token": "token"},
            "github": {"client_id": "id", "client_secret": "secret"},
            "google": {"client_id": "id", "client_secret": "secret", "project_id": "proj"},
            "inMemory": {"users": {"user": "pass"}},
            "introspection": {"introspection_url": "http://url", "client_id": "id", "client_secret": "secret"},
            "jwt": {"secret_key": "secret"},
            "oci": {"user_ocid": "u", "tenancy_ocid": "t", "api_key": "key", "fingerprint": "fp"},
            "scalekit": {"client_id": "id", "client_secret": "secret", "environment_url": "http://url"},
            "supabase": {"project_url": "http://url", "api_key": "key"},
            "workos": {"api_key": "key", "client_id": "id"}
        }
        auth_file.write_text(json.dumps(data))

        config = AuthConfig.load_from_file(str(auth_file))
        assert config.default_provider == AuthProviderType.AWS
        assert config.auth0 is not None
        assert config.aws is not None
        assert config.azure is not None
        assert config.descope is not None
        assert config.discord is not None
        assert config.github is not None
        assert config.google is not None
        assert config.in_memory is not None
        assert config.introspection is not None
        assert config.jwt is not None
        assert config.oci is not None
        assert config.scalekit is not None
        assert config.supabase is not None
        assert config.workos is not None
        
        # Verify default provider can be retrieved
        default = config.get_config(config.default_provider)
        assert default == config.aws
