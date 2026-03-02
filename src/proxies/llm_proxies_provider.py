from __future__ import annotations

import json
from app.app_config_provider import AppConfigProvider
from typing import TYPE_CHECKING, Any, Mapping
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBase
from fastapi.responses import JSONResponse, StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from starlette.applications import Starlette
from fastapi.security.utils import get_authorization_scheme_param
from tools.env import SERVER_NAME, SERVER_VERSION
from tools import setup_logging,LlmConfig

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider
    
logger = setup_logging("LlmProxiesProvider")

class ModelBase(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    def get(self, key: str, default: Any = None) -> Any:
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
    def __init__(self,providers: list[LlmConfig]) -> None:
        self.providers = providers
        self._clients: dict[str, AsyncOpenAI] = {}

    def get_client(self,provider_name:str) -> AsyncOpenAI:
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
    
class LlmProxiesProvider:
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
        if not providers or len(providers) == 0:
            raise ValueError("LLM proxy requires at least one provider configuration")
        self.providers = providers

        from app.cache_provider import CacheProvider
        self.cache = CacheProvider.get_cache_store()
        self.open_ai_factory = AsyncOpenAIFactory(self.providers)
        self._fastapi_app: FastAPI | None = None

    def mount(self, app: Starlette, route_prefix: str) -> None:
        app.mount(route_prefix, self._get_fastapi_app())

    def _get_fastapi_app(self) -> FastAPI:
        if self._fastapi_app is None:
            auth = None
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

            self._fastapi_app = app
        return self._fastapi_app

    @staticmethod
    def _transform_models(models: list[dict[str, Any]], provider: str) -> list[dict[str, Any]]:
        # This is a placeholder for any transformation logic you might want to apply to the models list.
        # For now, it just returns the input as-is.
        for model in models:
            model['provider'] = provider
            model['id'] = f"{provider}_{model.get('id', '')}"
        return models
    
    @staticmethod
    def parse_model_id(model_id: str) -> tuple[str, str]:
        """Parse model_id into provider_name and model_name.
        
        Args:
            model_id: Model identifier in format "provider_model_name"
            
        Returns:
            Tuple of (provider_name, model_name)
        """
        parts = model_id.split("_", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        # If no "_" found, treat the whole string as model_name with empty provider
        return "", model_id

    def extract_and_validate_model(self, source: Mapping[str, Any], key: str = "model") -> tuple[str, str] | JSONResponse:
        """Extract and validate model_id from input dict (body or form).

        Args:
            source: Input mapping (request body, form data, etc.).
            key: Key to extract model id (default: 'model').

        Returns:
            Tuple of (provider_name, model_name) or JSONResponse error.
        """
        model_id = source.get(key)
        if not model_id:
            return JSONResponse(content={"error": f"{key.capitalize()} ID is required"}, status_code=400)
        provider_name, model_name = self.parse_model_id(str(model_id))
        if not provider_name:
            return JSONResponse(content={"error": "Invalid model ID format. Expected 'provider_model_name'"}, status_code=400)
        return provider_name, model_name

    # _USER_ACTIONABLE_ERROR_KEYWORDS = (
    #     "missing required",
    #     "invalid",
    #     "not found",
    #     "already exists",
    #     "permission denied",
    #     "unauthorized",
    #     "forbidden",
    #     "rate limit",
    #     "quota",
    #     "timeout",
    # )

    # @staticmethod
    # def _is_user_actionable_error(message: str) -> bool:
    #     """Check if the error message is user-actionable.

    #     Args:
    #         message: The error message to check.

    #     Returns:
    #         True if the error is user-actionable.
    #     """
    #     lower = message.lower()
    #     return any(kw in lower for kw in LlmProxiesProvider._USER_ACTIONABLE_ERROR_KEYWORDS)

    @staticmethod
    def _sanitize_error_message(message: str) -> str:
        """Sanitize error message to prevent information exposure.

        Args:
            message: The raw error message.

        Returns:
            Sanitized error message safe for client consumption.
        """
        # if LlmProxiesProvider._is_user_actionable_error(message):
        #     return message
        return "An error occurred while processing the request"

    def handle_exception(self, e: Exception, context: str = "") -> JSONResponse:
        """Consistent error response and logging.

        Args:
            e: Exception instance.
            context: Optional context string for log.

        Returns:
            JSONResponse with error message.
        """
        logger.error("%s: %s", context, type(e).__name__)
        safe_message = self._sanitize_error_message(str(e))
        # status_code = 400 if self._is_user_actionable_error(str(e)) else 500
        return JSONResponse(content={"error": {"message": safe_message}}, status_code=400)

    # @staticmethod
    # def _collect_forward_headers(request: Request) -> dict[str, str]:
    #     forward_headers: dict[str, str] = {}
    #     for header_name, header_value in request.headers.items():
    #         header_name_lower = header_name.lower()
    #         if header_name_lower in LlmProxiesProvider._BLOCKED_FORWARD_HEADERS:
    #             continue
    #         if header_name_lower.startswith(LlmProxiesProvider._BLOCKED_FORWARD_PREFIXES):
    #             continue
    #         forward_headers[header_name] = header_value
    #     return forward_headers

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        """Convert a Pydantic model or dict to a dict."""
        if isinstance(obj, dict):
            return obj # type: ignore
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        else:
            return obj.__dict__

    @staticmethod
    def _json_response(data: Any, status_code: int = 200) -> JSONResponse:
        """Wrap data in a JSONResponse, converting objects to dict first.
        
        Args:
            data: Data to wrap (will be converted via _to_dict).
            status_code: HTTP status code (default: 200).
            
        Returns:
            JSONResponse with serialized data.
        """
        return JSONResponse(content=LlmProxiesProvider._to_dict(data), status_code=status_code)

    @staticmethod
    def _error_response(message: str, status_code: int = 400) -> JSONResponse:
        """Create a standardized error response.
        
        Args:
            message: Error message to return to client.
            status_code: HTTP status code (default: 400).
            
        Returns:
            JSONResponse with error structure.
        """
        return JSONResponse(content={"error": message}, status_code=status_code)

    @staticmethod
    def _form_data_to_dict(form_data: Any, exclude_key: str = "model") -> dict[str, Any]:
        """Convert form data to dict, excluding a specific key.
        
        Args:
            form_data: Form data object from request.form().
            exclude_key: Key to exclude from conversion (default: 'model').
            
        Returns:
            Dict with form data, excluding the specified key.
        """
        return {k: form_data.get(k) for k in form_data if k != exclude_key}

    @staticmethod
    def _require_form_field(form_data: Any, field_name: str) -> JSONResponse | None:
        """Check if a required form field exists.
        
        Args:
            form_data: Form data object from request.form().
            field_name: Name of required field.
            
        Returns:
            Error JSONResponse if field missing, None if present.
        """
        if not form_data.get(field_name):
            return LlmProxiesProvider._error_response(f"{field_name.capitalize()} is required")
        return None

    @staticmethod
    async def _format_response(response: Any, is_streaming: bool) -> JSONResponse | StreamingResponse:
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
            logger.info(f"Cache hit for models of provider '{provider_name}'")
            return cached_models
        
        # Cache miss, fetch from provider
        logger.info(f"fetching models of provider '{provider_name}'")
        client = self._get_openai_client(provider_name)
        
        # Get models from provider
        response = await client.models.list()
        if not response or not hasattr(response, "data") or not response.data:
            logger.warning(f"No models data found in response from provider '{provider_name}'")
            return []
        # Transform models to dict and add provider info
        models = [self._to_dict(model) for model in response.data]
        models= self._transform_models(models, provider_name)
        
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
    
    async def _get_models_endpoint(self,request: Request) -> dict[str, Any]:
        # For simplicity, we return a static list of models for each provider.
        # In a real implementation, you might want to cache this and refresh it periodically.
        provider = request.query_params.get("provider")
        models =await self._get_models_by_provider(provider) if provider else await self._get_all_models()
        return {"data": models}

    def _get_providers_endpoint(self) -> dict[str, Any]:
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

    @staticmethod
    def _split_params(
        body: dict[str, Any],
        known_params_set: set[str],
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Split request body into known API params and extra_body.

        Args:
            body: The raw request JSON body (or form data dict).
            known_params_set: Set of parameter names accepted by the API.

        Returns:
            Tuple of (known_params, extra_body). extra_body is None when
            there are no unknown keys.
        """
        known: dict[str, Any] = {}
        extra: dict[str, Any] = {}
        for key, value in body.items():
            if key in known_params_set:
                known[key] = value
            else:
                extra[key] = value
        return known, extra or None

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

    # Known Anthropic Messages API request parameters (documents accepted fields).
    _ANTHROPIC_MESSAGES_KNOWN_PARAMS: set[str] = {
        "model",
        "messages",
        "max_tokens",
        "system",
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
        "stream",
        "metadata",
        "tools",
        "tool_choice",
    }

    # Maps OpenAI finish_reason values to Anthropic stop_reason values.
    _FINISH_REASON_MAP: dict[str, str] = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
    }

    @staticmethod
    def _anthropic_to_openai_request(body: dict[str, Any], model_name: str) -> dict[str, Any]:
        """Convert an Anthropic Messages API request body to OpenAI chat completions format.

        Args:
            body: Raw Anthropic request body.
            model_name: Provider-stripped model name (e.g. "gpt-4o").

        Returns:
            Dict suitable for passing to the OpenAI client.
        """
        oai: dict[str, Any] = {"model": model_name}
        messages: list[dict[str, Any]] = []

        system: Any = body.get("system")
        if system:
            if isinstance(system, str):
                system_text: str = system
            else:
                system_text = " ".join(
                    str(blk.get("text", ""))
                    for blk in system
                    if isinstance(blk, dict) and blk.get("type") == "text"
                )
            messages.append({"role": "system", "content": system_text})

        raw_messages: list[Any] = body.get("messages") or []
        for msg in raw_messages:
            msg_dict_raw: dict[str, Any] = msg if isinstance(msg, dict) else {}
            role: str = str(msg_dict_raw.get("role") or "")
            content: Any = msg_dict_raw.get("content")

            if isinstance(content, str):
                messages.append({"role": role, "content": content})
                continue

            if not isinstance(content, list):
                messages.append({"role": role, "content": content})
                continue

            oai_content: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []
            tool_result_messages: list[dict[str, Any]] = []

            for block in content:
                block_d: dict[str, Any] = block if isinstance(block, dict) else {}
                block_type: Any = block_d.get("type")

                if block_type == "text":
                    oai_content.append({"type": "text", "text": str(block_d.get("text") or "")})

                elif block_type == "image":
                    source: dict[str, Any] = block_d.get("source") if isinstance(block_d.get("source"), dict) else {}
                    src_type: Any = source.get("type")
                    if src_type == "base64":
                        media_type: str = str(source.get("media_type") or "image/jpeg")
                        data: str = str(source.get("data") or "")
                        url: str = f"data:{media_type};base64,{data}"
                    elif src_type == "url":
                        url = str(source.get("url") or "")
                    else:
                        url = ""
                    oai_content.append({"type": "image_url", "image_url": {"url": url}})

                elif block_type == "tool_use":
                    tool_calls.append({
                        "id": str(block_d.get("id") or ""),
                        "type": "function",
                        "function": {
                            "name": str(block_d.get("name") or ""),
                            "arguments": json.dumps(block_d.get("input") or {}),
                        },
                    })

                elif block_type == "tool_result":
                    raw_result: Any = block_d.get("content") or ""
                    if isinstance(raw_result, list):
                        result_content: str = " ".join(
                            str(b.get("text") or "")
                            for b in raw_result
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    else:
                        result_content = str(raw_result)
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": str(block_d.get("tool_use_id") or ""),
                        "content": result_content,
                    })

            if tool_result_messages:
                messages.extend(tool_result_messages)
            elif tool_calls:
                assembled: dict[str, Any] = {"role": role}
                if oai_content:
                    assembled["content"] = oai_content
                assembled["tool_calls"] = tool_calls
                messages.append(assembled)
            elif len(oai_content) == 1 and oai_content[0].get("type") == "text":
                messages.append({"role": role, "content": str(oai_content[0].get("text") or "")})
            else:
                messages.append({"role": role, "content": oai_content})

        oai["messages"] = messages

        for param in ("max_tokens", "temperature", "top_p", "stream"):
            if param in body:
                oai[param] = body[param]

        if "stop_sequences" in body:
            oai["stop"] = body["stop_sequences"]

        metadata: Any = body.get("metadata")
        if isinstance(metadata, dict) and "user_id" in metadata:
            oai["user"] = metadata["user_id"]

        if "top_k" in body:
            oai["top_k"] = body["top_k"]

        raw_tools: Any = body.get("tools")
        if raw_tools:
            tools_list: list[Any] = raw_tools if isinstance(raw_tools, list) else []
            oai["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": str(t.get("name") or "") if isinstance(t, dict) else "",
                        "description": str(t.get("description") or "") if isinstance(t, dict) else "",
                        "parameters": t.get("input_schema") or {} if isinstance(t, dict) else {},
                    },
                }
                for t in tools_list
            ]

        raw_tool_choice: Any = body.get("tool_choice")
        if raw_tool_choice and isinstance(raw_tool_choice, dict):
            tool_choice: dict[str, Any] = raw_tool_choice
            tc_type: Any = tool_choice.get("type")
            if tc_type == "auto":
                oai["tool_choice"] = "auto"
            elif tc_type == "any":
                oai["tool_choice"] = "required"
            elif tc_type == "tool":
                oai["tool_choice"] = {
                    "type": "function",
                    "function": {"name": str(tool_choice.get("name") or "")},
                }

        return oai

    @staticmethod
    def _openai_to_anthropic_response(response: Any, model_id: str) -> dict[str, Any]:
        """Convert an OpenAI chat completion response to Anthropic Messages API format.

        Args:
            response: OpenAI response object or dict.
            model_id: Original model ID from the Anthropic request (e.g. "openai_gpt-4o").

        Returns:
            Dict conforming to the Anthropic Messages API response schema.
        """
        resp_dict: dict[str, Any] = LlmProxiesProvider._to_dict(response)

        choices: list[Any] = resp_dict.get("choices") or []
        choice: dict[str, Any] = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}

        message: dict[str, Any] = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        content: list[dict[str, Any]] = []

        text: Any = message.get("content")
        if text:
            content.append({"type": "text", "text": str(text)})

        raw_tool_calls: Any = message.get("tool_calls")
        for tc in (raw_tool_calls if isinstance(raw_tool_calls, list) else []):
            tc_d: dict[str, Any] = tc if isinstance(tc, dict) else {}
            fn: dict[str, Any] = tc_d.get("function") if isinstance(tc_d.get("function"), dict) else {}
            try:
                input_data: Any = json.loads(str(fn.get("arguments") or "{}"))
            except (json.JSONDecodeError, ValueError):
                input_data = {}
            content.append({
                "type": "tool_use",
                "id": str(tc_d.get("id") or ""),
                "name": str(fn.get("name") or ""),
                "input": input_data,
            })

        finish_reason: str = str(choice.get("finish_reason") or "stop")
        stop_reason: str = LlmProxiesProvider._FINISH_REASON_MAP.get(finish_reason, "end_turn")

        usage_raw: dict[str, Any] = resp_dict.get("usage") if isinstance(resp_dict.get("usage"), dict) else {}
        usage = {
            "input_tokens": int(usage_raw.get("prompt_tokens") or 0),
            "output_tokens": int(usage_raw.get("completion_tokens") or 0),
        }

        return {
            "id": str(resp_dict.get("id") or ""),
            "type": "message",
            "role": "assistant",
            "content": content,
            "model": model_id,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": usage,
        }

    @staticmethod
    async def _format_anthropic_streaming_response(stream: Any, model_id: str) -> StreamingResponse:
        """Wrap an OpenAI SSE stream as Anthropic-format SSE events.

        Args:
            stream: Async iterable of OpenAI completion chunks.
            model_id: Original model ID from the Anthropic request.

        Returns:
            StreamingResponse emitting Anthropic SSE events.
        """
        async def generator():
            msg_id: str = "msg_stream"
            output_tokens: int = 0
            stop_reason: str = "end_turn"
            started: bool = False

            async for chunk in stream:
                chunk_dict: dict[str, Any] = LlmProxiesProvider._to_dict(chunk)

                if not started:
                    msg_id = str(chunk_dict.get("id") or "msg_stream")
                    yield (
                        f"event: message_start\n"
                        f"data: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': model_id, 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
                    )
                    yield (
                        f"event: content_block_start\n"
                        f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                    )
                    yield f"event: ping\ndata: {json.dumps({'type': 'ping'})}\n\n"
                    started = True

                raw_choices: Any = chunk_dict.get("choices")
                choices: list[Any] = raw_choices if isinstance(raw_choices, list) else []
                if choices:
                    choice: dict[str, Any] = choices[0] if isinstance(choices[0], dict) else {}
                    delta: dict[str, Any] = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
                    text: Any = delta.get("content")
                    if text:
                        yield (
                            f"event: content_block_delta\n"
                            f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': str(text)}})}\n\n"
                        )
                    raw_finish: Any = choice.get("finish_reason")
                    if raw_finish:
                        stop_reason = LlmProxiesProvider._FINISH_REASON_MAP.get(str(raw_finish), "end_turn")

                raw_usage: Any = chunk_dict.get("usage")
                if isinstance(raw_usage, dict):
                    usage: dict[str, Any] = raw_usage
                    output_tokens = int(usage.get("completion_tokens") or output_tokens)

            yield (
                f"event: content_block_stop\n"
                f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
            )
            yield (
                f"event: message_delta\n"
                f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason, 'stop_sequence': None}, 'usage': {'output_tokens': output_tokens}})}\n\n"
            )
            yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

        return StreamingResponse(generator(), media_type="text/event-stream")

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

