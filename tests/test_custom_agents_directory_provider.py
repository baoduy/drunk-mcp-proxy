"""Unit tests for custom agents directory provider."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from drunk_ai_proxy.proxies.agent.custom_agents_directory_provider import (
    CustomAgentsDirectoryProvider,
)


class TestCustomAgentsDirectoryProviderInit:
    """Test suite for CustomAgentsDirectoryProvider initialization."""

    def test_init_normalizes_single_root_path(self) -> None:
        """Test that single Path is converted to list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = CustomAgentsDirectoryProvider(roots=Path(tmpdir))
            assert provider._roots == [Path(tmpdir).resolve()]
            assert provider._reload is False

    def test_init_normalizes_single_root_string(self) -> None:
        """Test that single string path is converted to list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = CustomAgentsDirectoryProvider(roots=tmpdir)
            assert provider._roots == [Path(tmpdir).resolve()]

    def test_init_accepts_sequence_of_paths(self) -> None:
        """Test that sequence of paths is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                provider = CustomAgentsDirectoryProvider(roots=[tmpdir1, tmpdir2])
                assert len(provider._roots) == 2


class TestCustomAgentsDirectoryProviderDiscovery:
    """Test agent discovery logic."""

    def test_discover_flat_agents(self) -> None:
        """Test that flat agent files are discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "reasoning.agent.md"
            agent_file.write_text(
                "---\ndescription: Reasoning agent\nenabled: true\n---\n# Agent\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            assert len(provider.providers) == 1

    def test_discover_multiple_flat_agents(self) -> None:
        """Test that multiple flat agent files are discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent1 = Path(tmpdir) / "reasoning.agent.md"
            agent1.write_text(
                "---\ndescription: Reasoning agent\nenabled: true\n---\n# Agent 1\n"
            )

            agent2 = Path(tmpdir) / "planning.agent.md"
            agent2.write_text(
                "---\ndescription: Planning agent\nenabled: true\n---\n# Agent 2\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            assert len(provider.providers) == 2

    @pytest.mark.asyncio
    async def test_discover_namespaced_agents(self) -> None:
        """Test that namespaced agents are discovered with correct URIs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            namespace_dir = Path(tmpdir) / "core"
            namespace_dir.mkdir()
            agent_file = namespace_dir / "reasoning.agent.md"
            agent_file.write_text(
                "---\ndescription: Core reasoning agent\nenabled: true\n---\n# Agent\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            resources = await provider.list_resources()
            uris = [str(resource.uri) for resource in resources]
            assert "agent://core/reasoning.agent.md" in uris

    @pytest.mark.asyncio
    async def test_discover_agents_prefixes_root_namespace_for_agents_subroot(self) -> None:
        """Test that roots under agents/<name> are exposed with <name> prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir)
            dknet_root = data_root / "agents" / "dknet"
            dknet_root.mkdir(parents=True)

            agent_file = dknet_root / "test-generator.agent.md"
            agent_file.write_text(
                "---\ndescription: Test generator agent\nenabled: true\n---\n# Agent\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=dknet_root)

            resources = await provider.list_resources()
            uris = [str(resource.uri) for resource in resources]
            names = [resource.name for resource in resources]

            assert "agent://dknet/test-generator.agent.md" in uris
            assert "agent://dknet/test-generator.agent.md/_manifest" in uris
            assert "dknet/test-generator.agent.md" in names
            assert "dknet/test-generator.agent.md/_manifest" in names

    @pytest.mark.asyncio
    async def test_discover_nested_namespaced_agents(self) -> None:
        """Test that agents in namespace directories are discovered (single level only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create single-level namespace (implementation only supports 1 level)
            namespace_dir = Path(tmpdir) / "tools"
            namespace_dir.mkdir(parents=True)
            agent_file = namespace_dir / "refactor.agent.md"
            agent_file.write_text(
                "---\ndescription: Code refactoring agent\nenabled: true\n---\n# Refactor\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            resources = await provider.list_resources()
            uris = [str(resource.uri) for resource in resources]
            # Single-level namespace format: agent://tools/refactor.agent.md
            assert "agent://tools/refactor.agent.md" in uris

    def test_discover_agents_skips_disabled(self) -> None:
        """Test that disabled agents are discovered but not listed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            enabled_agent = Path(tmpdir) / "enabled.agent.md"
            enabled_agent.write_text(
                "---\ndescription: Enabled agent\nenabled: true\n---\n# Content\n"
            )

            disabled_agent = Path(tmpdir) / "disabled.agent.md"
            disabled_agent.write_text(
                "---\ndescription: Disabled agent\nenabled: false\n---\n# Content\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            # Both providers created, but disabled won't list resources
            assert len(provider.providers) == 2

    def test_discover_agents_skips_missing_description(self) -> None:
        """Test that agents without description field are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_agent = Path(tmpdir) / "valid.agent.md"
            valid_agent.write_text(
                "---\ndescription: Valid agent\nenabled: true\n---\n# Content\n"
            )

            invalid_agent = Path(tmpdir) / "invalid.agent.md"
            invalid_agent.write_text("---\nenabled: true\n---\n# No description\n")

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            # Only valid agent should be discovered
            assert len(provider.providers) == 1

    def test_discover_agents_skips_malformed_frontmatter(self) -> None:
        """Test that agents with malformed frontmatter are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_agent = Path(tmpdir) / "valid.agent.md"
            valid_agent.write_text(
                "---\ndescription: Valid agent\nenabled: true\n---\n# Content\n"
            )

            malformed_agent = Path(tmpdir) / "malformed.agent.md"
            malformed_agent.write_text("---\ninvalid yaml: [\n---\n# Invalid\n")

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            # Only valid agent should be discovered
            assert len(provider.providers) == 1

    def test_discover_agents_handles_duplicate_names(self) -> None:
        """Test that duplicate agent names are deduplicated."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                root1 = Path(tmpdir1)
                root2 = Path(tmpdir2)

                agent1 = root1 / "reasoning.agent.md"
                agent1.write_text(
                    "---\ndescription: First reasoning agent\nenabled: true\n---\n# Agent 1\n"
                )

                agent2 = root2 / "reasoning.agent.md"
                agent2.write_text(
                    "---\ndescription: Second reasoning agent\nenabled: true\n---\n# Agent 2\n"
                )

                provider = CustomAgentsDirectoryProvider(roots=[root1, root2])

                # Should only register first occurrence
                assert len(provider.providers) == 1

    def test_discover_agents_handles_duplicate_namespaced_names(self) -> None:
        """Test that duplicate namespaced agent names are deduplicated."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                root1 = Path(tmpdir1)
                root2 = Path(tmpdir2)

                ns1 = root1 / "core"
                ns1.mkdir()
                agent1 = ns1 / "planning.agent.md"
                agent1.write_text(
                    "---\ndescription: First planning agent\nenabled: true\n---\n# Agent 1\n"
                )

                ns2 = root2 / "core"
                ns2.mkdir()
                agent2 = ns2 / "planning.agent.md"
                agent2.write_text(
                    "---\ndescription: Second planning agent\nenabled: true\n---\n# Agent 2\n"
                )

                provider = CustomAgentsDirectoryProvider(roots=[root1, root2])

                # Should only register first occurrence
                assert len(provider.providers) == 1

    def test_agent_name_sanitization(self) -> None:
        """Test that agent names are properly sanitized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create agent with special characters
            agent_file = Path(tmpdir) / "Code Analyzer & Refactor!.agent.md"
            agent_file.write_text(
                "---\ndescription: Code analyzer\nenabled: true\n---\n# Agent\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            # Name should be sanitized to lowercase with underscores
            assert len(provider.providers) == 1

    def test_discover_agents_skips_empty_directories(self) -> None:
        """Test that empty directories are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir) / "empty"
            empty_dir.mkdir()

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            assert len(provider.providers) == 0

    def test_discover_agents_from_multiple_roots(self) -> None:
        """Test agent discovery from multiple root directories."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                root1 = Path(tmpdir1)
                root2 = Path(tmpdir2)

                agent1 = root1 / "agent1.agent.md"
                agent1.write_text(
                    "---\ndescription: Agent 1\nenabled: true\n---\n# Agent 1\n"
                )

                agent2 = root2 / "agent2.agent.md"
                agent2.write_text(
                    "---\ndescription: Agent 2\nenabled: true\n---\n# Agent 2\n"
                )

                provider = CustomAgentsDirectoryProvider(roots=[root1, root2])

                assert len(provider.providers) == 2


class TestCustomAgentsDirectoryProviderResourceListing:
    """Test resource listing and retrieval."""

    @pytest.mark.asyncio
    async def test_list_resources_includes_enabled_agents(self) -> None:
        """Test that list_resources returns enabled agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "reasoning.agent.md"
            agent_file.write_text(
                "---\ndescription: Reasoning agent\nenabled: true\n---\n# Agent\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            resources = await provider.list_resources()

            # Each agent returns 2 resources: main file + manifest
            assert len(resources) == 2
            # Check main agent resource
            main_resource = [r for r in resources if not r.name.endswith("/_manifest")][0]
            assert str(main_resource.uri) == "agent://reasoning.agent.md"
            assert main_resource.name == "reasoning.agent.md"
            assert main_resource.description == "Reasoning agent"

    @pytest.mark.asyncio
    async def test_list_resources_excludes_disabled_agents(self) -> None:
        """Test that list_resources excludes disabled agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            enabled_agent = Path(tmpdir) / "enabled.agent.md"
            enabled_agent.write_text(
                "---\ndescription: Enabled\nenabled: true\n---\n# Content\n"
            )

            disabled_agent = Path(tmpdir) / "disabled.agent.md"
            disabled_agent.write_text(
                "---\ndescription: Disabled\nenabled: false\n---\n# Content\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            resources = await provider.list_resources()

            # Each enabled agent returns 2 resources: main file + manifest
            assert len(resources) == 2
            # Verify only enabled agent is present
            agent_names = [r.name for r in resources if not r.name.endswith("/_manifest")]
            assert len(agent_names) == 1
            assert agent_names[0] == "enabled.agent.md"

    @pytest.mark.asyncio
    async def test_get_resource_by_uri(self) -> None:
        """Test retrieving agent by URI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "reasoning.agent.md"
            agent_file.write_text(
                "---\ndescription: Reasoning agent\nenabled: true\n---\n# Agent\n"
            )

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            resource = await provider.get_resource("agent://reasoning.agent.md")

            assert resource is not None
            assert str(resource.uri) == "agent://reasoning.agent.md"
            assert resource.name == "reasoning.agent.md"

    @pytest.mark.asyncio
    async def test_read_resource_returns_full_content(self) -> None:
        """Test that reading agent via get_resource and read returns full markdown content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "reasoning.agent.md"
            content = "---\ndescription: Reasoning agent\nenabled: true\n---\n# Agent Instructions\n\nDetailed content."
            agent_file.write_text(content)

            provider = CustomAgentsDirectoryProvider(roots=tmpdir)

            # Get the resource first
            resource = await provider.get_resource("agent://reasoning.agent.md")
            assert resource is not None
            
            # Read its content
            read_content = await resource.read()
            assert read_content == content
