"""Unit tests for OpenAPI flow in MCP proxy provider."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from drunk_ai_proxy.proxies.mcp.proxy_provider import McpProxyProvider
from drunk_ai_proxy.utils import SpecType
from drunk_ai_proxy.utils.config_yaml import McpConfig


class TestMcpProxyProviderOpenApiRouteMapper:
    """Tests for OpenAPI route filtering behavior."""

    def test_route_mapper_no_filters_returns_original_type(self) -> None:
        """Return original MCP type when no filters are configured."""
        mock_config = Mock(spec=McpConfig)
        mock_config.get_openapi_filters.return_value = None

        provider = McpProxyProvider(mock_config)

        route = Mock()
        mcp_type = Mock()

        mapper = getattr(provider, "_openapi_route_mapper")
        result = mapper(route, mcp_type)

        assert result == mcp_type

    def test_route_mapper_excludes_non_matching_method(self) -> None:
        """Exclude route when method is not in allowed filter list."""
        from fastmcp.server.providers.openapi import MCPType

        mock_filters = Mock()
        mock_filters.methods = ["GET", "POST"]
        mock_filters.tags = None

        mock_config = Mock(spec=McpConfig)
        mock_config.get_openapi_filters.return_value = mock_filters

        provider = McpProxyProvider(mock_config)

        route = Mock()
        route.method = "DELETE"
        route.tags = []

        mapper = getattr(provider, "_openapi_route_mapper")
        result = mapper(route, MCPType.TOOL)

        assert result == MCPType.EXCLUDE

    def test_route_mapper_excludes_non_matching_tag(self) -> None:
        """Exclude route when tags do not intersect configured tag filters."""
        from fastmcp.server.providers.openapi import MCPType

        mock_filters = Mock()
        mock_filters.methods = None
        mock_filters.tags = ["public", "v1"]

        mock_config = Mock(spec=McpConfig)
        mock_config.get_openapi_filters.return_value = mock_filters

        provider = McpProxyProvider(mock_config)

        route = Mock()
        route.method = "GET"
        route.tags = ["internal"]

        mapper = getattr(provider, "_openapi_route_mapper")
        result = mapper(route, MCPType.TOOL)

        assert result == MCPType.EXCLUDE


class TestMcpProxyProviderOpenApiClient:
    """Tests for OpenAPI HTTP client creation."""

    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.httpx.AsyncClient")
    def test_create_openapi_client_uses_base_url_and_auth(self, mock_client_cls: Mock) -> None:
        """Create async client with resolved base URL and auth handler."""
        mock_config = Mock(spec=McpConfig)
        mock_config.get_openapi_base_url.return_value = "https://api.example.com"

        provider = McpProxyProvider(mock_config)

        with patch.object(provider, "_create_client_auth", return_value="auth-token"):
            create_openapi_client = getattr(provider, "_create_openapi_client")
            client = create_openapi_client()

        mock_client_cls.assert_called_once_with(
            base_url="https://api.example.com",
            auth="auth-token",
        )
        assert client == mock_client_cls.return_value

    def test_create_openapi_client_without_base_url_raises(self) -> None:
        """Raise ValueError when OpenAPI base URL is missing."""
        mock_config = Mock(spec=McpConfig)
        mock_config.get_openapi_base_url.return_value = None

        provider = McpProxyProvider(mock_config)

        with pytest.raises(ValueError, match="base_url is required"):
            create_openapi_client = getattr(provider, "_create_openapi_client")
            create_openapi_client()


class TestMcpProxyProviderOpenApiCreateProxy:
    """Tests for create_proxy OpenAPI branch."""

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.OpenAPIProvider")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_openapi_success(
        self,
        mock_create_fastmcp_server: Mock,
        mock_openapi_provider: Mock,
        mock_get_app_config: Mock,
    ) -> None:
        """Build OpenAPI provider and attach it to a FastMCP server."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/openapi"
        mock_config.spec_type = SpecType.OPENAPI
        mock_config.codemode_enabled = True
        mock_config.tags = ["v1"]
        mock_config.get_openapi_base_url.return_value = "https://api.example.com"
        mock_config.get_openapi_spec_data.return_value = {
            "openapi": "3.0.0",
            "info": {"title": "Demo", "version": "1.0.0"},
            "paths": {},
        }

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        openapi_mcp = MagicMock()
        mock_create_fastmcp_server.return_value = openapi_mcp
        provider_instance = Mock()
        mock_openapi_provider.return_value = provider_instance

        provider = McpProxyProvider(mock_config)

        with (
            patch.object(provider, "_add_skill_proxy"),
            patch.object(provider, "_add_prompt_proxy"),
            patch.object(provider, "_add_agent_proxy"),
            patch.object(provider, "_create_openapi_client", return_value=Mock()),
        ):
            result = provider.create_proxy()

        assert result == openapi_mcp
        mock_create_fastmcp_server.assert_called_once_with(
            "drunk-ai-proxy/openapi",
            "1.0.0",
            True,
        )
        mock_openapi_provider.assert_called_once()
        openapi_mcp.add_provider.assert_called_once_with(provider_instance)

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.OpenAPIProvider")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_openapi_returns_cached(
        self,
        mock_create_fastmcp_server: Mock,
        mock_openapi_provider: Mock,
        mock_get_app_config: Mock,
    ) -> None:
        """Avoid rebuilding OpenAPI proxy on repeated calls."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/openapi"
        mock_config.spec_type = SpecType.OPENAPI
        mock_config.codemode_enabled = True
        mock_config.tags = []
        mock_config.get_openapi_base_url.return_value = "https://api.example.com"
        mock_config.get_openapi_spec_data.return_value = {
            "openapi": "3.0.0",
            "info": {"title": "Demo", "version": "1.0.0"},
            "paths": {},
        }

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        mock_create_fastmcp_server.return_value = MagicMock()
        mock_openapi_provider.return_value = Mock()

        provider = McpProxyProvider(mock_config)

        with (
            patch.object(provider, "_add_skill_proxy"),
            patch.object(provider, "_add_prompt_proxy"),
            patch.object(provider, "_add_agent_proxy"),
            patch.object(provider, "_create_openapi_client", return_value=Mock()),
        ):
            first = provider.create_proxy()
            second = provider.create_proxy()

        assert first == second
        assert mock_create_fastmcp_server.call_count == 1
        assert mock_openapi_provider.call_count == 1

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    def test_create_proxy_openapi_missing_spec_data_raises(self, mock_get_app_config: Mock) -> None:
        """Raise ValueError when OpenAPI spec data is not loaded."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/openapi"
        mock_config.spec_type = SpecType.OPENAPI
        mock_config.codemode_enabled = True
        mock_config.tags = []
        mock_config.get_openapi_base_url.return_value = "https://api.example.com"
        mock_config.get_openapi_spec_data.return_value = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        provider = McpProxyProvider(mock_config)

        with (
            patch.object(provider, "_add_skill_proxy"),
            patch.object(provider, "_add_prompt_proxy"),
            patch.object(provider, "_add_agent_proxy"),
            patch.object(provider, "_create_openapi_client", return_value=Mock()),
            pytest.raises(ValueError, match="open_api.spec_data is required"),
        ):
            provider.create_proxy()
