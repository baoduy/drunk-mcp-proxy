"""
Generic OAuth2 client credentials authentication for httpx.

Provides a reusable httpx.Auth base class with token caching, expiry handling,
optional token storage, and sync/async auth flows.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Generator

import httpx
from httpx_oauth.oauth2 import (
    GetAccessTokenError,
    OAuth2,
    OAuth2ClientAuthMethod,
    OAuth2Token,
)
from key_value.aio.protocols import AsyncKeyValue

from drunk_ai_proxy.app.cache_provider import CacheProvider

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

TokenPayload = dict[str, object]


class _ClientCredentialsOAuth2(OAuth2):
    """OAuth2 client with client credentials support."""

    async def get_client_credentials_token(self, scope: str | None) -> OAuth2Token:
        """Fetch a client-credentials token.

        Args:
            scope: Space-separated scope string, if required.

        Returns:
            OAuth2Token payload.
        """
        async with self.get_httpx_client() as client:
            data: dict[str, str] = {"grant_type": "client_credentials"}
            if scope:
                data["scope"] = scope

            request, auth = self.build_request(
                client,
                "POST",
                self.access_token_endpoint,
                auth_method=self.token_endpoint_auth_method,
                data=data,
            )
            response = await self.send_request(client, request, auth, exc_class=GetAccessTokenError)
            token = self.get_json(response, exc_class=GetAccessTokenError)
            return OAuth2Token(token)


class HttpxOauthBase(httpx.Auth):
    """
    Generic OAuth2 client credentials authentication provider.

    Subclasses can override `_build_token_request_data()` and
    `_build_token_request_headers()` to customize the token request.
    """

    def __init__(
        self,
        
        client_id: str,
        client_secret: str,
        authorize_endpoint: str,
        access_token_endpoint: str,
        *,
        name: str ="httpx-oauth",
        scopes: list[str] | None = None,
        token_storage: AsyncKeyValue | None = None,
        expires_in_buffer: int = 60,
        token_endpoint_auth_method: OAuth2ClientAuthMethod = "client_secret_post",
    ) -> None:
        """
        Initialize the OAuth2 authentication provider.

        Args:
            client_id: OAuth2 client ID.
            client_secret: OAuth2 client secret.
            token_url: OAuth2 token endpoint URL.
            scope: OAuth2 scope(s), space-separated if multiple.
            token_storage: Optional token storage adapter.
            expires_in_buffer: Buffer in seconds subtracted from expiry.
            token_endpoint_auth_method: httpx-oauth auth method for token endpoint.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._storage = token_storage or CacheProvider.get_oauth_store()
        self._expires_in_buffer = expires_in_buffer
        self._scope = " ".join(scopes) if scopes else None
        self._oauth_client = _ClientCredentialsOAuth2(
            client_id,
            client_secret,
            authorize_endpoint=authorize_endpoint,
            access_token_endpoint=access_token_endpoint,
            token_endpoint_auth_method=token_endpoint_auth_method,
            name=name,
        )

    @property
    def client_id(self) -> str:
        """Get the OAuth2 client ID."""
        return self._client_id

    @property
    def client_secret(self) -> str:
        """Get the OAuth2 client secret."""
        return self._client_secret

    @property
    def storage(self) -> AsyncKeyValue:
        """Get the token storage adapter."""
        return self._storage

    @property
    def scope(self) -> str | None:
        """Get the OAuth2 scope(s)."""
        return self._scope

    def _build_token_request_data(self) -> dict[str, str]:
        """
        Build form data for the token request.

        Returns:
            Token request form data.
        """
        data: dict[str, str] = {"grant_type": "client_credentials"}
        if self._scope:
            data["scope"] = self._scope
        return data

    def _get_storage_key(self) -> str:
        """
        Get the storage key used to persist tokens.

        Returns:
            Storage key string.
        """
        return self._client_id

    def _get_access_token(self, token: TokenPayload) -> str:
        """
        Extract the access token from a token payload.

        Args:
            token: Token payload.

        Returns:
            Access token string.

        Raises:
            KeyError: If access_token is missing.
        """
        access_token = token.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise KeyError("access_token")
        return access_token

    async def _async_fetch_token(self) -> TokenPayload:
        """
        Fetch a new OAuth2 token from the token endpoint.

        Returns:
            Token payload including expires_at.
        """
        token = await self._oauth_client.get_client_credentials_token(self._scope)
        raw_token: TokenPayload = dict(token)

        expires_in = raw_token.get("expires_in")
        if isinstance(expires_in, (int, float)):
            expires_in_seconds = int(expires_in)
        else:
            expires_in_seconds = 3600

        raw_token["expires_at"] = time.time() + expires_in_seconds - self._expires_in_buffer
        return raw_token

    @staticmethod
    def _is_token_expired_dict(token: TokenPayload | None) -> bool:
        """Check if a given token dictionary is expired."""
        if not token:
            return True
        expires_at = token.get("expires_at")
        if not isinstance(expires_at, (int, float)):
            return True
        return expires_at < time.time()

    async def _fetch_token(self) -> TokenPayload:
        """Backward-compatible alias for fetching a new token (async)."""
        return await self._async_fetch_token()

    async def _async_get_token(self) -> TokenPayload:
        """
        Get a valid OAuth2 token from storage or fetch a new one (async).

        Returns:
            Token payload with access_token key.
        """
        storage_key = self._get_storage_key()
        stored_token = await self._storage.get(storage_key)
        if isinstance(stored_token, dict) and not self._is_token_expired_dict(stored_token):
            return stored_token

        token = await self._fetch_token()
        await self._storage.put(storage_key, token)
        return token

    def _get_token(self) -> TokenPayload:
        """
        Get a valid OAuth2 token (sync wrapper).

        Returns:
            Token payload with access_token key.

        Raises:
            RuntimeError: If called from within an async context.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            raise RuntimeError(
                "Cannot use sync auth_flow in async context. "
                "Use async_auth_flow with httpx.AsyncClient instead."
            )

        return asyncio.run(self._async_get_token())

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Add the OAuth2 bearer token to the request (sync)."""
        token = self._get_token()
        request.headers["Authorization"] = f"Bearer {self._get_access_token(token)}"
        yield request

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        """Add the OAuth2 bearer token to the request (async)."""
        token = await self._async_get_token()
        request.headers["Authorization"] = f"Bearer {self._get_access_token(token)}"
        yield request
