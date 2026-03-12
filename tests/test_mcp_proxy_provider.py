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

    def test_create_skill_proxy_with_no_skill_dirs(self):
        """Test that _create_skill_proxy returns early when no skill dirs."""
        mock_config = Mock(spec=McpConfig)
        mock_config.get_skill_dirs.return_value = []
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Should return early without error
        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_mcp.add_provider.assert_not_called()

    @patch("drunk_ai_proxy.utils.env.CONFIG_DIR", "/test/config")
    def test_create_skill_proxy_with_nonexistent_directory(self):
        """Test that _create_skill_proxy returns early when dir doesn't exist."""
        mock_config = Mock(spec=McpConfig)
        mock_config.get_skill_dirs.return_value = ["nonexistent_skills"]
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
        mock_config.get_skill_dirs.return_value = ["skills"]
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_skills_provider_cls.assert_called_once_with(
            roots=[mock_path_instance], reload=True
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
        mock_config.get_skill_dirs.return_value = ["skills"]
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
        assert call_args[1]["reload"] is True

        # Verify provider was added to mcp
        mock_mcp.add_provider.assert_called_once_with(mock_provider)


class TestMcpProxyProviderCreatePromptProxy:
    """Test suite for _create_prompt_proxy method."""

    @patch("drunk_ai_proxy.proxies.prompt.prompt_provider.McpPromptProvider")
    def test_create_prompt_proxy_uses_original_relative_dirs(
        self, mock_prompt_provider_cls, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that relative prompt dirs are passed unchanged to prompt provider."""
        monkeypatch.chdir(tmp_path)
        prompt_dir = tmp_path / "data" / "prompts" / "custom"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "test.md").write_text(
            "---\ndescription: test\n---\nhello",
            encoding="utf-8",
        )

        mock_config = Mock(spec=McpConfig)
        mock_config.get_prompt_dirs.return_value = ["prompts/custom"]
        mock_config.path = "/resources"

        mock_prompt_provider = Mock()
        mock_prompt_provider.register_to_mcp.return_value = 1
        mock_prompt_provider_cls.return_value = mock_prompt_provider

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        provider._create_prompt_proxy(mock_mcp)

        mock_prompt_provider_cls.assert_called_once_with(
            mock_config,
            prompt_dirs=["prompts/custom"],
        )
        mock_prompt_provider.register_to_mcp.assert_called_once_with(mock_mcp)


class TestMcpProxyProviderCreateProxy:
    """Test suite for create_proxy method."""

    @patch("drunk_ai_proxy.proxies.mcp.base_provider.AppConfigProvider.get_instance")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_agent_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_prompt_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_calls_create_skill_proxy(
        self,
        mock_create_fastmcp_server,
        mock_create_skill_proxy,
        mock_create_prompt_proxy,
        mock_create_agent_proxy,
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
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_agent_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_prompt_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_uses_root_mcp_for_root_path(
        self,
        mock_create_fastmcp_server,
        mock_create_skill_proxy,
        mock_create_prompt_proxy,
        mock_create_agent_proxy,
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
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_agent_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_prompt_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("drunk_ai_proxy.proxies.mcp.proxy_provider.McpProxyBuilder.create_fastmcp_server")
    def test_create_proxy_returns_cached_mcp(
        self,
        mock_create_fastmcp_server,
        mock_create_skill_proxy,
        mock_create_prompt_proxy,
        mock_create_agent_proxy,
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


class TestMcpConfigResourcesField:
    """Test suite for resource fields in McpConfig."""

    def test_mcp_config_with_skills_dirs(self):
        """Test that McpConfig accepts skills.dirs field."""
        config = McpConfig.model_validate(
            {
                "path": "/test",
                "spec_type": "mcp",
                "skills": {"dirs": ["skills"]},
                "mcpServers": {
                    "test-server": {"enabled": True}
                }
            }
        )

        assert config.get_skill_dirs() == ["skills"]

    def test_mcp_config_skills_defaults_to_empty(self):
        """Test that skills dirs default to empty when not specified."""
        config = McpConfig.model_validate(
            {"path": "/test", "spec_type": "mcp", "mcpServers": {"test-server": {"enabled": True}}}
        )

        assert config.get_skill_dirs() == []

    def test_mcp_config_rejects_legacy_skill_dir(self):
        """Test that McpConfig rejects legacy skill_dir field."""
        with pytest.raises(ValueError, match="Legacy MCP resource keys are no longer supported"):
            McpConfig.model_validate(
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

    def test_mcp_config_with_mcp_servers_and_resources(self):
        """Test McpConfig with mcpServers and resource dirs."""
        config = McpConfig.model_validate(
            {
                "path": "/",
                "spec_type": "mcp",
                "skills": {"dirs": ["skills"]},
                "prompts": {"dirs": ["prompts/custom"]},
                "agents": {"dirs": ["agents/core"]},
                "mcpServers": {
                    "test-server": {
                        "transport": "stdio",
                        "command": "node",
                        "args": ["server.js"],
                    }
                },
            }
        )

        assert config.get_skill_dirs() == ["skills"]
        assert config.get_prompt_dirs() == ["prompts/custom"]
        assert config.get_agent_dirs() == ["agents/core"]
        assert config.mcp_servers is not None
        assert "test-server" in config.mcp_servers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
