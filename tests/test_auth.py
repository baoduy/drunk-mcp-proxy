"""
Unit tests for auth.py module
Tests authentication functionality including API key management
"""

import pytest
import json
import os
import sys
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auth import (
    load_auth_config,
    save_auth_config_async,
    generate_api_key,
    hash_api_key,
    validate_api_key,
    create_api_key,
    revoke_api_key,
    enable_authentication,
    disable_authentication,
    is_auth_enabled,
    AUTH_CONFIG_FILE,
)


@pytest.fixture
def temp_auth_file(tmp_path):
    """Create a temporary auth config file"""
    auth_file = tmp_path / "auth.json"
    return str(auth_file)


@pytest.fixture
def mock_auth_config():
    """Return a mock auth configuration"""
    return {
        "enabled": True,
        "api_keys": {
            "client1": "hash1",
            "client2": "hash2"
        }
    }


class TestLoadAuthConfig:
    """Tests for load_auth_config function"""
    
    def test_load_auth_config_nonexistent_file(self):
        """Test loading config when file doesn't exist"""
        with patch('auth.AUTH_CONFIG_FILE', '/nonexistent/auth.json'):
            config = load_auth_config()
            assert config == {"enabled": False, "api_keys": {}}
    
    def test_load_auth_config_valid_file(self, temp_auth_file):
        """Test loading valid auth config"""
        test_config = {
            "enabled": True,
            "api_keys": {"test": "hash123"}
        }
        with open(temp_auth_file, 'w') as f:
            json.dump(test_config, f)
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            config = load_auth_config()
            assert config["enabled"] is True
            assert "test" in config["api_keys"]
    
    def test_load_auth_config_invalid_json(self, temp_auth_file, capsys):
        """Test loading config with invalid JSON"""
        with open(temp_auth_file, 'w') as f:
            f.write("invalid json{")
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            config = load_auth_config()
            assert config == {"enabled": False, "api_keys": {}}
            captured = capsys.readouterr()
            assert "Warning: Error loading auth config" in captured.out
    
    def test_load_auth_config_validation_failure(self, temp_auth_file, capsys):
        """Test loading config that fails validation"""
        test_config = {"invalid": "config"}
        with open(temp_auth_file, 'w') as f:
            json.dump(test_config, f)
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.validate_auth_config', return_value=False):
                config = load_auth_config()
                # Should still return the config but print warning
                captured = capsys.readouterr()
                assert "Warning: Auth configuration validation failed" in captured.out


class TestSaveAuthConfigAsync:
    """Tests for save_auth_config_async function"""
    
    @pytest.mark.asyncio
    async def test_save_auth_config_success(self, temp_auth_file):
        """Test saving auth config successfully"""
        config = {
            "enabled": True,
            "api_keys": {"client1": "a" * 64}  # Valid SHA-256 hash
        }
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            await save_auth_config_async(config)
            
            # Verify file was created and contains correct data
            assert os.path.exists(temp_auth_file)
            with open(temp_auth_file, 'r') as f:
                saved_config = json.load(f)
            assert saved_config == config
    
    @pytest.mark.asyncio
    async def test_save_auth_config_creates_directory(self, tmp_path):
        """Test that save creates parent directory if needed"""
        nested_path = tmp_path / "nested" / "dir" / "auth.json"
        config = {"enabled": False, "api_keys": {}}
        
        with patch('auth.AUTH_CONFIG_FILE', str(nested_path)):
            await save_auth_config_async(config)
            assert nested_path.exists()
    
    @pytest.mark.asyncio
    async def test_save_auth_config_validation_failure(self, temp_auth_file):
        """Test save fails when validation fails"""
        config = {"invalid": "config"}
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.validate_auth_config', return_value=False):
                with pytest.raises(ValueError, match="Auth configuration validation failed"):
                    await save_auth_config_async(config)
    
    @pytest.mark.asyncio
    async def test_save_auth_config_atomic_write(self, temp_auth_file):
        """Test that save uses atomic write (temp file + rename)"""
        config = {"enabled": False, "api_keys": {}}
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('os.replace') as mock_replace:
                with patch('builtins.open', mock_open()):
                    await save_auth_config_async(config)
                    # Verify os.replace was called for atomic write
                    mock_replace.assert_called_once()


