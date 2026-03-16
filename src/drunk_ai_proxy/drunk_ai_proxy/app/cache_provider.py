"""Cache providers and TTL wrapper utilities for auth token storage."""

from __future__ import annotations

from cryptography.fernet import Fernet
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from drunk_ai_proxy.app.ttl_key_value import CacheEntry, TTLAsyncKeyValue
from drunk_ai_proxy.utils.env import (
    REDIS_CONNECTION_STRING,
    OAUTH_STORAGE_TYPE,
    CONFIG_DIR,
    OAUTH_STORAGE_ENCRYPTION_KEY,
)

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class CacheProvider:
    """Static cache class for managing OAuth token storage and general caching."""

    token_storage: AsyncKeyValue | None = None
    cache_storage: TTLAsyncKeyValue | None = None

    @staticmethod
    def _create_key_value_store() -> AsyncKeyValue:
        """Create a new key-value store instance based on the configured storage type."""
        if (
            OAUTH_STORAGE_TYPE == "redis"
            and REDIS_CONNECTION_STRING is not None
            and len(REDIS_CONNECTION_STRING) > 0
        ):
            try:
                from key_value.aio.stores.redis import RedisStore
                return RedisStore(url=REDIS_CONNECTION_STRING)
            except ImportError:
                logger.warning("Redis store not available, falling back to memory store")

        if OAUTH_STORAGE_TYPE == "sqlite":
            from key_value.aio.stores.disk import DiskStore
            return DiskStore(directory=f"{CONFIG_DIR}/key-values")

        from key_value.aio.stores.memory import MemoryStore
        return MemoryStore()

    @staticmethod
    def get_oauth_store() -> AsyncKeyValue:
        """Get or create the OAuth token storage instance."""
        if CacheProvider.token_storage is not None:
            return CacheProvider.token_storage

        # log warning if encryption key is not set for non-memory storage types
        if len(OAUTH_STORAGE_ENCRYPTION_KEY) == 0 and OAUTH_STORAGE_TYPE != "memory":
            logger.warning(
                "OAUTH_STORAGE_ENCRYPTION_KEY is not set. "
                "This is not recommended for production environments "
                "when using non-memory storage types."
            )

        fernet = Fernet(OAUTH_STORAGE_ENCRYPTION_KEY) if OAUTH_STORAGE_ENCRYPTION_KEY else None
        key_value = CacheProvider._create_key_value_store()

        CacheProvider.token_storage = (
            FernetEncryptionWrapper(key_value=key_value, fernet=fernet) if fernet else key_value
        )
        assert CacheProvider.token_storage is not None
        return CacheProvider.token_storage

    @staticmethod
    def get_cache_store() -> TTLAsyncKeyValue:
        """Get or create a general-purpose cache storage instance with TTL support."""
        if CacheProvider.cache_storage is not None:
            return CacheProvider.cache_storage

        base_store = CacheProvider._create_key_value_store()
        CacheProvider.cache_storage = TTLAsyncKeyValue(base_store, default_ttl_seconds=15 * 60)

        logger.info("Cache store initialized with default TTL: 15 minutes")
        return CacheProvider.cache_storage
