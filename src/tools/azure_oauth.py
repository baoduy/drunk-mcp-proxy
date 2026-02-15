"""
Azure OAuth2 Client Credentials authentication module.

This module provides Azure AD (Entra ID) OAuth2 client credentials authentication
as a proper httpx.Auth subclass following the httpx authentication pattern.

It handles:
- Automatic token fetching and caching
- Token expiry detection and refresh
- Secure token storage via pluggable storage adapter
- Seamless integration with httpx.Client and httpx.AsyncClient
"""

from __future__ import annotations

import asyncio
import time
import typing

import httpx
from key_value.aio.protocols import AsyncKeyValue
from key_value.aio.stores.memory import MemoryStore


class AzureOauth(httpx.Auth):
    """
    Azure AD (Entra ID) OAuth2 client credentials authentication provider.

    Supports both sync and async flows with automatic token caching and refresh.

    This is a proper httpx.Auth subclass that implements the OAuth2 client
    credentials flow (RFC 6749) for Azure AD. It provides:

    - Automatic token fetching with dual-layer caching (in-memory + storage)
    - Token expiry detection and automatic refresh
    - Optional pluggable storage for token persistence
    - Full sync and async support via asyncio event loops
    - Graceful fallback when storage is unavailable

    Usage:
        # Async usage (recommended)
        oauth = AzureOauth(
            client_id="your-client-id",
            client_secret="your-client-secret",
            token_url="https://login.microsoftonline.com/tenant/oauth2/v2.0/token",
            scope="https://graph.microsoft.com/.default",
        )

        async with httpx.AsyncClient(auth=oauth) as client:
            response = await client.get("https://graph.microsoft.com/v1.0/users")

        # Sync usage (uses asyncio event loop)
        with httpx.Client(auth=oauth) as client:
            response = client.get("https://graph.microsoft.com/v1.0/users")

        # With token storage
        oauth = AzureOauth(
            client_id="...",
            client_secret="...",
            token_url="...",
            scope="...",
            token_storage=encrypted_token_storage,
        )
    """

    def __init__(
            self,
            client_id: str,
            client_secret: str,
            token_url: str,
            scope: str | None = None,
            *,
            token_storage: AsyncKeyValue | None = None,
    ):
        """
        Initialize the Azure OAuth2 authentication provider.

        Args:
            client_id: Azure AD client ID (application ID)
            client_secret: Azure AD client secret
            token_url: Azure AD token endpoint URL
            scope: OAuth2 scope(s), space-separated if multiple
            token_storage: Optional token storage adapter (for persistence/encryption)

        Examples:
            # Basic setup
            oauth = AzureOauth(
                client_id="my-client-id",
                client_secret="my-client-secret",
                token_url="https://login.microsoftonline.com/tenant/oauth2/v2.0/token",
                scope="https://graph.microsoft.com/.default",
            )

            # With token persistence
            oauth = AzureOauth(
                client_id="...",
                client_secret="...",
                token_url="...",
                scope="...",
                token_storage=token_storage_adapter,
            )
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scope = scope
        self.storage = token_storage or MemoryStore()
        self._cached_token: dict | None = None

    # =========================
    # TOKEN MANAGEMENT
    # =========================

    async def _async_fetch_token(self) -> dict:
        """
        Fetch a new OAuth2 token from the Azure AD token endpoint.

        Returns:
            Token dictionary with keys: access_token, token_type, expires_in, etc.

        Raises:
            httpx.HTTPStatusError: If token endpoint returns an error
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
            )

        response.raise_for_status()
        token = response.json()

        # Add expiry timestamp for local tracking (60-second buffer)
        token["expires_at"] = (
                time.time() + token.get("expires_in", 3600) - 60
        )

        return token

    @staticmethod
    def _is_token_expired_dict(token: dict) -> bool:
        """Check if a given token dictionary is expired."""
        if not token:
            return True
        return token.get("expires_at", 0) < time.time()

    async def _fetch_token(self) -> dict:
        """Backward-compatible alias for fetching a new token (async)."""
        return await self._async_fetch_token()

    async def _async_get_token(self) -> dict:
        """
        Get a valid OAuth2 token from storage or fetch new one (async).

        Token refresh logic:
        1. Check in-memory cache first
        2. Load from storage using client_id as key
        3. If valid (not expired), return
        4. If expired or not in storage, fetch new token from Azure AD
        5. Save to storage
        6. Return token

        Returns:
            Token dictionary with access_token key
        """
        # Check in-memory cache first
        if self._cached_token and not self._is_token_expired_dict(self._cached_token):
            return self._cached_token

        # Load from storage using client_id as key
        stored_token = await self.storage.get(self.client_id)
        if stored_token and not self._is_token_expired_dict(stored_token):
            self._cached_token = stored_token
            return stored_token

        # Fetch new token from Azure AD
        token = await self._fetch_token()
        # Save to storage using client_id as key
        await self.storage.put(self.client_id, token)
        self._cached_token = token

        return token

    def _get_token(self) -> dict:
        """
        Get a valid OAuth2 token (sync wrapper).

        Uses asyncio to run async token fetch in sync context.

        Returns:
            Token dictionary with access_token key

        Raises:
            RuntimeError: If called from within an async context
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # We're already in an async context, create new event loop in thread
            raise RuntimeError(
                "Cannot use sync auth_flow in async context. "
                "Use async_auth_flow with httpx.AsyncClient instead."
            )

        # Run async token fetch in new event loop
        return asyncio.run(self._async_get_token())

    # =========================
    # HTTPX AUTH FLOW
    # =========================

    def auth_flow(
            self, request: httpx.Request
    ) -> typing.Generator[httpx.Request, httpx.Response, None]:
        """
        Execute the authentication flow (synchronous).

        This is called by httpx.Client for synchronous requests.
        It fetches or retrieves a cached token and injects it into the request.

        Args:
            request: The HTTP request to authenticate

        Yields:
            The modified request with Authorization header set
        """
        token = self._get_token()
        request.headers["Authorization"] = f"Bearer {token['access_token']}"
        yield request

    async def async_auth_flow(
            self, request: httpx.Request
    ) -> typing.AsyncGenerator[httpx.Request, httpx.Response]:
        """
        Execute the authentication flow (asynchronous).

        This is called by httpx.AsyncClient for async requests.
        It fetches or retrieves a cached token and injects it into the request.

        Args:
            request: The HTTP request to authenticate

        Yields:
            The modified request with Authorization header set
        """
        token = await self._async_get_token()
        request.headers["Authorization"] = f"Bearer {token['access_token']}"
        yield request