class TestGenerateApiKey:
    """Tests for generate_api_key function"""
    
    def test_generate_api_key_returns_string(self):
        """Test that generate_api_key returns a string"""
        key = generate_api_key()
        assert isinstance(key, str)
        assert len(key) > 0
    
    def test_generate_api_key_unique(self):
        """Test that generated keys are unique"""
        keys = [generate_api_key() for _ in range(10)]
        assert len(keys) == len(set(keys))  # All unique
    
    def test_generate_api_key_format(self):
        """Test that generated key is URL-safe"""
        key = generate_api_key()
        # URL-safe base64 should only contain alphanumeric, -, _
        assert all(c.isalnum() or c in '-_' for c in key)


class TestHashApiKey:
    """Tests for hash_api_key function"""
    
    def test_hash_api_key_returns_string(self):
        """Test that hash_api_key returns a string"""
        hash_val = hash_api_key("test-key")
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64  # SHA256 hex is 64 characters
    
    def test_hash_api_key_consistent(self):
        """Test that hashing same key produces same hash"""
        key = "test-key-123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2
    
    def test_hash_api_key_different_keys(self):
        """Test that different keys produce different hashes"""
        hash1 = hash_api_key("key1")
        hash2 = hash_api_key("key2")
        assert hash1 != hash2


class TestValidateApiKey:
    """Tests for validate_api_key function"""
    
    def test_validate_api_key_auth_disabled(self):
        """Test validation when auth is disabled"""
        with patch('auth.load_auth_config', return_value={"enabled": False, "api_keys": {}}):
            is_valid, client = validate_api_key("any-key")
            assert is_valid is True
            assert client == "anonymous"
    
    def test_validate_api_key_no_key_provided(self):
        """Test validation when no key is provided"""
        with patch('auth.load_auth_config', return_value={"enabled": True, "api_keys": {}}):
            is_valid, client = validate_api_key(None)
            assert is_valid is False
            assert client is None
    
    def test_validate_api_key_valid_key(self):
        """Test validation with valid API key"""
        api_key = "test-key"
        key_hash = hash_api_key(api_key)
        config = {
            "enabled": True,
            "api_keys": {"test-client": key_hash}
        }
        
        with patch('auth.load_auth_config', return_value=config):
            is_valid, client = validate_api_key(api_key)
            assert is_valid is True
            assert client == "test-client"
    
    def test_validate_api_key_invalid_key(self):
        """Test validation with invalid API key"""
        config = {
            "enabled": True,
            "api_keys": {"client1": hash_api_key("correct-key")}
        }
        
        with patch('auth.load_auth_config', return_value=config):
            is_valid, client = validate_api_key("wrong-key")
            assert is_valid is False
            assert client is None
    
    def test_validate_api_key_multiple_clients(self):
        """Test validation with multiple clients"""
        key1 = "key1"
        key2 = "key2"
        config = {
            "enabled": True,
            "api_keys": {
                "client1": hash_api_key(key1),
                "client2": hash_api_key(key2)
            }
        }
        
        with patch('auth.load_auth_config', return_value=config):
            is_valid, client = validate_api_key(key2)
            assert is_valid is True
            assert client == "client2"


