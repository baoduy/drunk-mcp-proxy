"""
MCP Proxy Configuration model.

This module provides the Pydantic model for MCP proxy configurations.
"""

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict


class McpProxyConfig(BaseModel):
    """
    Configuration model for MCP proxy instances.

    This model holds the configuration for a single MCP proxy,
    including its name and the associated FastMCP server instance.

    Attributes:
        path: The path identifier for the proxy
        mcp_server: The FastMCP server instance
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    path: str
    mcp_server: FastMCP
