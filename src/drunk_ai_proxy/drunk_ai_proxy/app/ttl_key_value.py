"""TTL-aware async key-value wrapper and cache entry model."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import TypedDict, cast

from key_value.aio.protocols.key_value import AsyncKeyValue

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class CacheEntry(TypedDict):
    value: object
    expires_at: float


class TTLAsyncKeyValue:
    """Wrapper for AsyncKeyValue that adds TTL (Time To Live) support."""

    def __init__(self, store: AsyncKeyValue, default_ttl_seconds: int = 15 * 60):
        """Initialize TTL wrapper.

        Args:
            store: Underlying AsyncKeyValue store.
            default_ttl_seconds: Default TTL in seconds (default: 15 minutes).
        """
        self.store = store
        self.default_ttl_seconds = default_ttl_seconds

    @staticmethod
    def _is_cache_entry(value: object) -> bool:
        return isinstance(value, Mapping) and "value" in value and "expires_at" in value

    async def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        """Set a value in the cache with optional TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expiration_time = time.time() + ttl
        entry: CacheEntry = {"value": value, "expires_at": expiration_time}
        await self.store.put(key, entry)

        logger.debug("Cache SET: key=%s, ttl=%ss, expires_at=%s", key, ttl, expiration_time)

    async def get(self, key: str) -> object | None:
        """Get a value from the cache, checking if it has expired."""
        raw_value = await self.store.get(key)

        if self._is_cache_entry(raw_value):
            entry = cast(CacheEntry, raw_value)
            expiration_time = entry["expires_at"]
            if time.time() > expiration_time:
                await self.delete(key)
                logger.debug("Cache GET: key=%s, EXPIRED (at %s)", key, expiration_time)
                return None
            logger.debug("Cache GET: key=%s, found=True", key)
            return entry["value"]

        if raw_value is not None:
            logger.warning("Cache GET: key=%s exists but has no TTL metadata", key)

        logger.debug("Cache GET: key=%s, found=%s", key, raw_value is not None)
        return raw_value

    async def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        await self.store.delete(key)
        logger.debug("Cache DELETE: key=%s", key)
