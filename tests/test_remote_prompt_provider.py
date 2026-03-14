"""Tests for RemotePromptProvider registration behavior."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest
from fastmcp import FastMCP

from drunk_ai_proxy.proxies.prompt.remote_prompt_provider import (
    RemotePromptProvider,
    _parse_template_from_content,  # pyright: ignore[reportPrivateUsage]
)
from drunk_ai_proxy.utils.config_yaml import (
    McpConfig,
    McpResourceConfig,
    OnDemandRemoteResourceConfig,
    SpecType,
)


class TestRemotePromptProviderRegistration:
    """Regression tests for remote prompt registration and listing."""

    @pytest.mark.asyncio
    async def test_register_to_mcp_lists_remote_prompt(self) -> None:
        """Remote prompt registration should succeed and appear in prompt listing."""
        config = McpConfig(
            path="/resources",
            spec_type=SpecType.MCP,
            prompts=McpResourceConfig(
                remote_resources=[
                    OnDemandRemoteResourceConfig(
                        name="quick-reference",
                        url="https://example.com/quick-reference.md",
                    )
                ]
            ),
        )
        remote_config = config.get_prompt_remote_resources()[0]

        provider = RemotePromptProvider(
            config=config,
            remote_config=remote_config,
            cache=Mock(),
            http_client=Mock(spec=httpx.AsyncClient),
        )
        mcp = FastMCP("test")

        provider.register_to_mcp(mcp)
        prompts = await mcp.list_prompts(run_middleware=False)

        assert len(prompts) == 1
        assert prompts[0].name == "quick-reference"


class TestRemotePromptProviderParsing:
    """Tests for remote prompt markdown content parsing behavior."""

    def test_parse_template_from_content_with_frontmatter(self) -> None:
        """Parse prompt template metadata from YAML frontmatter content."""
        content = """---
description: Quick reference
parameters:
  topic: str
---
Use {topic}."""

        template = _parse_template_from_content(
            name="quick-reference",
            content=content,
            source="https://example.com/quick-reference.md",
        )

        assert template.description == "Quick reference"
        assert template.parameters == {"topic": str}

    def test_parse_template_from_content_without_frontmatter_falls_back_to_plain_markdown(self) -> None:
        """Fallback to raw markdown prompt when remote file has no YAML frontmatter."""
        content = "# Quick reference\nUse {language}."

        template = _parse_template_from_content(
            name="quick-reference",
            content=content,
            source="https://example.com/quick-reference.md",
        )

        assert template.description == "Prompt template 'quick-reference'"
        assert template.parameters == {}
        assert template.render() == content
