"""Tests for LlmWebSocketProvider - OpenAI WebSocket Mode Support.

This test suite covers:
- WebSocket connection establishment and authentication
- Message processing (response.create events)
- Model routing and provider validation
- Response caching and continuation
- Timeout handling
- Error cases (invalid tokens, missing models, etc.)
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta

from proxies.llm_websocket_provider import (
    LlmWebSocketProvider,
    ConnectionState,
    ResponseState,
)
from tools import LlmConfig


class TestResponseState:
    """Tests for ResponseState class."""

    def test_init(self) -> None:
        """Test ResponseState initialization."""
        response_id = "resp_123"
        model = "openai_gpt4"
        input_context = [{"type": "message", "content": "test"}]
        tools = [{"name": "tool1"}]

        state = ResponseState(response_id, model, input_context, tools)

        assert state.response_id == response_id
        assert state.model == model
        assert state.input_context == input_context
        assert state.tools == tools
        assert isinstance(state.created_at, datetime)


class TestConnectionState:
    """Tests for ConnectionState class."""

    def test_init(self) -> None:
        """Test ConnectionState initialization."""
        state = ConnectionState(connection_timeout_minutes=60)

        assert state.response_cache == {}
        assert state.backend_clients == {}
        assert isinstance(state.connection_time, datetime)
        assert state.connection_timeout_minutes == 60

    def test_cache_response(self) -> None:
        """Test caching a response - keeps only most recent."""
        state = ConnectionState()

        response1 = ResponseState("resp_1", "model1", [], [])
        response2 = ResponseState("resp_2", "model2", [], [])

        state.cache_response(response1)
        assert "resp_1" in state.response_cache

        # Caching new response clears old ones
        state.cache_response(response2)
        assert "resp_1" not in state.response_cache
        assert "resp_2" in state.response_cache

    def test_get_response(self) -> None:
        """Test retrieving cached response."""
        state = ConnectionState()
        response = ResponseState("resp_123", "model1", [], [])
        state.cache_response(response)

        retrieved = state.get_response("resp_123")
        assert retrieved == response

        not_found = state.get_response("nonexistent")
        assert not_found is None

    def test_evict_response(self) -> None:
        """Test evicting response from cache."""
        state = ConnectionState()
        response = ResponseState("resp_123", "model1", [], [])
        state.cache_response(response)

        state.evict_response("resp_123")
        assert state.get_response("resp_123") is None

    def test_is_expired_false(self) -> None:
        """Test is_expired returns False for recent connection."""
        state = ConnectionState(connection_timeout_minutes=60)
        assert state.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Test is_expired returns True for old connection."""
        state = ConnectionState(connection_timeout_minutes=1)
        # Set connection time to far past
        state.connection_time = datetime.now() - timedelta(minutes=2)
        assert state.is_expired() is True


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
        assert provider.connection_timeout_minutes == 60

    def test_init_without_providers(self) -> None:
        """Test initialization fails without providers."""
        with pytest.raises(ValueError, match="requires at least one provider"):
            LlmWebSocketProvider([])

    def test_init_custom_timeout(self) -> None:
        """Test initialization with custom timeout."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]

        provider = LlmWebSocketProvider(providers, connection_timeout_minutes=30)
        assert provider.connection_timeout_minutes == 30


class TestParseModelId:
    """Tests for model ID parsing."""

    def test_parse_valid_model_id(self) -> None:
        """Test parsing valid model ID."""
        provider_name, model_name = LlmWebSocketProvider._parse_model_id("openai_gpt4")
        assert provider_name == "openai"
        assert model_name == "gpt4"

    def test_parse_model_id_with_underscores(self) -> None:
        """Test parsing model ID with underscores in model name."""
        provider_name, model_name = LlmWebSocketProvider._parse_model_id("openai_gpt_4_turbo")
        assert provider_name == "openai"
        assert model_name == "gpt_4_turbo"

    def test_parse_invalid_model_id(self) -> None:
        """Test parsing invalid model ID (no underscore)."""
        provider_name, model_name = LlmWebSocketProvider._parse_model_id("gpt4")
        assert provider_name == ""
        assert model_name == "gpt4"


class TestToDict:
    """Tests for _to_dict helper."""

    def test_dict_input(self) -> None:
        """Test converting dict to dict."""
        data = {"key": "value"}
        result = LlmWebSocketProvider._to_dict(data)
        assert result == data

    def test_pydantic_model(self) -> None:
        """Test converting Pydantic model."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        result = LlmWebSocketProvider._to_dict(model)

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_generic_object(self) -> None:
        """Test converting generic object."""

        class TestObject:
            def __init__(self) -> None:
                self.attr = "value"

        obj = TestObject()
        result = LlmWebSocketProvider._to_dict(obj)

        assert isinstance(result, dict)
        assert result["attr"] == "value"


