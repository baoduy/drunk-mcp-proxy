"""
Unit tests for src/proxies/config_provider.py module.

Tests proxy configuration loading and management.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.proxies.static_proxies_provider import StaticProxiesProvider
from src.proxies.static_mcp_provider import McpProxyConfig
from src.proxies.mcp_proxy_provider import McpProxyProvider
from src.tools.spec_config import SpecType


class ConcreteProxiesProvider(StaticProxiesProvider):
    """Concrete implementation of StaticProxiesProvider for testing."""
    
    def create_proxy(self):
        """Implementation of abstract method for testing."""
        pass


class TestProxyConfigProviderInit:
    """Test suite for ProxyConfigProvider initialization."""

    def test_init_with_default_config_dir(self):
        """Test initialization with default CONFIG_DIR."""
        provider = ConcreteProxiesProvider()
        assert provider.config_dir is not None
        assert provider.config_file_path.endswith("config.json")
        assert provider.configs == []
        assert provider.logger is not None

    def test_init_with_custom_config_dir(self):
        """Test initialization with custom config directory."""
        provider = StaticProxiesProvider(config_dir="/custom/path")
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
                "path": "/test-api",
                "spec_file": "test.json",
                "spec_type": "mcp"
            }
        ]
        config_file.write_text(json.dumps(config_data))

        # Create the spec file
        spec_file = tmp_path / "test.json"
        spec_file.write_text(json.dumps({"mcpServers": {}, "transport": "stdio"}))

        provider = StaticProxiesProvider(config_dir=str(tmp_path))
        configs = provider._load_configs()

        assert len(configs) == 1
        assert configs[0].path == "/test-api"

    def test_load_configs_caches_result(self, tmp_path):
        """Test that configurations are cached after first load."""
        config_file = tmp_path / "config.json"
        config_data = [
            {
                "path": "/test-api",
                "spec_file": "test.json",
                "spec_type": "mcp"
            }
        ]
        config_file.write_text(json.dumps(config_data))

        spec_file = tmp_path / "test.json"
        spec_file.write_text(json.dumps({"mcpServers": {}, "transport": "stdio"}))

        provider = StaticProxiesProvider(config_dir=str(tmp_path))

        # Load twice
        configs1 = provider._load_configs()
        configs2 = provider._load_configs()

        # Should return the same cached list
        assert configs1 is configs2

    def test_load_configs_file_not_found(self, tmp_path):
        """Test loading configurations when file doesn't exist."""
        provider = StaticProxiesProvider(config_dir=str(tmp_path))

        with pytest.raises(FileNotFoundError):
            provider._load_configs()

    def test_load_configs_invalid_json(self, tmp_path):
        """Test loading configurations with invalid JSON."""
        config_file = tmp_path / "config.json"
        config_file.write_text("invalid json{}")

        provider = StaticProxiesProvider(config_dir=str(tmp_path))

        with pytest.raises(Exception):  # json.JSONDecodeError or similar
            provider._load_configs()


