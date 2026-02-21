"""
Tests for LLM configuration loading and validation.

This test suite covers the LlmConfig structure with list-based provider configurations:
- The root config is a JSON array of provider entries
- Configuration values support environment variable references
- Provider-specific fields are allowed
"""

import json
from pathlib import Path
from typing import Any

import pytest

from src.tools.llm_config import LlmConfig, LlmProviderConfig


class TestLlmConfigLoadFromFile:
    """Test LlmConfig.load_from_file() behavior."""

    def test_load_from_file_nonexistent(self) -> None:
        """Test loading from nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            LlmConfig.load_from_file("/nonexistent/path/llm.json")

    def test_load_from_file_empty_list(self, tmp_path: Path) -> None:
        """Test loading an empty provider list."""
        llm_file = tmp_path / "llm.json"
        llm_file.write_text("[]")

        config = LlmConfig.load_from_file(str(llm_file))
        assert config.providers == []

    def test_load_from_file_single_provider(self, tmp_path: Path) -> None:
        """Test loading a single provider config."""
        llm_file = tmp_path / "llm.json"
        data: list[dict[str, Any]] = [
            {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": "secret"
            }
        ]
        llm_file.write_text(json.dumps(data))

        config = LlmConfig.load_from_file(str(llm_file))
        assert len(config.providers) == 1
        assert isinstance(config.providers[0], LlmProviderConfig)
        assert config.providers[0].provider == "openrouter"

    def test_load_from_file_invalid_json(self, tmp_path: Path) -> None:
        """Test invalid JSON raises JSONDecodeError."""
        llm_file = tmp_path / "llm.json"
        llm_file.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            LlmConfig.load_from_file(str(llm_file))

    def test_load_from_file_not_list(self, tmp_path: Path) -> None:
        """Test loading file with JSON object instead of array raises ValueError."""
        llm_file = tmp_path / "llm.json"
        llm_file.write_text("{}")

        with pytest.raises(ValueError, match="must contain a JSON array"):
            LlmConfig.load_from_file(str(llm_file))

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Test missing required fields raises validation error."""
        llm_file = tmp_path / "llm.json"
        data: list[dict[str, Any]] = [
            {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1"
            }
        ]
        llm_file.write_text(json.dumps(data))

        with pytest.raises(ValueError):
            LlmConfig.load_from_file(str(llm_file))


class TestLlmConfigEnvironmentVariables:
    """Test environment variable resolution in LlmConfig."""

    def test_resolve_env_var_simple(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test resolving a simple environment variable."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "resolved-key")

        llm_file = tmp_path / "llm.json"
        data: list[dict[str, Any]] = [
            {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": "$OPENROUTER_API_KEY"
            }
        ]
        llm_file.write_text(json.dumps(data))

        config = LlmConfig.load_from_file(str(llm_file))
        assert config.providers[0].api_key == "resolved-key"

    def test_resolve_env_var_nested_extra_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test resolving env vars in nested extra fields."""
        monkeypatch.setenv("EXTRA_HEADER", "token-123")

        llm_file = tmp_path / "llm.json"
        data: list[dict[str, Any]] = [
            {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": "secret",
                "headers": {
                    "Authorization": "Bearer $EXTRA_HEADER"
                },
                "timeout": 30
            }
        ]
        llm_file.write_text(json.dumps(data))

        config = LlmConfig.load_from_file(str(llm_file))
        provider_dump = config.providers[0].model_dump()
        assert provider_dump["headers"]["Authorization"] == "Bearer token-123"
        assert provider_dump["timeout"] == 30

    def test_missing_env_var_raises_error(self, tmp_path: Path) -> None:
        """Test that missing environment variable raises ValueError."""
        llm_file = tmp_path / "llm.json"
        data: list[dict[str, Any]] = [
            {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": "$MISSING_VAR"
            }
        ]
        llm_file.write_text(json.dumps(data))

        with pytest.raises(ValueError, match="Environment variable"):
            LlmConfig.load_from_file(str(llm_file))
