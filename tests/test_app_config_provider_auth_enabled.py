"""Tests for AppConfigProvider auth toggle behavior."""

from __future__ import annotations

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
    monkeypatch.setattr(provider, "get_auth_config", get_auth_config)
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
    monkeypatch.setattr(provider, "get_auth_config", get_auth_config)
    monkeypatch.setattr("drunk_ai_proxy.app.app_config_provider.AUTH_ENABLED", True)

    auth_provider = provider.get_fast_mcp_auth_provider()

    assert isinstance(auth_provider, ApiKeyAuthProvider)
    assert auth_provider.token == "test-token"
    get_auth_config.assert_called_once_with(None)
