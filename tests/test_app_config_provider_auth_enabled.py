"""Tests for AppConfigProvider auth toggle behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from drunk_ai_proxy.app.app_config_provider import AppConfigProvider
from drunk_ai_proxy.auth.api_auth_provider import ApiKeyAuthProvider
from drunk_ai_proxy.utils import AuthType


def test_get_fast_mcp_auth_provider_returns_none_when_auth_disabled(
    monkeypatch,
) -> None:
    """Auth provider should be skipped when AUTH_ENABLED is false."""
    provider = AppConfigProvider.__new__(AppConfigProvider)

    get_auth_config = Mock(side_effect=AssertionError("Should not be called"))
    monkeypatch.setattr(provider, "_get_auth_config", get_auth_config)
    monkeypatch.setattr("drunk_ai_proxy.app.app_config_provider.AUTH_ENABLED", False)

    auth_provider = provider.get_fast_mcp_auth_provider()

    assert auth_provider is None
    get_auth_config.assert_not_called()


def test_get_fast_mcp_auth_provider_returns_basic_provider_when_enabled(
    monkeypatch,
) -> None:
    """Auth provider should be created when AUTH_ENABLED is true."""
    provider = AppConfigProvider.__new__(AppConfigProvider)

    get_auth_config = Mock(return_value=(AuthType.BASIC, {"token": "test-token"}))
    monkeypatch.setattr(provider, "_get_auth_config", get_auth_config)
    monkeypatch.setattr("drunk_ai_proxy.app.app_config_provider.AUTH_ENABLED", True)
    monkeypatch.setenv("FASTMCP_AUTH_ENABLED", "true")

    auth_provider = provider.get_fast_mcp_auth_provider()

    assert isinstance(auth_provider, ApiKeyAuthProvider)
    assert auth_provider.token == "test-token"
    get_auth_config.assert_called_once_with(None)


def test_get_fast_mcp_auth_provider_infers_enabled_when_default_provider_exists(
    monkeypatch,
) -> None:
    """Auth should be inferred on from config when env toggle is unset."""
    provider = AppConfigProvider.__new__(AppConfigProvider)
    provider._configs = SimpleNamespace(auth=SimpleNamespace(default_provider=AuthType.BASIC))

    get_auth_config = Mock(return_value=(AuthType.BASIC, {"token": "test-token"}))
    monkeypatch.setattr(provider, "_get_auth_config", get_auth_config)
    monkeypatch.setattr(provider, "_get_auth_provider_names", Mock(return_value=["basic"]))
    monkeypatch.setattr("drunk_ai_proxy.app.app_config_provider.AUTH_ENABLED", False)
    monkeypatch.delenv("FASTMCP_AUTH_ENABLED", raising=False)

    auth_provider = provider.get_fast_mcp_auth_provider()

    assert isinstance(auth_provider, ApiKeyAuthProvider)
    assert auth_provider.token == "test-token"
    get_auth_config.assert_called_once_with(None)


def test_get_fast_mcp_auth_provider_respects_explicit_env_false(
    monkeypatch,
) -> None:
    """Explicit FASTMCP_AUTH_ENABLED=false should keep auth disabled."""
    provider = AppConfigProvider.__new__(AppConfigProvider)
    provider._configs = SimpleNamespace(auth=SimpleNamespace(default_provider=AuthType.BASIC))

    get_auth_config = Mock(side_effect=AssertionError("Should not be called"))
    monkeypatch.setattr(provider, "_get_auth_config", get_auth_config)
    monkeypatch.setattr("drunk_ai_proxy.app.app_config_provider.AUTH_ENABLED", False)
    monkeypatch.setenv("FASTMCP_AUTH_ENABLED", "false")

    auth_provider = provider.get_fast_mcp_auth_provider()

    assert auth_provider is None
    get_auth_config.assert_not_called()
