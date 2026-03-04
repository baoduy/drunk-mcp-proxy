from __future__ import annotations

import json
from app.app_config_provider import AppConfigProvider
from logging import Logger
from typing import TYPE_CHECKING
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBase
from fastapi.responses import JSONResponse, StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from starlette.applications import Starlette
from fastapi.security.utils import get_authorization_scheme_param
from tools.env import SERVER_NAME, SERVER_VERSION
from tools import LlmConfig
from tools.logging_config import setup_logging
from proxies.llm_base_provider import LlmBaseProvider
from proxies.anthropic_provider import AnthropicProvider

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider
    
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

class FastAuthMiddleware(HTTPBase): 
    def __init__(self, auth_provider:AuthProvider):
        super().__init__(scheme="bearer")
        self.auth_provider = auth_provider
        self.auto_error = True

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        
        if not (authorization and scheme and token):
            raise self.make_not_authenticated_error()
        
        rs = await self.auth_provider.verify_token(token)
        if rs is not None and (rs.claims.__len__() > 0 or rs.scopes.__len__() > 0):
            return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
        raise self.make_not_authenticated_error()
        
    
class AsyncOpenAIFactory:
    """Factory for creating AsyncOpenAI clients with caching."""
    def __init__(self, providers: list[LlmConfig]) -> None:
        self._logger: Logger = setup_logging(__name__)
        self.providers = providers
        self._clients: dict[str, AsyncOpenAI] = {}

    def get_client(self, provider_name: str) -> AsyncOpenAI:
        """Get or create an AsyncOpenAI client for the given provider."""
        provider = next((p for p in self.providers if p.provider == provider_name), None)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        
        if provider.provider in self._clients:
            return self._clients[provider.provider]
        
        if provider.api_key is not None and len(provider.api_key) > 0:
            client = AsyncOpenAI(api_key=provider.api_key, base_url=provider.base_url)
        else:
            client = AsyncOpenAI(base_url=provider.base_url)
            
        self._clients[provider.provider] = client
        return client