class TestCreateApiKey:
    """Tests for create_api_key function"""
    
    @pytest.mark.asyncio
    async def test_create_api_key_success(self, temp_auth_file):
        """Test creating a new API key"""
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.load_auth_config', return_value={"enabled": False, "api_keys": {}}):
                api_key = await create_api_key("test-client")
                
                assert isinstance(api_key, str)
                assert len(api_key) > 0
    
    @pytest.mark.asyncio
    async def test_create_api_key_stores_hash(self, temp_auth_file):
        """Test that created key is stored as hash"""
        initial_config = {"enabled": False, "api_keys": {}}
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.load_auth_config', return_value=initial_config):
                saved_config = None
                
                async def capture_save(config):
                    nonlocal saved_config
                    saved_config = config
                
                with patch('auth.save_auth_config_async', side_effect=capture_save):
                    api_key = await create_api_key("test-client")
                    
                    # Verify hash was stored, not plain key
                    assert "test-client" in saved_config["api_keys"]
                    stored_hash = saved_config["api_keys"]["test-client"]
                    assert stored_hash != api_key
                    assert stored_hash == hash_api_key(api_key)
    
    @pytest.mark.asyncio
    async def test_create_api_key_replaces_existing(self, temp_auth_file):
        """Test that creating key for existing client replaces old key"""
        initial_config = {
            "enabled": True,
            "api_keys": {"test-client": "old-hash"}
        }
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.load_auth_config', return_value=initial_config):
                saved_config = None
                
                async def capture_save(config):
                    nonlocal saved_config
                    saved_config = config
                
                with patch('auth.save_auth_config_async', side_effect=capture_save):
                    api_key = await create_api_key("test-client")
                    
                    # Verify new hash is different from old
                    new_hash = saved_config["api_keys"]["test-client"]
                    assert new_hash != "old-hash"


class TestRevokeApiKey:
    """Tests for revoke_api_key function"""
    
    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, temp_auth_file):
        """Test revoking an existing API key"""
        initial_config = {
            "enabled": True,
            "api_keys": {"test-client": "hash123"}
        }
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.load_auth_config', return_value=initial_config):
                saved_config = None
                
                async def capture_save(config):
                    nonlocal saved_config
                    saved_config = config
                
                with patch('auth.save_auth_config_async', side_effect=capture_save):
                    result = await revoke_api_key("test-client")
                    
                    assert result is True
                    assert "test-client" not in saved_config["api_keys"]
    
    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, temp_auth_file):
        """Test revoking a non-existent API key"""
        initial_config = {
            "enabled": True,
            "api_keys": {}
        }
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.load_auth_config', return_value=initial_config):
                result = await revoke_api_key("nonexistent-client")
                assert result is False


class TestEnableAuthentication:
    """Tests for enable_authentication function"""
    
    @pytest.mark.asyncio
    async def test_enable_authentication(self, temp_auth_file):
        """Test enabling authentication"""
        initial_config = {"enabled": False, "api_keys": {}}
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.load_auth_config', return_value=initial_config):
                saved_config = None
                
                async def capture_save(config):
                    nonlocal saved_config
                    saved_config = config
                
                with patch('auth.save_auth_config_async', side_effect=capture_save):
                    await enable_authentication()
                    assert saved_config["enabled"] is True


class TestDisableAuthentication:
    """Tests for disable_authentication function"""
    
    @pytest.mark.asyncio
    async def test_disable_authentication(self, temp_auth_file):
        """Test disabling authentication"""
        initial_config = {"enabled": True, "api_keys": {}}
        
        with patch('auth.AUTH_CONFIG_FILE', temp_auth_file):
            with patch('auth.load_auth_config', return_value=initial_config):
                saved_config = None
                
                async def capture_save(config):
                    nonlocal saved_config
                    saved_config = config
                
                with patch('auth.save_auth_config_async', side_effect=capture_save):
                    await disable_authentication()
                    assert saved_config["enabled"] is False


class TestIsAuthEnabled:
    """Tests for is_auth_enabled function"""
    
    def test_is_auth_enabled_true(self):
        """Test when authentication is enabled"""
        with patch('auth.load_auth_config', return_value={"enabled": True, "api_keys": {}}):
            assert is_auth_enabled() is True
    
    def test_is_auth_enabled_false(self):
        """Test when authentication is disabled"""
        with patch('auth.load_auth_config', return_value={"enabled": False, "api_keys": {}}):
            assert is_auth_enabled() is False
    
    def test_is_auth_enabled_missing_key(self):
        """Test when enabled key is missing"""
        with patch('auth.load_auth_config', return_value={"api_keys": {}}):
            assert is_auth_enabled() is False
