"""Tests for AppConfigProvider remote resources configuration."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import Mock

from drunk_ai_proxy.app.app_config_provider import AppConfigProvider
from drunk_ai_proxy.utils import ConfigYaml, RemoteResourceConfig


class TestAppConfigProviderRemoteResources:
    """Tests for AppConfigProvider.get_remote_resources() method."""

    def test_get_remote_resources_returns_configured_resources(self) -> None:
        """Test get_remote_resources returns configured resource bundles."""
        # Create a mock ConfigYaml with remote_resources
        mock_config = Mock(spec=ConfigYaml)
        mock_resources = [
            RemoteResourceConfig(
                name="bundle1",
                to_dir="prompts/test",
                paths=["https://example.com/file1.md"]
            ),
            RemoteResourceConfig(
                name="bundle2",
                to_dir="skills/test",
                paths=["https://example.com/skill1.md", "https://example.com/skill2.md"]
            )
        ]
        mock_config.remote_resources = mock_resources
        
        # Create provider and inject the mock config
        provider = AppConfigProvider.__new__(AppConfigProvider)
        provider._configs = mock_config
        
        # Test get_remote_resources
        resources = provider.get_remote_resources()
        
        assert resources == mock_resources
        assert len(resources) == 2
        assert resources[0].name == "bundle1"
        assert resources[1].name == "bundle2"

    def test_get_remote_resources_returns_empty_list_when_none(self) -> None:
        """Test get_remote_resources returns empty list when no resources configured."""
        # Create a mock ConfigYaml with no remote_resources
        mock_config = Mock(spec=ConfigYaml)
        mock_config.remote_resources = None
        
        # Create provider and inject the mock config
        provider = AppConfigProvider.__new__(AppConfigProvider)
        provider._configs = mock_config
        
        # Test get_remote_resources
        resources = provider.get_remote_resources()
        
        assert resources == []
        assert len(resources) == 0

    def test_get_remote_resources_returns_empty_list_when_empty(self) -> None:
        """Test get_remote_resources returns empty list when resources list is empty."""
        # Create a mock ConfigYaml with empty remote_resources
        mock_config = Mock(spec=ConfigYaml)
        mock_config.remote_resources = []
        
        # Create provider and inject the mock config
        provider = AppConfigProvider.__new__(AppConfigProvider)
        provider._configs = mock_config
        
        # Test get_remote_resources
        resources = provider.get_remote_resources()
        
        assert resources == []
        assert len(resources) == 0

    def test_get_remote_resources_with_yaml_file(self) -> None:
        """Test get_remote_resources with actual YAML configuration."""
        yaml_content = """
auth:
  default_provider: basic

remote_resources:
  - name: python-docs
    to_dir: docs/python
    paths:
      - https://example.com/python-guide.md
      - https://example.com/python-reference.md
  - name: dotnet-docs
    to_dir: docs/dotnet
    paths:
      - https://example.com/dotnet-guide.md
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            # Load config and create provider
            config = ConfigYaml.load_from_file(temp_file)
            provider = AppConfigProvider.__new__(AppConfigProvider)
            provider._configs = config
            
            # Test get_remote_resources
            resources = provider.get_remote_resources()
            
            assert len(resources) == 2
            assert resources[0].name == "python-docs"
            assert resources[0].to_dir == "docs/python"
            assert len(resources[0].paths) == 2
            assert resources[1].name == "dotnet-docs"
            assert len(resources[1].paths) == 1
        finally:
            os.unlink(temp_file)
