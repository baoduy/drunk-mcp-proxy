"""Unit tests for AgentProvider."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from drunk_ai_proxy.proxies.agent.agent_provider import (
    AgentProvider,
    AgentResource,
    compute_file_hash,
    parse_frontmatter,
    scan_agent_files,
)


class TestAgentProviderInit:
    """Test suite for AgentProvider initialization."""

    def test_init_with_valid_agent_file(self) -> None:
        """Test initialization with valid agent markdown file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test-agent.agent.md"
            agent_file.write_text(
                "---\ndescription: Test agent for reasoning\nenabled: true\n---\n# Agent Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="test-agent.agent.md",
                description="Test agent for reasoning",
                enabled=True,
            )

            assert provider._agent_path == agent_file.resolve()
            assert provider._agent_name == "test-agent.agent.md"
            assert provider._description == "Test agent for reasoning"
            assert provider._enabled is True
            assert provider._agent_info is not None
            assert len(provider._agent_info.files) == 1

    def test_init_with_disabled_agent(self) -> None:
        """Test initialization with disabled agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "disabled-agent.agent.md"
            agent_file.write_text(
                "---\ndescription: Disabled agent\nenabled: false\n---\n# Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="disabled-agent.agent.md",
                description="Disabled agent",
                enabled=False,
            )

            assert provider._enabled is False

    def test_init_missing_agent_file_raises_error(self) -> None:
        """Test initialization with missing agent file raises FileNotFoundError."""
        missing_file = Path("/nonexistent/agent.agent.md")

        with pytest.raises(FileNotFoundError, match="Agent file not found"):
            AgentProvider(
                agent_path=missing_file,
                agent_name="missing_agent.agent.md",
                description="Missing agent",
                enabled=True,
            )


class TestAgentProviderListResources:
    """Test resource listing functionality."""

    @pytest.mark.asyncio
    async def test_list_resources_enabled_agent(self) -> None:
        """Test that enabled agents are included in resource list with manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "enabled-agent.agent.md"
            agent_file.write_text(
                "---\ndescription: Enabled agent\nenabled: true\n---\n# Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="enabled-agent.agent.md",
                description="Enabled agent",
                enabled=True,
            )

            resources = await provider.list_resources()

            assert len(resources) == 2  # Main file + manifest
            
            # Main agent file
            assert str(resources[0].uri) == "agent://enabled-agent.agent.md"
            assert resources[0].name == "enabled-agent.agent.md"
            assert resources[0].description == "Enabled agent"
            assert resources[0].mime_type == "text/markdown"
            assert resources[0].is_manifest is False
            
            # Manifest
            assert str(resources[1].uri) == "agent://enabled-agent.agent.md/_manifest"
            assert resources[1].name == "enabled-agent.agent.md/_manifest"
            assert "File listing" in resources[1].description
            assert resources[1].mime_type == "application/json"
            assert resources[1].is_manifest is True

    @pytest.mark.asyncio
    async def test_list_resources_disabled_agent(self) -> None:
        """Test that disabled agents are not included in resource list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "disabled-agent.md"
            agent_file.write_text(
                "---\ndescription: Disabled agent\nenabled: false\n---\n# Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="disabled_agent",
                description="Disabled agent",
                enabled=False,
            )

            resources = await provider.list_resources()

            assert len(resources) == 0


class TestAgentProviderGetResource:
    """Test resource retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_resource_by_uri(self) -> None:
        """Test retrieving resource by URI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test-agent.md"
            agent_file.write_text(
                "---\ndescription: Test agent\nenabled: true\n---\n# Agent Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="test_agent",
                description="Test agent",
                enabled=True,
            )

            resource = await provider.get_resource("agent://test_agent")

            assert resource is not None
            assert str(resource.uri) == "agent://test_agent"
            assert resource.name == "test_agent"

    @pytest.mark.asyncio
    async def test_get_resource_by_uri_disabled_agent(self) -> None:
        """Test retrieving disabled agent returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "disabled-agent.md"
            agent_file.write_text(
                "---\ndescription: Disabled agent\nenabled: false\n---\n# Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="disabled_agent",
                description="Disabled agent",
                enabled=False,
            )

            resource = await provider.get_resource("agent://disabled_agent")

            assert resource is None

    @pytest.mark.asyncio
    async def test_get_resource_wrong_uri_returns_none(self) -> None:
        """Test retrieving with wrong URI returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test-agent.md"
            agent_file.write_text(
                "---\ndescription: Test agent\nenabled: true\n---\n# Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="test_agent",
                description="Test agent",
                enabled=True,
            )

            resource = await provider.get_resource("agent://wrong_agent")

            assert resource is None

    @pytest.mark.asyncio
    async def test_get_manifest_resource(self) -> None:
        """Test retrieving manifest resource by URI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test-agent.md"
            agent_file.write_text(
                "---\ndescription: Test agent\nenabled: true\n---\n# Agent Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="test_agent",
                description="Test agent",
                enabled=True,
            )

            resource = await provider.get_resource("agent://test_agent/_manifest")

            assert resource is not None
            assert str(resource.uri) == "agent://test_agent/_manifest"
            assert resource.is_manifest is True
            assert resource.mime_type == "application/json"


