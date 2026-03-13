"""Factory for creating outbound client auth handlers."""

from __future__ import annotations

from typing import Any

import httpx

from drunk_ai_proxy.app.auth_type_registry import AuthTypeRegistry
from drunk_ai_proxy.utils import AuthType


class ClientAuthHandlerFactory:
    """Factory for creating outbound auth handlers by auth type."""

    @staticmethod
    def create(
        name: AuthType,
        config: dict[str, Any],
        provider_names: list[str],
    ) -> httpx.Auth:
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
        return AuthTypeRegistry.create_httpx_handler(
            name=name,
            config=config,
            provider_names=provider_names,
        )
