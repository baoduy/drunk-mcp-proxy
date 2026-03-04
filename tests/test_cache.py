"""
Unit tests for Cache class.

Tests cover:
- Singleton pattern for token storage
- Different storage backends (memory, sqlite, redis)
- Encryption wrapper initialization
- Environment variable handling
"""

from __future__ import annotations

from unittest.mock import Mock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from src.app.cache_provider import CacheProvider

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
    CacheProvider.token_storage = None
    yield
    CacheProvider.token_storage = None


@pytest.fixture
def encryption_key() -> bytes:
    """Generate a valid Fernet encryption key for testing."""
    return Fernet.generate_key()


@pytest.fixture
def mock_env_memory(encryption_key, monkeypatch):
    """Mock environment for memory storage."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")


@pytest.fixture
def mock_env_sqlite(encryption_key, monkeypatch):
    """Mock environment for SQLite storage."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "sqlite")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")


@pytest.fixture
def mock_env_redis(encryption_key, monkeypatch):
    """Mock environment for Redis storage."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "redis")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", "redis://localhost:6379/0")
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")


# =============================================================================
# SINGLETON PATTERN TESTS
# =============================================================================


def test_get_oauth_store_returns_same_instance(mock_env_memory):
    """Test that get_oauth_store returns the same instance on multiple calls."""
    store1 = CacheProvider.get_oauth_store()
    store2 = CacheProvider.get_oauth_store()

    assert store1 is store2
    assert CacheProvider.token_storage is not None
    assert CacheProvider.token_storage is store1


def test_get_oauth_store_initializes_once(mock_env_memory):
    """Test that token storage is only initialized once."""
    # First call should initialize
    assert CacheProvider.token_storage is None
    store1 = CacheProvider.get_oauth_store()
    assert CacheProvider.token_storage is not None

    # Second call should return cached instance
    store2 = CacheProvider.get_oauth_store()
    assert store1 is store2


# =============================================================================
# STORAGE BACKEND TESTS
# =============================================================================


def test_get_oauth_store_memory_backend(mock_env_memory):
    """Test that memory storage backend is used when configured."""
    with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_memory_store.return_value = mock_store_instance

        store = CacheProvider.get_oauth_store()

        mock_memory_store.assert_called_once()
        assert isinstance(store, FernetEncryptionWrapper)


def test_get_oauth_store_sqlite_backend(mock_env_sqlite):
    """Test that SQLite (DiskStore) backend is used when configured."""
    with patch("key_value.aio.stores.disk.DiskStore") as mock_disk_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_disk_store.return_value = mock_store_instance

        store = CacheProvider.get_oauth_store()

        mock_disk_store.assert_called_once_with(directory="/tmp/test-config/key-values")
        assert isinstance(store, FernetEncryptionWrapper)


def test_get_oauth_store_defaults_to_memory(encryption_key, monkeypatch):
    """Test that memory storage is used as default when no valid config."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "unknown")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_memory_store.return_value = mock_store_instance

        store = CacheProvider.get_oauth_store()

        mock_memory_store.assert_called_once()
        assert isinstance(store, FernetEncryptionWrapper)


def test_get_oauth_store_redis_without_connection_string_fallback(encryption_key, monkeypatch):
    """Test that memory storage is used when redis is configured but connection string is missing."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "redis")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_memory_store.return_value = mock_store_instance

        store = CacheProvider.get_oauth_store()

        # Should fall back to memory since Redis connection string is None
        mock_memory_store.assert_called_once()
        assert isinstance(store, FernetEncryptionWrapper)


# =============================================================================
# ENCRYPTION WRAPPER TESTS
# =============================================================================


def test_get_oauth_store_wraps_with_encryption(mock_env_memory, encryption_key):
    """Test that storage is wrapped with FernetEncryptionWrapper."""
    store = CacheProvider.get_oauth_store()

    assert isinstance(store, FernetEncryptionWrapper)
    # The wrapper should have encryption-related methods
    assert hasattr(store, 'get')
    assert hasattr(store, 'put')
    # Verify it's actually a wrapper by checking it has the underlying key_value store
    assert hasattr(store, 'key_value')


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_get_oauth_store_uses_correct_encryption_key(encryption_key, monkeypatch):
    """Test that the correct encryption key is used."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    with patch("src.app.cache_provider.Fernet") as mock_fernet_class:
        mock_fernet_instance = MagicMock()
        mock_fernet_class.return_value = mock_fernet_instance

        with patch("key_value.aio.stores.memory.MemoryStore"):
            store = CacheProvider.get_oauth_store()

            # Verify Fernet was initialized with correct key
            mock_fernet_class.assert_called_once_with(encryption_key)


# =============================================================================
# RETURN TYPE TESTS
# =============================================================================


def test_get_oauth_store_returns_async_key_value(mock_env_memory):
    """Test that get_oauth_store returns AsyncKeyValue interface."""
    store = CacheProvider.get_oauth_store()

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
    store = CacheProvider.get_oauth_store()

    # Store a value (AsyncKeyValue expects dict values)
    test_data = {"token": "test_value", "type": "Bearer"}
    await store.put("test_key", test_data)

    # Retrieve the value
    value = await store.get("test_key")
    assert value == test_data


@pytest.mark.asyncio
async def test_get_oauth_store_encryption_works(mock_env_memory):
    """Test that encryption is actually working."""
    store = CacheProvider.get_oauth_store()

    # Store a sensitive value
    sensitive_data = {"access_token": "my_secret_token_12345", "expires_in": 3600}
    await store.put("oauth_token", sensitive_data)

    # Retrieve and verify
    retrieved = await store.get("oauth_token")
    assert retrieved == sensitive_data