class LlmProxiesProvider(LlmBaseProvider):
    # _BLOCKED_FORWARD_HEADERS = {
    #     "authorization",
    #     "proxy-authorization",
    #     "forwarded",
    #     "via",
    #     "connection",
    #     "keep-alive",
    #     "te",
    #     "trailer",
    #     "transfer-encoding",
    #     "upgrade",
    #     "host",
    # }
    # _BLOCKED_FORWARD_PREFIXES = ("x-forwarded-",)
    
    def __init__(
        self,
        providers: list[LlmConfig]
    ) -> None:
        super().__init__()
        if not providers or len(providers) == 0:
            raise ValueError("LLM proxy requires at least one provider configuration")
        self.providers = providers
        from app.cache_provider import CacheProvider
        from proxies.llm_websocket_provider import LlmWebSocketProvider
        self.cache = CacheProvider.get_cache_store()
        self.open_ai_factory = AsyncOpenAIFactory(self.providers)
        self.websocket_provider = LlmWebSocketProvider(self.providers)
        self._fastapi_app: FastAPI | None = None

    def mount(self, app: Starlette, route_prefix: str) -> None:
        self._logger.info("Mounting LLM proxies at prefix '%s'", route_prefix)
        app.mount(route_prefix, self._get_fastapi_app())

    def _get_fastapi_app(self) -> FastAPI:
        if self._fastapi_app is None:
            dependencies = []
            
            auth = AppConfigProvider.get_instance().get_fast_mcp_auth_provider()
            if auth:
                dependencies = [Depends(FastAuthMiddleware(auth_provider=auth))]
           
            app = FastAPI(title=SERVER_NAME, version=SERVER_VERSION, dependencies=dependencies)
            
            app.add_api_route(
                "/chat/completions",
                self._chat_completions_endpoint,
                methods=["POST"],
            )
            app.add_api_route(
                "/embeddings",
                self._embeddings_endpoint,
                methods=["POST"],
            )
            app.add_api_route(
                "/audio/transcriptions",
                self._audio_transcriptions_endpoint,
                methods=["POST"],
            )
            app.add_api_route(
                "/audio/translations",
                self._audio_translations_endpoint,
                methods=["POST"],
            )
            app.add_api_route(
                "/images/generations",
                self._images_generations_endpoint,
                methods=["POST"],
            )
            app.add_api_route(
                "/models",
                self._get_models_endpoint,
                methods=["GET"],
            )
            app.add_api_route(
                "/providers",
                self._get_providers_endpoint,
                methods=["GET"],
                tags=["Providers"],
            )
            app.add_api_route(
                "/messages",
                self._anthropic_messages_endpoint,
                methods=["POST"],
            )

            app.add_websocket_route(
                "/responses",
                self.websocket_provider.websocket_response_endpoint,
            )

            self._fastapi_app = app
        return self._fastapi_app

    @staticmethod
    def _transform_models(models: list[dict[str, object]], provider: str) -> list[dict[str, object]]:
        # This is a placeholder for any transformation logic you might want to apply to the models list.
        # For now, it just returns the input as-is.
        for model in models:
            model["provider"] = provider
            model["id"] = f"{provider}_{model.get('id', '')}"
        return models

    @staticmethod
    async def _format_response(
        response: object,
        is_streaming: bool,
    ) -> JSONResponse | StreamingResponse:
        """Format chat completion response as either streaming or JSON response.
        
        Args:
            response: The response object from OpenAI client
            is_streaming: Whether streaming was requested
            
        Returns:
            StreamingResponse if streaming, JSONResponse otherwise
        """
        if is_streaming:
            async def stream_generator():
                async for chunk in response:
                    chunk_dict = LlmProxiesProvider._to_dict(chunk)
                    yield f"data: {json.dumps(chunk_dict)}\n\n"
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            return JSONResponse(content=LlmProxiesProvider._to_dict(response))

    def _get_openai_client(self, provider_name: str) -> AsyncOpenAI:
        return self.open_ai_factory.get_client(provider_name)

    async def _get_models_by_provider(self, provider_name: str) -> list[LlmModel]:
        # Check cache first
        cache_key = f"models_{provider_name}"
        cached_models = await self.cache.get(cache_key)
        if cached_models is not None:
            self._logger.info("Cache hit for models of provider '%s'", provider_name)
            return cached_models
        
        # Cache miss, fetch from provider
        self._logger.info("Fetching models of provider '%s'", provider_name)
        client = self._get_openai_client(provider_name)
        
        # Get models from provider
        response = await client.models.list()
        if not response or not hasattr(response, "data") or not response.data:
            self._logger.warning(
                "No models data found in response from provider '%s'",
                provider_name,
            )
            return []
        # Transform models to dict and add provider info
        models = [self._to_dict(model) for model in response.data]
        models = self._transform_models(models, provider_name)
        
        # Cache the models list with TTL
        await self.cache.set(cache_key, models)
        return [LlmModel(**model) for model in models]
    
    async def _get_all_models(self) -> list[LlmModel]:
        # Fetch models from all providers and aggregate them
        all_models: list[LlmModel] = []
        for provider in self.providers:
            models = await self._get_models_by_provider(provider.provider)
            all_models.extend(models)
        return all_models
    
    async def _get_models_endpoint(self, request: Request) -> dict[str, object]:
        # For simplicity, we return a static list of models for each provider.
        # In a real implementation, you might want to cache this and refresh it periodically.
        provider = request.query_params.get("provider")
        models =await self._get_models_by_provider(provider) if provider else await self._get_all_models()
        return {"data": models}

    def _get_providers_endpoint(self) -> dict[str, object]:
        providers_list = [ProviderModel(name=p.provider, slug=p.provider) for p in self.providers]
        return {"data": [self._to_dict(p) for p in providers_list]}
    
    async def _embeddings_endpoint(self, request: Request):
        """Handle embeddings requests."""
        body = await request.json()
        result = self.extract_and_validate_model(body)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        client = self._get_openai_client(provider_name)
        try:
            body["model"] = model_name
            known_params, extra_body = self._split_params(body, self._EMBEDDINGS_KNOWN_PARAMS)
            if extra_body:
                known_params["extra_body"] = extra_body
            response = await client.embeddings.create(**known_params)
            return self._json_response(response)
        except Exception as e:
            return self.handle_exception(e, f"embeddings for '{model_name}'")
    
    async def _audio_transcriptions_endpoint(self, request: Request):
        """Handle audio transcriptions requests."""
        form_data = await request.form()
        result = self.extract_and_validate_model(form_data)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        client = self._get_openai_client(provider_name)
        try:
            file_error = self._require_form_field(form_data, "file")
            if file_error:
                return file_error
            form_dict = self._form_data_to_dict(form_data)
            form_dict["model"] = model_name
            known_params, extra_body = self._split_params(form_dict, self._AUDIO_TRANSCRIPTIONS_KNOWN_PARAMS)
            if extra_body:
                known_params["extra_body"] = extra_body
            response = await client.audio.transcriptions.create(**known_params)  # type: ignore[arg-type]
            return self._json_response(response)
        except Exception as e:
            return self.handle_exception(e, f"audio transcriptions for '{model_name}'")
    
    async def _audio_translations_endpoint(self, request: Request):
        """Handle audio translations requests."""
        form_data = await request.form()
        result = self.extract_and_validate_model(form_data)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        client = self._get_openai_client(provider_name)
        try:
            file_error = self._require_form_field(form_data, "file")
            if file_error:
                return file_error
            form_dict = self._form_data_to_dict(form_data)
            form_dict["model"] = model_name
            known_params, extra_body = self._split_params(form_dict, self._AUDIO_TRANSLATIONS_KNOWN_PARAMS)
            if extra_body:
                known_params["extra_body"] = extra_body
            response = await client.audio.translations.create(**known_params)  # type: ignore[arg-type]
            return self._json_response(response)
        except Exception as e:
            return self.handle_exception(e, f"audio translations for '{model_name}'")
    
    async def _images_generations_endpoint(self, request: Request):
        """Handle image generations requests."""
        body = await request.json()
        result = self.extract_and_validate_model(body)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        client = self._get_openai_client(provider_name)
        try:
            body["model"] = model_name
            known_params, extra_body = self._split_params(body, self._IMAGES_GENERATE_KNOWN_PARAMS)
            if extra_body:
                known_params["extra_body"] = extra_body
            response = await client.images.generate(**known_params)
            return self._json_response(response)
        except Exception as e:
            return self.handle_exception(e, f"images generations for '{model_name}'")
    
    # Known parameters accepted by the OpenAI embeddings API.
    _EMBEDDINGS_KNOWN_PARAMS: set[str] = {
        "input",
        "model",
        "dimensions",
        "encoding_format",
        "user",
    }

    # Known parameters accepted by the OpenAI images generate API.
    _IMAGES_GENERATE_KNOWN_PARAMS: set[str] = {
        "prompt",
        "background",
        "model",
        "moderation",
        "n",
        "output_compression",
        "output_format",
        "partial_images",
        "quality",
        "response_format",
        "size",
        "stream",
        "style",
        "user",
    }

    # Known parameters accepted by the OpenAI audio transcriptions API.
    _AUDIO_TRANSCRIPTIONS_KNOWN_PARAMS: set[str] = {
        "file",
        "model",
        "chunking_strategy",
        "include",
        "known_speaker_names",
        "known_speaker_references",
        "language",
        "prompt",
        "response_format",
        "stream",
        "temperature",
        "timestamp_granularities",
    }

    # Known parameters accepted by the OpenAI audio translations API.
    _AUDIO_TRANSLATIONS_KNOWN_PARAMS: set[str] = {
        "file",
        "model",
        "prompt",
        "response_format",
        "temperature",
    }

    # Known parameters accepted by the OpenAI chat completions API.
    _CHAT_COMPLETION_KNOWN_PARAMS: set[str] = {
        "messages",
        "model",
        "audio",
        "frequency_penalty",
        "function_call",
        "functions",
        "logit_bias",
        "logprobs",
        "max_completion_tokens",
        "max_tokens",
        "metadata",
        "modalities",
        "n",
        "parallel_tool_calls",
        "prediction",
        "presence_penalty",
        "prompt_cache_key",
        "prompt_cache_retention",
        "reasoning_effort",
        "response_format",
        "safety_identifier",
        "seed",
        "service_tier",
        "stop",
        "store",
        "stream",
        "stream_options",
        "temperature",
        "tool_choice",
        "tools",
        "top_logprobs",
        "top_p",
        "user",
        "verbosity",
        "web_search_options",
    }

    async def _chat_completions_endpoint(self, request: Request):
        body = await request.json()
        result = self.extract_and_validate_model(body)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        if "messages" not in body:
            return JSONResponse(
                content={"error": {"message": "messages is required"}},
                status_code=400,
            )
        client = self._get_openai_client(provider_name)
        try:
            body["model"] = model_name
            is_streaming = body.get("stream", False)

            known_params, extra_body = self._split_params(body, self._CHAT_COMPLETION_KNOWN_PARAMS)
            if extra_body:
                known_params["extra_body"] = extra_body

            response = await client.chat.completions.create(**known_params)
            return await self._format_response(response, is_streaming)
        except Exception as e:
            return self.handle_exception(e, f"chat completions for '{model_name}'")

    # Anthropic conversion handled by AnthropicProvider

    @staticmethod
    def _anthropic_to_openai_request(
        body: dict[str, object],
        model_name: str,
    ) -> dict[str, object]:
        """Delegate to AnthropicProvider for conversion."""
        return AnthropicProvider.anthropic_to_openai_request(body, model_name)

    @staticmethod
    def _openai_to_anthropic_response(
        response: object,
        model_id: str,
    ) -> dict[str, object]:
        """Delegate to AnthropicProvider for conversion."""
        return AnthropicProvider.openai_to_anthropic_response(response, model_id)

    @staticmethod
    async def _format_anthropic_streaming_response(
        stream: object,
        model_id: str,
    ) -> StreamingResponse:
        """Delegate to AnthropicProvider for streaming conversion."""
        return await AnthropicProvider.format_anthropic_streaming_response(stream, model_id)

    async def _anthropic_messages_endpoint(self, request: Request):
        """Handle Anthropic Messages API compatible requests (POST /messages)."""
        body = await request.json()
        result = self.extract_and_validate_model(body)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result

        if "messages" not in body:
            return JSONResponse(
                content={"type": "error", "error": {"type": "invalid_request_error", "message": "messages is required"}},
                status_code=400,
            )
        if "max_tokens" not in body:
            return JSONResponse(
                content={"type": "error", "error": {"type": "invalid_request_error", "message": "max_tokens is required"}},
                status_code=400,
            )

        client = self._get_openai_client(provider_name)
        try:
            oai_body = self._anthropic_to_openai_request(body, model_name)
            is_streaming = bool(oai_body.get("stream", False))

            known_params, extra_body = self._split_params(oai_body, self._CHAT_COMPLETION_KNOWN_PARAMS)
            if extra_body:
                known_params["extra_body"] = extra_body

            response = await client.chat.completions.create(**known_params)

            if is_streaming:
                return await self._format_anthropic_streaming_response(response, body.get("model", model_name))

            return JSONResponse(
                content=self._openai_to_anthropic_response(response, body.get("model", model_name))
            )
        except Exception as e:
            return self.handle_exception(e, f"anthropic messages for '{model_name}'")

