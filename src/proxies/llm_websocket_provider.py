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
from typing import Any

import websockets
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from starlette.applications import Starlette

from app.app_config_provider import AppConfigProvider
from proxies.llm_base_provider import LlmBaseProvider
from tools import setup_logging
from tools.env import SERVER_NAME, SERVER_VERSION
from tools import LlmConfig

logger = setup_logging(__name__)

class WebSocketFactory:
    """Factory for creating backend WebSocket connections with auth.
    
    Manages WebSocket connections to backend providers with proper
    authentication headers and URLs from provider configuration.
    """
    
    def __init__(self, providers: list[LlmConfig]) -> None:
        """Initialize WebSocket factory.
        
        Args:
            providers: List of provider configurations
        """
        self._provider_configs = {p.provider: p for p in providers}
    
    async def create_connection(
        self, provider_name: str
    ) -> Any:  # websockets.WebSocketClientProtocol
        """Create WebSocket connection to backend provider.
        
        Args:
            provider_name: Provider name from model ID
            
        Returns:
            WebSocket connection to backend
            
        Raises:
            ValueError: If provider not found or API key not configured
            websockets.exceptions.WebSocketException: If connection fails
        """
        # Get provider config
        provider_config = self._provider_configs.get(provider_name)
        if not provider_config:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        
        # Get API key
        api_key = provider_config.api_key
        if not api_key:
            raise ValueError(f"API key not configured for provider '{provider_name}'")
        
        # Build WebSocket URL
        ws_url = self._build_websocket_url(provider_config)
        
        # Create connection with Authorization header
        headers = {"Authorization": f"Bearer {api_key}"}
        logger.debug("Connecting to backend WebSocket: %s", ws_url)
        
        return await websockets.connect(ws_url, extra_headers=headers)
    
    @staticmethod
    def _build_websocket_url(provider_config: LlmConfig) -> str:
        """Build WebSocket URL from provider config.
        
        Args:
            provider_config: Provider configuration
            
        Returns:
            WebSocket URL (e.g., wss://api.openai.com/v1/responses)
        """
        base_url = provider_config.base_url or "https://api.openai.com/v1"
        
        # Convert HTTP(S) URL to WebSocket URL
        if base_url.startswith("https://"):
            ws_url = base_url.replace("https://", "wss://")
        elif base_url.startswith("http://"):
            ws_url = base_url.replace("http://", "ws://")
        else:
            # Assume wss:// if no scheme
            ws_url = f"wss://{base_url}"
        
        # Ensure /v1 suffix if not present
        if not ws_url.endswith("/v1"):
            ws_url = ws_url.rstrip("/") + "/v1"
        
        # Append /responses endpoint
        return f"{ws_url}/responses"


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
            raise ValueError("WebSocket proxy requires at least one provider configuration")

        self.providers = providers
        self.ws_factory = WebSocketFactory(providers)
        self._fastapi_app: FastAPI | None = None

    def mount(self, app: Starlette, route_prefix: str) -> None:
        """Mount WebSocket provider to Starlette app.

        Args:
            app: Starlette application
            route_prefix: Route prefix for mounting (e.g., "/api/v1")
        """
        logger.info("Mounting LLM WebSocket provider at prefix '%s'", route_prefix)
        fastapi_app = self._get_fastapi_app()
        app.mount(route_prefix, fastapi_app)

    def _get_fastapi_app(self) -> FastAPI:
        """Create internal FastAPI instance with WebSocket endpoint.

        Returns:
            FastAPI instance with /responses WebSocket route
        """
        if self._fastapi_app is None:
            dependencies = []
            
            auth = AppConfigProvider.get_instance().get_fast_mcp_auth_provider()
            if auth:
                from proxies.llm_proxies_provider import FastAuthMiddleware
                dependencies = [Depends(FastAuthMiddleware(auth_provider=auth))]
           
            app = FastAPI(
                title=SERVER_NAME,
                version=SERVER_VERSION,
                dependencies=dependencies,
            )
            app.add_websocket_route("/responses", self.websocket_response_endpoint)
            self._fastapi_app = app

        return self._fastapi_app

    @staticmethod
    def create_error(error_code: str, message: str, status: int = 500) -> dict[str, Any]:
        """Create standardized WebSocket error response.
        
        Args:
            error_code: Error code identifier (e.g., 'server_error', 'backend_connection_error')
            message: Human-readable error message
            status: HTTP status code (default: 500)
            
        Returns:
            Error response dictionary in OpenAI WebSocket format
        """
        return {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "code": error_code,
                "message": message,
            },
            "status": status,
        }
    
    async def websocket_response_endpoint(self, websocket: WebSocket) -> None:
        """Handle WebSocket connection lifecycle.
        
        Note: Authentication is handled by FastAPI middleware/dependencies.
        Backend enforces 60-minute connection timeout per OpenAI specs.

        Args:
            websocket: WebSocket connection object
        """
        logger.info("WebSocket client connected: %s", websocket.client)
        # Accept connection (auth already validated by middleware)
        await websocket.accept()
        
        # Track backend connection for reuse across messages
        backend_ws: Any = None  # websockets.WebSocketClientProtocol
        current_provider: str | None = None

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()

                # Forward message to backend
                backend_ws, current_provider = await self._forward_to_backend(
                    websocket, data, backend_ws, current_provider
                )

        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected")
        except Exception as e:
            logger.error("WebSocket error: %s", type(e).__name__)
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
            # Clean up backend WebSocket connection
            if backend_ws is not None:
                try:
                    await backend_ws.close()
                except Exception:
                    pass

    async def _forward_to_backend(
        self,
        websocket: WebSocket,
        data: dict[str, Any],
        backend_ws: Any,
        current_provider: str | None,
    ) -> tuple[Any, str | None]:
        """Forward client message to backend with model ID transformation.

        Args:
            websocket: Client WebSocket connection
            data: Client message data
            backend_ws: Existing backend WebSocket (for reuse)
            current_provider: Current provider name (for reuse check)
            
        Returns:
            Tuple of (backend_ws, provider_name) for connection reuse.
            Returns (None, None) on error.
        """
        try:
            # Extract and parse model ID to determine provider
            model = data.get("model", "")
            provider_name, model_name = self.parse_model_id(model)
            
            # Get or establish backend WebSocket connection
            backend_ws = await self._get_backend_websocket(
                provider_name, backend_ws, current_provider
            )
            
            # Transform model ID in message (provider_model -> model)
            data["model"] = model_name
            
            # Forward message to backend
            await backend_ws.send(json.dumps(data))
            
            # Forward backend responses to client (bidirectional)
            async for message in backend_ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                
                try:
                    event_dict = json.loads(message)
                    await websocket.send_json(event_dict)
                    
                    # Stop streaming after response.done or error
                    msg_type = event_dict.get("type")
                    if msg_type in ("response.done", "error"):
                        break
                        
                except json.JSONDecodeError as je:
                    logger.error("Failed to decode backend message: %s", type(je).__name__)
                    continue
            
            return backend_ws, provider_name

        except websockets.exceptions.WebSocketException as e:
            logger.error("Backend WebSocket error: %s", type(e).__name__)
            # Close backend connection on error
            if backend_ws is not None:
                try:
                    await backend_ws.close()
                except Exception:
                    pass
            error_msg = self.create_error(
                "backend_connection_error",
                "Backend service connection error"
            )
            await websocket.send_json(error_msg)
            return None, None
        except Exception as e:
            logger.error("Error forwarding message: %s", type(e).__name__)
            error_msg = self.create_error(
                "server_error",
                "An error occurred while processing the request"
            )
            await websocket.send_json(error_msg)
            return None, None

    async def _get_backend_websocket(
        self,
        provider_name: str,
        backend_ws: Any,
        current_provider: str | None,
    ) -> Any:  # websockets.WebSocketClientProtocol
        """Get or establish backend WebSocket connection (Auth 2: Proxy -> Service).

        Args:
            provider_name: Provider name from model ID
            backend_ws: Existing backend WebSocket (if any)
            current_provider: Current provider name (for reuse check)

        Returns:
            WebSocket connection to backend

        Raises:
            ValueError: If provider not found or not configured
            websockets.exceptions.WebSocketException: If connection fails
        """
        # Reuse existing connection if provider matches
        if backend_ws is not None and current_provider == provider_name:
            # Check if connection is still alive
            if not backend_ws.closed:
                return backend_ws
            else:
                # Connection closed, create new one below
                try:
                    await backend_ws.close()
                except Exception:
                    pass

        # Create new connection using factory
        return await self.ws_factory.create_connection(provider_name)
