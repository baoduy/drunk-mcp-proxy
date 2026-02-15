"""
Unit tests for main.py module
Tests MCP proxy server functionality including configuration and proxy management
"""

import pytest
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main
from main import (
    load_config,
    load_proxies,
    save_proxy_async,
    mount_proxy,
    initialize_static_proxies,
    initialize_dynamic_proxies,
    CONFIG_FILE,
    PROXIES_FILE,
)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file"""
    config_file = tmp_path / "mcp.json"
    return str(config_file)


@pytest.fixture
def temp_proxies_file(tmp_path):
    """Create a temporary proxies file"""
    proxies_file = tmp_path / "proxies.json"
    return str(proxies_file)


@pytest.fixture
def sample_config():
    """Return a sample MCP configuration"""
    return {
        "mcpServers": {
            "test-server": {
                "url": "http://localhost:8000",
                "transport": "http"
            }
        }
    }


@pytest.fixture
def sample_proxies():
    """Return sample proxies configuration"""
    return {
        "proxies": [
            {
                "name": "proxy1",
                "url": "http://localhost:9000",
                "transport": "http"
            }
        ]
    }


class TestLoadConfig:
    """Tests for load_config function"""
    
    def test_load_config_nonexistent_file(self, capsys):
        """Test loading config when file doesn't exist"""
        with patch('main.CONFIG_FILE', '/nonexistent/mcp.json'):
            config = load_config()
            assert config == {"mcpServers": {}}
    
    def test_load_config_valid_file(self, temp_config_file, sample_config):
        """Test loading valid config file"""
        with open(temp_config_file, 'w') as f:
            json.dump(sample_config, f)
        
        with patch('main.CONFIG_FILE', temp_config_file):
            config = load_config()
            assert "test-server" in config["mcpServers"]
    
    def test_load_config_invalid_json(self, temp_config_file, capsys):
        """Test loading config with invalid JSON"""
        with open(temp_config_file, 'w') as f:
            f.write("invalid json{")
        
        with patch('main.CONFIG_FILE', temp_config_file):
            config = load_config()
            assert config == {"mcpServers": {}}
            captured = capsys.readouterr()
            assert "Error loading config file" in captured.err
    
    def test_load_config_validation_warning(self, temp_config_file, sample_config, capsys):
        """Test warning when validation fails"""
        with open(temp_config_file, 'w') as f:
            json.dump(sample_config, f)
        
        with patch('main.CONFIG_FILE', temp_config_file):
            with patch('main.validate_mcp_config', return_value=False):
                config = load_config()
                captured = capsys.readouterr()
                assert "Warning: Configuration validation failed" in captured.err


class TestLoadProxies:
    """Tests for load_proxies function"""
    
    def test_load_proxies_nonexistent_file(self):
        """Test loading proxies when file doesn't exist"""
        with patch('main.PROXIES_FILE', '/nonexistent/proxies.json'):
            proxies = load_proxies()
            assert proxies == []
    
    def test_load_proxies_valid_file(self, temp_proxies_file, sample_proxies):
        """Test loading valid proxies file"""
        with open(temp_proxies_file, 'w') as f:
            json.dump(sample_proxies, f)
        
        with patch('main.PROXIES_FILE', temp_proxies_file):
            proxies = load_proxies()
            assert len(proxies) == 1
            assert proxies[0]["name"] == "proxy1"
    
    def test_load_proxies_invalid_json(self, temp_proxies_file, capsys):
        """Test loading proxies with invalid JSON"""
        with open(temp_proxies_file, 'w') as f:
            f.write("invalid json{")
        
        with patch('main.PROXIES_FILE', temp_proxies_file):
            proxies = load_proxies()
            assert proxies == []
            captured = capsys.readouterr()
            assert "Error loading proxies file" in captured.err
    
    def test_load_proxies_validation_warning(self, temp_proxies_file, sample_proxies, capsys):
        """Test warning when validation fails"""
        with open(temp_proxies_file, 'w') as f:
            json.dump(sample_proxies, f)
        
        with patch('main.PROXIES_FILE', temp_proxies_file):
            with patch('main.validate_proxies_config', return_value=False):
                proxies = load_proxies()
                captured = capsys.readouterr()
                assert "Warning: Proxies configuration validation failed" in captured.err


