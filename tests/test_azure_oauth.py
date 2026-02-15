"""
Unit tests for src/tools/azure_oauth.py module.

Tests Azure OAuth2 authentication functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.tools.azure_oauth import AzureOauth


class TestAzureOauthInit:
    """Test suite for AzureOauth initialization."""

    def test_init_basic(self):
        """Test basic initialization without storage."""
        oauth = AzureOauth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://login.microsoftonline.com/test/token",
            scope="https://graph.microsoft.com/.default"
        )
        
        assert oauth.client_id == "test_client"
        assert oauth.client_secret == "test_secret"
        assert oauth.token_url == "https://login.microsoftonline.com/test/token"
        assert oauth.scope == "https://graph.microsoft.com/.default"
        assert oauth.storage is not None  # Should have default storage

    def test_init_with_custom_storage(self):
        """Test initialization with custom storage."""
        mock_storage = Mock()
        
        oauth = AzureOauth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://login.microsoftonline.com/test/token",
            scope="https://graph.microsoft.com/.default",
            token_storage=mock_storage
        )
        
        assert oauth.storage == mock_storage

    def test_init_without_scope(self):
        """Test initialization without scope."""
        oauth = AzureOauth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://login.microsoftonline.com/test/token"
        )
        
        assert oauth.scope is None

    def test_init_with_empty_scope(self):
        """Test initialization with empty scope string."""
        oauth = AzureOauth(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://login.microsoftonline.com/test/token",
            scope=""
        )
        
        assert oauth.scope == ""


class TestAzureOauthProperties:
    """Test suite for AzureOauth properties and attributes."""

    def test_has_storage_property(self):
        """Test that oauth instance has storage property."""
        oauth = AzureOauth(
            client_id="test",
            client_secret="secret",
            token_url="https://login.test.com/token"
        )
        
        assert hasattr(oauth, 'storage')
        assert oauth.storage is not None

    def test_inherits_from_httpx_auth(self):
        """Test that AzureOauth inherits from httpx.Auth."""
        import httpx
        
        oauth = AzureOauth(
            client_id="test",
            client_secret="secret",
            token_url="https://login.test.com/token"
        )
        
        assert isinstance(oauth, httpx.Auth)


class TestAzureOauthUsage:
    """Test suite for AzureOauth usage patterns."""

    def test_can_be_used_as_auth_object(self):
        """Test that AzureOauth can be used as httpx auth."""
        import httpx
        
        oauth = AzureOauth(
            client_id="test",
            client_secret="secret",
            token_url="https://login.test.com/token"
        )
        
        # Should be able to pass as auth parameter (not actually making requests)
        # Just testing the interface
        assert callable(getattr(oauth, 'sync_auth_flow', None)) or callable(getattr(oauth, 'auth_flow', None))
