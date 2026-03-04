"""
Tests for LlmProxiesProvider Starlette app.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from fastapi.responses import JSONResponse

from drunk_ai_proxy.proxies.llm_proxies_provider import (
    AsyncOpenAIFactory,
    LlmModel,
    LlmProxiesProvider,
)
from drunk_ai_proxy.tools.config_yaml import LlmConfig


def _build_provider() -> LlmProxiesProvider:
    # TODO: Mock this provider for testing instead of using a real config
    provider_config = LlmConfig.model_validate(
        {
            "provider": "openrouter",
            "base_url": "https://example.com/api/v1",
            "api_key": "test-key",
        }
    )
    return LlmProxiesProvider(providers=[provider_config])


def _build_app(provider: LlmProxiesProvider) -> Starlette:
    app = Starlette()
    # Patch the correct import path used in src/proxies/llm_proxies_provider.py
    with patch(
        "drunk_ai_proxy.proxies.llm_proxies_provider.AppConfigProvider.get_instance"
    ) as mock_get_app_config:
        mock_app_config = Mock()
        mock_app_config.get_fast_mcp_auth_provider.return_value = None
        mock_get_app_config.return_value = mock_app_config
        provider.mount(app, route_prefix="/llm/v1")
    return app


def test_chat_completions_requires_messages() -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/chat/completions", json={"model": "openrouter_test"}
    )
    assert response.status_code == 400
    error_msg = response.json()["error"]["message"]
    assert "messages" in error_msg


def test_chat_completions_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response_payload = {
        "id": "gen-1",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
    }

    class FakeChatCompletions:
        async def create(self, **_: Any) -> dict[str, Any]:
            return response_payload

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/chat/completions",
        json={
            "model": "openrouter_test",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "ok"


def test_embeddings_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response_payload = {
        "data": [
            {
                "object": "embedding",
                "index": 0,
                "embedding": [0.1, 0.2],
            }
        ]
    }

    class FakeEmbeddings:
        async def create(self, **_: Any) -> dict[str, Any]:
            return response_payload

    class FakeClient:
        embeddings = FakeEmbeddings()

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/embeddings",
        json={
            "model": "openrouter_test",
            "input": "hello",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["embedding"] == [0.1, 0.2]


def test_models_aggregates(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    async def fake_get_all_models(*_: Any, **__: Any) -> list[LlmModel]:
        return [
            LlmModel(id="openrouter_test", provider="openrouter"),
            LlmModel(id="openrouter_test-2", provider="openrouter"),
        ]

    monkeypatch.setattr(provider, "_get_all_models", fake_get_all_models)

    response = client.get("/llm/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert {item["id"] for item in body["data"]} == {
        "openrouter_test",
        "openrouter_test-2",
    }


def test_providers_returns_all_providers() -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.get("/llm/v1/providers")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "openrouter"
    assert body["data"][0]["slug"] == "openrouter"


# Test AsyncOpenAIFactory
def test_async_openai_factory_get_client():
    """Test AsyncOpenAIFactory caching and client creation."""
    provider1 = LlmConfig.model_validate(
        {
            "provider": "openrouter",
            "base_url": "https://example.com/api/v1",
            "api_key": "test-key-1",
        }
    )
    provider2 = LlmConfig.model_validate(
        {
            "provider": "anthropic",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": "test-key-2",
        }
    )

    factory = AsyncOpenAIFactory([provider1, provider2])

    # Get client for provider1 - should create new
    client1 = factory.get_client("openrouter")
    assert client1 is not None

    # Get client for provider1 again - should return cached
    client1_cached = factory.get_client("openrouter")
    assert client1 is client1_cached

    # Get client for provider2 - should create new
    client2 = factory.get_client("anthropic")
    assert client2 is not None
    assert client2 is not client1


def test_async_openai_factory_provider_not_found():
    """Test AsyncOpenAIFactory raises error for unknown provider."""
    provider = LlmConfig.model_validate(
        {
            "provider": "openrouter",
            "base_url": "https://example.com/api/v1",
            "api_key": "test-key",
        }
    )

    factory = AsyncOpenAIFactory([provider])

    with pytest.raises(ValueError, match="Provider 'unknown' not found"):
        factory.get_client("unknown")


# Test LlmProxiesProvider initialization
def test_llm_proxies_provider_with_providers():
    """Test LlmProxiesProvider initialization with providers list."""
    provider_config = LlmConfig.model_validate(
        {
            "provider": "openrouter",
            "base_url": "https://example.com/api/v1",
            "api_key": "test-key",
        }
    )

    provider = LlmProxiesProvider(providers=[provider_config])
    assert provider.providers == [provider_config]
    assert provider.open_ai_factory is not None




# Test model ID parsing
def test_parse_model_id_with_provider():
    """Test parse_model_id with provider_model format."""
    provider_name, model_name = LlmProxiesProvider.parse_model_id("openrouter_gpt-4")
    assert provider_name == "openrouter"
    assert model_name == "gpt-4"


def test_parse_model_id_without_provider():
    """Test parse_model_id with just model name."""
    provider_name, model_name = LlmProxiesProvider.parse_model_id("gpt-4")
    assert provider_name == ""
    assert model_name == "gpt-4"


# Test extract_and_validate_model method
def test_extract_and_validate_model_success():
    """Test extract_and_validate_model with valid model_id."""
    provider = _build_provider()
    source = {"model": "openrouter_gpt-4"}

    result = provider.extract_and_validate_model(source)

    assert isinstance(result, tuple)
    assert result == ("openrouter", "gpt-4")


def test_extract_and_validate_model_missing_model():
    """Test extract_and_validate_model with missing model key."""
    provider = _build_provider()
    source = {"input": "test"}

    result = provider.extract_and_validate_model(source)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert "Model ID is required" in result.body.decode()


def test_extract_and_validate_model_invalid_format():
    """Test extract_and_validate_model with invalid model format (no underscore)."""
    provider = _build_provider()
    source = {"model": "invalidformat"}

    result = provider.extract_and_validate_model(source)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert "Invalid model ID format" in result.body.decode()


def test_split_params_separates_known_and_extra():
    """Test _split_params correctly separates known and unknown parameters."""
    body = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.7,
        "custom_param": "value",
        "another_unknown": 123,
    }
    known_params = {"model", "messages", "temperature"}

    result_known, result_extra = LlmProxiesProvider._split_params(body, known_params)

    assert result_known == {"model": "gpt-4", "messages": [{"role": "user", "content": "hello"}], "temperature": 0.7}
    assert result_extra == {"custom_param": "value", "another_unknown": 123}


def test_split_params_returns_none_extra_when_all_known():
    """Test _split_params returns None for extra_body when all params are known."""
    body = {"model": "gpt-4", "temperature": 0.5}
    known_params = {"model", "temperature"}

    result_known, result_extra = LlmProxiesProvider._split_params(body, known_params)

    assert result_known == {"model": "gpt-4", "temperature": 0.5}
    assert result_extra is None


# Test _to_dict conversion
def test_to_dict_with_dict():
    """Test _to_dict with a dict input."""
    input_dict = {"key": "value"}
    result = LlmProxiesProvider._to_dict(input_dict)
    assert result == input_dict


def test_to_dict_with_pydantic_model():
    """Test _to_dict with a Pydantic model."""
    model = LlmModel(id="test-id", provider="test-provider")
    result = LlmProxiesProvider._to_dict(model)
    assert result["id"] == "test-id"
    assert result["provider"] == "test-provider"


def test_to_dict_with_object():
    """Test _to_dict with a regular object."""

    class TestObj:
        def __init__(self):
            self.field = "value"

    obj = TestObj()
    result = LlmProxiesProvider._to_dict(obj)
    assert result["field"] == "value"


# Test streaming response
@pytest.mark.asyncio
async def test_format_response_non_streaming():
    """Test _format_response for non-streaming responses."""
    response_data = {"id": "test", "object": "chat.completion"}
    result = await LlmProxiesProvider._format_response(
        response_data, is_streaming=False
    )

    assert result.status_code == 200
    assert result.body == b'{"id":"test","object":"chat.completion"}'


@pytest.mark.asyncio
async def test_format_response_streaming():
    """Test _format_response for streaming responses."""

    async def mock_stream():
        yield {"id": "chunk1", "object": "chat.completion.chunk"}
        yield {"id": "chunk2", "object": "chat.completion.chunk"}

    class MockStreamResponse:
        def __aiter__(self):
            return mock_stream()

    result = await LlmProxiesProvider._format_response(
        MockStreamResponse(), is_streaming=True
    )

    assert result.status_code == 200
    assert result.media_type == "text/event-stream"


# Test endpoint errors
def test_chat_completions_missing_model():
    """Test chat completions endpoint with missing model."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post("/llm/v1/chat/completions", json={"messages": []})
    assert response.status_code == 400
    assert "Model ID is required" in response.json()["error"]


