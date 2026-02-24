from __future__ import annotations
import json
from app.app_config_provider import AppConfigProvider
from typing import TYPE_CHECKING, Any
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
        client = AsyncOpenAI(api_key=provider.api_key, base_url=provider.base_url)
        self._clients[provider.provider] = client
        return client
    
class LlmProxiesProvider:
    _BLOCKED_FORWARD_HEADERS = {
        "authorization",
        "proxy-authorization",
        "forwarded",
        "via",
        "connection",
        "keep-alive",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "host",
    }
    _BLOCKED_FORWARD_PREFIXES = ("x-forwarded-",)
    
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

    @staticmethod
    def _sanitize_error_message(error: Exception) -> str:
        """Sanitize error messages to prevent information exposure.
        
        Returns a generic error message while preserving user-actionable information.
        Sensitive information like API keys, paths, and internal details are removed.
        """
        error_str = str(error)
        # Preserve certain user-actionable error patterns
        if any(keyword in error_str for keyword in ["Missing required", "is required", "does not support"]):
            return error_str
        # Return generic message for all other errors to prevent information exposure
        return "An error occurred while processing the request"

    def mount(self, app: Starlette, route_prefix: str = "/llm/v1") -> None:
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
                "/completions",
                self._completions_endpoint,
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

            self._fastapi_app = app
        return self._fastapi_app

    @staticmethod
    def _parse_model_id(model_id: str) -> tuple[str, str]:
        """Parse model_id into provider_name and model_name.
        
        Args:
            model_id: Model identifier in format "provider/model_name"
            
        Returns:
            Tuple of (provider_name, model_name)
        """
        parts = model_id.split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        # If no "/" found, treat the whole string as model_name with empty provider
        return "", model_id

    @staticmethod
    def _collect_forward_headers(request: Request) -> dict[str, str]:
        forward_headers: dict[str, str] = {}
        for header_name, header_value in request.headers.items():
            header_name_lower = header_name.lower()
            if header_name_lower in LlmProxiesProvider._BLOCKED_FORWARD_HEADERS:
                continue
            if header_name_lower.startswith(LlmProxiesProvider._BLOCKED_FORWARD_PREFIXES):
                continue
            forward_headers[header_name] = header_value
        return forward_headers

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        """Convert a Pydantic model or dict to a dict."""
        if isinstance(obj, dict):
            return obj
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        else:
            return obj.__dict__

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

    @staticmethod
    def _transform_models(models: list[dict[str, Any]], provider: str) -> list[dict[str, Any]]:
        # This is a placeholder for any transformation logic you might want to apply to the models list.
        # For now, it just returns the input as-is.
        for model in models:
            model['provider'] = provider
            model['id'] = f"{provider}/{model.get('id', '')}"
        return models
    
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
        response = await client.models.list()
        models = [dict(model.model_dump() if hasattr(model, 'model_dump') else model.__dict__) for model in response.data]
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
    
    async def _fetch_all_models(self) -> dict[str, Any]:
        """Fetch all models from all providers and return as LlmModel instances."""
        models = await self._get_all_models()
        return {"data": models}
    
    async def _get_models_endpoint(self,request: Request) -> dict[str, Any]:
        # For simplicity, we return a static list of models for each provider.
        # In a real implementation, you might want to cache this and refresh it periodically.
        provider = request.query_params.get("provider")
        models =await self._get_models_by_provider(provider) if provider else await self._fetch_all_models()
        return {"data": models}

    def _get_providers_endpoint(self) -> dict[str, Any]:
        providers_list = [ProviderModel(name=p.provider, slug=p.provider) for p in self.providers]
        return {"data": [p.model_dump() for p in providers_list]}
    
    async def _embeddings_endpoint(self, request: Request):
        """Handle embeddings requests."""
        body = await request.json()
        model_id = body.get("model")
        if not model_id:
            return JSONResponse(content={"error": "Model ID is required"}, status_code=400)
        
        provider_name, model_name = self._parse_model_id(model_id)
        if not provider_name:
            return JSONResponse(content={"error": "Invalid model ID format. Expected 'provider/model_name'"}, status_code=400)
        
        client = self._get_openai_client(provider_name)
        
        try:
            body["model"] = model_name
            response = await client.embeddings.create(**body)
            response_dict = self._to_dict(response)
            return JSONResponse(content=response_dict)
        except Exception as e:
            sanitized_msg = self._sanitize_error_message(e)
            logger.error(f"Error calling embeddings for provider '{provider_name}': {type(e).__name__}")
            # Check if this is a user-actionable error
            if any(keyword in str(e) for keyword in ["Missing required", "does not support"]):
                return JSONResponse(
                    content={"error": {"message": sanitized_msg}}, 
                    status_code=400
                )
            return JSONResponse(
                content={"error": {"message": sanitized_msg}}, 
                status_code=500
            )
    
    async def _audio_transcriptions_endpoint(self, request: Request):
        """Handle audio transcriptions requests."""
        form_data = await request.form()
        model_id = form_data.get("model")
        if not model_id:
            return JSONResponse(content={"error": "Model ID is required"}, status_code=400)
        
        # Ensure model_id is a string
        model_id = str(model_id)
        provider_name, model_name = self._parse_model_id(model_id)
        if not provider_name:
            return JSONResponse(content={"error": "Invalid model ID format. Expected 'provider/model_name'"}, status_code=400)
        
        client = self._get_openai_client(provider_name)
        
        try:
            file = form_data.get("file")
            if not file:
                return JSONResponse(content={"error": "File is required"}, status_code=400)
            
            # Build kwargs from form data, excluding model and file
            kwargs = {}
            for key in form_data:
                if key not in ["model", "file"]:
                    kwargs[key] = form_data.get(key)
            
            response = await client.audio.transcriptions.create(
                model=model_name,
                file=file,  # type: ignore
                **kwargs
            )
            return JSONResponse(content=self._to_dict(response))
        except Exception as e:
            sanitized_msg = self._sanitize_error_message(e)
            logger.error(f"Error calling audio transcriptions for provider '{provider_name}': {type(e).__name__}")
            return JSONResponse(
                content={"error": f"Failed to call audio transcriptions: {sanitized_msg}"}, 
                status_code=500
            )
    
    async def _audio_translations_endpoint(self, request: Request):
        """Handle audio translations requests."""
        form_data = await request.form()
        model_id = form_data.get("model")
        if not model_id:
            return JSONResponse(content={"error": "Model ID is required"}, status_code=400)
        
        # Ensure model_id is a string
        model_id = str(model_id)
        provider_name, model_name = self._parse_model_id(model_id)
        if not provider_name:
            return JSONResponse(content={"error": "Invalid model ID format. Expected 'provider/model_name'"}, status_code=400)
        
        client = self._get_openai_client(provider_name)
        
        try:
            file = form_data.get("file")
            if not file:
                return JSONResponse(content={"error": "File is required"}, status_code=400)
            
            # Build kwargs from form data, excluding model and file
            kwargs = {}
            for key in form_data:
                if key not in ["model", "file"]:
                    kwargs[key] = form_data.get(key)
            
            response = await client.audio.translations.create(
                model=model_name,
                file=file,  # type: ignore
                **kwargs
            )
            return JSONResponse(content=self._to_dict(response))
        except Exception as e:
            sanitized_msg = self._sanitize_error_message(e)
            logger.error(f"Error calling audio translations for provider '{provider_name}': {type(e).__name__}")
            return JSONResponse(
                content={"error": f"Failed to call audio translations: {sanitized_msg}"}, 
                status_code=500
            )
    
    async def _images_generations_endpoint(self, request: Request):
        """Handle image generations requests."""
        body = await request.json()
        model_id = body.get("model")
        if not model_id:
            return JSONResponse(content={"error": "Model ID is required"}, status_code=400)
        
        provider_name, model_name = self._parse_model_id(model_id)
        if not provider_name:
            return JSONResponse(content={"error": "Invalid model ID format. Expected 'provider/model_name'"}, status_code=400)
        
        client = self._get_openai_client(provider_name)
        
        try:
            body["model"] = model_name
            response = await client.images.generate(**body)
            return JSONResponse(content=self._to_dict(response))
        except Exception as e:
            sanitized_msg = self._sanitize_error_message(e)
            logger.error(f"Error calling images.generate for provider '{provider_name}': {type(e).__name__}")
            return JSONResponse(
                content={"error": f"Failed to call images.generate: {sanitized_msg}"}, 
                status_code=500
            )
    
    async def _completions_endpoint(self, request: Request):
        """Handle legacy completions requests."""
        body = await request.json()
        model_id = body.get("model")
        if not model_id:
            return JSONResponse(content={"error": "Model ID is required"}, status_code=400)
        
        provider_name, model_name = self._parse_model_id(model_id)
        if not provider_name:
            return JSONResponse(content={"error": "Invalid model ID format. Expected 'provider/model_name'"}, status_code=400)
        
        client = self._get_openai_client(provider_name)
        
        try:
            body["model"] = model_name
            is_streaming = body.get("stream", False)
            response = await client.completions.create(**body)
            return await self._format_response(response, is_streaming)
        except Exception as e:
            sanitized_msg = self._sanitize_error_message(e)
            logger.error(f"Error calling completions for provider '{provider_name}': {type(e).__name__}")
            return JSONResponse(
                content={"error": f"Failed to call completions: {sanitized_msg}"}, 
                status_code=500
            )
    
    async def _chat_completions_endpoint(self,request: Request):
        # This is a placeholder for the chat completions endpoint implementation.
        # You would need to implement the logic to handle incoming requests, forward them to the appropriate provider,
        # and return the response in the expected format.
        body = await request.json()
        model_id = body.get("model")
        if not model_id:
            return JSONResponse(content={"error": "Model ID is required"}, status_code=400)
        # Extract provider name and model name from model ID
        provider_name, model_name = self._parse_model_id(model_id)
        if not provider_name:
            return JSONResponse(content={"error": "Invalid model ID format. Expected 'provider/model_name'"}, status_code=400)
        # Get the appropriate OpenAI client for the provider
        client = self._get_openai_client(provider_name)
        # Forward the request to the provider's chat completions endpoint
        
        try:
            body["model"] = model_name
            is_streaming = body.get("stream", False)

            response = await client.chat.completions.create(**body)
            return await self._format_response(response, is_streaming)
        except Exception as e:
            sanitized_msg = self._sanitize_error_message(e)
            logger.error(f"Error calling chat completions for provider '{provider_name}': {type(e).__name__}")
            # Check if this is a user-actionable error
            if any(keyword in str(e) for keyword in ["Missing required", "is required", "does not support"]):
                return JSONResponse(
                    content={"error": {"message": sanitized_msg}}, 
                    status_code=400
                )
            return JSONResponse(
                content={"error": {"message": sanitized_msg}}, 
                status_code=500
            )