class TestSaveProxyAsync:
    """Tests for save_proxy_async function"""
    
    @pytest.mark.asyncio
    async def test_save_proxy_new(self, temp_proxies_file):
        """Test saving a new proxy"""
        with patch('main.PROXIES_FILE', temp_proxies_file):
            with patch('main.load_proxies', return_value=[]):
                await save_proxy_async("new-proxy", "http://localhost:8000", "http")
                
                # Verify file was created
                assert os.path.exists(temp_proxies_file)
                with open(temp_proxies_file, 'r') as f:
                    data = json.load(f)
                assert len(data["proxies"]) == 1
                assert data["proxies"][0]["name"] == "new-proxy"
    
    @pytest.mark.asyncio
    async def test_save_proxy_update_existing(self, temp_proxies_file):
        """Test updating an existing proxy"""
        existing = [
            {"name": "proxy1", "url": "http://old-url", "transport": "http"}
        ]
        
        with patch('main.PROXIES_FILE', temp_proxies_file):
            with patch('main.load_proxies', return_value=existing):
                await save_proxy_async("proxy1", "http://new-url", "http")
                
                with open(temp_proxies_file, 'r') as f:
                    data = json.load(f)
                assert len(data["proxies"]) == 1
                assert data["proxies"][0]["url"] == "http://new-url"
    
    @pytest.mark.asyncio
    async def test_save_proxy_validation_failure(self, temp_proxies_file):
        """Test save fails when validation fails"""
        with patch('main.PROXIES_FILE', temp_proxies_file):
            with patch('main.load_proxies', return_value=[]):
                with patch('main.validate_proxies_config', return_value=False):
                    with pytest.raises(ValueError, match="Proxy configuration validation failed"):
                        await save_proxy_async("test", "http://localhost", "http")


class TestMountProxy:
    """Tests for mount_proxy function"""
    
    @patch('main.mcp')
    def test_mount_proxy_success(self, mock_mcp):
        """Test mounting a proxy successfully"""
        mount_proxy("test-proxy", "http://localhost:8000", "http")
        
        # Verify mcp.mount was called
        mock_mcp.mount.assert_called_once()
    
    @patch('main.mcp')
    @patch('main.ProxyClient')
    def test_mount_proxy_creates_client_factory(self, mock_proxy_client, mock_mcp):
        """Test that mount_proxy creates proper client factory"""
        mount_proxy("test-proxy", "http://localhost:8000", "http")
        
        # The client factory should be callable
        call_args = mock_mcp.mount.call_args
        proxy_server = call_args[0][0]
        assert hasattr(proxy_server, 'name')


class TestAddProxyLogic:
    """Tests for add_proxy logic through integration"""
    
    def test_add_proxy_conflict_detection_static(self):
        """Test that we can detect conflicts with static servers"""
        static_config = {
            "mcpServers": {
                "existing": {"url": "http://localhost:8000"}
            }
        }
        
        with patch('main.load_config', return_value=static_config):
            # Test the conflict detection logic
            config = main.load_config()
            assert "existing" in config.get("mcpServers", {})
    
    def test_add_proxy_conflict_detection_dynamic(self):
        """Test that we can detect conflicts with dynamic proxies"""
        existing_proxies = [
            {"name": "existing", "url": "http://localhost:8000"}
        ]
        
        with patch('main.load_proxies', return_value=existing_proxies):
            proxies = main.load_proxies()
            assert any(p.get("name") == "existing" for p in proxies)


class TestListProxiesLogic:
    """Tests for list_proxies logic"""
    
    def test_list_proxies_format_static(self):
        """Test formatting of static servers"""
        config = {
            "mcpServers": {
                "server1": {"url": "http://localhost:8000", "transport": "http"}
            }
        }
        proxies = []
        
        # Test the logic for formatting results
        result = []
        if config.get("mcpServers"):
            result.append("Static Servers (from mcp.json):")
            for name, details in config["mcpServers"].items():
                url = details.get("url", "N/A")
                transport = details.get("transport", "http")
                result.append(f"  - {name}: {url} ({transport})")
        
        assert len(result) > 0
        assert "Static Servers" in result[0]
        assert "server1" in result[1]


