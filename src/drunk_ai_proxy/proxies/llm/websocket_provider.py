"""OpenAI WebSocket Mode Provider for Responses API.

This module implements a transparent WebSocket proxy that forwards messages between
clients and backend LLM providers (OpenAI, Ollama, etc.) with model ID transformation.

Architecture:
    Client (WebSocket) → LlmWebSocketProvider → Backend WebSocket Provider
                              ↓
                    Transform: provider_model → model

Message Flow:
    1. Client connects via WebSocket with bearer token
    2. Client sends any message with model format: provider_modelname
    3. Proxy transforms model ID and forwards to backend WebSocket
    4. Backend responses are forwarded directly to client
    5. Continuation with previous_response_id is handled by backend
"""

from __future__ import annotations

import json
from typing import Protocol

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
from drunk_ai_proxy.proxies.llm.base_provider import LlmBaseProvider
from drunk_ai_proxy.utils import LlmConfig
from drunk_ai_proxy.proxies.llm.websocket_transport import (
    BackendConnectionPool,
    WebSocketFactory,
)


class AsyncOpenAIFactoryProtocol(Protocol):
    """Protocol for AsyncOpenAI factory dependency."""

    def get_client(self, provider_name: str) -> AsyncOpenAI:
        """Get configured AsyncOpenAI client for provider."""
        ...


