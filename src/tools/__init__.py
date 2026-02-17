"""Tools package for MCP proxy."""

from .auth_config import AuthConfig, AuthProviderType
from .spec_config import SpecConfig

__all__ = ["SpecConfig", "AuthConfig", "AuthProviderType"]
