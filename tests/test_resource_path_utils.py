"""Tests for the resource path utilities."""

from __future__ import annotations

from pathlib import Path

from drunk_ai_proxy.proxies.mcp.resource_path_utils import ResourcePathNamespaceResolver

get_root_namespace = ResourcePathNamespaceResolver.get_root_namespace


class TestGetRootNamespace:
    """Test suite for get_root_namespace utility function."""

    # String-based path tests
    def test_string_path_with_slash_returns_last_part(self) -> None:
        """Test that string paths with / return the last folder."""
        assert get_root_namespace("skills/dknet") == "dknet"
        assert get_root_namespace("agents/dknet") == "dknet"
        assert get_root_namespace("prompts/dotnet") == "dotnet"

    def test_string_reserved_keyword_alone_returns_none(self) -> None:
        """Test that reserved keywords alone return None."""
        assert get_root_namespace("skills") is None
        assert get_root_namespace("agents") is None
        assert get_root_namespace("prompts") is None

    def test_string_non_reserved_alone_returns_itself(self) -> None:
        """Test that non-reserved names alone return themselves."""
        assert get_root_namespace("dknet") == "dknet"
        assert get_root_namespace("custom-skills") == "custom-skills"
        assert get_root_namespace("my-namespace") == "my-namespace"

    def test_string_with_trailing_slash(self) -> None:
        """Test that trailing slashes are handled correctly."""
        assert get_root_namespace("skills/dknet/") == "dknet"
        assert get_root_namespace("agents/dknet/") == "dknet"

    def test_string_deep_path_returns_last_part(self) -> None:
        """Test that deep paths return only the last part."""
        assert get_root_namespace("skills/subfolder/dknet") == "dknet"
        assert get_root_namespace("a/b/c/d") == "d"

    # Path object tests
    def test_path_under_skills_returns_child(self) -> None:
        """Test that Path under skills/ returns the child folder."""
        # Simulate: /data/skills/dknet
        p = Path("/data/skills/dknet")
        assert get_root_namespace(p) == "dknet"

    def test_path_under_agents_returns_child(self) -> None:
        """Test that Path under agents/ returns the child folder."""
        p = Path("/data/agents/dknet")
        assert get_root_namespace(p) == "dknet"

    def test_path_under_prompts_returns_child(self) -> None:
        """Test that Path under prompts/ returns the child folder."""
        p = Path("/data/prompts/dotnet")
        assert get_root_namespace(p) == "dotnet"

    def test_path_not_under_reserved_returns_none(self) -> None:
        """Test that Path not under reserved keywords returns None."""
        p = Path("/data/custom/dknet")
        assert get_root_namespace(p) is None

    def test_path_reserved_alone_returns_none(self) -> None:
        """Test that Path to reserved keywords alone returns None."""
        assert get_root_namespace(Path("/data/skills")) is None
        assert get_root_namespace(Path("/data/agents")) is None
        assert get_root_namespace(Path("/data/prompts")) is None

    def test_path_deep_under_reserved_returns_first_child(self) -> None:
        """Test that deep paths return first child of reserved folder."""
        # For /data/skills/dknet/subfolder, should return dknet
        p = Path("/data/skills/dknet/subfolder")
        assert get_root_namespace(p) == "dknet"

    def test_path_relative_paths(self) -> None:
        """Test that relative Path objects work correctly."""
        p = Path("skills/dknet")
        assert get_root_namespace(p) == "dknet"

        p = Path("agents/dknet")
        assert get_root_namespace(p) == "dknet"

        p = Path("dknet")
        assert get_root_namespace(p) is None  # Not under reserved keyword
