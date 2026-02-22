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

from src.proxies.llm_proxies_provider import (
    AsyncOpenAIFactory,
    LlmModel,
    LlmProxiesProvider,
)
from src.tools.llm_config import LlmProviderConfig


def _build_provider() -> LlmProxiesProvider:
    # TODO: Mock this provider for testing instead of using a real config
    provider_config = LlmProviderConfig.model_validate(
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
        "app.auth_provider.GlobalAuthProvider.get_auth_provider", return_value=None
    ):
        provider.mount(app)
    return app


def test_chat_completions_requires_messages() -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post(
        "/llm/v1/chat/completions", json={"model": "openrouter/test"}
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
            "model": "openrouter/test",
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
            "model": "openrouter/test",
            "input": "hello",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["embedding"] == [0.1, 0.2]


def test_models_aggregates(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    async def fake_fetch_all_models(*_: Any, **__: Any) -> list[LlmModel]:
        return [
            LlmModel(id="openrouter/test", provider="openrouter"),
            LlmModel(id="openrouter/test-2", provider="openrouter"),
        ]

    monkeypatch.setattr(provider, "_fetch_all_models", fake_fetch_all_models)

    response = client.get("/llm/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert {item["id"] for item in body["data"]} == {
        "openrouter/test",
        "openrouter/test-2",
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
    provider1 = LlmProviderConfig.model_validate(
        {
            "provider": "openrouter",
            "base_url": "https://example.com/api/v1",
            "api_key": "test-key-1",
        }
    )
    provider2 = LlmProviderConfig.model_validate(
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
    provider = LlmProviderConfig.model_validate(
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
    provider_config = LlmProviderConfig.model_validate(
        {
            "provider": "openrouter",
            "base_url": "https://example.com/api/v1",
            "api_key": "test-key",
        }
    )

    provider = LlmProxiesProvider(providers=[provider_config])
    assert provider.providers == [provider_config]
    assert provider.open_ai_factory is not None


def test_llm_proxies_provider_with_config_dir():
    """Test LlmProxiesProvider initialization with config_dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "llm.json"
        config_path.write_text("""[
            {
                "provider": "openrouter",
                "base_url": "https://example.com/api/v1",
                "api_key": "test-key",
                "enabled": true
            }
        ]""")

        provider = LlmProxiesProvider(config_dir=tmpdir)
        assert len(provider.providers) == 1
        assert provider.providers[0].provider == "openrouter"


def test_llm_proxies_provider_requires_providers_or_config():
    """Test LlmProxiesProvider raises error if neither providers nor config_dir provided."""
    with pytest.raises(
        ValueError, match="Either config_dir or providers must be provided"
    ):
        LlmProxiesProvider()


def test_llm_proxies_provider_requires_at_least_one_provider():
    """Test LlmProxiesProvider raises error if no providers configured."""
    with pytest.raises(ValueError, match="at least one provider"):
        LlmProxiesProvider(providers=[])


# Test model ID parsing
def test_parse_model_id_with_provider():
    """Test _parse_model_id with provider/model format."""
    provider_name, model_name = LlmProxiesProvider._parse_model_id("openrouter/gpt-4")
    assert provider_name == "openrouter"
    assert model_name == "gpt-4"


def test_parse_model_id_without_provider():
    """Test _parse_model_id with just model name."""
    provider_name, model_name = LlmProxiesProvider._parse_model_id("gpt-4")
    assert provider_name == ""
    assert model_name == "gpt-4"


# Test header collection
def test_collect_forward_headers_blocks_auth():
    """Test that authorization headers are blocked."""
    mock_request = Mock()
    mock_request.headers = {
        "Authorization": "Bearer token",
        "Content-Type": "application/json",
        "User-Agent": "test",
    }

    headers = LlmProxiesProvider._collect_forward_headers(mock_request)
    assert all(k.lower() != "authorization" for k in headers.keys())
    assert "Content-Type" in headers
    assert "User-Agent" in headers


def test_collect_forward_headers_blocks_proxy_headers():
    """Test that proxy-related headers are blocked."""
    mock_request = Mock()
    mock_request.headers = {
        "X-Forwarded-For": "192.168.1.1",
        "X-Forwarded-Host": "example.com",
        "Via": "1.1 proxy",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
    }

    headers = LlmProxiesProvider._collect_forward_headers(mock_request)
    assert "x-forwarded-for" not in headers
    assert "x-forwarded-host" not in headers
    assert "via" not in headers
    assert "connection" not in headers
    assert "Content-Type" in headers


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
        "/llm/v1/embeddings", json={"model": "openrouter/test", "input": "test"}
    )
    assert response.status_code == 500
    assert "Test error" in response.json()["error"]["message"]


def test_completions_endpoint(monkeypatch: pytest.MonkeyPatch):
    """Test completions endpoint."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response_payload = {
        "id": "cmpl-1",
        "object": "text_completion",
        "choices": [{"text": "Hello", "index": 0, "finish_reason": "stop"}],
    }

    class FakeCompletions:
        async def create(self, **_: Any):
            return response_payload

    class FakeClient:
        completions = FakeCompletions()

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: FakeClient())

    response = client.post(
        "/llm/v1/completions", json={"model": "openrouter/test", "prompt": "Hello"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["text"] == "Hello"


def test_completions_missing_model():
    """Test completions endpoint with missing model."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post("/llm/v1/completions", json={"prompt": "test"})
    assert response.status_code == 400
    assert "Model ID is required" in response.json()["error"]


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
        json={"model": "openrouter/dall-e-3", "prompt": "A cat"},
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
        json={"model": "openrouter/dall-e-3", "prompt": "test"},
    )
    assert response.status_code == 500
    assert "Image generation failed" in response.json()["error"]


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
        "/llm/v1/audio/transcriptions", data={"model": "openrouter/whisper-1"}
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
        "/llm/v1/audio/translations", data={"model": "openrouter/whisper-1"}
    )
    assert response.status_code == 400
    assert "File is required" in response.json()["error"]


# Test models caching
@pytest.mark.asyncio
async def test_get_models_by_provider_caching(monkeypatch: pytest.MonkeyPatch):
    """Test that models are cached by provider."""
    provider = _build_provider()

    # Mock the cache
    cache_data = {}

    async def mock_cache_get(key: str):
        return cache_data.get(key)

    async def mock_cache_set(key: str, value: Any, ttl_seconds: int | None = None):
        cache_data[key] = value

    provider.cache.get = mock_cache_get
    provider.cache.set = mock_cache_set

    # Mock the OpenAI client
    class MockModel:
        def __init__(self, id: str):
            self.id = id

        def model_dump(self):
            return {"id": self.id}

    class MockModels:
        async def list(self):
            return SimpleNamespace(data=[MockModel("model1"), MockModel("model2")])

    class MockClient:
        models = MockModels()

    monkeypatch.setattr(provider, "_get_openai_client", lambda *_: MockClient())

    # First call - should fetch and cache
    models1 = await provider._get_models_by_provider("openrouter")
    assert len(models1) == 2
    assert models1[0]["id"] == "openrouter/model1"

    # Second call - should return cached
    models2 = await provider._get_models_by_provider("openrouter")
    assert models2 == models1


def test_models_endpoint_with_provider_filter(monkeypatch: pytest.MonkeyPatch):
    """Test models endpoint with provider filter."""
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    async def mock_get_models_by_provider(provider_name: str):
        return [
            {"id": f"{provider_name}/model1", "provider": provider_name},
            {"id": f"{provider_name}/model2", "provider": provider_name},
        ]

    monkeypatch.setattr(
        provider, "_get_models_by_provider", mock_get_models_by_provider
    )

    response = client.get("/llm/v1/models?provider=openrouter")
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert body["data"][0]["id"] == "openrouter/model1"


# Test load providers from file
def test_load_providers_filters_disabled():
    """Test that _load_providers filters out disabled providers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "llm.json"
        config_path.write_text("""[
            {
                "provider": "enabled_provider",
                "base_url": "https://example.com/api/v1",
                "api_key": "key1",
                "enabled": true
            },
            {
                "provider": "disabled_provider",
                "base_url": "https://example.com/api/v2",
                "api_key": "key2",
                "enabled": false
            }
        ]""")

        providers = LlmProxiesProvider._load_providers(str(config_path))
        assert len(providers) == 1
        assert providers[0].provider == "enabled_provider"


# Test chat completions streaming
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
            "model": "openrouter/test",
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
        "/llm/v1/chat/completions", json={"model": "openrouter/test", "messages": []}
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

    response = client.post("/llm/v1/embeddings", json={"model": "openrouter/test"})
    assert response.status_code == 400


def test_transform_models():
    """Test _transform_models adds provider and updates id."""
    models = [
        {"id": "model1", "object": "model"},
        {"id": "model2", "object": "model"},
    ]

    result = LlmProxiesProvider._transform_models(models, "openrouter")

    assert result[0]["provider"] == "openrouter"
    assert result[0]["id"] == "openrouter/model1"
    assert result[1]["provider"] == "openrouter"
    assert result[1]["id"] == "openrouter/model2"
