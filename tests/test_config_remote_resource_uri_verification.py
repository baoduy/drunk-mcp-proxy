"""Configuration-driven verification tests for remote resource names and URIs."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from drunk_ai_proxy.utils.config_yaml import ConfigYaml
from drunk_ai_proxy.utils.config_yaml_uri import ConfigYamlUriBuilder

build_agent_resource_uri = ConfigYamlUriBuilder.build_agent_resource_uri
build_prompt_resource_uri = ConfigYamlUriBuilder.build_prompt_resource_uri
build_skill_resource_uris = ConfigYamlUriBuilder.build_skill_resource_uris


class TestConfigRemoteResourceUriVerification:
    """Validate remote resource name and URI conventions from config.yaml."""

    @staticmethod
    def _config_path() -> str:
        """Return absolute path to the workspace config.yaml."""
        return str(Path(__file__).resolve().parents[1] / "data" / "config.yaml")

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize a configured resource name for URI assertions."""
        return name.strip().strip("/").lower()

    @staticmethod
    def _set_env_placeholders(monkeypatch: pytest.MonkeyPatch) -> None:
        """Set placeholder values for all `$VAR` references in config.yaml."""
        # Keep this test independent from local developer secrets.
        config_text = Path(TestConfigRemoteResourceUriVerification._config_path()).read_text()
        env_names = set(re.findall(r"\$\{?([A-Z0-9_]+)\}?", config_text))
        for env_name in env_names:
            monkeypatch.setenv(env_name, "test-value")

    @staticmethod
    def _expected_agent_uri_from_name(name: str) -> str:
        """Build expected agent URI from configured name convention."""
        normalized_name = TestConfigRemoteResourceUriVerification._normalize_name(name)
        parts = [part for part in normalized_name.split("/") if part]
        file_name = parts[-1] if parts else "remote"
        if not file_name.endswith(".agent.md"):
            if "." in file_name:
                file_name = f"{file_name.rsplit('.', 1)[0]}.agent.md"
            else:
                file_name = f"{file_name}.agent.md"
        path_parts = parts[:-1]
        if path_parts:
            return f"agent://{'/'.join(path_parts)}/{file_name}"
        return f"agent://{file_name}"

    def test_config_remote_skills_name_and_uri_rules(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate all configured remote skill entries map to expected URIs."""
        # Load the real workspace config with temporary env placeholders injected.
        self._set_env_placeholders(monkeypatch)
        config = ConfigYaml.load_from_file(self._config_path())
        mcp_entries = config.mcp or []

        skill_resources = [
            resource
            for mcp_config in mcp_entries
            for resource in mcp_config.get_skill_remote_resources()
        ]

        assert skill_resources, "Expected at least one remote skill resource in data/config.yaml"

        for skill in skill_resources:
            assert skill.urls is not None
            normalized_name = self._normalize_name(skill.name)

            # Reuse production URI builder so this test verifies real runtime behavior.
            uri_map = build_skill_resource_uris(skill.urls, resource_name=skill.name)

            skill_main_urls = [url for url in skill.urls if url.endswith("SKILL.md")]
            assert skill_main_urls, f"Missing SKILL.md URL for skill '{skill.name}'"

            # Main skill file must always map to built-in FastMCP convention.
            expected_main_uri = f"skill://{normalized_name}/SKILL.md"
            assert uri_map[skill_main_urls[0]] == expected_main_uri

            for url, uri in uri_map.items():
                # Every mapped file must stay under the configured skill namespace.
                assert uri.startswith(f"skill://{normalized_name}/"), (
                    f"Skill URI '{uri}' does not follow configured name '{normalized_name}'"
                )
                assert url in skill.urls

            # Manifest URI convention expected from RemoteSkillProvider.
            expected_manifest_uri = f"skill://{normalized_name}/_manifest"
            assert expected_manifest_uri.startswith("skill://")

    def test_config_remote_prompts_name_and_uri_rules(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate all configured remote prompt entries map to expected URIs."""
        # Load from actual config to catch config-specific naming regressions.
        self._set_env_placeholders(monkeypatch)
        config = ConfigYaml.load_from_file(self._config_path())
        mcp_entries = config.mcp or []

        prompt_resources = [
            resource
            for mcp_config in mcp_entries
            for resource in mcp_config.get_prompt_remote_resources()
        ]

        assert prompt_resources, "Expected at least one remote prompt resource in data/config.yaml"

        for prompt in prompt_resources:
            assert prompt.url is not None
            normalized_name = self._normalize_name(prompt.name)

            uri = build_prompt_resource_uri(prompt.url, resource_name=prompt.name)

            # Prompt resources use a single identifier URI (no file suffix segment).
            assert uri == f"prompt://{normalized_name}"

    def test_config_remote_agents_name_and_uri_rules(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate all configured remote agent entries map to expected URIs."""
        # Validate agent URI behavior against the same source used in runtime.
        self._set_env_placeholders(monkeypatch)
        config = ConfigYaml.load_from_file(self._config_path())
        mcp_entries = config.mcp or []

        agent_resources = [
            resource
            for mcp_config in mcp_entries
            for resource in mcp_config.get_agent_remote_resources()
        ]

        assert agent_resources, "Expected at least one remote agent resource in data/config.yaml"

        for agent in agent_resources:
            assert agent.url is not None
            normalized_name = self._normalize_name(agent.name)

            uri = build_agent_resource_uri(agent.url, resource_name=agent.name)
            expected_uri = self._expected_agent_uri_from_name(agent.name)

            # Agent URIs must resolve to canonical .agent.md naming.
            assert uri == expected_uri
            assert uri.startswith("agent://")
            assert normalized_name.split("/")[-1].split(".")[0] in uri
