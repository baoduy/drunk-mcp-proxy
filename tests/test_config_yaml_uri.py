"""Tests for URI derivation utilities used by remote resources."""

from __future__ import annotations

import pytest

from drunk_ai_proxy.utils.config_yaml_uri import (
    build_name_from_url,
    build_agent_resource_uri,
    build_prompt_resource_uri,
    build_skill_resource_uris,
)


class TestBuildNameFromUrl:
    """Test suite for fallback resource name derivation."""

    def test_skill_md_uses_parent_folder_name(self) -> None:
        """SKILL.md URLs derive name from parent folder."""
        url = (
            "https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/"
            "plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md"
        )

        name = build_name_from_url(url)

        assert name == "optimizing-ef-core-queries"

    def test_non_skill_file_uses_filename_stem(self) -> None:
        """Non-SKILL.md URLs derive name from filename stem."""
        url = (
            "https://raw.githubusercontent.com/baoduy/DKNet.Templates/refs/heads/main/"
            "Skills/QUICK-REFERENCE.md"
        )

        name = build_name_from_url(url)

        assert name == "quick-reference"


class TestBuildSkillResourceUris:
    """Test suite for remote skill URI derivation."""

    def test_main_skill_uri_uses_skill_md_convention(self) -> None:
        """Main skill URL is mapped to the built-in SKILL.md URI convention."""
        urls = [
            "https://example.com/skills/optimizing-ef-core-queries/SKILL.md",
            "https://example.com/skills/optimizing-ef-core-queries/query-plan.md",
        ]

        uri_map = build_skill_resource_uris(urls)

        assert (
            uri_map[urls[0]]
            == "skill://optimizing-ef-core-queries/SKILL.md"
        )
        assert (
            uri_map[urls[1]]
            == "skill://optimizing-ef-core-queries/query-plan.md"
        )

    def test_skill_uri_uses_configured_name_when_provided(self) -> None:
        """Configured skill name drives URI namespace when present."""
        urls = [
            "https://example.com/skills/optimizing-ef-core-queries/SKILL.md",
            "https://example.com/skills/optimizing-ef-core-queries/query-plan.md",
        ]

        uri_map = build_skill_resource_uris(urls, resource_name="dotnet/ef-core")

        assert uri_map[urls[0]] == "skill://dotnet/ef-core/SKILL.md"
        assert uri_map[urls[1]] == "skill://dotnet/ef-core/query-plan.md"

    def test_raises_when_skill_md_is_missing(self) -> None:
        """Validation fails when SKILL.md is not present in the skill URL list."""
        urls = [
            "https://example.com/skills/optimizing-ef-core-queries/query-plan.md",
        ]

        with pytest.raises(ValueError, match="SKILL.md"):
            build_skill_resource_uris(urls)


class TestBuildAgentResourceUri:
    """Test suite for remote agent URI derivation."""

    def test_agent_uri_uses_agents_path_and_agent_filename(self) -> None:
        """URLs under /agents map to agent://<path>/<file_name>.agent.md."""
        url = "https://example.com/data/agents/core/reasoning.agent.md"

        uri = build_agent_resource_uri(url)

        assert uri == "agent://core/reasoning.agent.md"

    def test_agent_uri_uses_configured_name_when_provided(self) -> None:
        """Configured agent name drives URI path and filename when present."""
        url = "https://example.com/anything/ignored.md"

        uri = build_agent_resource_uri(url, resource_name="dotnet/modernize-agent")

        assert uri == "agent://dotnet/modernize-agent.agent.md"

    def test_agent_uri_fallback_uses_last_folder_and_normalized_filename(self) -> None:
        """URLs without /agents use last folder plus normalized .agent.md filename."""
        url = "https://example.com/custom/tools/refactor.md"

        uri = build_agent_resource_uri(url)

        assert uri == "agent://tools/refactor.agent.md"


class TestBuildPromptResourceUri:
    """Test suite for remote prompt URI derivation."""

    def test_prompt_uri_uses_configured_name_when_provided(self) -> None:
        """Configured prompt name drives prompt URI when present."""
        url = "https://example.com/prompts/ignored.md"

        uri = build_prompt_resource_uri(url, resource_name="dotnet/refactor-guide")

        assert uri == "prompt://dotnet/refactor-guide"

    def test_prompt_uri_fallback_uses_filename_when_name_missing(self) -> None:
        """Prompt URI falls back to URL filename when no explicit name is provided."""
        url = "https://example.com/prompts/generate-tests.md"

        uri = build_prompt_resource_uri(url)

        assert uri == "prompt://generate-tests"
