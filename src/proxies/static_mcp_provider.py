"""Static MCP Provider abstract base class.

This module provides an abstract base class for creating MCP provider implementations.
"""
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING
from app import GlobalAuthProvider
from src.tools.auth_config import AuthProviderType
from tools import SpecConfig

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


class StaticMcpProvider(ABC):
    """Abstract base class for MCP provider implementations."""

    def __init__(self, config: SpecConfig) -> None:
        """Initialize the StaticMcpProvider.

        Args:
            config: The SpecConfig instance for this provider.
        """
        self.config = config

    def _create_auth_provider(self, provider_name: AuthProviderType | None = None) -> AuthProvider | None:
        """Create and return an authentication handler.

        Returns:
            An Authentication provider instance for the provider.
        """
        return GlobalAuthProvider.get_auth_provider(provider_name)
