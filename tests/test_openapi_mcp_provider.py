"""
Unit tests for src/proxies/openapi_mcp_provider.py module.

Tests OpenAPI MCP provider functionality.
"""

from unittest.mock import Mock, patch

import pytest

from src.proxies.openapi_mcp_provider import OpenApiMcpProvider
from src.tools.spec_config import SpecConfig, AzureAuthConfig


class TestOpenApiMcpProviderInit:
    """Test suite for OpenApiMcpProvider initialization."""

    def test_init_with_config(self):
        """Test initialization with SpecConfig."""
        mock_config = Mock(spec=SpecConfig)
        provider = OpenApiMcpProvider(mock_config)

        assert provider.config == mock_config
        assert provider.mcp is None
        assert provider.logger is not None


class TestOpenApiMcpProviderCustomRouteMapper:
    """Test suite for custom_route_mapper method."""

    def test_route_mapper_no_filters(self):
        """Test route mapper with no filters configured."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.filters = None
        provider = OpenApiMcpProvider(mock_config)

        mock_route = Mock()
        mock_mcp_type = Mock()

        result = provider.custom_route_mapper(mock_route, mock_mcp_type)
        assert result == mock_mcp_type

    def test_route_mapper_method_filter_passes(self):
        """Test route mapper when method matches filter."""

        mock_config = Mock(spec=SpecConfig)
        mock_filters = Mock()
        mock_filters.methods = ["GET", "POST"]
        mock_filters.tags = None
        mock_config.filters = mock_filters

        provider = OpenApiMcpProvider(mock_config)

        mock_route = Mock()
        mock_route.method = "GET"
        mock_mcp_type = Mock()

        result = provider.custom_route_mapper(mock_route, mock_mcp_type)
        assert result == mock_mcp_type

    def test_route_mapper_method_filter_excludes(self):
        """Test route mapper when method doesn't match filter."""
        mock_config = Mock(spec=SpecConfig)
        mock_filters = Mock()
        mock_filters.methods = ["GET", "POST"]
        mock_filters.tags = None
        mock_config.filters = mock_filters

        provider = OpenApiMcpProvider(mock_config)

        mock_route = Mock()
        mock_route.method = "DELETE"

        # Import MCPType locally to avoid module-level import
        from fastmcp.server.providers.openapi import MCPType
        mock_mcp_type = Mock()

        result = provider.custom_route_mapper(mock_route, mock_mcp_type)
        assert result == MCPType.EXCLUDE

    def test_route_mapper_tag_filter_passes(self):
        """Test route mapper when tag matches filter."""
        mock_config = Mock(spec=SpecConfig)
        mock_filters = Mock()
        mock_filters.methods = None
        mock_filters.tags = ["public", "v1"]
        mock_config.filters = mock_filters

        provider = OpenApiMcpProvider(mock_config)

        mock_route = Mock()
        mock_route.tags = ["public", "api"]
        mock_mcp_type = Mock()

        result = provider.custom_route_mapper(mock_route, mock_mcp_type)
        assert result == mock_mcp_type

    def test_route_mapper_tag_filter_excludes(self):
        """Test route mapper when tag doesn't match filter."""
        mock_config = Mock(spec=SpecConfig)
        mock_filters = Mock()
        mock_filters.methods = None
        mock_filters.tags = ["public", "v1"]
        mock_config.filters = mock_filters

        provider = OpenApiMcpProvider(mock_config)

        mock_route = Mock()
        mock_route.tags = ["internal", "admin"]

        # Import MCPType locally to avoid module-level import
        from fastmcp.server.providers.openapi import MCPType
        mock_mcp_type = Mock()

        result = provider.custom_route_mapper(mock_route, mock_mcp_type)
        assert result == MCPType.EXCLUDE


class TestOpenApiMcpProviderCreateClient:
    """Test suite for create_client method."""

    @patch('src.proxies.openapi_mcp_provider.httpx.AsyncClient')
    def test_create_client_without_auth(self, mock_client_cls):
        """Test creating client without authentication."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.auth = None
        mock_config.base_url = "https://api.example.com"
        mock_config.path = "/test"

        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        provider = OpenApiMcpProvider(mock_config)
        result = provider.create_client()

        mock_client_cls.assert_called_once_with(base_url="https://api.example.com", auth=None, headers={})
        assert result == mock_client

    @patch('src.proxies.openapi_mcp_provider.httpx.AsyncClient')
    def test_create_client_with_azure_auth(self, mock_client_cls):
        """Test creating client with Azure authentication."""
        mock_azure_config = Mock(spec=AzureAuthConfig)
        mock_auth_obj = Mock()
        mock_config = Mock(spec=SpecConfig)
        mock_config.base_url = "https://api.example.com"
        mock_config.path = "/test"
        mock_config.auth = Mock()
        mock_config.auth.azure = mock_azure_config

        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        provider = OpenApiMcpProvider(mock_config)

        with patch.object(provider, '_create_client_auth', return_value=mock_auth_obj):
            result = provider.create_client()

        mock_client_cls.assert_called_once_with(base_url="https://api.example.com", auth=mock_auth_obj, headers={})
        assert result == mock_client

    def test_create_client_without_base_url_raises_error(self):
        """Test creating client without base_url raises ValueError."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.auth = None
        mock_config.base_url = None
        mock_config.path = "/test"

        provider = OpenApiMcpProvider(mock_config)

        with pytest.raises(ValueError) as exc_info:
            provider.create_client()
        assert "base_url is required" in str(exc_info.value)


