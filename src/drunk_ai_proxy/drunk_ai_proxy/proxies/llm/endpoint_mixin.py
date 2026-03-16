"""LLM endpoint handler mixin for LlmProxiesProvider."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai import AsyncOpenAI

from drunk_ai_proxy.proxies.llm.anthropic_provider import AnthropicProvider
from drunk_ai_proxy.proxies.llm.base_provider import LlmBaseProvider
from drunk_ai_proxy.utils import audit_log

from fastmcp.utilities import logging

logger = logging.get_logger(__name__)


class LlmEndpointMixin:
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
                    chunk_dict = LlmBaseProvider._to_dict(chunk)
                    yield f"data: {json.dumps(chunk_dict)}\n\n"
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            return JSONResponse(content=LlmBaseProvider._to_dict(response))

    def _get_openai_client(self, provider_name: str) -> AsyncOpenAI:
        return self.open_ai_factory.get_client(provider_name)
    
    async def _get_models_endpoint(self, request: Request) -> ModelsResponse:
        # For simplicity, we return a static list of models for each provider.
        # In a real implementation, you might want to cache this and refresh it periodically.
        provider = request.query_params.get("provider")
        raw_models = (
            await self._model_catalog.get_models_by_provider(provider)
            if provider
            else await self._model_catalog.get_all_models()
        )
        return ModelsResponse(data=[LlmModel(**model) for model in raw_models])

    def _get_providers_endpoint(self) -> ProvidersResponse:
        providers_list = [ProviderModel(name=p.provider, slug=p.provider) for p in self.providers]
        return ProvidersResponse(data=providers_list)
    
    async def _embeddings_endpoint(
        self,
        body: EmbeddingsRequest,
    ) -> JSONResponse | StreamingResponse:
        """Handle embeddings requests."""
        payload = body.model_dump(exclude_none=True)
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
    
    async def _audio_transcriptions_endpoint(
        self,
        request: Request,
    ) -> JSONResponse | StreamingResponse:
        """Handle audio transcriptions requests."""
        form_data = await request.form()
        result = self.extract_and_validate_model(form_data)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        file_error = self._require_form_field(form_data, "file")
        if file_error:
            return file_error
        form_dict = self._form_data_to_dict(form_data)
        return await self._call_openai_endpoint(
            provider_name=provider_name,
            model_name=model_name,
            payload=form_dict,
            known_params=self._AUDIO_TRANSCRIPTIONS_KNOWN_PARAMS,
            call_fn=lambda client, params: client.audio.transcriptions.create(  # type: ignore[arg-type]
                **params
            ),
            context=f"audio transcriptions for '{model_name}'",
            response_builder=self._format_json_response,
        )
    
    async def _audio_translations_endpoint(
        self,
        request: Request,
    ) -> JSONResponse | StreamingResponse:
        """Handle audio translations requests."""
        form_data = await request.form()
        result = self.extract_and_validate_model(form_data)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        file_error = self._require_form_field(form_data, "file")
        if file_error:
            return file_error
        form_dict = self._form_data_to_dict(form_data)
        return await self._call_openai_endpoint(
            provider_name=provider_name,
            model_name=model_name,
            payload=form_dict,
            known_params=self._AUDIO_TRANSLATIONS_KNOWN_PARAMS,
            call_fn=lambda client, params: client.audio.translations.create(  # type: ignore[arg-type]
                **params
            ),
            context=f"audio translations for '{model_name}'",
            response_builder=self._format_json_response,
        )
    
    async def _images_generations_endpoint(
        self,
        request: Request,
    ) -> JSONResponse | StreamingResponse:
        """Handle image generations requests."""
        body = await request.json()
        result = self.extract_and_validate_model(body)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        return await self._call_openai_endpoint(
            provider_name=provider_name,
            model_name=model_name,
            payload=body,
            known_params=self._IMAGES_GENERATE_KNOWN_PARAMS,
            call_fn=lambda client, params: client.images.generate(**params),
            context=f"images generations for '{model_name}'",
            response_builder=self._format_json_response,
        )
    
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

    async def _chat_completions_endpoint(
        self,
        body: ChatCompletionRequest,
    ) -> JSONResponse | StreamingResponse:
        payload = body.model_dump(exclude_none=True)
        result = self.extract_and_validate_model(payload)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        if not body.messages:
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

    def _build_openai_params(
        self,
        payload: dict[str, object],
        model_name: str,
        known_params: set[str],
    ) -> dict[str, object]:
        return self._dispatcher.build_openai_params(
            payload=payload,
            model_name=model_name,
            split_params=self._split_params,
            known_params=known_params,
        )

    async def _call_openai_endpoint(
        self,
        *,
        provider_name: str,
        model_name: str,
        payload: dict[str, object],
        known_params: set[str],
        call_fn: Callable[[AsyncOpenAI, dict[str, object]], Awaitable[object]],
        context: str,
        response_builder: Callable[[object, dict[str, object]], Awaitable[JSONResponse | StreamingResponse]],
    ) -> JSONResponse | StreamingResponse:
        return await self._dispatcher.call_openai_endpoint(
            provider_name=provider_name,
            model_name=model_name,
            payload=payload,
            known_params=known_params,
            split_params=self._split_params,
            call_fn=call_fn,
            context=context,
            response_builder=response_builder,
        )

    @staticmethod
    async def _format_json_response(
        response: object,
        _: dict[str, object],
    ) -> JSONResponse:
        return LlmBaseProvider._json_response(response)

    async def _format_chat_response(
        self,
        response: object,
        payload: dict[str, object],
    ) -> JSONResponse | StreamingResponse:
        is_streaming = bool(payload.get("stream", False))
        return await self._format_response(response, is_streaming)

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

    async def _dispatch_anthropic_call(
        self,
        body: dict[str, object],
        model_name: str,
        provider_name: str,
    ) -> JSONResponse | StreamingResponse:
        """Execute validated Anthropic request against the OpenAI-compatible backend.

        Args:
            body: Raw Anthropic request body.
            model_name: Parsed model name (without provider prefix).
            provider_name: Provider key for client lookup.

        Returns:
            Formatted Anthropic-compatible JSON or streaming response.
        """
        client = self._get_openai_client(provider_name)
        try:
            known_params, model_id, is_streaming = self._build_anthropic_openai_params(
                body,
                model_name,
            )
            response = await client.chat.completions.create(**known_params)

            if is_streaming:
                return await self._format_anthropic_streaming_response(response, model_id)

            return JSONResponse(content=self._openai_to_anthropic_response(response, model_id))
        except Exception as e:
            audit_log(
                logger=logger,
                event="anthropic_messages_failed",
                status="failure",
                resource="/messages",
                details={"provider": provider_name, "model": model_name, "error_type": type(e).__name__},
            )
            return self.handle_exception(e, f"anthropic messages for '{model_name}'")

    async def _anthropic_messages_endpoint(
        self,
        request: Request,
    ) -> JSONResponse | StreamingResponse:
        """Handle Anthropic Messages API compatible requests (POST /messages)."""
        body = await request.json()
        result = self.extract_and_validate_model(body)
        if isinstance(result, JSONResponse):
            return result
        provider_name, model_name = result
        validation_error = self._validate_anthropic_body(body)
        if validation_error is not None:
            return validation_error
        return await self._dispatch_anthropic_call(body, model_name, provider_name)

    @staticmethod
    def _anthropic_validation_error(message: str) -> JSONResponse:
        """Build Anthropic-formatted validation error response."""
        return JSONResponse(
            content={"type": "error", "error": {"type": "invalid_request_error", "message": message}},
            status_code=400,
        )

    def _validate_anthropic_body(self, body: dict[str, object]) -> JSONResponse | None:
        """Validate required Anthropic request fields."""
        if "messages" not in body:
            return self._anthropic_validation_error("messages is required")
        if "max_tokens" not in body:
            return self._anthropic_validation_error("max_tokens is required")
        return None

    def _build_anthropic_openai_params(
        self,
        body: dict[str, object],
        model_name: str,
    ) -> tuple[dict[str, object], str, bool]:
        """Convert Anthropic body to OpenAI request params."""
        oai_body = self._anthropic_to_openai_request(body, model_name)
        model_id = str(body.get("model", model_name))
        is_streaming = bool(oai_body.get("stream", False))
        known_params, extra_body = self._split_params(oai_body, self._CHAT_COMPLETION_KNOWN_PARAMS)
        if extra_body:
            known_params["extra_body"] = extra_body
        return known_params, model_id, is_streaming