def test_chat_completions_invalid_model_format():
    """Test chat completions endpoint with invalid model format."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/chat/completions", json={"model": "invalidformat", "messages": []}
    )
    assert response.status_code == 400
    assert "Invalid model ID format" in response.json()["error"]


def test_embeddings_missing_model():
    """Test embeddings endpoint with missing model."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post("/llm/v1/embeddings", json={"input": "test"})
    assert response.status_code == 400
    assert "Model ID is required" in response.json()["error"]


def test_embeddings_invalid_model_format():
    """Test embeddings endpoint with invalid model format."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/embeddings", json={"model": "invalidformat", "input": "test"}
    )
    assert response.status_code == 400
    assert "Invalid model ID format" in response.json()["error"]


def test_embeddings_error_handling(monkeypatch: pytest.MonkeyPatch):
    """Test embeddings endpoint error handling."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    class FakeEmbeddings:
        async def create(self, **_: Any):
            raise Exception("Test error")

    class FakeClient:
        embeddings = FakeEmbeddings()

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/embeddings", json={"model": "openrouter_test", "input": "test"}
    )
    assert response.status_code == 400
    # Security fix: error messages are sanitized to prevent information exposure
    assert "An error occurred while processing the request" in response.json()["error"]["message"]


def test_images_generations_endpoint(monkeypatch: pytest.MonkeyPatch):
    """Test images generations endpoint."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response_payload = {
        "created": 1234567890,
        "data": [{"url": "https://example.com/image.png"}],
    }

    class FakeImages:
        async def generate(self, **_: Any):
            return response_payload

    class FakeClient:
        images = FakeImages()

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/images/generations",
        json={"model": "openrouter_dall-e-3", "prompt": "A cat"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert "url" in body["data"][0]


def test_images_generations_missing_model():
    """Test images generations endpoint with missing model."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post("/llm/v1/images/generations", json={"prompt": "test"})
    assert response.status_code == 400
    assert "Model ID is required" in response.json()["error"]


