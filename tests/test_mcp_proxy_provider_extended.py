"""
Extended tests for McpProxyProvider to increase coverage.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.proxies.mcp_proxy_provider import McpProxyProvider
from src.tools.config_yaml import McpConfig


class TestMcpProxyProviderCreateProxy:
    """Test suite for create_proxy method."""

    @patch("src.proxies.static_mcp_provider.AppConfigProvider.get_instance")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    def test_create_proxy_returns_cached_instance(
        self, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test that create_proxy returns cached mcp instance on subsequent calls."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        mock_config.spec_data = {"mcpServers": {"test": {"url": "http://example.com"}}}
        mock_config.skill_dir = None
        mock_config.auth = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        provider = McpProxyProvider(mock_config)

        # Mock FastMCP instance
        mock_mcp = MagicMock()
        mock_fastmcp_cls.return_value = mock_mcp

        # First call should create new instance
        result1 = provider.create_proxy()
        assert result1 == mock_mcp

        # Second call should return cached instance
        result2 = provider.create_proxy()
        assert result2 == result1

        # FastMCP should only be called once
        assert mock_fastmcp_cls.call_count == 1

    @patch("src.proxies.static_mcp_provider.AppConfigProvider.get_instance")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    @patch("src.proxies.mcp_proxy_provider.SERVER_NAME", "test-server")
    @patch("src.proxies.mcp_proxy_provider.SERVER_VERSION", "2.0.0")
    def test_create_proxy_with_root_path_uses_root_mcp(
        self, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test that create_proxy uses root_mcp for path='/'."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/"
        mock_config.spec_data = {"mcpServers": {"test": {"url": "http://example.com"}}}
        mock_config.skill_dir = None
        mock_config.auth = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        mock_root_mcp = MagicMock()
        provider = McpProxyProvider(mock_config, root_mcp=mock_root_mcp)

        result = provider.create_proxy()

        # Should use root_mcp, not create new FastMCP
        assert result == mock_root_mcp
        mock_fastmcp_cls.assert_not_called()

    @patch("src.proxies.static_mcp_provider.AppConfigProvider.get_instance")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    @patch("src.proxies.mcp_proxy_provider.SERVER_NAME", "test-server")
    @patch("src.proxies.mcp_proxy_provider.SERVER_VERSION", "2.0.0")
    def test_create_proxy_with_non_root_path_creates_new_mcp(
        self, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test that create_proxy creates new FastMCP for non-root paths."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/api"
        mock_config.spec_data = {"mcpServers": {"test": {"url": "http://example.com"}}}
        mock_config.skill_dir = None
        mock_config.auth = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        mock_mcp = MagicMock()
        mock_fastmcp_cls.return_value = mock_mcp

        mock_root_mcp = MagicMock()
        provider = McpProxyProvider(mock_config, root_mcp=mock_root_mcp)

        result = provider.create_proxy()

        # Should create new FastMCP instance
        mock_fastmcp_cls.assert_called_once_with("test-server/api", version="2.0.0")
        assert result == mock_mcp

    @patch("src.proxies.static_mcp_provider.AppConfigProvider.get_instance")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    @patch("fastmcp.server.create_proxy")
    def test_create_proxy_calls_create_proxy_method(
        self, mock_create_proxy_fn, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test that create_proxy calls _create_proxy with spec_data."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        mock_config.spec_data = {"mcpServers": {"test": {"url": "http://example.com"}}}
        mock_config.skill_dir = None
        mock_config.auth = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        mock_mcp = MagicMock()
        mock_fastmcp_cls.return_value = mock_mcp

        mock_proxy = Mock()
        mock_create_proxy_fn.return_value = mock_proxy

        provider = McpProxyProvider(mock_config)
        provider.create_proxy()

        # Should call create_proxy from fastmcp.server
        mock_create_proxy_fn.assert_called_once_with(
            mock_config.spec_data, name=mock_config.path
        )
        mock_mcp.mount.assert_called_once_with(mock_proxy)


class TestMcpProxyProviderCreateProxyMethod:
    """Test suite for _create_proxy method."""

    def test_create_proxy_with_none_spec_data(self):
        """Test that _create_proxy returns None when spec_data is None."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        mock_config.spec_data = None

        provider = McpProxyProvider(mock_config)
        mock_mcp = MagicMock()

        result = provider._create_proxy(mock_mcp)

        assert result is None
        mock_mcp.mount.assert_not_called()

    @patch("fastmcp.server.create_proxy")
    def test_create_proxy_logs_info(self, mock_create_proxy_fn):
        """Test that _create_proxy logs info message."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        mock_config.spec_data = {"mcpServers": {"test": {"url": "http://example.com"}}}

        mock_proxy = Mock()
        mock_create_proxy_fn.return_value = mock_proxy

        provider = McpProxyProvider(mock_config)
        mock_mcp = MagicMock()

        with patch.object(provider.logger, "info") as mock_log_info:
            provider._create_proxy(mock_mcp)
            mock_log_info.assert_called_once()
            assert "Creating proxy for MCP config" in str(mock_log_info.call_args)


class TestMcpProxyProviderCreateMcpProxiesConfigs:
    """Test suite for create_mcp_proxies_configs static method."""

    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    @patch("src.proxies.mcp_proxy_provider.SERVER_NAME", "test-server")
    @patch("src.proxies.mcp_proxy_provider.SERVER_VERSION", "1.0.0")
    def test_create_mcp_proxies_configs_empty_list(self, mock_fastmcp_cls):
        """Test create_mcp_proxies_configs with empty config list."""
        mock_root = Mock()
        mock_fastmcp_cls.return_value = mock_root

        result = McpProxyProvider.create_mcp_proxies_configs([])

        # Should return empty list for empty input
        assert result == []

    @patch("src.proxies.static_mcp_provider.AppConfigProvider.get_instance")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    @patch("src.proxies.mcp_proxy_provider.SERVER_NAME", "test-server")
    @patch("src.proxies.mcp_proxy_provider.SERVER_VERSION", "1.0.0")
    def test_create_mcp_proxies_configs_creates_root_mcp(
        self, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test create_mcp_proxies_configs creates root MCP instance."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/api"
        mock_config.spec_data = {"mcpServers": {"test": {"url": "http://example.com"}}}
        mock_config.skill_dir = None
        mock_config.auth = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        mock_root = Mock()
        mock_fastmcp_cls.return_value = mock_root

        result = McpProxyProvider.create_mcp_proxies_configs([mock_config])

        # Should create root FastMCP
        mock_fastmcp_cls.assert_called()
        # Should have at least the root config
        assert len(result) >= 1
        assert result[0].path == "/"
        assert result[0].mcp_server == mock_root

    @patch("src.proxies.static_mcp_provider.AppConfigProvider.get_instance")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    def test_create_mcp_proxies_configs_skips_none_spec_data(
        self, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test create_mcp_proxies_configs skips configs with None spec_data."""
        mock_config1 = Mock(spec=McpConfig)
        mock_config1.path = "/api1"
        mock_config1.spec_data = None
        mock_config1.auth = None

        mock_config2 = Mock(spec=McpConfig)
        mock_config2.path = "/api2"
        mock_config2.spec_data = {"mcpServers": {"test": {"url": "http://example.com"}}}
        mock_config2.skill_dir = None
        mock_config2.auth = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        mock_root = Mock()
        mock_fastmcp_cls.return_value = mock_root

        result = McpProxyProvider.create_mcp_proxies_configs(
            [mock_config1, mock_config2]
        )

        # Should have root + 1 valid config (skipping the None spec_data)
        assert len(result) == 2
        assert result[0].path == "/"
        # config1 should be skipped, so only config2 is processed

    @patch("src.proxies.static_mcp_provider.AppConfigProvider.get_instance")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    def test_create_mcp_proxies_configs_processes_multiple_configs(
        self, mock_fastmcp_cls, mock_get_app_config
    ):
        """Test create_mcp_proxies_configs processes multiple valid configs."""
        mock_config1 = Mock(spec=McpConfig)
        mock_config1.path = "/api1"
        mock_config1.spec_data = {
            "mcpServers": {"test1": {"url": "http://example1.com"}}
        }
        mock_config1.skill_dir = None
        mock_config1.auth = None

        mock_config2 = Mock(spec=McpConfig)
        mock_config2.path = "/api2"
        mock_config2.spec_data = {
            "mcpServers": {"test2": {"url": "http://example2.com"}}
        }
        mock_config2.skill_dir = None
        mock_config2.auth = None

        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        mock_root = Mock()
        mock_fastmcp_cls.return_value = mock_root

        result = McpProxyProvider.create_mcp_proxies_configs(
            [mock_config1, mock_config2]
        )

        # Should have root + 2 configs
        assert len(result) == 3
        assert result[0].path == "/"
