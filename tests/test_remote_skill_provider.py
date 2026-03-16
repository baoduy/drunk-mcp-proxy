"""Tests for RemoteSkillProvider manifest URI naming behavior."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from drunk_ai_proxy.proxies.mcp.remote_skill_provider import RemoteSkillProvider
from drunk_ai_proxy.utils.config_yaml import OnDemandRemoteResourceConfig


class TestRemoteSkillProviderManifestNaming:
    """Manifest URI should preserve full configured skill name."""

    @pytest.mark.asyncio
    async def test_list_resources_preserves_namespaced_skill_main_uri(self) -> None:
        """Listed resource URIs should include full namespaced skill name."""
        config = OnDemandRemoteResourceConfig(
            name="dotnet/ef-core",
            urls=[
                "https://example.com/skills/dotnet/ef-core/SKILL.md",
                "https://example.com/skills/dotnet/ef-core/query-plan.md",
            ],
        )

        provider = RemoteSkillProvider(
            config=config,
            cache=Mock(),
            http_client=Mock(spec=httpx.AsyncClient),
        )

        resources = await provider.list_resources()
        uris = {str(resource.uri) for resource in resources}

        assert "skill://dotnet/ef-core/SKILL.md" in uris

    @pytest.mark.asyncio
    async def test_manifest_uri_uses_full_namespaced_skill_name(self) -> None:
        """Manifest URI should be skill://<full-name>/_manifest."""
        config = OnDemandRemoteResourceConfig(
            name="dotnet/ef-core",
            urls=[
                "https://example.com/skills/dotnet/ef-core/SKILL.md",
                "https://example.com/skills/dotnet/ef-core/query-plan.md",
            ],
        )

        provider = RemoteSkillProvider(
            config=config,
            cache=Mock(),
            http_client=Mock(spec=httpx.AsyncClient),
        )

        resources = await provider.list_resources()
        uris = {str(resource.uri) for resource in resources}

        assert "skill://dotnet/ef-core/_manifest" in uris
