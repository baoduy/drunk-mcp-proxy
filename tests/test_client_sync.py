"""Tests for Drunk AI Client configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from drunk_ai_client.main import ClientConfig


ENV_KEYS = [
    "API_URL",
    "API_KEY",
    "SKILL_DIR",
    "AGENTS_DIR",
    "ALLOWS_OVERWRITE",
    "SYNC_ENABLED",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure every test starts with a clean client-related environment."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _set_plain_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent pytest CLI args from being parsed by ClientConfig.from_env."""
    monkeypatch.setattr("sys.argv", ["client.py"])


def test_from_env_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loads required URL from env and applies defaults."""
    _set_plain_argv(monkeypatch)
    monkeypatch.setenv("API_URL", "https://example.com/mcp")

    config = ClientConfig.from_env()

    assert config.url == "https://example.com/mcp"
    assert config.api_key is None
    assert config.skill_dir is None
    assert config.agents_dir is None
    assert config.allows_overwrite is False
    assert config.sync_enabled is True


def test_from_env_with_cli_args_override_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI args override URL/API key while directory env values are still used."""
    skill_dir = tmp_path / "skills"
    agents_dir = tmp_path / "agents"

    monkeypatch.setenv("API_URL", "https://env.com/mcp")
    monkeypatch.setenv("API_KEY", "env-token")
    monkeypatch.setenv("SKILL_DIR", str(skill_dir))
    monkeypatch.setenv("AGENTS_DIR", str(agents_dir))
    monkeypatch.setenv("ALLOWS_OVERWRITE", "true")
    monkeypatch.setenv("SYNC_ENABLED", "false")
    monkeypatch.setattr(
        "sys.argv",
        ["client.py", "--url", "https://cli.com/mcp", "--api-key", "cli-token"],
    )

    config = ClientConfig.from_env()

    assert config.url == "https://cli.com/mcp"
    assert config.api_key == "cli-token"
    assert config.skill_dir == skill_dir
    assert config.agents_dir == agents_dir
    assert config.allows_overwrite is True
    assert config.sync_enabled is False
    assert skill_dir.exists()
    assert agents_dir.exists()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("invalid", False),
    ],
)
def test_from_env_allows_overwrite_parsing(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    expected: bool,
) -> None:
    """Parses ALLOWS_OVERWRITE with expected defaults for invalid values."""
    _set_plain_argv(monkeypatch)
    monkeypatch.setenv("API_URL", "https://example.com/mcp")
    monkeypatch.setenv("ALLOWS_OVERWRITE", value)

    config = ClientConfig.from_env()
    assert config.allows_overwrite is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("invalid", True),
    ],
)
def test_from_env_sync_enabled_parsing(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    expected: bool,
) -> None:
    """Parses SYNC_ENABLED with default-true behavior for invalid values."""
    _set_plain_argv(monkeypatch)
    monkeypatch.setenv("API_URL", "https://example.com/mcp")
    monkeypatch.setenv("SYNC_ENABLED", value)

    config = ClientConfig.from_env()
    assert config.sync_enabled is expected


def test_from_env_missing_url_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raises ValueError when URL is missing from both CLI and environment."""
    _set_plain_argv(monkeypatch)

    with pytest.raises(
        ValueError,
        match="API_URL environment variable or --url argument required",
    ):
        ClientConfig.from_env()


def test_from_env_invalid_url_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raises ValueError when URL is not http/https with host."""
    _set_plain_argv(monkeypatch)
    monkeypatch.setenv("API_URL", "invalid-url")

    with pytest.raises(ValueError, match="Invalid URL"):
        ClientConfig.from_env()
