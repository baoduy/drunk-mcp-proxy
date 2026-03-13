"""FastAPI route wiring for LLM proxy endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, FastAPI
from starlette.websockets import WebSocket

from drunk_ai_proxy.middleware.fast_auth import FastAuthMiddleware
from drunk_ai_proxy.utils.env import SERVER_NAME, SERVER_VERSION

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


class LlmRouter:
    """Builds and caches a FastAPI app for LLM proxy routes."""

    def __init__(
        self,
        get_auth_provider: Callable[[], "AuthProvider | None"],
        chat_completions_endpoint: Callable[..., object],
        embeddings_endpoint: Callable[..., object],
        audio_transcriptions_endpoint: Callable[..., object],
        audio_translations_endpoint: Callable[..., object],
        images_generations_endpoint: Callable[..., object],
        get_models_endpoint: Callable[..., object],
        get_providers_endpoint: Callable[..., object],
        anthropic_messages_endpoint: Callable[..., object],
        websocket_response_endpoint: Callable[[WebSocket], Awaitable[None]],
        models_response_model: object,
        providers_response_model: object,
    ) -> None:
        self._get_auth_provider = get_auth_provider
        self._chat_completions_endpoint = chat_completions_endpoint
        self._embeddings_endpoint = embeddings_endpoint
        self._audio_transcriptions_endpoint = audio_transcriptions_endpoint
        self._audio_translations_endpoint = audio_translations_endpoint
        self._images_generations_endpoint = images_generations_endpoint
        self._get_models_endpoint = get_models_endpoint
        self._get_providers_endpoint = get_providers_endpoint
        self._anthropic_messages_endpoint = anthropic_messages_endpoint
        self._websocket_response_endpoint = websocket_response_endpoint
        self._models_response_model = models_response_model
        self._providers_response_model = providers_response_model
        self._app: FastAPI | None = None

    def get_app(self) -> FastAPI:
        """Get or create configured FastAPI application for LLM routes."""
        if self._app is not None:
            return self._app

        dependencies = []
        auth = self._get_auth_provider()
        if auth is not None:
            dependencies = [Depends(FastAuthMiddleware(auth_provider=auth))]

        app = FastAPI(title=SERVER_NAME, version=SERVER_VERSION, dependencies=dependencies)
        router = APIRouter()

        router.add_api_route(
            "/chat/completions",
            self._chat_completions_endpoint,
            methods=["POST"],
            response_model=None,
        )
        router.add_api_route(
            "/embeddings",
            self._embeddings_endpoint,
            methods=["POST"],
            response_model=None,
        )
        router.add_api_route(
            "/audio/transcriptions",
            self._audio_transcriptions_endpoint,
            methods=["POST"],
            response_model=None,
        )
        router.add_api_route(
            "/audio/translations",
            self._audio_translations_endpoint,
            methods=["POST"],
            response_model=None,
        )
        router.add_api_route(
            "/images/generations",
            self._images_generations_endpoint,
            methods=["POST"],
            response_model=None,
        )
        router.add_api_route(
            "/models",
            self._get_models_endpoint,
            methods=["GET"],
            response_model=self._models_response_model,
        )
        router.add_api_route(
            "/providers",
            self._get_providers_endpoint,
            methods=["GET"],
            tags=["Providers"],
            response_model=self._providers_response_model,
        )
        router.add_api_route(
            "/messages",
            self._anthropic_messages_endpoint,
            methods=["POST"],
            response_model=None,
        )

        app.include_router(router)
        app.add_websocket_route("/responses", self._websocket_response_endpoint)

        self._app = app
        return app
