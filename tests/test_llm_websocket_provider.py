"""Simplified tests for LlmWebSocketProvider - OpenAI WebSocket Mode Support.

This test suite covers:
- WebSocket provider initialization
- Model ID parsing (inherited from base class)
- Factory pattern for WebSocket connections
- Error response formatting
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock

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


class TestProviderCapabilities:
    """Tests for provider capability lookup and routing helpers."""

    def test_supports_native_websocket(self) -> None:
        """Test websocket capability from provider config."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
                websocket=True,
            ),
            LlmConfig(
                enabled=True,
                provider="ollama",
                base_url="http://localhost:11434/v1",
                websocket=False,
            ),
        ]
        provider = LlmWebSocketProvider(providers)

        assert provider._supports_native_websocket("openai") is True
        assert provider._supports_native_websocket("ollama") is False

    def test_build_fallback_payload_from_response_create(self) -> None:
        """Test transformation for OpenAI websocket response.create payloads."""
        payload = LlmWebSocketProvider._build_fallback_payload(
            {
                "type": "response.create",
                "response": {
                    "model": "openai_gpt-4o-mini",
                    "input": "Hello",
                },
            },
            model_name="gpt-4o-mini",
        )

        assert payload["model"] == "gpt-4o-mini"
        assert payload["input"] == "Hello"


class TestRouting:
    """Tests for backend route selection in websocket forwarding."""

    @pytest.mark.asyncio
    async def test_routes_to_native_backend_when_supported(self) -> None:
        """Use native websocket forwarding for websocket-enabled providers."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
                websocket=True,
            )
        ]
        provider = LlmWebSocketProvider(providers)
        websocket = AsyncMock()

        native_backend = AsyncMock()
        http_backend = AsyncMock()
        setattr(provider, "_forward_to_native_backend", native_backend)
        setattr(provider, "_forward_to_http_backend", http_backend)

        await provider._forward_to_backend(
            websocket=websocket,
            data={"model": "openai_gpt-4o"},
            client_id="client-1",
        )

        native_backend.assert_awaited_once()
        http_backend.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_routes_to_http_fallback_when_not_supported(self) -> None:
        """Use AsyncOpenAI fallback forwarding for non-websocket providers."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="ollama",
                base_url="http://localhost:11434/v1",
                websocket=False,
            )
        ]
        provider = LlmWebSocketProvider(providers)
        websocket = AsyncMock()

        native_backend = AsyncMock()
        http_backend = AsyncMock()
        setattr(provider, "_forward_to_native_backend", native_backend)
        setattr(provider, "_forward_to_http_backend", http_backend)

        await provider._forward_to_backend(
            websocket=websocket,
            data={"model": "ollama_llama3"},
            client_id="client-1",
        )

        http_backend.assert_awaited_once()
        native_backend.assert_not_awaited()
