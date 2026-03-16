"""LLM proxy provider that mounts OpenAI-compatible and Anthropic-compatible endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from starlette.applications import Starlette
from drunk_ai_proxy.proxies.llm.request_dispatcher import LlmRequestDispatcher
from drunk_ai_proxy.proxies.llm.router import LlmRouter
from drunk_ai_proxy.utils.protocols import AuthProviderFactory, TokenStore
from drunk_ai_proxy.utils.env import SERVER_NAME, SERVER_VERSION
from drunk_ai_proxy.utils import LlmConfig
from drunk_ai_proxy.proxies.llm.base_provider import LlmBaseProvider, MountableLlmProvider
from drunk_ai_proxy.proxies.llm.client_factory import AsyncOpenAIFactory
from drunk_ai_proxy.proxies.llm.model_catalog import LlmModelCatalog
from drunk_ai_proxy.proxies.llm.endpoint_mixin import LlmEndpointMixin

if TYPE_CHECKING:
    from drunk_ai_proxy.proxies.llm.websocket_provider import LlmWebSocketProvider

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class _InMemoryCacheStore:
    """Simple async in-memory store used when no cache dependency is provided."""

    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    async def get(self, key: str) -> object | None:
        return self._values.get(key)

    async def set(
        self,
        key: str,
        value: object,
        ttl_seconds: int | None = None,
    ) -> None:
        del ttl_seconds
        self._values[key] = value

class ModelBase(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def get(self, key: str, default: object | None = None) -> object | None:
        return getattr(self, key, default)


class LlmModel(ModelBase):
    id: str
    provider: str


class ProviderModel(ModelBase):
    name: str
    slug: str


class ChatCompletionRequest(ModelBase):
    model: str | None = None
    messages: list[dict[str, object]] | None = None
    stream: bool = False


class EmbeddingsRequest(ModelBase):
    model: str | None = None
    input: str | list[str] | None = None


class ModelsResponse(ModelBase):
    data: list[LlmModel]


class ProvidersResponse(ModelBase):
    data: list[ProviderModel]


class LlmProxiesProvider(LlmEndpointMixin, MountableLlmProvider):
    def __init__(
        self,
        providers: list[LlmConfig],
        auth_factory: AuthProviderFactory | None = None,
        cache: TokenStore | None = None,
    ) -> None:
        super().__init__()
        if not providers or len(providers) == 0:
            raise ValueError("LLM proxy requires at least one provider configuration")
        self.providers = providers
        from drunk_ai_proxy.proxies.llm.websocket_provider import LlmWebSocketProvider
        self._auth_factory = auth_factory
        self.cache: TokenStore = cache or _InMemoryCacheStore()
        self.open_ai_factory = AsyncOpenAIFactory(self.providers)
        self.websocket_provider = LlmWebSocketProvider(self.providers)
        self._fastapi_app: FastAPI | None = None
        self._model_catalog = LlmModelCatalog(
            providers=[provider.provider for provider in self.providers],
            cache=self.cache,
            get_client=lambda provider_name: self._get_openai_client(provider_name),
            to_dict=self._to_dict,
        )
        self._dispatcher = LlmRequestDispatcher(
            get_client=lambda provider_name: self._get_openai_client(provider_name),
            handle_exception=self.handle_exception,
        )
        self._router = LlmRouter(
            get_auth_provider=lambda: (
                self._auth_factory.get_fast_mcp_auth_provider()
                if self._auth_factory
                else None
            ),
            chat_completions_endpoint=self._chat_completions_endpoint,
            embeddings_endpoint=self._embeddings_endpoint,
            audio_transcriptions_endpoint=self._audio_transcriptions_endpoint,
            audio_translations_endpoint=self._audio_translations_endpoint,
            images_generations_endpoint=self._images_generations_endpoint,
            get_models_endpoint=self._get_models_endpoint,
            get_providers_endpoint=self._get_providers_endpoint,
            anthropic_messages_endpoint=self._anthropic_messages_endpoint,
            websocket_response_endpoint=self.websocket_provider.websocket_response_endpoint,
            models_response_model=ModelsResponse,
            providers_response_model=ProvidersResponse,
        )

    @staticmethod
    def _transform_models(models: list[dict[str, object]], provider: str) -> list[dict[str, object]]:
        return LlmModelCatalog._transform_models(models, provider)

    async def _get_models_by_provider(self, provider_name: str) -> list[LlmModel]:
        models = await self._model_catalog.get_models_by_provider(provider_name)
        return [LlmModel(**model) for model in models]

    async def _get_all_models(self) -> list[LlmModel]:
        models = await self._model_catalog.get_all_models()
        return [LlmModel(**model) for model in models]

    async def _get_models_endpoint(self, request: Request) -> ModelsResponse:
        provider = request.query_params.get("provider")
        models = await self._get_models_by_provider(provider) if provider else await self._get_all_models()
        return ModelsResponse(data=models)

    def _get_providers_endpoint(self) -> ProvidersResponse:
        providers_list = [ProviderModel(name=p.provider, slug=p.provider) for p in self.providers]
        return ProvidersResponse(data=providers_list)

    async def _embeddings_endpoint(
        self,
        request: Request,
    ) -> JSONResponse | StreamingResponse:
        body = await request.json()
        payload = body if isinstance(body, dict) else {}
        result = self.extract_and_validate_model(payload)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        return await self._call_openai_endpoint(
            provider_name=provider_name,
            model_name=model_name,
            payload=payload,
            known_params=self._EMBEDDINGS_KNOWN_PARAMS,
            call_fn=lambda client, params: client.embeddings.create(**params),
            context=f"embeddings for '{model_name}'",
            response_builder=self._format_json_response,
        )

    async def _chat_completions_endpoint(
        self,
        request: Request,
    ) -> JSONResponse | StreamingResponse:
        body = await request.json()
        payload = body if isinstance(body, dict) else {}
        result = self.extract_and_validate_model(payload)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        messages = payload.get("messages")
        if not messages:
            return JSONResponse(
                content={"error": {"message": "messages is required"}},
                status_code=400,
            )
        return await self._call_openai_endpoint(
            provider_name=provider_name,
            model_name=model_name,
            payload=payload,
            known_params=self._CHAT_COMPLETION_KNOWN_PARAMS,
            call_fn=lambda client, params: client.chat.completions.create(**params),
            context=f"chat completions for '{model_name}'",
            response_builder=self._format_chat_response,
        )

    def mount(self, app: Starlette, route_prefix: str) -> None:
        logger.info("Mounting LLM proxies at prefix '%s'", route_prefix)
        app.mount(route_prefix, self._get_fastapi_app())

    def _get_fastapi_app(self) -> FastAPI:
        if self._fastapi_app is None:
            self._fastapi_app = self._router.get_app()
        return self._fastapi_app

