"""
Unit tests for src/proxies/config_provider.py module.

Tests proxy configuration loading and management.
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.proxies.config_provider import ProxyConfigProvider
from src.tools.spec_config import SpecType


class TestProxyConfigProviderInit:
    """Test suite for ProxyConfigProvider initialization."""

    def test_init_with_default_config_dir(self):
        """Test initialization with default CONFIG_DIR."""
        provider = ProxyConfigProvider()
        assert provider.config_dir is not None
        assert provider.config_file_path.endswith("config.json")
        assert provider.configs == []
        assert provider.logger is not None

    def test_init_with_custom_config_dir(self):
        """Test initialization with custom config directory."""
        provider = ProxyConfigProvider(config_dir="/custom/path")
        assert provider.config_dir == "/custom/path"
        assert provider.config_file_path == "/custom/path/config.json"


class TestProxyConfigProviderLoadConfigs:
    """Test suite for ProxyConfigProvider._load_configs method."""

    def test_load_configs_success(self, tmp_path):
        """Test successful loading of configurations."""
        # Create a temporary config file
        config_file = tmp_path / "config.json"
        config_data = [
            {
                "name": "test-api",
                "specFile": "test.json",
                "specType": "mcp"
            }
        ]
        config_file.write_text(json.dumps(config_data))
        
        # Create the spec file
        spec_file = tmp_path / "test.json"
        spec_file.write_text(json.dumps({"mcpServers": {}, "transport": "stdio"}))
        
        provider = ProxyConfigProvider(config_dir=str(tmp_path))
        configs = provider._load_configs()
        
        assert len(configs) == 1
        assert configs[0].name == "test-api"

    def test_load_configs_caches_result(self, tmp_path):
        """Test that configurations are cached after first load."""
        config_file = tmp_path / "config.json"
        config_data = [
            {
                "name": "test-api",
                "specFile": "test.json",
                "specType": "mcp"
            }
        ]
        config_file.write_text(json.dumps(config_data))
        
        spec_file = tmp_path / "test.json"
        spec_file.write_text(json.dumps({"mcpServers": {}, "transport": "stdio"}))
        
        provider = ProxyConfigProvider(config_dir=str(tmp_path))
        
        # Load twice
        configs1 = provider._load_configs()
        configs2 = provider._load_configs()
        
        # Should return the same cached list
        assert configs1 is configs2

    def test_load_configs_file_not_found(self, tmp_path):
        """Test loading configurations when file doesn't exist."""
        provider = ProxyConfigProvider(config_dir=str(tmp_path))
        
        with pytest.raises(FileNotFoundError):
            provider._load_configs()

    def test_load_configs_invalid_json(self, tmp_path):
        """Test loading configurations with invalid JSON."""
        config_file = tmp_path / "config.json"
        config_file.write_text("invalid json{}")
        
        provider = ProxyConfigProvider(config_dir=str(tmp_path))
        
        with pytest.raises(Exception):  # json.JSONDecodeError or similar
            provider._load_configs()


