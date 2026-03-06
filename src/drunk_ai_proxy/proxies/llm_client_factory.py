"""Factory for creating configured AsyncOpenAI clients."""

from __future__ import annotations

from logging import Logger

from openai import AsyncOpenAI

from drunk_ai_proxy.tools import LlmConfig
from drunk_ai_proxy.tools.logging_config import setup_logging


class AsyncOpenAIFactory:
    """Factory for creating AsyncOpenAI clients with caching."""

    def __init__(self, providers: list[LlmConfig]) -> None:
        """Initialize the factory with configured LLM providers.

        Args:
            providers: List of LLM provider configurations.
        """
        self._logger: Logger = setup_logging(__name__)
        self._providers = providers
        self._clients: dict[str, AsyncOpenAI] = {}

    def get_client(self, provider_name: str) -> AsyncOpenAI:
        """Get or create an AsyncOpenAI client for the given provider.

        Args:
            provider_name: Provider name from configuration.

        Returns:
            Cached or newly created AsyncOpenAI client.

        Raises:
            ValueError: If provider is not configured.
        """
        provider = next((p for p in self._providers if p.provider == provider_name), None)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")

        if provider.provider in self._clients:
            return self._clients[provider.provider]

        if provider.api_key is not None and len(provider.api_key) > 0:
            client = AsyncOpenAI(api_key=provider.api_key, base_url=provider.base_url)
        else:
            client = AsyncOpenAI(base_url=provider.base_url)

        self._clients[provider.provider] = client
        return client
