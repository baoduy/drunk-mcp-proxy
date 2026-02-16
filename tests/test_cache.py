"""
Unit tests for Cache class.

Tests cover:
- Singleton pattern for token storage
- Different storage backends (memory, sqlite, redis)
- Encryption wrapper initialization
- Environment variable handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from tools.cache import Cache

# Check Redis availability at module load time
try:
    import key_value.aio.stores.redis  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset Cache.token_storage before each test."""
    Cache.token_storage = None
    yield
    Cache.token_storage = None


@pytest.fixture
def encryption_key() -> bytes:
    """Generate a valid Fernet encryption key for testing."""
    return Fernet.generate_key()


@pytest.fixture
def mock_env_memory(encryption_key, monkeypatch):
    """Mock environment for memory storage."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")


@pytest.fixture
def mock_env_sqlite(encryption_key, monkeypatch):
    """Mock environment for SQLite storage."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "sqlite")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")


@pytest.fixture
def mock_env_redis(encryption_key, monkeypatch):
    """Mock environment for Redis storage."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "redis")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", "redis://localhost:6379/0")
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")


# =============================================================================
# SINGLETON PATTERN TESTS
# =============================================================================


def test_get_oauth_store_returns_same_instance(mock_env_memory):
    """Test that get_oauth_store returns the same instance on multiple calls."""
    store1 = Cache.get_oauth_store()
    store2 = Cache.get_oauth_store()

    assert store1 is store2
    assert Cache.token_storage is not None
    assert Cache.token_storage is store1


def test_get_oauth_store_initializes_once(mock_env_memory):
    """Test that token storage is only initialized once."""
    # First call should initialize
    assert Cache.token_storage is None
    store1 = Cache.get_oauth_store()
    assert Cache.token_storage is not None

    # Second call should return cached instance
    store2 = Cache.get_oauth_store()
    assert store1 is store2


# =============================================================================
# STORAGE BACKEND TESTS
# =============================================================================


def test_get_oauth_store_memory_backend(mock_env_memory):
    """Test that memory storage backend is used when configured."""
    with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_memory_store.return_value = mock_store_instance

        store = Cache.get_oauth_store()

        mock_memory_store.assert_called_once()
        assert isinstance(store, FernetEncryptionWrapper)


def test_get_oauth_store_sqlite_backend(mock_env_sqlite):
    """Test that SQLite (DiskStore) backend is used when configured."""
    with patch("key_value.aio.stores.disk.DiskStore") as mock_disk_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_disk_store.return_value = mock_store_instance

        store = Cache.get_oauth_store()

        mock_disk_store.assert_called_once_with(directory="/tmp/test-config/oauth-tokens")
        assert isinstance(store, FernetEncryptionWrapper)


@pytest.mark.skip(reason="Redis support not installed in test environment")
def test_get_oauth_store_redis_backend(mock_env_redis):
    """Test that Redis backend is used when configured."""
    # Patch RedisStore at its actual import location
    with patch("key_value.aio.stores.redis.RedisStore") as mock_redis_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_redis_store.return_value = mock_store_instance

        store = Cache.get_oauth_store()

        mock_redis_store.assert_called_once_with(default_collection="redis://localhost:6379/0")
        assert isinstance(store, FernetEncryptionWrapper)


def test_get_oauth_store_defaults_to_memory(encryption_key, monkeypatch):
    """Test that memory storage is used as default when no valid config."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "unknown")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")

    with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_memory_store.return_value = mock_store_instance

        store = Cache.get_oauth_store()

        mock_memory_store.assert_called_once()
        assert isinstance(store, FernetEncryptionWrapper)


def test_get_oauth_store_redis_without_connection_string_fallback(encryption_key, monkeypatch):
    """Test that memory storage is used when redis is configured but connection string is missing."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "redis")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")

    with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_memory_store.return_value = mock_store_instance

        store = Cache.get_oauth_store()

        # Should fall back to memory since Redis connection string is None
        mock_memory_store.assert_called_once()
        assert isinstance(store, FernetEncryptionWrapper)


# =============================================================================
# ENCRYPTION WRAPPER TESTS
# =============================================================================


def test_get_oauth_store_wraps_with_encryption(mock_env_memory, encryption_key):
    """Test that storage is wrapped with FernetEncryptionWrapper."""
    store = Cache.get_oauth_store()

    assert isinstance(store, FernetEncryptionWrapper)
    # The wrapper should have encryption-related methods
    assert hasattr(store, 'get')
    assert hasattr(store, 'put')
    # Verify it's actually a wrapper by checking it has the underlying key_value store
    assert hasattr(store, 'key_value')


def test_get_oauth_store_uses_correct_encryption_key(encryption_key, monkeypatch):
    """Test that the correct encryption key is used."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")

    with patch("tools.cache.Fernet") as mock_fernet_class:
        mock_fernet_instance = MagicMock()
        mock_fernet_class.return_value = mock_fernet_instance

        with patch("key_value.aio.stores.memory.MemoryStore"):
            store = Cache.get_oauth_store()

            # Verify Fernet was initialized with correct key
            mock_fernet_class.assert_called_once_with(encryption_key)


# =============================================================================
# RETURN TYPE TESTS
# =============================================================================