class TestExtractBearerToken:
    """Tests for bearer token extraction."""

    def test_extract_valid_token(self) -> None:
        """Test extracting valid bearer token."""
        websocket = MagicMock()
        websocket.headers = {"authorization": "Bearer token123"}

        token = LlmWebSocketProvider._extract_bearer_token(websocket)
        assert token == "token123"

    def test_extract_token_case_insensitive(self) -> None:
        """Test token extraction is case insensitive for header name."""
        websocket = MagicMock()
        websocket.headers = {"Authorization": "Bearer token123"}

        token = LlmWebSocketProvider._extract_bearer_token(websocket)
        assert token == "token123"

    def test_extract_no_token(self) -> None:
        """Test extraction when no authorization header."""
        websocket = MagicMock()
        websocket.headers = {}

        token = LlmWebSocketProvider._extract_bearer_token(websocket)
        assert token is None

    def test_extract_invalid_scheme(self) -> None:
        """Test extraction with invalid scheme."""
        websocket = MagicMock()
        websocket.headers = {"authorization": "Basic dGVzdDp0ZXN0"}

        token = LlmWebSocketProvider._extract_bearer_token(websocket)
        assert token is None

    def test_extract_malformed_header(self) -> None:
        """Test extraction with malformed header."""
        websocket = MagicMock()
        websocket.headers = {"authorization": "InvalidFormat"}

        token = LlmWebSocketProvider._extract_bearer_token(websocket)
        assert token is None