class TestProxyConfigProviderGetConfigsByType:
    """Test suite for ProxyConfigProvider._get_configs_by_type method."""

    @patch.object(StaticProxiesProvider, '_load_configs')
    def test_get_configs_by_type_openapi(self, mock_load):
        """Test filtering configurations by OpenAPI type."""
        mock_config1 = Mock()
        mock_config1.spec_type = SpecType.OPENAPI
        mock_config1.path = "/api1"

        mock_config2 = Mock()
        mock_config2.spec_type = SpecType.MCP
        mock_config2.path = "/mcp1"

        provider = ConcreteProxiesProvider()
        provider.configs = [mock_config1, mock_config2]

        openapi_configs = provider._get_configs_by_type(SpecType.OPENAPI)

        assert len(openapi_configs) == 1
        assert openapi_configs[0].path == "/api1"

    @patch.object(StaticProxiesProvider, '_load_configs')
    def test_get_configs_by_type_mcp(self, mock_load):
        """Test filtering configurations by MCP type."""
        mock_config1 = Mock()
        mock_config1.spec_type = SpecType.OPENAPI
        mock_config1.path = "/api1"

        mock_config2 = Mock()
        mock_config2.spec_type = SpecType.MCP
        mock_config2.path = "/mcp1"

        provider = ConcreteProxiesProvider()
        provider.configs = [mock_config1, mock_config2]

        mcp_configs = provider._get_configs_by_type(SpecType.MCP)

        assert len(mcp_configs) == 1
        assert mcp_configs[0].path == "/mcp1"

    @patch.object(StaticProxiesProvider, '_load_configs')
    def test_get_configs_by_type_empty(self, mock_load):
        """Test filtering when no configs match type."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.OPENAPI

        provider = ConcreteProxiesProvider()
        provider.configs = [mock_config]

        mcp_configs = provider._get_configs_by_type(SpecType.MCP)

        assert len(mcp_configs) == 0


class TestProxyConfigProviderProperties:
    """Test suite for ProxyConfigProvider properties."""

    @patch.object(StaticProxiesProvider, '_get_configs_by_type')
    def test_openapi_configs_property(self, mock_get_configs):
        """Test openapi_configs property."""
        mock_configs = [Mock(), Mock()]
        mock_get_configs.return_value = mock_configs

        provider = ConcreteProxiesProvider()
        result = provider.openapi_configs

        mock_get_configs.assert_called_once_with(SpecType.OPENAPI)
        assert result == mock_configs

    @patch.object(StaticProxiesProvider, '_get_configs_by_type')
    def test_mcp_configs_property(self, mock_get_configs):
        """Test mcp_configs property."""
        mock_configs = [Mock(), Mock()]
        mock_get_configs.return_value = mock_configs

        provider = ConcreteProxiesProvider()
        result = provider.mcp_configs

        mock_get_configs.assert_called_once_with(SpecType.MCP)
        assert result == mock_configs


class TestProxyConfigProviderGetMcpServices:
    """Test suite for ProxyConfigProvider._get_mcp_services method."""

    @patch.object(StaticProxiesProvider, 'mcp_configs', [])
    def test_get_mcp_services_empty_configs(self):
        """Test _get_mcp_services with no MCP configurations."""
        provider = ConcreteProxiesProvider()

        result = provider._get_mcp_services()

        assert len(result) == 0

    @patch('src.proxies.static_proxies_provider.McpProxyProvider.create_mcp_proxies_configs')
    @patch.object(StaticProxiesProvider, 'mcp_configs')
    def test_get_mcp_services_with_root_path(self, mock_mcp_configs, mock_create_mcp_proxies):
        """Test _get_mcp_services with root path configuration."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.MCP
        mock_config.path = "/"
        mock_config.spec_data = {"test": "data"}
        
        mock_mcp_configs_list = [mock_config]
        type(mock_mcp_configs).fget = Mock(return_value=mock_mcp_configs_list)
        
        # Create the expected McpProxyConfig result
        mock_proxy_config = Mock(spec=McpProxyConfig)
        mock_proxy_config.path = "/"
        mock_create_mcp_proxies.return_value = [mock_proxy_config]

        provider = ConcreteProxiesProvider()
        provider.configs = [mock_config]

        result = provider._get_mcp_services()

        assert len(result) == 1
        assert result[0].path == "/"
        mock_create_mcp_proxies.assert_called_once_with(mock_mcp_configs_list)

    @patch('src.proxies.static_proxies_provider.McpProxyProvider.create_mcp_proxies_configs')
    @patch.object(StaticProxiesProvider, 'mcp_configs')
    def test_get_mcp_services_with_custom_path(self, mock_mcp_configs, mock_create_mcp_proxies):
        """Test _get_mcp_services with custom path configuration."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.MCP
        mock_config.path = "/custom"
        mock_config.spec_data = {"test": "data"}
        
        mock_mcp_configs_list = [mock_config]
        type(mock_mcp_configs).fget = Mock(return_value=mock_mcp_configs_list)
        
        # Create the expected McpProxyConfig results
        mock_custom_config = Mock(spec=McpProxyConfig)
        mock_custom_config.path = "/custom"
        mock_create_mcp_proxies.return_value = [mock_custom_config]

        provider = ConcreteProxiesProvider()
        provider.configs = [mock_config]

        result = provider._get_mcp_services()

        assert len(result) == 1
        assert result[0].path == "/custom"
        mock_create_mcp_proxies.assert_called_once_with(mock_mcp_configs_list)

    @patch('src.proxies.static_proxies_provider.McpProxyProvider.create_mcp_proxies_configs')
    @patch.object(StaticProxiesProvider, 'mcp_configs')
    def test_get_mcp_services_skips_none_spec_data(self, mock_mcp_configs, mock_create_mcp_proxies):
        """Test _get_mcp_services skips configs with None spec_data."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.MCP
        mock_config.spec_data = None
        
        mock_mcp_configs_list = [mock_config]
        type(mock_mcp_configs).fget = Mock(return_value=mock_mcp_configs_list)
        
        # Return empty list since the config has None spec_data
        mock_create_mcp_proxies.return_value = []

        provider = ConcreteProxiesProvider()
        provider.configs = [mock_config]

        result = provider._get_mcp_services()

        assert len(result) == 0
        mock_create_mcp_proxies.assert_called_once_with(mock_mcp_configs_list)