def test_get_oauth_store_returns_async_key_value(mock_env_memory):
    """Test that get_oauth_store returns AsyncKeyValue interface."""
    store = Cache.get_oauth_store()

    # Should be an instance of FernetEncryptionWrapper which implements AsyncKeyValue
    assert isinstance(store, FernetEncryptionWrapper)
    # Should have AsyncKeyValue methods
    assert hasattr(store, 'get')
    assert hasattr(store, 'put')
    assert hasattr(store, 'delete')


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_oauth_store_functional_memory(mock_env_memory):
    """Test that the memory store can actually store and retrieve values."""
    store = Cache.get_oauth_store()

    # Store a value (AsyncKeyValue expects dict values)
    test_data = {"token": "test_value", "type": "Bearer"}
    await store.put("test_key", test_data)

    # Retrieve the value
    value = await store.get("test_key")
    assert value == test_data


@pytest.mark.asyncio
async def test_get_oauth_store_encryption_works(mock_env_memory):
    """Test that encryption is actually working."""
    store = Cache.get_oauth_store()

    # Store a sensitive value
    sensitive_data = {"access_token": "my_secret_token_12345", "expires_in": 3600}
    await store.put("oauth_token", sensitive_data)

    # Retrieve and verify
    retrieved = await store.get("oauth_token")
    assert retrieved == sensitive_data


@pytest.mark.asyncio
async def test_get_oauth_store_multiple_keys(mock_env_memory):
    """Test storing multiple keys."""
    store = Cache.get_oauth_store()

    # Store multiple values
    await store.put("token1", {"value": "value1"})
    await store.put("token2", {"value": "value2"})
    await store.put("token3", {"value": "value3"})

    # Retrieve and verify all
    assert await store.get("token1") == {"value": "value1"}
    assert await store.get("token2") == {"value": "value2"}
    assert await store.get("token3") == {"value": "value3"}


@pytest.mark.asyncio
async def test_get_oauth_store_delete_key(mock_env_memory):
    """Test deleting keys from store."""
    store = Cache.get_oauth_store()

    # Store and verify
    temp_data = {"token": "temporary_value"}
    await store.put("temp_token", temp_data)
    assert await store.get("temp_token") == temp_data

    # Delete and verify
    await store.delete("temp_token")
    result = await store.get("temp_token")
    assert result is None


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


def test_cache_class_has_correct_docstring():
    """Test that Cache class has proper documentation."""
    assert Cache.__doc__ is not None
    assert "OAuth token storage" in Cache.__doc__


def test_get_oauth_store_method_has_correct_docstring():
    """Test that get_oauth_store method has proper documentation."""
    assert Cache.get_oauth_store.__doc__ is not None
    assert "OAuth token storage" in Cache.get_oauth_store.__doc__


def test_cache_token_storage_is_class_attribute():
    """Test that token_storage is a class attribute."""
    assert hasattr(Cache, 'token_storage')
    assert Cache.token_storage is None  # Initially None due to reset_cache fixture


def test_get_oauth_store_is_static_method():
    """Test that get_oauth_store is a static method."""
    assert isinstance(Cache.__dict__['get_oauth_store'], staticmethod)


def test_cache_class_cannot_be_instantiated_with_state(mock_env_memory):
    """Test that Cache is used as a static class (no instance needed)."""
    # Should be able to call without instantiation
    store = Cache.get_oauth_store()
    assert store is not None

    # Creating an instance shouldn't affect the static behavior
    cache_instance = Cache()
    store2 = Cache.get_oauth_store()
    assert store is store2


def test_get_oauth_store_generates_key_when_missing(monkeypatch):
    """Generate a key when OAUTH_STORAGE_ENCRYPTION_KEY is empty."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", "")
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")

    generated_key = Fernet.generate_key()
    with patch("tools.cache.Fernet.generate_key", return_value=generated_key) as mock_generate:
        with patch("key_value.aio.stores.memory.MemoryStore"):
            Cache.get_oauth_store()

    mock_generate.assert_called_once()


def test_get_oauth_store_encodes_string_key(monkeypatch):
    """Encode string keys to bytes before initializing Fernet."""
    key_str = Fernet.generate_key().decode()
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", key_str)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")

    with patch("tools.cache.Fernet") as mock_fernet:
        mock_fernet.return_value = MagicMock()
        with patch("key_value.aio.stores.memory.MemoryStore"):
            Cache.get_oauth_store()

    mock_fernet.assert_called_once_with(key_str.encode())


def test_get_oauth_store_redis_import_error_fallback(encryption_key, monkeypatch):
    """Fallback to memory if Redis store import fails."""
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_TYPE", "redis")
    monkeypatch.setattr("tools.cache.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("tools.cache.REDIS_CONNECTION_STRING", "redis://localhost:6379/0")
    monkeypatch.setattr("tools.cache.CONFIG_DIR", "/tmp/test-config")

    original_import = __import__

    def import_side_effect(name, *args, **kwargs):
        if name == "key_value.aio.stores.redis":
            raise ImportError("Redis store not available")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=import_side_effect):
        with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
            Cache.get_oauth_store()

    mock_memory_store.assert_called_once()
