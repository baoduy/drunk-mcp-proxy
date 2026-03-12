"""
Proxies package.

This package contains proxy providers for MCP and LLM services:
- llm: LLM proxy implementations (OpenAI, Anthropic, Mistral, etc.)
- mcp: MCP proxy implementations (static, OpenAPI)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm import LlmBaseProvider, LlmProxiesProvider
    from .mcp import (
        McpBaseProvider,
        McpProxyConfig,
        McpProxyProvider,
        StaticProxiesProvider,
    )

__all__ = [
    # LLM
    "LlmBaseProvider",
    "LlmProxiesProvider",
    # MCP
    "McpBaseProvider",
    "McpProxyConfig",
    "McpProxyProvider",
    "StaticProxiesProvider",
]


def __getattr__(name: str) -> object:
    if name in {"LlmBaseProvider", "LlmProxiesProvider"}:
        from . import llm

        return getattr(llm, name)

    if name in {
        "McpBaseProvider",
        "McpProxyConfig",
        "McpProxyProvider",
        "StaticProxiesProvider",
    }:
        from . import mcp

        return getattr(mcp, name)

    raise AttributeError(f"module 'proxies' has no attribute {name!r}")
