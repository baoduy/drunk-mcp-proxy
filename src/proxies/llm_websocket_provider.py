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

import asyncio
import json
from typing import Any

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from proxies.llm_base_provider import LlmBaseProvider
from tools import setup_logging
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
        
        return await websockets.connect(ws_url, additional_headers=headers)
    
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


class BackendConnectionPool:
    """Pool for managing backend WebSocket connections per client identity.
    
    Maintains a mapping of (client_id, provider_name) to backend WebSocket
    connections, enabling connection reuse across multiple messages from the
    same client until disconnection.
    """
    
    def __init__(self) -> None:
        """Initialize connection pool."""
        self._connections: dict[tuple[str, str], Any] = {}  # (client_id, provider) -> backend_ws
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}  # Per-key locks for concurrency
    
    def _get_lock(self, client_id: str, provider_name: str) -> asyncio.Lock:
        """Get or create lock for given client-provider pair.
        
        Args:
            client_id: Client identifier
            provider_name: Provider name
            
        Returns:
            asyncio.Lock for the client-provider pair
        """
        key = (client_id, provider_name)
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
    
    @staticmethod
    def _check_connection_alive(backend_ws: Any) -> bool:
        """Check if backend WebSocket connection is still alive.
        
        Args:
            backend_ws: Backend WebSocket connection
            
        Returns:
            True if connection is open, False otherwise
        """
        return backend_ws is not None and not backend_ws.closed
    
    async def get_connection(
        self,
        client_id: str,
        provider_name: str,
        ws_factory: WebSocketFactory,
    ) -> Any:  # websockets.WebSocketClientProtocol
        """Get existing or create new backend WebSocket connection.
        
        Args:
            client_id: Client identifier (IP address or user ID)
            provider_name: Provider name from model ID
            ws_factory: Factory for creating new connections
            
        Returns:
            Backend WebSocket connection
            
        Raises:
            ValueError: If provider not found or not configured
            websockets.exceptions.WebSocketException: If connection fails
        """
        key = (client_id, provider_name)
        lock = self._get_lock(client_id, provider_name)
        
        async with lock:
            # Check if we have an existing connection
            existing_ws = self._connections.get(key)
            if self._check_connection_alive(existing_ws):
                logger.debug(
                    "Reusing backend connection for client=%s, provider=%s",
                    client_id, provider_name
                )
                return existing_ws
            
            # Clean up stale connection if present
            if existing_ws is not None:
                try:
                    await existing_ws.close()
                except Exception:
                    pass
                del self._connections[key]
            
            # Create new connection
            logger.debug(
                "Creating new backend connection for client=%s, provider=%s",
                client_id, provider_name
            )
            new_ws = await ws_factory.create_connection(provider_name)
            self._connections[key] = new_ws
            return new_ws
    
    async def release_connection(self, client_id: str, provider_name: str) -> None:
        """Close and remove backend connection for given client-provider pair.
        
        Args:
            client_id: Client identifier
            provider_name: Provider name
        """
        key = (client_id, provider_name)
        lock = self._get_lock(client_id, provider_name)
        
        async with lock:
            backend_ws = self._connections.get(key)
            if backend_ws is not None:
                try:
                    await backend_ws.close()
                except Exception:
                    pass
                del self._connections[key]
                logger.debug(
                    "Released backend connection for client=%s, provider=%s",
                    client_id, provider_name
                )
    
    async def release_all_for_client(self, client_id: str) -> None:
        """Close and remove all backend connections for given client.
        
        Args:
            client_id: Client identifier
        """
        # Find all keys for this client
        keys_to_remove = [key for key in self._connections if key[0] == client_id]
        
        for key in keys_to_remove:
            client_id, provider_name = key
            await self.release_connection(client_id, provider_name)
        
        # Clean up locks for this client
        locks_to_remove = [key for key in self._locks if key[0] == client_id]
        for key in locks_to_remove:
            del self._locks[key]
        
        if keys_to_remove:
            logger.debug(
                "Released %d backend connection(s) for client=%s",
                len(keys_to_remove), client_id
            )


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
        self.ws_factory = WebSocketFactory(providers)
        self.connection_pool = BackendConnectionPool()

    def mount(self, app: Any, route_prefix: str) -> None:
        """Mount provider to Starlette application.
        
        Note: WebSocket endpoint is now registered directly on the LLM FastAPI app,
        so this method is a no-op stub to satisfy the abstract base class requirement.
        
        Args:
            app: Starlette application instance (unused)
            route_prefix: Route prefix for mounting (unused)
        """
        pass

    @staticmethod
    def create_error(error_code: str, message: str, status: int = 400) -> dict[str, Any]:
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
        logger.info("Llm websocket client connected: %s", websocket.client)
        # Accept connection (auth already validated by middleware)
        await websocket.accept()
        
        # Extract client identity for connection pooling
        client_id = self._extract_client_identity(websocket)
        logger.debug("Client identity: %s", client_id)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()

                # Forward message to backend
                await self._forward_to_backend(websocket, data, client_id)

        except WebSocketDisconnect:
            logger.debug("Llm websocket client disconnected")
        except Exception as e:
            logger.error("Llm websocket error: %s",str(e))
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
        data: dict[str, Any],
        client_id: str,
    ) -> None:
        """Forward client message to backend with model ID transformation.

        Args:
            websocket: Client WebSocket connection
            data: Client message data
            client_id: Client identifier for connection pooling
        """
        provider_name: str | None = None
        
        try:
            # Extract and parse model ID to determine provider
            model = data.get("model", "")
            provider_name, model_name = self.parse_model_id(model)
            
            # Get or establish backend WebSocket connection from pool
            backend_ws = await self.connection_pool.get_connection(
                client_id, provider_name, self.ws_factory
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
                    logger.error("Failed to decode backend message: %s", str(je))
                    continue

        except websockets.exceptions.WebSocketException as e:
            logger.error("Backend WebSocket error: %s", str(e))
            # Release backend connection on error
            if provider_name is not None:
                await self.connection_pool.release_connection(client_id, provider_name)
            error_msg = self.create_error(
                "backend_connection_error",
                "Backend service connection error"
            )
            await websocket.send_json(error_msg)
        except Exception as e:
            logger.error("Error forwarding message: %s", str(e))
            error_msg = self.create_error(
                "server_error",
                "An error occurred while processing the request"
            )
            await websocket.send_json(error_msg)
