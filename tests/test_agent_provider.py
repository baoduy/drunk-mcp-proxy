"""Unit tests for AgentProvider."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from drunk_ai_proxy.proxies.agent.agent_provider import AgentProvider, AgentResource


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
        """Test that enabled agents are included in resource list."""
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

            assert len(resources) == 1
            assert str(resources[0].uri) == "agent://enabled-agent.agent.md"
            assert resources[0].name == "enabled-agent.agent.md"
            assert resources[0].description == "Enabled agent"

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
        )

        assert str(resource.uri) == "agent://test"
        assert resource.name == "test"
        assert resource.description == "Test agent"
        assert resource.mime_type == "text/markdown"
        assert resource.enabled is True
        assert resource.file_path == Path("/path/to/agent.md")

    @pytest.mark.asyncio
    async def test_agent_resource_read_method(self) -> None:
        """Test AgentResource read method."""
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
        )

        with pytest.raises(FileNotFoundError):
            await resource.read()