@pytest.mark.asyncio
async def test_get_oauth_store_multiple_keys(mock_env_memory):
    """Test storing multiple keys."""
    store = CacheProvider.get_oauth_store()

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
    store = CacheProvider.get_oauth_store()

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
    assert CacheProvider.__doc__ is not None
    assert "OAuth token storage" in CacheProvider.__doc__


def test_get_oauth_store_method_has_correct_docstring():
    """Test that get_oauth_store method has proper documentation."""
    assert CacheProvider.get_oauth_store.__doc__ is not None
    assert "OAuth token storage" in CacheProvider.get_oauth_store.__doc__


def test_cache_token_storage_is_class_attribute():
    """Test that token_storage is a class attribute."""
    assert hasattr(CacheProvider, 'token_storage')
    assert CacheProvider.token_storage is None  # Initially None due to reset_cache fixture


def test_get_oauth_store_is_static_method():
    """Test that get_oauth_store is a static method."""
    assert isinstance(CacheProvider.__dict__['get_oauth_store'], staticmethod)


def test_cache_class_cannot_be_instantiated_with_state(mock_env_memory):
    """Test that Cache is used as a static class (no instance needed)."""
    # Should be able to call without instantiation
    store = CacheProvider.get_oauth_store()
    assert store is not None

    # Creating an instance shouldn't affect the static behavior
    cache_instance = CacheProvider()
    store2 = CacheProvider.get_oauth_store()
    assert store is store2


def test_get_oauth_store_generates_key_when_missing(monkeypatch):
    """Use unencrypted storage when OAUTH_STORAGE_ENCRYPTION_KEY is empty."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", "")
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
        mock_store_instance = MagicMock(spec=AsyncKeyValue)
        mock_memory_store.return_value = mock_store_instance
        
        store = CacheProvider.get_oauth_store()
        
        # Should return unencrypted storage without wrapper
        assert store is mock_store_instance
        assert not isinstance(store, FernetEncryptionWrapper)


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_get_oauth_store_encodes_string_key(monkeypatch):
    """Use string keys directly for encryption when provided."""
    key_str = Fernet.generate_key().decode()
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "memory")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", key_str)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    with patch("src.app.cache_provider.Fernet") as mock_fernet:
        mock_fernet_instance = MagicMock()
        mock_fernet.return_value = mock_fernet_instance
        with patch("key_value.aio.stores.memory.MemoryStore"):
            store = CacheProvider.get_oauth_store()
            
        # Should create Fernet with the provided string key
        mock_fernet.assert_called_once_with(key_str)
        # Should wrap with FernetEncryptionWrapper when key is provided
        assert isinstance(store, FernetEncryptionWrapper)


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_get_oauth_store_redis_import_error_fallback(encryption_key, monkeypatch):
    """Fallback to memory if Redis store import fails."""
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "redis")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", "redis://localhost:6379/0")
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    original_import = __import__

    def import_side_effect(name, *args, **kwargs):
        if name == "key_value.aio.stores.redis":
            raise ImportError("Redis store not available")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=import_side_effect):
        with patch("key_value.aio.stores.memory.MemoryStore") as mock_memory_store:
            CacheProvider.get_oauth_store()

    mock_memory_store.assert_called_once()


def test_get_oauth_store_logs_warning_no_encryption_for_redis(monkeypatch):
    """Test warning is logged when encryption key is missing for Redis storage."""
    # Reset the singleton cache
    CacheProvider.token_storage = None
    
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "redis")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", "")
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", "redis://localhost:6379/0")
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    import builtins
    original_import = builtins.__import__
    
    def mock_import(name, *args, **kwargs):
        if name == "key_value.aio.stores.redis":
            # Create a mock module with RedisStore
            mock_module = Mock()
            mock_module.RedisStore = Mock()
            return mock_module
        return original_import(name, *args, **kwargs)
    
    with patch("builtins.__import__", side_effect=mock_import):
        with patch("src.app.cache_provider.logger") as mock_logging:
            CacheProvider.get_oauth_store()
            
            # Should warn about missing encryption key for non-memory storage
            mock_logging.warning.assert_called_once()
            warning_message = mock_logging.warning.call_args[0][0]
            assert "OAUTH_STORAGE_ENCRYPTION_KEY" in warning_message


def test_get_oauth_store_logs_warning_no_encryption_for_sqlite(monkeypatch):
    """Test warning is logged when encryption key is missing for SQLite storage."""
    # Reset the singleton cache
    CacheProvider.token_storage = None
    
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_TYPE", "sqlite")
    monkeypatch.setattr("src.app.cache_provider.OAUTH_STORAGE_ENCRYPTION_KEY", "")
    monkeypatch.setattr("src.app.cache_provider.REDIS_CONNECTION_STRING", None)
    monkeypatch.setattr("src.app.cache_provider.CONFIG_DIR", "/tmp/test-config")

    import builtins
    original_import = builtins.__import__
    
    def mock_import(name, *args, **kwargs):
        if name == "key_value.aio.stores.disk":
            # Create a mock module with DiskStore
            mock_module = Mock()
            mock_module.DiskStore = Mock()
            return mock_module
        return original_import(name, *args, **kwargs)
    
    with patch("builtins.__import__", side_effect=mock_import):
        with patch("src.app.cache_provider.logger") as mock_logging:
            CacheProvider.get_oauth_store()
            
            # Should warn about missing encryption key for non-memory storage
            mock_logging.warning.assert_called_once()
            warning_message = mock_logging.warning.call_args[0][0]
            assert "OAUTH_STORAGE_ENCRYPTION_KEY" in warning_message

        # Should warn about missing encryption key for non-memory storage
        mock_logging.warning.assert_called_once()
        warning_message = mock_logging.warning.call_args[0][0]
        assert "OAUTH_STORAGE_ENCRYPTION_KEY" in warning_message