class TestProxyConfigProviderGetOpenapiServices:
    """Test suite for ProxyConfigProvider._get_openapi_services method."""

    @patch.object(StaticProxiesProvider, 'openapi_configs', [])
    def test_get_openapi_services_empty_configs(self):
        """Test _get_openapi_services with no OpenAPI configurations."""
        provider = ConcreteProxiesProvider()

        result = provider._get_openapi_services()

        assert len(result) == 0

    @patch('src.proxies.openapi_mcp_provider.OpenApiMcpProvider.create_mcp_proxies_configs')
    @patch.object(StaticProxiesProvider, 'openapi_configs')
    def test_get_openapi_services_success(self, mock_openapi_configs, mock_create_mcp_proxies):
        """Test _get_openapi_services with valid configuration."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.OPENAPI
        mock_config.path = "/api"
        mock_config.spec_data = {"openapi": "3.0"}
        mock_openapi_configs.__get__ = Mock(return_value=[mock_config])

        mock_proxy_config = Mock()
        mock_proxy_config.path = "/api"
        mock_create_mcp_proxies.return_value = [mock_proxy_config]

        provider = ConcreteProxiesProvider()

        result = provider._get_openapi_services()

        assert len(result) == 1
        assert result[0].path == "/api"
        mock_create_mcp_proxies.assert_called_once_with([mock_config])

    @patch.object(StaticProxiesProvider, 'openapi_configs')
    def test_get_openapi_services_skips_none_spec_data(self, mock_openapi_configs):
        """Test _get_openapi_services skips configs with None spec_data."""
        mock_config = Mock()
        mock_config.spec_type = SpecType.OPENAPI
        mock_config.spec_data = None
        mock_openapi_configs.__get__ = Mock(return_value=[mock_config])

        provider = ConcreteProxiesProvider()

        result = provider._get_openapi_services()

        assert len(result) == 0


class TestProxyConfigProviderGetConfigServices:
    """Test suite for ProxyConfigProvider.get_config_services method."""

    @patch.object(StaticProxiesProvider, '_get_openapi_services')
    @patch.object(StaticProxiesProvider, '_get_mcp_services')
    def test_get_config_services(self, mock_get_mcp, mock_get_openapi):
        """Test get_config_services combines MCP and OpenAPI services."""
        mock_mcp_service = Mock()
        mock_mcp_service.path = "/mcp1"
        mock_openapi_service = Mock()
        mock_openapi_service.path = "/api1"

        mock_get_mcp.return_value = [mock_mcp_service]
        mock_get_openapi.return_value = [mock_openapi_service]

        provider = ConcreteProxiesProvider()
        result = provider.get_config_services()

        assert len(result) == 2
        assert result[0].path == "/mcp1"
        assert result[1].path == "/api1"

    @patch.object(StaticProxiesProvider, '_get_openapi_services')
    @patch.object(StaticProxiesProvider, '_get_mcp_services')
    def test_get_config_services_empty(self, mock_get_mcp, mock_get_openapi):
        """Test get_config_services with no services."""
        mock_get_mcp.return_value = []
        mock_get_openapi.return_value = []

        provider = ConcreteProxiesProvider()
        result = provider.get_config_services()

        assert len(result) == 0
