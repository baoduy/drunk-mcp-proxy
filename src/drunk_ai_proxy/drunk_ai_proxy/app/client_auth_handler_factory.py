"""Factory for creating outbound client auth handlers."""

from __future__ import annotations

from typing import Any

from drunk_ai_proxy.app.cache_provider import CacheProvider
from drunk_ai_proxy.utils import AuthType


class ClientAuthHandlerFactory:
    """Factory for creating outbound auth handlers by auth type."""

    @staticmethod
    def create(
        name: AuthType,
        config: dict[str, Any],
        provider_names: list[str],
    ) -> object:
        """Create an outbound httpx auth handler for the given auth type.

        Args:
            name: Auth provider type.
            config: Auth provider configuration.
            provider_names: Available provider names for error messages.

        Returns:
            Auth handler instance.

        Raises:
            ValueError: If provider type is unsupported.
        """
        match name:
            case AuthType.BASIC:
                from fastmcp.client.auth import BearerAuth

                return BearerAuth(**config)
            case AuthType.AZURE:
                from drunk_ai_proxy.auth import HttpxAzureOauth

                return HttpxAzureOauth(
                    client_id=config["client_id"],
                    client_secret=config["client_secret"],
                    tenant_id=config["tenant_id"],
                    token_storage=CacheProvider.get_oauth_store(),
                )
            case _:
                raise ValueError(
                    f"Unsupported authentication provider type: {name} in {provider_names}"
                )
