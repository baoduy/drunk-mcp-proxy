"""
Unit tests for src/proxies/mcp_proxy_provider.py module.

Tests MCP proxy provider functionality including SkillDirectoryProvider support.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from drunk_ai_proxy.proxies.mcp.proxy_provider import McpProxyProvider
from drunk_ai_proxy.proxies.mcp.base_provider import McpBaseProvider
from drunk_ai_proxy.utils.config_yaml import McpConfig


class TestMcpProxyProviderInit:
    """Test suite for McpProxyProvider initialization."""

    def test_init_with_config(self):
        """Test initialization with SpecConfig."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        provider = McpProxyProvider(mock_config)

        assert provider.config == mock_config
        assert provider.root_mcp is None
        assert provider.mcp is None
        assert provider._logger is not None

    def test_init_with_root_mcp(self):
        """Test initialization with root_mcp parameter."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        mock_root_mcp = Mock()

        provider = McpProxyProvider(mock_config, root_mcp=mock_root_mcp)

        assert provider.config == mock_config
        assert provider.root_mcp == mock_root_mcp
        assert provider.mcp is None


class TestMcpProxyProviderCreateSkillProxy:
    """Test suite for _create_skill_proxy method."""

    def test_create_skill_proxy_with_none_skill_dir(self):
        """Test that _create_skill_proxy returns early when skill_dir is None."""
        mock_config = Mock(spec=McpConfig)
        mock_config.skill_dir = None
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Should return early without error
        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_mcp.add_provider.assert_not_called()

    @patch("drunk_ai_proxy.utils.env.CONFIG_DIR", "/test/config")
    def test_create_skill_proxy_with_nonexistent_directory(self):
        """Test that _create_skill_proxy returns early when skill_dir doesn't exist."""
        mock_config = Mock(spec=McpConfig)
        mock_config.skill_dir = "nonexistent_skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Should return early without error
        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_mcp.add_provider.assert_not_called()

    @patch("pathlib.Path")
    @patch(
        "drunk_ai_proxy.proxies.mcp.custom_skills_directory_provider.CustomSkillsDirectoryProvider"
    )
    def test_create_skill_proxy_with_empty_directory(
        self, mock_skills_provider_cls, mock_path_cls
    ):
        """Test that _create_skill_proxy returns early when no skills are discovered."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance

        mock_provider = Mock()
        mock_provider.providers = []
        mock_skills_provider_cls.return_value = mock_provider

        mock_config = Mock(spec=McpConfig)
        mock_config.skill_dir = "skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_skills_provider_cls.assert_called_once_with(
            roots=[mock_path_instance], reload=False
        )
        mock_mcp.add_provider.assert_not_called()

    @patch("pathlib.Path")
    @patch(
        "drunk_ai_proxy.proxies.mcp.custom_skills_directory_provider.CustomSkillsDirectoryProvider"
    )
    def test_create_skill_proxy_with_valid_subdirectories(
        self, mock_skills_provider_cls, mock_path_cls
    ):
        """Test that _create_skill_proxy adds provider when skills are discovered."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance

        mock_provider = Mock()
        mock_provider.providers = [Mock()]
        mock_skills_provider_cls.return_value = mock_provider

        mock_config = Mock(spec=McpConfig)
        mock_config.skill_dir = "skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Execute
        provider._create_skill_proxy(mock_mcp)

        # Verify CustomSkillsDirectoryProvider was created with correct parameters
        assert mock_skills_provider_cls.call_count == 1
        call_args = mock_skills_provider_cls.call_args

        # Check that roots parameter contains the parent skill directory
        roots = call_args[1]["roots"]
        assert roots == [mock_path_instance]
        assert call_args[1]["reload"] is False

        # Verify provider was added to mcp
        mock_mcp.add_provider.assert_called_once_with(mock_provider)


