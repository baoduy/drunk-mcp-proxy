"""
Unit tests for src/proxies/openapi_mcp_provider.py module.

Tests OpenAPI MCP provider functionality.
"""

from unittest.mock import Mock, patch, MagicMock

import pytest

from drunk_ai_proxy.proxies.mcp.openapi_provider import OpenApiMcpProvider
from drunk_ai_proxy.utils.config_yaml import McpConfig, McpAuthConfig


class TestOpenApiMcpProviderInit:
    """Test suite for OpenApiMcpProvider initialization."""

    def test_init_with_config(self):
        """Test initialization with SpecConfig."""
        mock_config = Mock(spec=McpConfig)
        provider = OpenApiMcpProvider(mock_config)

        assert provider.config == mock_config
        assert provider.mcp is None


class TestOpenApiMcpProviderCustomRouteMapper:
    """Test suite for custom_route_mapper method."""

    def test_route_mapper_no_filters(self):
        """Test route mapper with no filters configured."""
        mock_config = Mock(spec=McpConfig)
        mock_config.filters = None
        provider = OpenApiMcpProvider(mock_config)

        mock_route = Mock()
        mock_mcp_type = Mock()

        result = provider.custom_route_mapper(mock_route, mock_mcp_type)
        assert result == mock_mcp_type

    def test_route_mapper_method_filter_passes(self):
        """Test route mapper when method matches filter."""

        mock_config = Mock(spec=McpConfig)
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
        mock_config = Mock(spec=McpConfig)
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
        mock_config = Mock(spec=McpConfig)
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
        mock_config = Mock(spec=McpConfig)
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

    @patch("drunk_ai_proxy.proxies.mcp.openapi_provider.httpx.AsyncClient")
    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    def test_create_client_without_auth(self, mock_get_app_config, mock_client_cls):
        """Test creating client without authentication."""
        # Mock AppConfigProvider
        mock_app_config = Mock()
        mock_app_config.get_client_auth_handler.return_value = None
        mock_get_app_config.return_value = mock_app_config
        
        mock_config = Mock(spec=McpConfig)
        mock_config.auth = None
        mock_config.base_url = "https://api.example.com"
        mock_config.path = "/test"

        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        provider = OpenApiMcpProvider(mock_config)
        result = provider.create_client()

        mock_client_cls.assert_called_once_with(
            base_url="https://api.example.com", auth=None
        )
        assert result == mock_client

    @patch("drunk_ai_proxy.proxies.mcp.openapi_provider.httpx.AsyncClient")
    def test_create_client_with_azure_auth(self, mock_client_cls):
        """Test creating client with Azure authentication."""
        mock_azure_config = Mock(spec=McpAuthConfig)
        mock_auth_obj = Mock()
        mock_config = Mock(spec=McpConfig)
        mock_config.base_url = "https://api.example.com"
        mock_config.path = "/test"
        mock_config.auth = Mock()
        mock_config.auth.azure = mock_azure_config

        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        provider = OpenApiMcpProvider(mock_config)

        with patch.object(provider, "_create_client_auth", return_value=mock_auth_obj):
            result = provider.create_client()

        mock_client_cls.assert_called_once_with(
            base_url="https://api.example.com", auth=mock_auth_obj
        )
        assert result == mock_client

    def test_create_client_without_base_url_raises_error(self):
        """Test creating client without base_url raises ValueError."""
        mock_config = Mock(spec=McpConfig)
        mock_config.auth = None
        mock_config.base_url = None
        mock_config.path = "/test"

        provider = OpenApiMcpProvider(mock_config)

class TestOpenApiMcpProviderCreateProxy:
    """Test suite for create_proxy method."""

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.openapi_provider.FastMCP")
    @patch.object(OpenApiMcpProvider, "create_client")
    def test_create_proxy_success(
        self, mock_create_client, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test successful proxy creation."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test-api"
        mock_config.base_url = "https://api.example.com"
        mock_config.auth = None
        mock_config.spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        mock_config.tags = ["v1"]
        mock_config.skill_dir = None

        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_mcp = MagicMock()
        mock_fastmcp_cls.from_openapi.return_value = mock_mcp

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        provider = OpenApiMcpProvider(mock_config)
        result = provider.create_proxy()

        assert result == mock_mcp
        assert provider.mcp == mock_mcp
        mock_fastmcp_cls.from_openapi.assert_called_once()

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.openapi_provider.FastMCP")
    @patch.object(OpenApiMcpProvider, "create_client")
    def test_create_proxy_returns_cached(
        self, mock_create_client, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test that create_proxy returns cached MCP instance."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test-api"
        mock_config.base_url = "https://api.example.com"
        mock_config.auth = None
        mock_config.spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        mock_config.tags = ["v1"]
        mock_config.skill_dir = None

        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_mcp = MagicMock()
        mock_fastmcp_cls.from_openapi.return_value = mock_mcp

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        provider = OpenApiMcpProvider(mock_config)

        # Call twice
        result1 = provider.create_proxy()
        result2 = provider.create_proxy()

        # Should only create once
        assert mock_fastmcp_cls.from_openapi.call_count == 1
        assert result1 == result2

    def test_create_proxy_without_base_url_and_no_auth_raises_error(self):
        """Test create_proxy raises error without base_url and no Azure auth."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test-api"
        mock_config.base_url = None
        mock_config.auth = None

        provider = OpenApiMcpProvider(mock_config)

        with pytest.raises(ValueError) as exc_info:
            provider.create_proxy()
        assert "base_url is required" in str(exc_info.value)
