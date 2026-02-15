"""Tools package for MCP proxy."""

from .azure_oauth import AzureOauth
from .spec_config import SpecConfig

__all__ = ["SpecConfig", "AzureOauth"]
