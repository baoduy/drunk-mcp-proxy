"""Transport helpers for LLM WebSocket proxy connections."""

from __future__ import annotations

import asyncio

import websockets
from websockets.asyncio.client import ClientConnection

from drunk_ai_proxy.utils import LlmConfig

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class WebSocketFactory:
    """Factory for creating backend WebSocket connections with auth.

    Manages WebSocket connections to backend providers with proper
    authentication headers and URLs from provider configuration.
    """

    def __init__(self, providers: list[LlmConfig]) -> None:
        """Initialize WebSocket factory.

        Args:
            providers: List of provider configurations.
        """
        self._provider_configs = {p.provider: p for p in providers}

    async def create_connection(self, provider_name: str) -> ClientConnection:
        """Create WebSocket connection to backend provider.

        Args:
            provider_name: Provider name from model ID.

        Returns:
            WebSocket connection to backend.

        Raises:
            ValueError: If provider not found or API key not configured.
            websockets.exceptions.WebSocketException: If connection fails.
        """
        provider_config = self._provider_configs.get(provider_name)
        if not provider_config:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")

        api_key = provider_config.api_key
        if not api_key:
            raise ValueError(f"API key not configured for provider '{provider_name}'")

        ws_url = self._build_websocket_url(provider_config)
        headers = {"Authorization": f"Bearer {api_key}"}
        logger.debug("Connecting to backend WebSocket: %s", ws_url)

        return await websockets.connect(ws_url, additional_headers=headers)

    @staticmethod
    def _build_websocket_url(provider_config: LlmConfig) -> str:
        """Build WebSocket URL from provider config.

        Args:
            provider_config: Provider configuration.

        Returns:
            WebSocket URL (e.g., wss://api.openai.com/v1/responses).
        """
        base_url = provider_config.base_url or "https://api.openai.com/v1"

        if base_url.startswith("https://"):
            ws_url = base_url.replace("https://", "wss://")
        elif base_url.startswith("http://"):
            ws_url = base_url.replace("http://", "ws://")
        else:
            ws_url = f"wss://{base_url}"

        if not ws_url.endswith("/v1"):
            ws_url = ws_url.rstrip("/") + "/v1"

        return f"{ws_url}/responses"


class BackendConnectionPool:
    """Pool for managing backend WebSocket connections per client identity.

    Maintains a mapping of (client_id, provider_name) to backend WebSocket
    connections, enabling connection reuse across multiple messages from the
    same client until disconnection.
    """

    def __init__(self) -> None:
        """Initialize connection pool."""
        self._connections: dict[tuple[str, str], ClientConnection] = {}
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    def _get_lock(self, client_id: str, provider_name: str) -> asyncio.Lock:
        """Get or create lock for given client-provider pair.

        Args:
            client_id: Client identifier.
            provider_name: Provider name.

        Returns:
            asyncio.Lock for the client-provider pair.
        """
        key = (client_id, provider_name)
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    @staticmethod
    def _check_connection_alive(backend_ws: ClientConnection | None) -> bool:
        """Check if backend WebSocket connection is still alive.

        Args:
            backend_ws: Backend WebSocket connection.

        Returns:
            True if connection is open, False otherwise.
        """
        if backend_ws is None:
            return False

        closed_attr = getattr(backend_ws, "closed", None)
        if isinstance(closed_attr, bool):
            return not closed_attr

        state = getattr(backend_ws, "state", None)
        if state is not None:
            state_name = getattr(state, "name", str(state))
            return str(state_name).upper() == "OPEN"

        open_attr = getattr(backend_ws, "open", None)
        if isinstance(open_attr, bool):
            return open_attr

        close_code = getattr(backend_ws, "close_code", None)
        if close_code is not None:
            return False

        return True

    async def get_connection(
        self,
        client_id: str,
        provider_name: str,
        ws_factory: WebSocketFactory,
    ) -> ClientConnection:
        """Get existing or create new backend WebSocket connection.

        Args:
            client_id: Client identifier (IP address or user ID).
            provider_name: Provider name from model ID.
            ws_factory: Factory for creating new connections.

        Returns:
            Backend WebSocket connection.

        Raises:
            ValueError: If provider not found or not configured.
            websockets.exceptions.WebSocketException: If connection fails.
        """
        key = (client_id, provider_name)
        lock = self._get_lock(client_id, provider_name)

        async with lock:
            existing_ws = self._connections.get(key)
            if existing_ws is not None and self._check_connection_alive(existing_ws):
                logger.debug(
                    "Reusing backend connection for client=%s, provider=%s",
                    client_id,
                    provider_name,
                )
                return existing_ws

            if existing_ws is not None:
                try:
                    await existing_ws.close()
                except Exception:
                    pass
                del self._connections[key]

            logger.debug(
                "Creating new backend connection for client=%s, provider=%s",
                client_id,
                provider_name,
            )
            new_ws = await ws_factory.create_connection(provider_name)
            self._connections[key] = new_ws
            return new_ws

    async def release_connection(self, client_id: str, provider_name: str) -> None:
        """Close and remove backend connection for given client-provider pair.

        Args:
            client_id: Client identifier.
            provider_name: Provider name.
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
                    client_id,
                    provider_name,
                )

    async def release_all_for_client(self, client_id: str) -> None:
        """Close and remove all backend connections for given client.

        Args:
            client_id: Client identifier.
        """
        keys_to_remove = [key for key in self._connections if key[0] == client_id]

        for key in keys_to_remove:
            connection_client_id, provider_name = key
            await self.release_connection(connection_client_id, provider_name)

        locks_to_remove = [key for key in self._locks if key[0] == client_id]
        for key in locks_to_remove:
            del self._locks[key]

        if keys_to_remove:
            logger.debug(
                "Released %d backend connection(s) for client=%s",
                len(keys_to_remove),
                client_id,
            )
