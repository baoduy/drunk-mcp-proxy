"""Unit tests for custom MCP skills directory provider."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from drunk_ai_proxy.proxies.mcp.custom_skills_directory_provider import (
    CustomSkillsDirectoryProvider,
)


class TestCustomSkillsDirectoryProviderInit:
    """Test suite for CustomSkillsDirectoryProvider initialization."""

    def test_init_normalizes_single_root_path(self) -> None:
        """Test that single Path is converted to list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = CustomSkillsDirectoryProvider(roots=Path(tmpdir))
            assert provider._roots == [Path(tmpdir).resolve()]
            assert provider._reload is False
            assert provider._main_file_name == "SKILL.md"

    def test_init_normalizes_single_root_string(self) -> None:
        """Test that single string path is converted to list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = CustomSkillsDirectoryProvider(roots=tmpdir)
            assert provider._roots == [Path(tmpdir).resolve()]

    def test_init_accepts_sequence_of_paths(self) -> None:
        """Test that sequence of paths is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                provider = CustomSkillsDirectoryProvider(roots=[tmpdir1, tmpdir2])
                assert len(provider._roots) == 2


class TestCustomSkillsDirectoryProviderDiscovery:
    """Test skill discovery logic."""

    def test_discover_flat_skills(self) -> None:
        """Test that flat skill folders are discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skill1"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Skill 1\n")

            provider = CustomSkillsDirectoryProvider(roots=tmpdir)

            assert len(provider.providers) == 1

    @pytest.mark.asyncio
    async def test_discover_namespaced_skills(self) -> None:
        """Test that namespaced skills are discovered with namespaced URIs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            namespace_dir = Path(tmpdir) / "dknet"
            namespace_dir.mkdir()
            skill_dir = namespace_dir / "dknet-overview"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Skill\n")

            provider = CustomSkillsDirectoryProvider(roots=tmpdir)

            resources = await provider.list_resources()
            uris = [str(resource.uri) for resource in resources]
            assert "skill://dknet/dknet-overview/SKILL.md" in uris

    @pytest.mark.asyncio
    async def test_discover_skills_prefixes_root_namespace_for_skills_subroot(self) -> None:
        """Test that roots under skills/<name> are exposed with <name> prefix in URI and name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir)
            dknet_root = data_root / "skills" / "dknet"
            dknet_root.mkdir(parents=True)

            skill_dir = dknet_root / "dknet-overview"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Skill\n")

            provider = CustomSkillsDirectoryProvider(roots=dknet_root)

            resources = await provider.list_resources()
            uris = [str(resource.uri) for resource in resources]
            names = [resource.name for resource in resources]
            
            assert "skill://dknet/dknet-overview/SKILL.md" in uris
            assert "dknet/dknet-overview/SKILL.md" in names

    def test_discover_skills_skips_missing_main_file(self) -> None:
        """Test that directories without main file are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "not_a_skill").mkdir()
            (root / "skill1").mkdir()
            (root / "skill1" / "SKILL.md").write_text("# Skill\n")

            provider = CustomSkillsDirectoryProvider(roots=root)

            assert len(provider.providers) == 1

    def test_discover_skills_skips_duplicate_namespaced_keys(self) -> None:
        """Test that duplicate namespaced skills are deduplicated."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                root1 = Path(tmpdir1)
                root2 = Path(tmpdir2)

                ns1 = root1 / "dknet"
                ns1.mkdir()
                skill1 = ns1 / "dknet-overview"
                skill1.mkdir()
                (skill1 / "SKILL.md").write_text("# Skill\n")

                ns2 = root2 / "dknet"
                ns2.mkdir()
                skill2 = ns2 / "dknet-overview"
                skill2.mkdir()
                (skill2 / "SKILL.md").write_text("# Skill\n")

                provider = CustomSkillsDirectoryProvider(roots=[root1, root2])

                assert len(provider.providers) == 1
