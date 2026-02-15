from cryptography.fernet import Fernet
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from .env import REDIS_CONNECTION_STRING, OAUTH_STORAGE_TYPE, CONFIG_DIR, OAUTH_STORAGE_ENCRYPTION_KEY


class Cache:
    """Static cache class for managing OAuth token storage."""

    token_storage: AsyncKeyValue | None = None

    @staticmethod
    def get_oauth_store() -> AsyncKeyValue:
        """Get or create the OAuth token storage instance."""
        if Cache.token_storage is not None:
            return Cache.token_storage

        # Generate or validate encryption key
        encryption_key = OAUTH_STORAGE_ENCRYPTION_KEY
        if not encryption_key or len(encryption_key) == 0:
            # Generate a temporary key for testing or when no key is configured
            # In production, this should be set via environment variable
            encryption_key = Fernet.generate_key()
        elif isinstance(encryption_key, str):
            # Convert string to bytes if needed
            encryption_key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key

        fernet = Fernet(encryption_key)
        key_value: AsyncKeyValue | None = None

        if OAUTH_STORAGE_TYPE == "redis" and REDIS_CONNECTION_STRING is not None:
            try:
                from key_value.aio.stores.redis import RedisStore
                key_value = RedisStore(default_collection=REDIS_CONNECTION_STRING)
            except ImportError:
                # Redis not available, will fall back to memory store
                pass

        if key_value is None and OAUTH_STORAGE_TYPE == "sqlite":
            from key_value.aio.stores.disk import DiskStore
            key_value = DiskStore(directory=f"{CONFIG_DIR}/oauth-tokens")

        if key_value is None:
            from key_value.aio.stores.memory import MemoryStore
            key_value = MemoryStore()

        # key_value is guaranteed to be non-None at this point
        assert key_value is not None
        Cache.token_storage = FernetEncryptionWrapper(key_value=key_value, fernet=fernet)
        assert Cache.token_storage is not None
        return Cache.token_storage