def test_images_generations_error_handling(monkeypatch: pytest.MonkeyPatch):
    """Test images generations error handling."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    class FakeImages:
        async def generate(self, **_: Any):
            raise Exception("Image generation failed")

    class FakeClient:
        images = FakeImages()

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/images/generations",
        json={"model": "openrouter_dall-e-3", "prompt": "test"},
    )
    assert response.status_code == 400
    # Security fix: error messages are sanitized to prevent information exposure
    assert "An error occurred while processing the request" in response.json()["error"]["message"]


def test_audio_transcriptions_missing_model():
    """Test audio transcriptions with missing model."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/audio/transcriptions",
        files={"file": ("test.mp3", io.BytesIO(b"fake audio"))},
    )
    assert response.status_code == 400
    assert "Model ID is required" in response.json()["error"]


def test_audio_transcriptions_missing_file():
    """Test audio transcriptions with missing file."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/audio/transcriptions", data={"model": "openrouter_whisper-1"}
    )
    assert response.status_code == 400
    assert "File is required" in response.json()["error"]


def test_audio_translations_missing_model():
    """Test audio translations with missing model."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/audio/translations",
        files={"file": ("test.mp3", io.BytesIO(b"fake audio"))},
    )
    assert response.status_code == 400
    assert "Model ID is required" in response.json()["error"]


