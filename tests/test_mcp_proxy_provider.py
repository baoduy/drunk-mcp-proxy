"""
Unit tests for src/proxies/mcp_proxy_provider.py module.

Tests MCP proxy provider functionality including SkillDirectoryProvider support.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call, MagicMock

import pytest

from src.proxies.mcp_proxy_provider import McpProxyProvider
from src.proxies.static_mcp_provider import StaticMcpProvider
from src.tools.spec_config import SpecConfig


class TestMcpProxyProviderInit:
    """Test suite for McpProxyProvider initialization."""

    def test_init_with_config(self):
        """Test initialization with SpecConfig."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/test"
        provider = McpProxyProvider(mock_config)

        assert provider.config == mock_config
        assert provider.root_mcp is None
        assert provider.mcp is None
        assert provider.logger is not None

    def test_init_with_root_mcp(self):
        """Test initialization with root_mcp parameter."""
        mock_config = Mock(spec=SpecConfig)
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
        mock_config = Mock(spec=SpecConfig)
        mock_config.skill_dir = None
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Should return early without error
        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_mcp.add_provider.assert_not_called()

    @patch("src.tools.env.CONFIG_DIR", "/test/config")
    def test_create_skill_proxy_with_nonexistent_directory(self):
        """Test that _create_skill_proxy returns early when skill_dir doesn't exist."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.skill_dir = "nonexistent_skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Should return early without error
        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_mcp.add_provider.assert_not_called()

    @patch("pathlib.Path")
    def test_create_skill_proxy_with_empty_directory(self, mock_path_cls):
        """Test that _create_skill_proxy returns early when skill_dir has no subdirectories."""
        # Setup mock path with empty directory
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = []  # Empty directory
        mock_path_cls.return_value = mock_path_instance

        mock_config = Mock(spec=SpecConfig)
        mock_config.skill_dir = "skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Should return early because no subdirectories
        result = provider._create_skill_proxy(mock_mcp)

        assert result is None
        mock_mcp.add_provider.assert_not_called()

    @patch("pathlib.Path")
    @patch("fastmcp.server.providers.skills.SkillsDirectoryProvider")
    def test_create_skill_proxy_with_valid_subdirectories(
        self, mock_skills_provider_cls, mock_path_cls
    ):
        """Test that _create_skill_proxy creates and adds SkillsDirectoryProvider with valid subdirectories."""
        # Create mock subdirectories
        mock_skill1 = Mock()
        mock_skill1.is_dir.return_value = True
        mock_skill1.name = "skill1"
        mock_skill1.__lt__ = lambda s, o: s.name < o.name
        mock_skill2 = Mock()
        mock_skill2.is_dir.return_value = True
        mock_skill2.name = "skill2"
        mock_skill2.__lt__ = lambda s, o: s.name < o.name
        mock_skill3 = Mock()
        mock_skill3.is_dir.return_value = True
        mock_skill3.name = "skill3"
        mock_skill3.__lt__ = lambda s, o: s.name < o.name

        subdirs = [mock_skill1, mock_skill2, mock_skill3]

        # Setup mock path
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = subdirs
        mock_path_cls.return_value = mock_path_instance

        # Create a mock provider instance
        mock_provider = Mock()
        mock_skills_provider_cls.return_value = mock_provider

        mock_config = Mock(spec=SpecConfig)
        mock_config.skill_dir = "skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        # Execute
        provider._create_skill_proxy(mock_mcp)

        # Verify SkillsDirectoryProvider was created with correct parameters
        assert mock_skills_provider_cls.call_count == 1
        call_args = mock_skills_provider_cls.call_args

        # Check that roots parameter contains the subdirectories
        roots = call_args[1]["roots"]
        assert len(roots) == 3
        assert call_args[1]["reload"] is False

        # Verify provider was added to mcp
        mock_mcp.add_provider.assert_called_once_with(mock_provider)

    @patch("pathlib.Path")
    @patch("fastmcp.server.providers.skills.SkillsDirectoryProvider")
    def test_create_skill_proxy_subdirectories_sorted(
        self, mock_skills_provider_cls, mock_path_cls
    ):
        """Test that subdirectories are sorted before being passed to SkillsDirectoryProvider."""
        # Create mock subdirectories in non-alphabetical order
        mock_zebra = Mock()
        mock_zebra.is_dir.return_value = True
        mock_zebra.name = "zebra"
        mock_zebra.__lt__ = lambda s, o: s.name < o.name
        mock_apple = Mock()
        mock_apple.is_dir.return_value = True
        mock_apple.name = "apple"
        mock_apple.__lt__ = lambda s, o: s.name < o.name
        mock_banana = Mock()
        mock_banana.is_dir.return_value = True
        mock_banana.name = "banana"
        mock_banana.__lt__ = lambda s, o: s.name < o.name

        # Setup mock path to return unsorted list
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = [mock_zebra, mock_apple, mock_banana]
        mock_path_cls.return_value = mock_path_instance

        mock_provider = Mock()
        mock_skills_provider_cls.return_value = mock_provider

        mock_config = Mock(spec=SpecConfig)
        mock_config.skill_dir = "skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        provider._create_skill_proxy(mock_mcp)

        # Get the roots argument
        call_args = mock_skills_provider_cls.call_args
        roots = call_args[1]["roots"]

        # Verify they are sorted
        names = [d.name for d in roots]
        assert names == sorted(names)
        assert names == ["apple", "banana", "zebra"]

    @patch("pathlib.Path")
    @patch("fastmcp.server.providers.skills.SkillsDirectoryProvider")
    def test_create_skill_proxy_ignores_files(
        self, mock_skills_provider_cls, mock_path_cls
    ):
        """Test that _create_skill_proxy ignores files and only includes subdirectories."""
        # Create mock subdirectories and mock files
        mock_skill1 = Mock()
        mock_skill1.is_dir.return_value = True
        mock_skill1.name = "skill1"
        mock_skill1.__lt__ = lambda s, o: s.name < o.name
        mock_file = Mock()
        mock_file.is_dir.return_value = False
        mock_file.name = "README.md"
        mock_skill2 = Mock()
        mock_skill2.is_dir.return_value = True
        mock_skill2.name = "skill2"
        mock_skill2.__lt__ = lambda s, o: s.name < o.name
        mock_hidden = Mock()
        mock_hidden.is_dir.return_value = True
        mock_hidden.name = ".hidden"
        mock_hidden.__lt__ = lambda s, o: s.name < o.name

        # Setup mock path to return mixed list
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = [
            mock_skill1,
            mock_file,
            mock_skill2,
            mock_hidden,
        ]
        mock_path_cls.return_value = mock_path_instance

        mock_provider = Mock()
        mock_skills_provider_cls.return_value = mock_provider

        mock_config = Mock(spec=SpecConfig)
        mock_config.skill_dir = "skills"
        mock_config.path = "/test"

        provider = McpProxyProvider(mock_config)
        mock_mcp = Mock()

        provider._create_skill_proxy(mock_mcp)

        # Get the roots argument
        call_args = mock_skills_provider_cls.call_args
        roots = call_args[1]["roots"]

        # Should only have 3 directories (skill1, skill2, .hidden)
        assert len(roots) == 3

        # Verify README.md was not included
        names = [d.name for d in roots]
        assert "README.md" not in names


class TestMcpProxyProviderCreateProxy:
    """Test suite for create_proxy method."""

    @patch("src.app.auth_provider.GlobalAuthProvider.get_auth_provider")
    @patch("src.proxies.mcp_proxy_provider.McpProxyProvider._create_proxy")
    @patch("src.proxies.mcp_proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    def test_create_proxy_calls_create_skill_proxy(
        self,
        mock_fastmcp_cls,
        mock_create_skill_proxy,
        mock_create_proxy,
        mock_get_auth,
    ):
        """Test that create_proxy calls _create_skill_proxy."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/test"
        mock_config.spec_data = {"mcpServers": {}}

        mock_mcp = Mock()
        mock_fastmcp_cls.return_value = mock_mcp
        mock_get_auth.return_value = None

        provider = McpProxyProvider(mock_config)
        result = provider.create_proxy()

        # Verify _create_skill_proxy was called
        mock_create_skill_proxy.assert_called_once_with(mock_mcp)
        assert result == mock_mcp

    @patch("src.app.auth_provider.GlobalAuthProvider.get_auth_provider")
    @patch("src.proxies.mcp_proxy_provider.McpProxyProvider._create_proxy")
    @patch("src.proxies.mcp_proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    def test_create_proxy_uses_root_mcp_for_root_path(
        self,
        mock_fastmcp_cls,
        mock_create_skill_proxy,
        mock_create_proxy,
        mock_get_auth,
    ):
        """Test that create_proxy uses root_mcp when path is '/'."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/"
        mock_config.spec_data = {"mcpServers": {}}

        mock_root_mcp = Mock()
        mock_get_auth.return_value = None

        provider = McpProxyProvider(mock_config, root_mcp=mock_root_mcp)
        result = provider.create_proxy()

        # Should use root_mcp instead of creating new one
        assert result == mock_root_mcp
        mock_fastmcp_cls.assert_not_called()
        mock_create_skill_proxy.assert_called_once_with(mock_root_mcp)

    @patch("src.app.auth_provider.GlobalAuthProvider.get_auth_provider")
    @patch("src.proxies.mcp_proxy_provider.McpProxyProvider._create_proxy")
    @patch("src.proxies.mcp_proxy_provider.McpProxyProvider._create_skill_proxy")
    @patch("src.proxies.mcp_proxy_provider.FastMCP")
    def test_create_proxy_returns_cached_mcp(
        self,
        mock_fastmcp_cls,
        mock_create_skill_proxy,
        mock_create_proxy,
        mock_get_auth,
    ):
        """Test that create_proxy returns cached mcp on subsequent calls."""
        mock_config = Mock(spec=SpecConfig)
        mock_config.path = "/test"
        mock_config.spec_data = {"mcpServers": {}}

        mock_mcp = Mock()
        mock_fastmcp_cls.return_value = mock_mcp
        mock_get_auth.return_value = None

        provider = McpProxyProvider(mock_config)

        # Call twice
        result1 = provider.create_proxy()
        result2 = provider.create_proxy()

        # Should only create once
        assert mock_fastmcp_cls.call_count == 1
        assert result1 == result2
        assert mock_create_skill_proxy.call_count == 1


class TestSpecConfigSkillDirField:
    """Test suite for skill_dir field in SpecConfig."""

    def test_spec_config_with_skill_dir(self):
        """Test that SpecConfig accepts skill_dir field."""
        config = SpecConfig.model_validate(
            {
                "path": "/test",
                "spec_file": "test.json",
                "spec_type": "mcp",
                "skill_dir": "skills",
            }
        )

        assert config.skill_dir == "skills"

    def test_spec_config_skill_dir_defaults_to_none(self):
        """Test that skill_dir defaults to None when not specified."""
        config = SpecConfig.model_validate(
            {"path": "/test", "spec_file": "test.json", "spec_type": "mcp"}
        )

        assert config.skill_dir is None

    def test_spec_config_with_mcp_servers_and_skill_dir(self):
        """Test SpecConfig with both mcpServers and skill_dir."""
        config = SpecConfig.model_validate(
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
