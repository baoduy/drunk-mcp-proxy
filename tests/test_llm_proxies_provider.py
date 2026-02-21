"""
Tests for LlmProxiesProvider Starlette app.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from src.proxies.llm_proxies_provider import LlmModel, LlmProxiesProvider
from src.tools.llm_config import LlmProviderConfig


def _build_provider() -> LlmProxiesProvider:
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
    provider.mount(app)
    return app


def test_chat_completions_requires_messages() -> None:
    provider = _build_provider()
    client = TestClient(_build_app(provider))

    response = client.post("/llm/v1/chat/completions", json={"model": "openrouter/test"})
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
    assert {item["id"] for item in body["data"]} == {"openrouter/test", "openrouter/test-2"}


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