def test_audio_translations_missing_file():
    """Test audio translations with missing file."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/audio/translations", data={"model": "openrouter_whisper-1"}
    )
    assert response.status_code == 400
    assert "File is required" in response.json()["error"]


# Test models caching
@pytest.mark.asyncio

# Test load providers from file
def test_chat_completions_streaming(monkeypatch: pytest.MonkeyPatch):
    """Test chat completions with streaming enabled."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    async def mock_stream():
        yield {"id": "chunk1", "choices": [{"delta": {"content": "Hello"}}]}
        yield {"id": "chunk2", "choices": [{"delta": {"content": " World"}}]}

    class MockStreamResponse:
        def __aiter__(self):
            return mock_stream()

    class FakeChatCompletions:
        async def create(self, **kwargs: Any):
            return MockStreamResponse()

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/chat/completions",
        json={
            "model": "openrouter_test",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    assert response.status_code == 200
    # Streaming response should be event-stream
    assert "text/event-stream" in response.headers.get("content-type", "")


# Test error handling for chat completions
def test_chat_completions_missing_required_error(monkeypatch: pytest.MonkeyPatch):
    """Test chat completions handles 'Missing required' errors with 400."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    class FakeChatCompletions:
        async def create(self, **_: Any):
            raise Exception("Missing required parameter: messages")

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/chat/completions", json={"model": "openrouter_test", "messages": []}
    )
    assert response.status_code == 400


def test_embeddings_missing_required_error(monkeypatch: pytest.MonkeyPatch):
    """Test embeddings handles 'Missing required' errors with 400."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    class FakeEmbeddings:
        async def create(self, **_: Any):
            raise Exception("Missing required parameter: input")

    class FakeClient:
        embeddings = FakeEmbeddings()

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post("/llm/v1/embeddings", json={"model": "openrouter_test"})
    assert response.status_code == 400


def test_transform_models():
    """Test _transform_models adds provider and updates id."""
    models = [
        {"id": "model1", "object": "model"},
        {"id": "model2", "object": "model"},
    ]

    result = LlmProxiesProvider._transform_models(models, "openrouter")

    assert result[0]["provider"] == "openrouter"
    assert result[0]["id"] == "openrouter_model1"
    assert result[1]["provider"] == "openrouter"
    assert result[1]["id"] == "openrouter_model2"


# ---------------------------------------------------------------------------
# Anthropic Messages endpoint tests
# ---------------------------------------------------------------------------

def test_anthropic_messages_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test basic Anthropic messages request returns Anthropic-format response."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response_payload = {
        "id": "chatcmpl-abc",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello there!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    class FakeChatCompletions:
        async def create(self, **_: Any) -> dict[str, Any]:
            return response_payload

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/messages",
        json={
            "model": "openrouter_gpt-4o",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "message"
    assert body["role"] == "assistant"
    assert body["content"][0]["type"] == "text"
    assert body["content"][0]["text"] == "Hello there!"
    assert body["stop_reason"] == "end_turn"
    assert body["usage"]["input_tokens"] == 10
    assert body["usage"]["output_tokens"] == 5
    assert body["model"] == "openrouter_gpt-4o"


def test_anthropic_messages_with_system(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that system prompt is converted to an OpenAI system message."""
    provider = _build_provider()

    captured: dict[str, Any] = {}

    class FakeChatCompletions:
        async def create(self, **kwargs: Any) -> dict[str, Any]:
            captured["messages"] = kwargs.get("messages", [])
            return {
                "id": "x",
                "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {},
            }

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())
    client = TestClient(_build_app(provider))

    client.post(
        "/llm/v1/messages",
        json={
            "model": "openrouter_gpt-4o",
            "max_tokens": 50,
            "system": "You are a helpful assistant.",
            "messages": [{"role": "user", "content": "Hi"}],
        },
    )

    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][0]["content"] == "You are a helpful assistant."
    assert captured["messages"][1]["role"] == "user"


def test_anthropic_messages_with_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tool definitions are converted to OpenAI format and tool_use blocks come back."""
    provider = _build_provider()

    captured: dict[str, Any] = {}

    class FakeChatCompletions:
        async def create(self, **kwargs: Any) -> dict[str, Any]:
            captured["tools"] = kwargs.get("tools")
            captured["tool_choice"] = kwargs.get("tool_choice")
            return {
                "id": "x",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "get_weather", "arguments": '{"location":"NYC"}'},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            }

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/messages",
        json={
            "model": "openrouter_gpt-4o",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "What is the weather in NYC?"}],
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "input_schema": {"type": "object", "properties": {"location": {"type": "string"}}},
                }
            ],
            "tool_choice": {"type": "auto"},
        },
    )

    # Verify tool format was converted correctly
    assert captured["tools"] is not None
    assert captured["tools"][0]["type"] == "function"
    assert captured["tools"][0]["function"]["name"] == "get_weather"
    assert captured["tool_choice"] == "auto"

    # Verify response has tool_use block
    assert response.status_code == 200
    body = response.json()
    assert body["stop_reason"] == "tool_use"
    tool_block = next(b for b in body["content"] if b["type"] == "tool_use")
    assert tool_block["name"] == "get_weather"
    assert tool_block["input"] == {"location": "NYC"}