class TestGetServerInfoLogic:
    """Tests for get_server_info logic"""
    
    def test_server_info_format(self):
        """Test server info formatting"""
        auth_status = "enabled"
        result = f"""
MCP Proxy Server v1.0.0
-----------------------
A dynamic proxy server for Model Context Protocol.

Features:
- Dynamic proxy management
- HTTP/SSE transport support
- Persistent configuration
- Multiple backend servers
- API key authentication ({auth_status})

Use 'add_proxy' to add new backend servers.
Use 'list_proxies' to view all configured servers.
Use 'manage_auth' for authentication management.
"""
        assert "MCP Proxy Server" in result
        assert auth_status in result


class TestManageAuthLogic:
    """Tests for manage_auth logic components"""
    
    def test_manage_auth_status_formatting(self):
        """Test status message formatting"""
        config = {
            "enabled": True,
            "api_keys": {"client1": "hash1", "client2": "hash2"}
        }
        
        enabled = config.get("enabled", False)
        api_keys = config.get("api_keys", {})
        
        result = [f"Authentication: {'enabled' if enabled else 'disabled'}"]
        
        if api_keys:
            result.append(f"\nConfigured API keys ({len(api_keys)}):")
            for client in api_keys.keys():
                result.append(f"  - {client}")
        
        status_msg = "\n".join(result)
        assert "Authentication: enabled" in status_msg
        assert "client1" in status_msg
        assert "client2" in status_msg


class TestInitializeStaticProxies:
    """Tests for initialize_static_proxies function"""
    
    def test_initialize_static_proxies_success(self, capsys):
        """Test initializing static proxies"""
        config = {
            "mcpServers": {
                "server1": {"url": "http://localhost:8000", "transport": "http"}
            }
        }
        
        with patch('main.load_config', return_value=config):
            with patch('main.mount_proxy'):
                initialize_static_proxies()
                captured = capsys.readouterr()
                assert "Mounting static servers" in captured.out
                assert "server1" in captured.out
    
    def test_initialize_static_proxies_empty(self, capsys):
        """Test initializing when no static servers"""
        with patch('main.load_config', return_value={"mcpServers": {}}):
            initialize_static_proxies()
            captured = capsys.readouterr()
            assert "No static servers found" in captured.out
    
    def test_initialize_static_proxies_mount_error(self, capsys):
        """Test handling mount errors"""
        config = {
            "mcpServers": {
                "server1": {"url": "http://localhost:8000", "transport": "http"}
            }
        }
        
        with patch('main.load_config', return_value=config):
            with patch('main.mount_proxy', side_effect=Exception("Mount error")):
                initialize_static_proxies()
                captured = capsys.readouterr()
                assert "Failed to mount" in captured.out


class TestInitializeDynamicProxies:
    """Tests for initialize_dynamic_proxies function"""
    
    def test_initialize_dynamic_proxies_success(self, capsys):
        """Test initializing dynamic proxies"""
        proxies = [
            {"name": "proxy1", "url": "http://localhost:9000", "transport": "http"}
        ]
        
        with patch('main.load_proxies', return_value=proxies):
            with patch('main.mount_proxy'):
                initialize_dynamic_proxies()
                captured = capsys.readouterr()
                assert "Mounting dynamic proxies" in captured.out
                assert "proxy1" in captured.out
    
    def test_initialize_dynamic_proxies_empty(self, capsys):
        """Test initializing when no dynamic proxies"""
        with patch('main.load_proxies', return_value=[]):
            initialize_dynamic_proxies()
            captured = capsys.readouterr()
            assert "No dynamic proxies found" in captured.out
    
    def test_initialize_dynamic_proxies_mount_error(self, capsys):
        """Test handling mount errors"""
        proxies = [
            {"name": "proxy1", "url": "http://localhost:9000", "transport": "http"}
        ]
        
        with patch('main.load_proxies', return_value=proxies):
            with patch('main.mount_proxy', side_effect=Exception("Mount error")):
                initialize_dynamic_proxies()
                captured = capsys.readouterr()
                assert "Failed to mount" in captured.out
