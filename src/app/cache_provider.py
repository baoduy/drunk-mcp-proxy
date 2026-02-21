import time
from collections.abc import Mapping
from typing import Any, TypedDict, cast
from cryptography.fernet import Fernet
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from tools.logging_config import setup_logging
from tools.env import REDIS_CONNECTION_STRING, OAUTH_STORAGE_TYPE, CONFIG_DIR, OAUTH_STORAGE_ENCRYPTION_KEY

logging = setup_logging(__name__)


class CacheEntry(TypedDict):
    value: Any
    expires_at: float


class TTLAsyncKeyValue:
    """Wrapper for AsyncKeyValue that adds TTL (Time To Live) support.
    
    Stores TTL metadata inside CacheEntry.
    """

    def __init__(self, store: AsyncKeyValue, default_ttl_seconds: int = 15 * 60):
        """
        Initialize TTL wrapper.
        
        Args:
            store: Underlying AsyncKeyValue store
            default_ttl_seconds: Default TTL in seconds (default: 15 minutes)
        """
        self.store = store
        self.default_ttl_seconds = default_ttl_seconds

    @staticmethod
    def _is_cache_entry(value: Any) -> bool:
        return isinstance(value, Mapping) and "value" in value and "expires_at" in value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Set a value in the cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Optional custom TTL in seconds. If not provided, uses default.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expiration_time = time.time() + ttl
        
        # Store value and TTL metadata together in CacheEntry
        entry: CacheEntry = {"value": value, "expires_at": expiration_time}
        await self.store.put(key, entry)

        logging.debug(f"Cache SET: key={key}, ttl={ttl}s, expires_at={expiration_time}")

    async def get(self, key: str) -> Any | None:
        """
        Get a value from the cache, checking if it has expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        raw_value = await self.store.get(key)

        if self._is_cache_entry(raw_value):
            entry = cast(CacheEntry, raw_value)
            expiration_time = entry["expires_at"]
            if time.time() > expiration_time:
                await self.delete(key)
                logging.debug(f"Cache GET: key={key}, EXPIRED (at {expiration_time})")
                return None
            logging.debug(f"Cache GET: key={key}, found=True")
            return entry["value"]

        if raw_value is not None:
            logging.warning(f"Cache GET: key={key} exists but has no TTL metadata")

        logging.debug(f"Cache GET: key={key}, found={raw_value is not None}")
        return raw_value

    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        await self.store.delete(key)
        logging.debug(f"Cache DELETE: key={key}")


class CacheProvider:
    """Static cache class for managing OAuth token storage and general caching."""

    token_storage: AsyncKeyValue | None = None
    cache_storage: TTLAsyncKeyValue | None = None

    @staticmethod
    def _create_key_value_store() -> AsyncKeyValue:
        """Create a new key-value store instance based on the configured storage type."""
        
        if OAUTH_STORAGE_TYPE == "redis" and REDIS_CONNECTION_STRING is not None:
            from key_value.aio.stores.redis import RedisStore
            return RedisStore(default_collection=REDIS_CONNECTION_STRING)

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
            logging.warning(
                "OAUTH_STORAGE_ENCRYPTION_KEY is not set. This is not recommended for production environments when using non-memory storage types."
            )

        fernet = Fernet(OAUTH_STORAGE_ENCRYPTION_KEY) if OAUTH_STORAGE_ENCRYPTION_KEY else None
        key_value = CacheProvider._create_key_value_store()

        CacheProvider.token_storage = FernetEncryptionWrapper(key_value=key_value, fernet=fernet) if fernet else key_value
        assert CacheProvider.token_storage is not None
        return CacheProvider.token_storage
    
    @staticmethod
    def get_cache_store() -> TTLAsyncKeyValue:
        """Get or create a general-purpose cache storage instance with TTL support."""
        if CacheProvider.cache_storage is not None:
            return CacheProvider.cache_storage

        base_store = CacheProvider._create_key_value_store()
        CacheProvider.cache_storage = TTLAsyncKeyValue(base_store, default_ttl_seconds=15 * 60)
        
        logging.info(f"Cache store initialized with backend: {OAUTH_STORAGE_TYPE}, default TTL: 15 minutes")
        return CacheProvider.cache_storage