class LlmWebSocketProvider(LlmBaseProvider):
    """Provider for OpenAI WebSocket Mode (Responses API).

    Handles WebSocket connections at /api/v1/responses, manages per-connection state,
    and forwards requests to configured LLM backends.
    """

    def __init__(
        self,
        providers: list[LlmConfig],
    ) -> None:
        """Initialize WebSocket provider.

        Args:
            providers: List of LLM provider configurations

        Raises:
            ValueError: If no providers configured
        """
        super().__init__()
        if not providers or len(providers) == 0:
            raise ValueError("Llm websocket proxy requires at least one provider configuration")

        self.providers = providers
        self._provider_configs = {provider.provider: provider for provider in providers}
        self.ws_factory = WebSocketFactory(providers)
        self.open_ai_factory: AsyncOpenAIFactoryProtocol | None = None
        self.connection_pool = BackendConnectionPool()

    def _get_openai_factory(self) -> AsyncOpenAIFactoryProtocol:
        """Get or lazily create AsyncOpenAI factory.

        Returns:
            Shared AsyncOpenAI factory implementation.
        """
        if self.open_ai_factory is None:
            from drunk_ai_proxy.proxies.llm.client_factory import AsyncOpenAIFactory

            self.open_ai_factory = AsyncOpenAIFactory(self.providers)
        return self.open_ai_factory

    def _get_provider_config(self, provider_name: str) -> LlmConfig:
        """Get provider configuration by provider name.

        Args:
            provider_name: Provider name from model ID.

        Returns:
            Provider configuration.

        Raises:
            ValueError: If provider is not configured.
        """
        provider_config = self._provider_configs.get(provider_name)
        if provider_config is None:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        return provider_config

    def _supports_native_websocket(self, provider_name: str) -> bool:
        """Check if provider supports native backend websocket.

        Args:
            provider_name: Provider name from model ID.

        Returns:
            True when provider is configured with websocket support.
        """
        provider_config = self._get_provider_config(provider_name)
        return provider_config.websocket

    def mount(self, app: object, route_prefix: str) -> None:
        """Mount provider to Starlette application.
        
        Note: WebSocket endpoint is now registered directly on the LLM FastAPI app,
        so this method is a no-op stub to satisfy the abstract base class requirement.
        
        Args:
            app: Starlette application instance (unused)
            route_prefix: Route prefix for mounting (unused)
        """
        pass

    @staticmethod
    def create_error(
        error_code: str,
        message: str,
        status: int = 400,
    ) -> dict[str, object]:
        """Create standardized WebSocket error response.
        
        Args:
            error_code: Error code identifier (e.g., 'server_error', 'backend_connection_error')
            message: Human-readable error message
            status: HTTP status code (default: 400)
            
        Returns:
            Error response dictionary in OpenAI WebSocket format
        """
        return {
            "type": "error",
            "error": {
                "type": "llm_websocket_request_error",
                "code": error_code,
                "message": message,
            },
            "status": status,
        }
    
    def _extract_client_identity(self, websocket: WebSocket) -> str:
        """Extract stable client identifier from WebSocket connection.
        
        Uses authenticated user ID if available (via auth middleware),
        otherwise falls back to client IP address.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            Client identifier string (user ID or IP address)
        """
        # Check if auth middleware attached user ID
        if hasattr(websocket, "state") and hasattr(websocket.state, "user_id"):
            return str(websocket.state.user_id)
        
        # Fall back to IP address
        if websocket.client and websocket.client.host:
            return websocket.client.host
        
        # Last resort fallback
        return "unknown"
    
    async def websocket_response_endpoint(self, websocket: WebSocket) -> None:
        """Handle WebSocket connection lifecycle.
        
        Note: Authentication is handled by FastAPI middleware/dependencies.
        Backend enforces 60-minute connection timeout per OpenAI specs.

        Args:
            websocket: WebSocket connection object
        """
        self._logger.info("Llm websocket client connected: %s", websocket.client)
        # Accept connection (auth already validated by middleware)
        await websocket.accept()
        
        # Extract client identity for connection pooling
        client_id = self._extract_client_identity(websocket)
        self._logger.debug("Client identity: %s", client_id)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()

                # Forward message to backend
                await self._forward_to_backend(websocket, data, client_id)

        except WebSocketDisconnect:
            self._logger.debug("Llm websocket client disconnected")
        except Exception as e:
            self._logger.error("Llm websocket error: %s", type(e).__name__)
            try:
                error_msg = self.create_error(
                    "server_error",
                    "An error occurred while processing the request"
                )
                await websocket.send_json(error_msg)
            except Exception:
                pass
            finally:
                await websocket.close(code=1011, reason="Server error")
        finally:
            # Clean up all backend connections for this client
            await self.connection_pool.release_all_for_client(client_id)

    async def _forward_to_backend(
        self,
        websocket: WebSocket,
        data: dict[str, object],
        client_id: str,
    ) -> None:
        """Forward client message to backend with model ID transformation.

        Args:
            websocket: Client WebSocket connection
            data: Client message data
            client_id: Client identifier for connection pooling
        """
        try:
            # Extract and parse model ID to determine provider
            model = data.get("model", "")
            provider_name, model_name = self.parse_model_id(model)

            if not provider_name:
                error_msg = self.create_error(
                    "invalid_model_id",
                    "Invalid model ID format. Expected 'provider_model_name'",
                )
                await websocket.send_json(error_msg)
                return

            if self._supports_native_websocket(provider_name):
                await self._forward_to_native_backend(
                    websocket=websocket,
                    data=data,
                    client_id=client_id,
                    provider_name=provider_name,
                    model_name=model_name,
                )
            else:
                await self._forward_to_http_backend(
                    websocket=websocket,
                    data=data,
                    provider_name=provider_name,
                    model_name=model_name,
                )
        except Exception as e:
            self._logger.error("Error forwarding message: %s", type(e).__name__)
            error_msg = self.create_error(
                "server_error",
                "An error occurred while processing the request"
            )
            await websocket.send_json(error_msg)

    async def _forward_to_native_backend(
        self,
        websocket: WebSocket,
        data: dict[str, object],
        client_id: str,
        provider_name: str,
        model_name: str,
    ) -> None:
        """Forward request to provider native websocket backend.

        Args:
            websocket: Client websocket connection.
            data: Client request payload.
            client_id: Client identity for connection pooling.
            provider_name: Selected provider name.
            model_name: Model name without provider prefix.
        """
        try:
            backend_ws = await self.connection_pool.get_connection(
                client_id, provider_name, self.ws_factory
            )

            native_payload = dict(data)
            native_payload["model"] = model_name

            await backend_ws.send(json.dumps(native_payload))

            async for message in backend_ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                try:
                    event_dict = json.loads(message)
                except json.JSONDecodeError as e:
                    self._logger.error("Failed to decode backend message: %s", type(e).__name__)
                    continue

                await websocket.send_json(event_dict)
                if self._is_terminal_event(event_dict):
                    break

        except websockets.exceptions.WebSocketException as e:
            self._logger.error("Backend WebSocket error: %s", type(e).__name__)
            await self.connection_pool.release_connection(client_id, provider_name)
            error_msg = self.create_error(
                "backend_connection_error",
                "Backend service connection error"
            )
            await websocket.send_json(error_msg)

    @staticmethod
    def _build_fallback_payload(
        data: dict[str, object],
        model_name: str,
    ) -> dict[str, object]:
        """Transform websocket request payload into AsyncOpenAI responses payload.

        Args:
            data: Incoming websocket message payload.
            model_name: Provider-specific model name.

        Returns:
            Payload compatible with `client.responses.create`.
        """
        msg_type = data.get("type")
        if msg_type == "response.create" and isinstance(data.get("response"), dict):
            payload = dict(data["response"])
        else:
            payload = dict(data)
            payload.pop("type", None)

        payload["model"] = model_name
        return payload

    @staticmethod
    def _is_terminal_event(event_dict: dict[str, object]) -> bool:
        """Check whether a websocket event is terminal.

        Args:
            event_dict: Event payload dictionary.

        Returns:
            True for terminal events.
        """
        event_type = event_dict.get("type")
        return event_type in {
            "response.done",
            "response.completed",
            "response.failed",
            "error",
        }

    async def _forward_to_http_backend(
        self,
        websocket: WebSocket,
        data: dict[str, object],
        provider_name: str,
        model_name: str,
    ) -> None:
        """Forward request through AsyncOpenAI Responses API and emit websocket events.

        Args:
            websocket: Client websocket connection.
            data: Client request payload.
            provider_name: Selected provider name.
            model_name: Model name without provider prefix.
        """
        if data.get("previous_response_id"):
            error_msg = self.create_error(
                "unsupported_feature",
                "previous_response_id is not supported for non-websocket providers",
                status=400,
            )
            await websocket.send_json(error_msg)
            return

        client: AsyncOpenAI = self._get_openai_factory().get_client(provider_name)
        payload = self._build_fallback_payload(data, model_name)

        try:
            stream = await client.responses.create(stream=True, **payload)
        except Exception as e:
            self._logger.error("Fallback responses request failed: %s", type(e).__name__)
            error_msg = self.create_error(
                "backend_request_error",
                "Backend request failed",
                status=400,
            )
            await websocket.send_json(error_msg)
            return

        seen_terminal = False
        async for event in stream:
            event_dict = self._to_dict(event)
            if "type" not in event_dict:
                continue

            await websocket.send_json(event_dict)
            if self._is_terminal_event(event_dict):
                seen_terminal = True
                break

        if not seen_terminal:
            await websocket.send_json({"type": "response.done"})