class TestOpenApiMcpProviderScopeValue:
    """Test suite for _scope_value static method."""

    def test_scope_value_with_scopes(self):
        """Test _scope_value with configured scopes."""
        mock_config = Mock(spec=AzureAuthConfig)
        mock_config.scopes = ["read", "write", "admin"]

        result = OpenApiMcpProvider._scope_value(mock_config)
        assert result == "read write admin"

    def test_scope_value_with_empty_scopes(self):
        """Test _scope_value with empty scopes list."""
        mock_config = Mock(spec=AzureAuthConfig)
        mock_config.scopes = []

        result = OpenApiMcpProvider._scope_value(mock_config)
        assert result is None

    def test_scope_value_with_none_scopes(self):
        """Test _scope_value with None scopes."""
        mock_config = Mock(spec=AzureAuthConfig)
        mock_config.scopes = None

        result = OpenApiMcpProvider._scope_value(mock_config)
        assert result is None


class TestOpenApiMcpProviderCreateClientAuth:
    """Test suite for _create_client_auth method."""

    @patch('src.proxies.static_mcp_provider.AzureOauth')
    @patch('src.proxies.static_mcp_provider.CacheProvider.get_oauth_store')
    def test_create_client_auth(self, mock_get_oauth_store, mock_azure_oauth_cls):
        """Test creating Azure OAuth authentication."""
        mock_azure_config = Mock(spec=AzureAuthConfig)
        mock_azure_config.client_id = "test_client_id"
        mock_azure_config.client_secret = "test_secret"
        mock_azure_config.token_url = "https://login.microsoftonline.com/token"
        mock_azure_config.scopes = ["api://test/.default"]

        mock_auth = Mock()
        mock_azure_oauth_cls.return_value = mock_auth

        mock_token_storage = Mock()
        mock_get_oauth_store.return_value = mock_token_storage

        mock_config = Mock(spec=SpecConfig)
        mock_config.base_url = "https://api.example.com"

        provider = OpenApiMcpProvider(mock_config)

        result = provider._create_client_auth(mock_azure_config)

        mock_azure_oauth_cls.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_secret",
            token_url="https://login.microsoftonline.com/token",
            scope="api://test/.default",
            token_storage=mock_token_storage
        )
        assert result == mock_auth


class TestOpenApiMcpProviderCreateProxy:
    """Test suite for create_proxy method."""

    @patch.object(OpenApiMcpProvider, '_get_global_auth_provider')
    @patch('src.proxies.openapi_mcp_provider.FastMCP')
    @patch.object(OpenApiMcpProvider, 'create_client')
    def test_create_proxy_success(self, mock_create_client, mock_fastmcp_cls, mock_get_auth):
        """Test successful proxy creation."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/test-api"
        mock_config.base_url = "https://api.example.com"
        mock_config.auth = None
        mock_config.spec_data = {"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}
        mock_config.tags = ["v1"]

        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_mcp = Mock()
        mock_fastmcp_cls.from_openapi.return_value = mock_mcp

        mock_get_auth.return_value = None

        provider = OpenApiMcpProvider(mock_config)
        result = provider.create_proxy()

        assert result == mock_mcp
        assert provider.mcp == mock_mcp
        mock_fastmcp_cls.from_openapi.assert_called_once()

    @patch.object(OpenApiMcpProvider, '_get_global_auth_provider')
    @patch('src.proxies.openapi_mcp_provider.FastMCP')
    @patch.object(OpenApiMcpProvider, 'create_client')
    def test_create_proxy_returns_cached(self, mock_create_client, mock_fastmcp_cls, mock_get_auth):
        """Test that create_proxy returns cached MCP instance."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/test-api"
        mock_config.base_url = "https://api.example.com"
        mock_config.auth = None
        mock_config.spec_data = {"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}
        mock_config.tags = ["v1"]

        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_mcp = Mock()
        mock_fastmcp_cls.from_openapi.return_value = mock_mcp

        mock_get_auth.return_value = None

        provider = OpenApiMcpProvider(mock_config)

        # Call twice
        result1 = provider.create_proxy()
        result2 = provider.create_proxy()

        # Should only create once
        assert mock_fastmcp_cls.from_openapi.call_count == 1
        assert result1 == result2

    def test_create_proxy_without_base_url_and_no_auth_raises_error(self):
        """Test create_proxy raises error without base_url and no Azure auth."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/test-api"
        mock_config.base_url = None
        mock_config.auth = None

        provider = OpenApiMcpProvider(mock_config)

        with pytest.raises(ValueError) as exc_info:
            provider.create_proxy()
        assert "base_url is required" in str(exc_info.value)

    @patch.object(OpenApiMcpProvider, '_get_global_auth_provider')
    @patch('src.proxies.openapi_mcp_provider.FastMCP')
    @patch.object(OpenApiMcpProvider, 'create_client')
    def test_create_proxy_initialization_failure(self, mock_create_client, mock_fastmcp_cls, mock_get_auth):
        """Test create_proxy raises error when FastMCP initialization fails."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/test-api"
        mock_config.base_url = "https://api.example.com"
        mock_config.auth = None
        mock_config.spec_data = {"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}
        mock_config.tags = []

        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_get_auth.return_value = None

        # Return None to simulate initialization failure
        mock_fastmcp_cls.from_openapi.return_value = None

        provider = OpenApiMcpProvider(mock_config)

        with pytest.raises(RuntimeError) as exc_info:
            provider.create_proxy()
        assert "FastMCP failed to initialize" in str(exc_info.value)
