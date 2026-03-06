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

from key_value.aio.protocols import AsyncKeyValue

from drunk_ai_proxy.auth.httpx_oauth_base import HttpxOauthBase


class HttpxAzureOauth(HttpxOauthBase):
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
        oauth = HttpxAzureOauth(
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
        oauth = HttpxAzureOauth(
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
    ) -> None:
        """
        Initialize the Azure OAuth2 authentication provider.

        Args:
            client_id: Azure AD client ID (application ID).
            client_secret: Azure AD client secret.
            token_url: Azure AD token endpoint URL.
            scope: OAuth2 scope(s), space-separated if multiple.
            token_storage: Optional token storage adapter (for persistence/encryption).
        """
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            scope=scope,
            token_storage=token_storage,
        )