def test_anthropic_messages_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Anthropic streaming response emits correct SSE event types."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    async def mock_stream():
        yield {"id": "chatcmpl-1", "choices": [{"delta": {"content": "Hello"}, "finish_reason": None}], "usage": None}
        yield {"id": "chatcmpl-1", "choices": [{"delta": {"content": " world"}, "finish_reason": None}], "usage": None}
        yield {"id": "chatcmpl-1", "choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"completion_tokens": 2}}

    class MockStreamResponse:
        def __aiter__(self):
            return mock_stream()

    class FakeChatCompletions:
        async def create(self, **_: Any) -> MockStreamResponse:
            return MockStreamResponse()

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/messages",
        json={
            "model": "openrouter_gpt-4o",
            "max_tokens": 100,
            "stream": True,
            "messages": [{"role": "user", "content": "Hi"}],
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    raw = response.text
    event_types = [
        line.removeprefix("event: ").strip()
        for line in raw.splitlines()
        if line.startswith("event:")
    ]
    assert "message_start" in event_types
    assert "content_block_start" in event_types
    assert "ping" in event_types
    assert "content_block_delta" in event_types
    assert "content_block_stop" in event_types
    assert "message_delta" in event_types
    assert "message_stop" in event_types


def test_anthropic_messages_missing_model() -> None:
    """Test Anthropic messages endpoint returns 400 when model is missing."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/messages",
        json={"max_tokens": 100, "messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 400


def test_anthropic_messages_missing_max_tokens() -> None:
    """Test Anthropic messages endpoint returns 400 when max_tokens is missing."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/messages",
        json={"model": "openrouter_gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 400
    assert "max_tokens" in response.json()["error"]["message"]


def test_anthropic_messages_missing_messages() -> None:
    """Test Anthropic messages endpoint returns 400 when messages is missing."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/messages",
        json={"model": "openrouter_gpt-4o", "max_tokens": 100},
    )
    assert response.status_code == 400
    assert "messages" in response.json()["error"]["message"]


def test_anthropic_to_openai_request_stop_sequences() -> None:
    """Test stop_sequences is renamed to stop in the converted request."""
    body = {
        "model": "openrouter_x",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 50,
        "stop_sequences": ["END", "STOP"],
    }
    result = LlmProxiesProvider._anthropic_to_openai_request(body, "x")
    assert result["stop"] == ["END", "STOP"]
    assert "stop_sequences" not in result


def test_anthropic_to_openai_request_tool_choice_any() -> None:
    """Test tool_choice 'any' maps to 'required' in OpenAI format."""
    body = {
        "model": "openrouter_x",
        "messages": [],
        "max_tokens": 50,
        "tool_choice": {"type": "any"},
    }
    result = LlmProxiesProvider._anthropic_to_openai_request(body, "x")
    assert result["tool_choice"] == "required"


def test_openai_to_anthropic_response_finish_reason_mapping() -> None:
    """Test finish_reason to stop_reason conversion."""
    for finish_reason, expected_stop_reason in [
        ("stop", "end_turn"),
        ("length", "max_tokens"),
        ("tool_calls", "tool_use"),
        ("content_filter", "end_turn"),
    ]:
        oai_response = {
            "id": "x",
            "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        result = LlmProxiesProvider._openai_to_anthropic_response(oai_response, "openrouter_x")
        assert result["stop_reason"] == expected_stop_reason, f"Failed for {finish_reason}"
