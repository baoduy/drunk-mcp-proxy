"""LLM model catalog service for provider model discovery and caching."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from drunk_ai_proxy.utils.protocols import TokenStore

from fastmcp.utilities import logging

logger = logging.get_logger(__name__)


class LlmModelCatalog:
    """Fetches, transforms, and caches model lists across LLM providers."""

    def __init__(
        self,
        providers: list[str],
        cache: TokenStore,
        get_client: Callable[[str], object],
        to_dict: Callable[[object], dict[str, object]],
    ) -> None:
        self._providers = providers
        self._cache = cache
        self._get_client = get_client
        self._to_dict = to_dict

    @staticmethod
    def _transform_models(models: list[dict[str, object]], provider: str) -> list[dict[str, object]]:
        for model in models:
            model["provider"] = provider
            model["id"] = f"{provider}_{model.get('id', '')}"
        return models

    @staticmethod
    def _cached_model_key(provider_name: str) -> str:
        return f"models_{provider_name}"

    async def _models_from_cache(self, key: str) -> list[dict[str, object]] | None:
        cached = await self._cache.get(key)
        if cached is not None:
            logger.info("Cache hit for models key '%s'", key)
            return cached  # type: ignore[return-value]
        return None

    async def _fetch_provider_models_from_remote(self, provider_name: str) -> list[dict[str, object]]:
        logger.info("Fetching models of provider '%s'", provider_name)
        client = self._get_client(provider_name)
        list_coro = getattr(getattr(client, "models"), "list")
        response = await list_coro()
        if not response or not hasattr(response, "data") or not response.data:
            logger.warning(
                "No models data found in response from provider '%s'",
                provider_name,
            )
            return []
        models = [self._to_dict(model) for model in response.data]
        models = self._transform_models(models, provider_name)
        cache_key = self._cached_model_key(provider_name)
        await self._cache.set(cache_key, models)
        return models

    async def get_models_by_provider(self, provider_name: str) -> list[dict[str, object]]:
        cache_key = self._cached_model_key(provider_name)
        cached = await self._models_from_cache(cache_key)
        if cached is not None:
            return cached
        return await self._fetch_provider_models_from_remote(provider_name)

    async def get_all_models(self) -> list[dict[str, object]]:
        results = await asyncio.gather(
            *[self.get_models_by_provider(provider_name) for provider_name in self._providers]
        )
        return [model for models in results for model in models]