class TestMcpProxyProviderCreateProxy:
    """Test suite for create_proxy method."""

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_calls_create_skill_proxy(
        self,
        mock_create_fastmcp_server,
        mock_create_skill_proxy,
        mock_create_proxy,
        mock_get_app_config,
    ):
        """Test that create_proxy calls _create_skill_proxy."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        mock_config.spec_data = {"mcpServers": {}}
        mock_config.auth = None  # Add auth attribute

        mock_mcp = MagicMock()  # Use MagicMock to allow setting auth attribute
        mock_create_fastmcp_server.return_value = mock_mcp
        
        # Mock AppConfigProvider
        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        provider = McpProxyProvider(mock_config)
        result = provider.create_proxy()

        # Verify _create_skill_proxy was called
        mock_create_skill_proxy.assert_called_once_with(mock_mcp)
        assert result == mock_mcp

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_uses_root_mcp_for_root_path(
        self,
        mock_create_fastmcp_server,
        mock_create_skill_proxy,
        mock_create_proxy,
        mock_get_app_config,
    ):
        """Test that create_proxy uses root_mcp when path is '/'."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/"
        mock_config.spec_data = {"mcpServers": {}}
        mock_config.auth = None  # Add auth attribute

        mock_root_mcp = MagicMock()  # Use MagicMock to allow setting auth attribute
        
        # Mock AppConfigProvider
        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        provider = McpProxyProvider(mock_config, root_mcp=mock_root_mcp)
        result = provider.create_proxy()

        # Should use root_mcp instead of creating new one
        assert result == mock_root_mcp
        mock_create_fastmcp_server.assert_not_called()
        mock_create_skill_proxy.assert_called_once_with(mock_root_mcp)

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_returns_cached_mcp(
        self,
        mock_create_fastmcp_server,
        mock_create_skill_proxy,
        mock_create_proxy,
        mock_get_app_config,
    ):
        """Test that create_proxy returns cached mcp on subsequent calls."""
        mock_config = Mock(spec=McpConfig)
        mock_config.path = "/test"
        mock_config.spec_data = {"mcpServers": {}}
        mock_config.auth = None  # Add auth attribute

        mock_mcp = MagicMock()  # Use MagicMock to allow setting auth attribute
        mock_create_fastmcp_server.return_value = mock_mcp
        
        # Mock AppConfigProvider
        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config

        provider = McpProxyProvider(mock_config)

        # Call twice
        result1 = provider.create_proxy()
        result2 = provider.create_proxy()

        # Should only create once
        assert mock_create_fastmcp_server.call_count == 1
        assert result1 == result2
        assert mock_create_skill_proxy.call_count == 1


class TestMcpConfigSkillDirField:
    """Test suite for skill_dir field in McpConfig."""

    def test_mcp_config_with_skill_dir(self):
        """Test that McpConfig accepts skill_dir field."""
        config = McpConfig.model_validate(
            {
                "path": "/test",
                "spec_type": "mcp",
                "skill_dir": "skills",
                "mcpServers": {
                    "test-server": {"enabled": True}
                }
            }
        )

        assert config.skill_dir == "skills"

    def test_mcp_config_skill_dir_defaults_to_none(self):
        """Test that skill_dir defaults to None when not specified."""
        config = McpConfig.model_validate(
            {"path": "/test", "spec_type": "mcp", "mcpServers": {"test-server": {"enabled": True}}}
        )

        assert config.skill_dir is None

    def test_mcp_config_with_mcp_servers_and_skill_dir(self):
        """Test McpConfig with both mcpServers and skill_dir."""
        config = McpConfig.model_validate(
            {
                "path": "/",
                "spec_type": "mcp",
                "skill_dir": "skills",
                "mcpServers": {
                    "test-server": {
                        "transport": "stdio",
                        "command": "node",
                        "args": ["server.js"],
                    }
                },
            }
        )

        assert config.skill_dir == "skills"
        assert config.mcp_servers is not None
        assert "test-server" in config.mcp_servers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