class TestProxyConfigProviderGetConfigsByType:
    """Test suite for ProxyConfigProvider._get_configs_by_type method."""

    @patch.object(ProxyConfigProvider, '_load_configs')
    def test_get_configs_by_type_openapi(self, mock_load):
        """Test filtering configurations by OpenAPI type."""
        mock_config1 = Mock()
        mock_config1.spec_type = SpecType.OPENAPI
        mock_config1.name = "api1"
        
        mock_config2 = Mock()
        mock_config2.spec_type = SpecType.MCP
        mock_config2.name = "mcp1"
        
        provider = ProxyConfigProvider()
        provider.configs = [mock_config1, mock_config2]
        
        openapi_configs = provider._get_configs_by_type(SpecType.OPENAPI)
        
        assert len(openapi_configs) == 1
        assert openapi_configs[0].name == "api1"

    @patch.object(ProxyConfigProvider, '_load_configs')
    def test_get_configs_by_type_mcp(self, mock_load):
        """Test filtering configurations by MCP type."""
        mock_config1 = Mock()
        mock_config1.spec_type = SpecType.OPENAPI
        mock_config1.name = "api1"
        
        mock_config2 = Mock()
        mock_config2.spec_type = SpecType.MCP
        mock_config2.name = "mcp1"
        
        provider = ProxyConfigProvider()
        provider.configs = [mock_config1, mock_config2]
        
        mcp_configs = provider._get_configs_by_type(SpecType.MCP)
        
        assert len(mcp_configs) == 1
        assert mcp_configs[0].name == "mcp1"

    @patch.object(ProxyConfigProvider, '_load_configs')
    def test_get_configs_by_type_empty(self, mock_load):
        """Test filtering when no configs match type."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.OPENAPI
        
        provider = ProxyConfigProvider()
        provider.configs = [mock_config]
        
        mcp_configs = provider._get_configs_by_type(SpecType.MCP)
        
        assert len(mcp_configs) == 0


class TestProxyConfigProviderProperties:
    """Test suite for ProxyConfigProvider properties."""

    @patch.object(ProxyConfigProvider, '_get_configs_by_type')
    def test_openapi_configs_property(self, mock_get_configs):
        """Test openapi_configs property."""
        mock_configs = [Mock(), Mock()]
        mock_get_configs.return_value = mock_configs
        
        provider = ProxyConfigProvider()
        result = provider.openapi_configs
        
        mock_get_configs.assert_called_once_with(SpecType.OPENAPI)
        assert result == mock_configs

    @patch.object(ProxyConfigProvider, '_get_configs_by_type')
    def test_mcp_configs_property(self, mock_get_configs):
        """Test mcp_configs property."""
        mock_configs = [Mock(), Mock()]
        mock_get_configs.return_value = mock_configs
        
        provider = ProxyConfigProvider()
        result = provider.mcp_configs
        
        mock_get_configs.assert_called_once_with(SpecType.MCP)
        assert result == mock_configs


class TestProxyConfigProviderGetMcpServices:
    """Test suite for ProxyConfigProvider._get_mcp_services method."""

    @patch.object(ProxyConfigProvider, 'mcp_configs', [])
    def test_get_mcp_services_empty_configs(self):
        """Test _get_mcp_services with no MCP configurations."""
        provider = ProxyConfigProvider()
        
        result = provider._get_mcp_services()
        
        assert len(result) == 0

    @patch('src.proxies.config_provider.McpProxyConfig')
    @patch('src.proxies.config_provider.create_proxy')
    @patch('src.proxies.config_provider.FastMCP')
    @patch.object(ProxyConfigProvider, 'mcp_configs')
    def test_get_mcp_services_with_root_path(self, mock_mcp_configs, mock_fastmcp_cls, mock_create_proxy, mock_proxy_config_cls):
        """Test _get_mcp_services with root path configuration."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.MCP
        mock_config.name = "test-mcp"
        mock_config.path = "/"
        mock_config.namespace = None
        mock_config.spec_data = {"test": "data"}
        mock_mcp_configs.__get__ = Mock(return_value=[mock_config])
        
        mock_root_mcp = Mock()
        mock_fastmcp_cls.return_value = mock_root_mcp
        mock_proxy = Mock()
        mock_create_proxy.return_value = mock_proxy
        
        # Set up proxy config mock to return object with name attribute
        mock_root_config = Mock()
        mock_root_config.name = "root"
        mock_proxy_config_cls.return_value = mock_root_config
        
        provider = ProxyConfigProvider()
        
        result = provider._get_mcp_services()
        
        assert len(result) == 1
        assert result[0].name == "root"
        mock_root_mcp.mount.assert_called_once_with(mock_proxy, namespace=None)

    @patch('src.proxies.config_provider.McpProxyConfig')
    @patch('src.proxies.config_provider.create_proxy')
    @patch('src.proxies.config_provider.FastMCP')
    @patch.object(ProxyConfigProvider, 'mcp_configs')
    def test_get_mcp_services_with_custom_path(self, mock_mcp_configs, mock_fastmcp_cls, mock_create_proxy, mock_proxy_config_cls):
        """Test _get_mcp_services with custom path configuration."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.MCP
        mock_config.name = "test-mcp"
        mock_config.path = "/custom"
        mock_config.namespace = "test"
        mock_config.spec_data = {"test": "data"}
        mock_mcp_configs.__get__ = Mock(return_value=[mock_config])
        
        mock_root_mcp = Mock()
        mock_custom_mcp = Mock()
        mock_fastmcp_cls.side_effect = [mock_root_mcp, mock_custom_mcp]
        mock_proxy = Mock()
        mock_create_proxy.return_value = mock_proxy
        
        # Create mock proxy configs with proper names
        mock_root_config = Mock()
        mock_root_config.name = "root"
        mock_custom_config = Mock()
        mock_custom_config.name = "test-mcp"
        mock_proxy_config_cls.side_effect = [mock_root_config, mock_custom_config]
        
        provider = ProxyConfigProvider()
        
        result = provider._get_mcp_services()
        
        assert len(result) == 2
        assert result[0].name == "root"
        assert result[1].name == "test-mcp"
        mock_custom_mcp.mount.assert_called_once_with(mock_proxy, namespace="test")

    @patch('src.proxies.config_provider.McpProxyConfig')
    @patch('src.proxies.config_provider.create_proxy')
    @patch('src.proxies.config_provider.FastMCP')
    @patch.object(ProxyConfigProvider, 'mcp_configs')
    def test_get_mcp_services_skips_none_spec_data(self, mock_mcp_configs, mock_fastmcp, mock_create_proxy, mock_proxy_config_cls):
        """Test _get_mcp_services skips configs with None spec_data."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.MCP
        mock_config.name = "test-mcp"
        mock_config.spec_data = None
        mock_mcp_configs.__get__ = Mock(return_value=[mock_config])
        
        mock_root_mcp = Mock()
        mock_fastmcp.return_value = mock_root_mcp
        
        mock_root_config = Mock()
        mock_root_config.name = "root"
        mock_proxy_config_cls.return_value = mock_root_config
        
        provider = ProxyConfigProvider()
        
        result = provider._get_mcp_services()
        
        # Should only have root, no custom MCP
        assert len(result) == 1
        assert result[0].name == "root"
        mock_create_proxy.assert_not_called()


