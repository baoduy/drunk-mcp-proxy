"""Simplified tests for LlmWebSocketProvider - OpenAI WebSocket Mode Support.

This test suite covers:
- WebSocket provider initialization
- Model ID parsing (inherited from base class)
- Factory pattern for WebSocket connections
- Error response formatting
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from proxies.llm_websocket_provider import (
    LlmWebSocketProvider,
    WebSocketFactory,
)
from tools import LlmConfig


class TestLlmWebSocketProviderInit:
    """Tests for LlmWebSocketProvider initialization."""

    def test_init_with_providers(self) -> None:
        """Test initialization with valid providers."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]

        provider = LlmWebSocketProvider(providers)
        assert provider.providers == providers
        assert hasattr(provider, 'ws_factory')

    def test_init_without_providers(self) -> None:
        """Test initialization fails without providers."""
        with pytest.raises(ValueError, match="requires at least one provider"):
            LlmWebSocketProvider([])


class TestParseModelId:
    """Tests for model ID parsing (inherited from base class)."""

    def test_parse_valid_model_id(self) -> None:
        """Test parsing valid model ID."""
        provider_name, model_name = LlmWebSocketProvider.parse_model_id("openai_gpt4")
        assert provider_name == "openai"
        assert model_name == "gpt4"

    def test_parse_model_id_with_underscores(self) -> None:
        """Test parsing model ID with underscores in model name."""
        provider_name, model_name = LlmWebSocketProvider.parse_model_id("openai_gpt_4_turbo")
        assert provider_name == "openai"
        assert model_name == "gpt_4_turbo"

    def test_parse_invalid_model_id(self) -> None:
        """Test parsing invalid model ID (no underscore)."""
        provider_name, model_name = LlmWebSocketProvider.parse_model_id("gpt4")
        assert provider_name == ""
        assert model_name == "gpt4"


class TestWebSocketFactory:
    """Tests for WebSocketFactory class."""

    def test_factory_init(self) -> None:
        """Test factory initialization."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        
        factory = WebSocketFactory(providers)
        assert factory._provider_configs["openai"] == providers[0]


class TestMount:
    """Tests for mount method."""

    def test_mount_stub(self) -> None:
        """Test mount method exists as stub."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)
        
        # Mount should exist and not raise
        from starlette.applications import Starlette
        app = Starlette()
        provider.mount(app, "/api/v1")  # Should not raise


class TestCreateError:
    """Tests for create_error static method."""

    def test_create_error_default_status(self) -> None:
        """Test creating error with default status."""
        error = LlmWebSocketProvider.create_error("test_code", "Test message")
        
        assert error["type"] == "error"
        assert error["error"]["type"] == "llm_websocket_request_error"
        assert error["error"]["code"] == "test_code"
        assert error["error"]["message"] == "Test message"
        assert error["status"] == 400

    def test_create_error_custom_status(self) -> None:
        """Test creating error with custom status."""
        error = LlmWebSocketProvider.create_error("auth_error", "Unauthorized", status=401)
        
        assert error["type"] == "error"
        assert error["status"] == 401