class TestAgentProviderReadResource:
    """Test resource content reading functionality."""

    @pytest.mark.asyncio
    async def test_read_resource_returns_full_markdown(self) -> None:
        """Test that reading agent returns full markdown content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test-agent.md"
            content = "---\ndescription: Test agent\nenabled: true\n---\n# Agent Instructions\n\nDetailed agent guidelines."
            agent_file.write_text(content)

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="test_agent",
                description="Test agent",
                enabled=True,
            )

            read_content = await provider._read_resource("agent://test_agent")

            assert read_content == content

    @pytest.mark.asyncio
    async def test_read_resource_wrong_uri_raises_error(self) -> None:
        """Test that reading wrong URI raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test-agent.md"
            agent_file.write_text(
                "---\ndescription: Test\nenabled: true\n---\n# Content\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="test_agent",
                description="Test",
                enabled=True,
            )

            with pytest.raises(FileNotFoundError, match="Agent not found"):
                await provider._read_resource("agent://wrong_agent")

    @pytest.mark.asyncio
    async def test_read_manifest_returns_json(self) -> None:
        """Test that reading manifest resource returns JSON with file info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test-agent.md"
            agent_file.write_text(
                "---\ndescription: Test agent\nenabled: true\n---\n# Agent Instructions\n"
            )

            provider = AgentProvider(
                agent_path=agent_file,
                agent_name="test_agent",
                description="Test agent",
                enabled=True,
            )

            manifest_content = await provider._read_resource("agent://test_agent/_manifest")

            # Should be valid JSON
            manifest = json.loads(manifest_content)
            assert manifest["agent"] == "test_agent"
            assert manifest["enabled"] is True
            assert manifest["description"] == "Test agent"
            assert "files" in manifest
            assert len(manifest["files"]) == 1
            assert manifest["files"][0]["path"] == "test-agent.md"
            assert "size" in manifest["files"][0]
            assert "hash" in manifest["files"][0]
            assert manifest["files"][0]["hash"].startswith("sha256:")


class TestAgentResource:
    """Test suite for AgentResource model."""

    def test_agent_resource_creation(self) -> None:
        """Test creating AgentResource instance."""
        from pydantic import AnyUrl
        
        resource = AgentResource(
            uri=AnyUrl("agent://test"),
            name="test",
            description="Test agent",
            mime_type="text/markdown",
            enabled=True,
            file_path=Path("/path/to/agent.md"),
            is_manifest=False,
        )

        assert str(resource.uri) == "agent://test"
        assert resource.name == "test"
        assert resource.description == "Test agent"
        assert resource.mime_type == "text/markdown"
        assert resource.enabled is True
        assert resource.file_path == Path("/path/to/agent.md")
        assert resource.is_manifest is False

    @pytest.mark.asyncio
    async def test_agent_resource_read_method(self) -> None:
        """Test AgentResource read method for markdown file."""
        from pydantic import AnyUrl
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test.md"
            content = "# Test Agent\n\nAgent content here."
            agent_file.write_text(content)

            resource = AgentResource(
                uri=AnyUrl("agent://test"),
                name="test",
                description="Test",
                mime_type="text/markdown",
                enabled=True,
                file_path=agent_file,
                is_manifest=False,
            )

            read_content = await resource.read()
            assert read_content == content

    @pytest.mark.asyncio
    async def test_agent_resource_read_missing_file(self) -> None:
        """Test AgentResource read with missing file raises error."""
        from pydantic import AnyUrl
        
        resource = AgentResource(
            uri=AnyUrl("agent://test"),
            name="test",
            description="Test",
            mime_type="text/markdown",
            enabled=True,
            file_path=Path("/nonexistent.md"),
            is_manifest=False,
        )

        with pytest.raises(FileNotFoundError):
            await resource.read()


class TestAgentUtilities:
    """Test suite for agent utility functions."""

    def test_parse_frontmatter_with_valid_yaml(self) -> None:
        """Test parsing valid YAML frontmatter."""
        content = """---
description: Test agent
enabled: true
---
# Agent Content"""
        frontmatter, body = parse_frontmatter(content)
        
        assert frontmatter["description"] == "Test agent"
        assert frontmatter["enabled"] is True
        assert body.strip() == "# Agent Content"

    def test_parse_frontmatter_without_frontmatter(self) -> None:
        """Test parsing content without frontmatter."""
        content = "# Agent Content\n\nNo frontmatter here."
        frontmatter, body = parse_frontmatter(content)
        
        assert frontmatter == {}
        assert body == content

    def test_compute_file_hash(self) -> None:
        """Test computing SHA256 hash of a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")
            
            file_hash = compute_file_hash(test_file)
            
            assert file_hash.startswith("sha256:")
            # Verify it's actually a valid hex string
            hex_part = file_hash.split(":")[1]
            assert len(hex_part) == 64  # SHA256 produces 64 hex characters
            assert all(c in "0123456789abcdef" for c in hex_part)

    def test_scan_agent_files(self) -> None:
        """Test scanning agent file for manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "agent.md"
            agent_file.write_text("# Test Agent")
            
            files = scan_agent_files(agent_file)
            
            assert len(files) == 1
            assert files[0].path == "agent.md"
            assert files[0].size > 0
            assert files[0].hash.startswith("sha256:")