class TestProxyConfigProviderGetOpenapiServices:
    """Test suite for ProxyConfigProvider._get_openapi_services method."""

    @patch.object(ProxyConfigProvider, 'openapi_configs', [])
    def test_get_openapi_services_empty_configs(self):
        """Test _get_openapi_services with no OpenAPI configurations."""
        provider = ProxyConfigProvider()
        
        result = provider._get_openapi_services()
        
        assert len(result) == 0

    @patch('src.proxies.config_provider.McpProxyConfig')
    @patch('src.proxies.openapi_mcp_provider.OpenApiMcpProvider')
    @patch.object(ProxyConfigProvider, 'openapi_configs')
    def test_get_openapi_services_success(self, mock_openapi_configs, mock_openapi_provider_cls, mock_proxy_config_cls):
        """Test _get_openapi_services with valid configuration."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.OPENAPI
        mock_config.name = "test-api"
        mock_config.path = "/api"
        mock_config.spec_data = {"openapi": "3.0"}
        mock_openapi_configs.__get__ = Mock(return_value=[mock_config])
        
        mock_mcp = Mock()
        mock_provider = Mock()
        mock_provider.create_proxy.return_value = mock_mcp
        mock_openapi_provider_cls.return_value = mock_provider
        
        mock_proxy_config = Mock()
        mock_proxy_config.name = "test-api"
        mock_proxy_config_cls.return_value = mock_proxy_config
        
        provider = ProxyConfigProvider()
        
        result = provider._get_openapi_services()
        
        assert len(result) == 1
        assert result[0].name == "test-api"
        mock_openapi_provider_cls.assert_called_once_with(mock_config)

    @patch.object(ProxyConfigProvider, 'openapi_configs')
    def test_get_openapi_services_skips_none_spec_data(self, mock_openapi_configs):
        """Test _get_openapi_services skips configs with None spec_data."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.OPENAPI
        mock_config.name = "test-api"
        mock_config.spec_data = None
        mock_openapi_configs.__get__ = Mock(return_value=[mock_config])
        
        provider = ProxyConfigProvider()
        
        result = provider._get_openapi_services()
        
        assert len(result) == 0


class TestProxyConfigProviderGetConfigServices:
    """Test suite for ProxyConfigProvider.get_config_services method."""

    @patch.object(ProxyConfigProvider, '_get_openapi_services')
    @patch.object(ProxyConfigProvider, '_get_mcp_services')
    def test_get_config_services(self, mock_get_mcp, mock_get_openapi):
        """Test get_config_services combines MCP and OpenAPI services."""
        mock_mcp_service = Mock()
        mock_mcp_service.name = "mcp1"
        mock_openapi_service = Mock()
        mock_openapi_service.name = "api1"
        
        mock_get_mcp.return_value = [mock_mcp_service]
        mock_get_openapi.return_value = [mock_openapi_service]
        
        provider = ProxyConfigProvider()
        result = provider.get_config_services()
        
        assert len(result) == 2
        assert result[0].name == "mcp1"
        assert result[1].name == "api1"

    @patch.object(ProxyConfigProvider, '_get_openapi_services')
    @patch.object(ProxyConfigProvider, '_get_mcp_services')
    def test_get_config_services_empty(self, mock_get_mcp, mock_get_openapi):
        """Test get_config_services with no services."""
        mock_get_mcp.return_value = []
        mock_get_openapi.return_value = []
        
        provider = ProxyConfigProvider()
        result = provider.get_config_services()
        
        assert len(result) == 0