@pytest.mark.asyncio
class TestValidateToken:
    """Tests for token validation."""

    async def test_validate_token_no_token(self) -> None:
        """Test validation fails without token."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        result = await provider._validate_token(None)
        assert result is False

    @patch("proxies.llm_websocket_provider.AppConfigProvider.get_instance")
    async def test_validate_token_auth_disabled(self, mock_config: Mock) -> None:
        """Test validation succeeds when auth is disabled."""
        mock_instance = MagicMock()
        mock_instance.get_fast_mcp_auth_provider.return_value = None
        mock_config.return_value = mock_instance

        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        result = await provider._validate_token("any_token")
        assert result is True

    @patch("proxies.llm_websocket_provider.AppConfigProvider.get_instance")
    async def test_validate_token_invalid(self, mock_config: Mock) -> None:
        """Test validation fails with invalid token."""
        mock_auth = AsyncMock()
        mock_auth.verify_token.return_value = None
        mock_instance = MagicMock()
        mock_instance.get_fast_mcp_auth_provider.return_value = mock_auth
        mock_config.return_value = mock_instance

        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        result = await provider._validate_token("invalid_token")
        assert result is False

    @patch("proxies.llm_websocket_provider.AppConfigProvider.get_instance")
    async def test_validate_token_valid_with_claims(self, mock_config: Mock) -> None:
        """Test validation succeeds with valid token containing claims."""
        mock_result = MagicMock()
        mock_result.claims = {"sub": "user123"}
        mock_result.scopes = []
        mock_auth = AsyncMock()
        mock_auth.verify_token.return_value = mock_result
        mock_instance = MagicMock()
        mock_instance.get_fast_mcp_auth_provider.return_value = mock_auth
        mock_config.return_value = mock_instance

        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        result = await provider._validate_token("valid_token")
        assert result is True
        mock_auth.verify_token.assert_called_once_with("valid_token")

    @patch("proxies.llm_websocket_provider.AppConfigProvider.get_instance")
    async def test_validate_token_valid_with_scopes(self, mock_config: Mock) -> None:
        """Test validation succeeds with valid token containing scopes."""
        mock_result = MagicMock()
        mock_result.claims = {}
        mock_result.scopes = ["read", "write"]
        mock_auth = AsyncMock()
        mock_auth.verify_token.return_value = mock_result
        mock_instance = MagicMock()
        mock_instance.get_fast_mcp_auth_provider.return_value = mock_auth
        mock_config.return_value = mock_instance

        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        result = await provider._validate_token("valid_token")
        assert result is True

    @patch("proxies.llm_websocket_provider.AppConfigProvider.get_instance")
    async def test_validate_token_empty_claims_and_scopes(self, mock_config: Mock) -> None:
        """Test validation fails with empty claims and scopes."""
        mock_result = MagicMock()
        mock_result.claims = {}
        mock_result.scopes = []
        mock_auth = AsyncMock()
        mock_auth.verify_token.return_value = mock_result
        mock_instance = MagicMock()
        mock_instance.get_fast_mcp_auth_provider.return_value = mock_auth
        mock_config.return_value = mock_instance

        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        result = await provider._validate_token("token_with_empty_data")
        assert result is False

    @patch("proxies.llm_websocket_provider.AppConfigProvider.get_instance")
    async def test_validate_token_exception(self, mock_config: Mock) -> None:
        """Test validation fails gracefully on exception."""
        mock_auth = AsyncMock()
        mock_auth.verify_token.side_effect = Exception("Auth error")
        mock_instance = MagicMock()
        mock_instance.get_fast_mcp_auth_provider.return_value = mock_auth
        mock_config.return_value = mock_instance

        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        result = await provider._validate_token("any_token")
        assert result is False


class TestGetOpenAIClient:
    """Tests for _get_openai_client (Auth 2: Proxy -> Service)."""

    def test_get_openai_client_creates_new(self) -> None:
        """Test creating new OpenAI client with API key from provider config."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test-key-123",
            )
        ]
        provider = LlmWebSocketProvider(providers)
        connection_state = ConnectionState()

        with patch.object(provider.open_ai_factory, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = provider._get_openai_client("openai", connection_state)

            # Should call factory which injects API key from provider config
            mock_get_client.assert_called_once_with("openai")
            assert result is mock_client
            # Should cache in connection state
            assert connection_state.backend_clients["openai"] is mock_client

    def test_get_openai_client_uses_cache(self) -> None:
        """Test reusing cached OpenAI client."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)
        connection_state = ConnectionState()

        # Pre-populate cache
        cached_client = MagicMock()
        connection_state.backend_clients["openai"] = cached_client

        with patch.object(provider.open_ai_factory, "get_client") as mock_get_client:
            result = provider._get_openai_client("openai", connection_state)

            # Should use cache, not call factory
            mock_get_client.assert_not_called()
            assert result is cached_client

    def test_get_openai_client_invalid_provider(self) -> None:
        """Test error when provider not found."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)
        connection_state = ConnectionState()

        with patch.object(
            provider.open_ai_factory, "get_client", side_effect=ValueError("Provider 'invalid' not found")
        ):
            with pytest.raises(ValueError, match="Provider 'invalid' not found"):
                provider._get_openai_client("invalid", connection_state)


class TestIsConfiguredProvider:
    """Tests for _is_configured_provider."""

    def test_is_configured_provider_true(self) -> None:
        """Test provider is configured."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        assert provider._is_configured_provider("openai") is True

    def test_is_configured_provider_false(self) -> None:
        """Test provider is not configured."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        assert provider._is_configured_provider("nonexistent") is False


class TestMountAndFastApiApp:
    """Tests for mounting and FastAPI app creation."""

    def test_get_fastapi_app(self) -> None:
        """Test FastAPI app creation."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        app = provider._get_fastapi_app()

        assert app is not None
        # Note: title comes from SERVER_NAME environment variable
        assert app.title is not None
    def test_get_fastapi_app_cached(self) -> None:
        """Test FastAPI app is cached."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        app1 = provider._get_fastapi_app()
        app2 = provider._get_fastapi_app()

        assert app1 is app2

    def test_mount(self) -> None:
        """Test mounting provider to Starlette app."""
        from starlette.applications import Starlette

        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        app = Starlette()
        provider.mount(app, route_prefix="/api/v1")

        # Verify mount was called (app now has sub-app)
        assert len(app.routes) > 0


class TestProcessMessage:
    """Tests for message processing."""

    @pytest.mark.asyncio
    async def test_process_invalid_type(self) -> None:
        """Test processing message with invalid type."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        websocket = AsyncMock()
        connection_state = ConnectionState()

        data = {"type": "invalid.type"}

        await provider._process_message(websocket, data, connection_state)

        # Should send error
        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["error"]["code"] == "invalid_request"


class TestCreateResponse:
    """Tests for response.create handling."""

    @pytest.mark.asyncio
    async def test_create_response_missing_model(self) -> None:
        """Test response.create without model."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        websocket = AsyncMock()
        connection_state = ConnectionState()

        data = {"type": "response.create"}

        await provider._create_response(websocket, data, connection_state)

        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert "Model is required" in call_args["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_response_invalid_model_id(self) -> None:
        """Test response.create with invalid model ID."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        websocket = AsyncMock()
        connection_state = ConnectionState()

        data = {"type": "response.create", "model": "invalid_model"}

        await provider._create_response(websocket, data, connection_state)

        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert "Invalid model ID format" in call_args["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_response_previous_not_found(self) -> None:
        """Test response.create with nonexistent previous_response_id."""
        providers = [
            LlmConfig(
                enabled=True,
                provider="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        ]
        provider = LlmWebSocketProvider(providers)

        websocket = AsyncMock()
        connection_state = ConnectionState()

        data = {
            "type": "response.create",
            "model": "openai_gpt4",
            "previous_response_id": "nonexistent",
        }

        await provider._create_response(websocket, data, connection_state)

        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["error"]["code"] == "previous_response_not_found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
