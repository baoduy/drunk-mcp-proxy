"""Shared Protocol interfaces for cross-layer dependency inversion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from drunk_ai_proxy.utils.config_yaml import AuthType


class AuthProviderFactory(Protocol):
    """Interface for creating FastMCP auth providers and client auth handlers."""

    def get_fast_mcp_auth_provider(
        self,
        provider_name: "AuthType | None" = None,
    ) -> object | None: ...

    def get_client_auth_handler(
        self,
        provider_name: "AuthType | None" = None,
        auth_passthrough: bool = False,
    ) -> object | None: ...


class TokenStore(Protocol):
    """Interface for asynchronous key-value token/cache storage."""

    async def get(self, key: str) -> object | None: ...

    async def set(
        self,
        key: str,
        value: object,
        ttl_seconds: int | None = None,
    ) -> None: ...
