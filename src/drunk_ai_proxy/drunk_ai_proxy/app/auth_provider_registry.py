"""FastMCP auth provider registry and factory."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from drunk_ai_proxy.app.auth_type_registry import AuthTypeRegistry
from drunk_ai_proxy.utils import AuthType

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


class AuthProviderRegistry:
    """Registry for creating FastMCP auth providers by auth type."""

    @staticmethod
    def create(
        name: AuthType,
        config: dict[str, Any],
        provider_names: list[str],
    ) -> "AuthProvider":
        """Create a FastMCP auth provider for the given auth type.

        Args:
            name: Auth provider type.
            config: Auth provider configuration.
            provider_names: Available provider names for error messages.

        Returns:
            FastMCP auth provider instance.

        Raises:
            ValueError: If provider type is unsupported.
        """
        return AuthTypeRegistry.create_fastmcp_provider(
            name=name,
            config=config,
            provider_names=provider_names,
        )
