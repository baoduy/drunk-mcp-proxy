"""
Integration tests for main.py tool functions
These tests use importlib to reload the module with mocked decorators
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
import importlib

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class MockFastMCP:
    """Mock FastMCP class that doesn't wrap functions"""
    
    def __init__(self, *args, **kwargs):
        self.tools = {}
        self.mounted = []
    
    def tool(self):
        """Mock tool decorator that doesn't wrap the function"""
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator
    
    def mount(self, proxy):
        """Mock mount method"""
        self.mounted.append(proxy)


@pytest.fixture
def mock_main_module():
    """Fixture that reloads main module with mocked FastMCP"""
    # Mock FastMCP before importing main
    mock_fastmcp = MockFastMCP()
    
    with patch('fastmcp.FastMCP', return_value=mock_fastmcp):
        with patch('fastmcp.server.proxy.ProxyClient'):
            with patch('fastmcp.server.proxy.FastMCPProxy'):
                # Remove main from sys.modules if it exists
                if 'main' in sys.modules:
                    del sys.modules['main']
                
                # Import main with mocked FastMCP
                import main as reloaded_main
                yield reloaded_main
                
                # Clean up
                if 'main' in sys.modules:
                    del sys.modules['main']


class TestToolFunctions:
    """Tests for tool functions with direct access"""
    
    @pytest.mark.asyncio
    async def test_add_proxy_success(self, mock_main_module):
        """Test add_proxy function succeeds"""
        with patch.object(mock_main_module, 'load_config', return_value={"mcpServers": {}}):
            with patch.object(mock_main_module, 'load_proxies', return_value=[]):
                with patch.object(mock_main_module, 'mount_proxy'):
                    with patch.object(mock_main_module, 'save_proxy_async', new_callable=AsyncMock):
                        result = await mock_main_module.add_proxy("test-proxy", "http://localhost:8000")
                        assert "✓ Added and mounted proxy" in result
    
    @pytest.mark.asyncio
    async def test_add_proxy_static_conflict(self, mock_main_module):
        """Test add_proxy detects static server conflict"""
        config = {"mcpServers": {"existing": {"url": "http://localhost:8000"}}}
        with patch.object(mock_main_module, 'load_config', return_value=config):
            result = await mock_main_module.add_proxy("existing", "http://localhost:9000")
            assert "✗ Cannot add proxy" in result
            assert "static server" in result
    
    @pytest.mark.asyncio
    async def test_add_proxy_dynamic_conflict(self, mock_main_module):
        """Test add_proxy detects dynamic proxy conflict"""
        proxies = [{"name": "existing", "url": "http://localhost:8000"}]
        with patch.object(mock_main_module, 'load_config', return_value={"mcpServers": {}}):
            with patch.object(mock_main_module, 'load_proxies', return_value=proxies):
                result = await mock_main_module.add_proxy("existing", "http://localhost:9000")
                assert "✗ Cannot add proxy" in result
                assert "dynamic proxy" in result
    
    @pytest.mark.asyncio
    async def test_add_proxy_mount_failure(self, mock_main_module):
        """Test add_proxy handles mount failure"""
        with patch.object(mock_main_module, 'load_config', return_value={"mcpServers": {}}):
            with patch.object(mock_main_module, 'load_proxies', return_value=[]):
                with patch.object(mock_main_module, 'mount_proxy', side_effect=Exception("Mount error")):
                    result = await mock_main_module.add_proxy("test", "http://localhost:8000")
                    assert "✗ Failed to mount proxy" in result
    
    def test_list_proxies_empty(self, mock_main_module):
        """Test list_proxies with no proxies"""
        with patch.object(mock_main_module, 'load_config', return_value={"mcpServers": {}}):
            with patch.object(mock_main_module, 'load_proxies', return_value=[]):
                result = mock_main_module.list_proxies()
                assert result == "No proxies configured"
    
    def test_list_proxies_static_only(self, mock_main_module):
        """Test list_proxies with static servers"""
        config = {"mcpServers": {"server1": {"url": "http://localhost:8000", "transport": "http"}}}
        with patch.object(mock_main_module, 'load_config', return_value=config):
            with patch.object(mock_main_module, 'load_proxies', return_value=[]):
                result = mock_main_module.list_proxies()
                assert "Static Servers" in result
                assert "server1" in result
    
    def test_list_proxies_dynamic_only(self, mock_main_module):
        """Test list_proxies with dynamic proxies"""
        proxies = [{"name": "proxy1", "url": "http://localhost:9000", "transport": "http"}]
        with patch.object(mock_main_module, 'load_config', return_value={"mcpServers": {}}):
            with patch.object(mock_main_module, 'load_proxies', return_value=proxies):
                result = mock_main_module.list_proxies()
                assert "Dynamic Proxies" in result
                assert "proxy1" in result
    
    def test_list_proxies_both(self, mock_main_module):
        """Test list_proxies with both static and dynamic"""
        config = {"mcpServers": {"server1": {"url": "http://localhost:8000"}}}
        proxies = [{"name": "proxy1", "url": "http://localhost:9000"}]
        with patch.object(mock_main_module, 'load_config', return_value=config):
            with patch.object(mock_main_module, 'load_proxies', return_value=proxies):
                result = mock_main_module.list_proxies()
                assert "Static Servers" in result
                assert "Dynamic Proxies" in result
    
    def test_get_server_info_auth_enabled(self, mock_main_module):
        """Test get_server_info with auth enabled"""
        with patch.object(mock_main_module, 'is_auth_enabled', return_value=True):
            result = mock_main_module.get_server_info()
            assert "MCP Proxy Server" in result
            assert "enabled" in result
    
    def test_get_server_info_auth_disabled(self, mock_main_module):
        """Test get_server_info with auth disabled"""
        with patch.object(mock_main_module, 'is_auth_enabled', return_value=False):
            result = mock_main_module.get_server_info()
            assert "MCP Proxy Server" in result
            assert "disabled" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_enable(self, mock_main_module):
        """Test manage_auth enable action"""
        with patch.object(mock_main_module, 'enable_authentication', new_callable=AsyncMock):
            result = await mock_main_module.manage_auth("enable")
            assert "✓ Authentication enabled" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_disable(self, mock_main_module):
        """Test manage_auth disable action"""
        with patch.object(mock_main_module, 'disable_authentication', new_callable=AsyncMock):
            result = await mock_main_module.manage_auth("disable")
            assert "✓ Authentication disabled" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_create_key(self, mock_main_module):
        """Test manage_auth create_key action"""
        with patch.object(mock_main_module, 'create_api_key', new_callable=AsyncMock, return_value="test-key-123"):
            result = await mock_main_module.manage_auth("create_key", "client1")
            assert "✓ API key created" in result
            assert "test-key-123" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_create_key_no_client(self, mock_main_module):
        """Test manage_auth create_key without client name"""
        result = await mock_main_module.manage_auth("create_key")
        assert "✗ Client name is required" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_create_key_failure(self, mock_main_module):
        """Test manage_auth create_key handles errors"""
        with patch.object(mock_main_module, 'create_api_key', new_callable=AsyncMock, side_effect=Exception("Error")):
            result = await mock_main_module.manage_auth("create_key", "client1")
            assert "✗ Failed to create API key" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_revoke_key(self, mock_main_module):
        """Test manage_auth revoke_key action"""
        with patch.object(mock_main_module, 'revoke_api_key', new_callable=AsyncMock, return_value=True):
            result = await mock_main_module.manage_auth("revoke_key", "client1")
            assert "✓ API key revoked" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_revoke_key_not_found(self, mock_main_module):
        """Test manage_auth revoke_key when not found"""
        with patch.object(mock_main_module, 'revoke_api_key', new_callable=AsyncMock, return_value=False):
            result = await mock_main_module.manage_auth("revoke_key", "client1")
            assert "✗ No API key found" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_revoke_key_no_client(self, mock_main_module):
        """Test manage_auth revoke_key without client name"""
        result = await mock_main_module.manage_auth("revoke_key")
        assert "✗ Client name is required" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_status(self, mock_main_module):
        """Test manage_auth status action"""
        config = {"enabled": True, "api_keys": {"client1": "hash1", "client2": "hash2"}}
        with patch.object(mock_main_module, 'load_auth_config', return_value=config):
            result = await mock_main_module.manage_auth("status")
            assert "Authentication: enabled" in result
            assert "client1" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_status_no_keys(self, mock_main_module):
        """Test manage_auth status with no keys"""
        config = {"enabled": False, "api_keys": {}}
        with patch.object(mock_main_module, 'load_auth_config', return_value=config):
            result = await mock_main_module.manage_auth("status")
            assert "disabled" in result
            assert "No API keys configured" in result
    
    @pytest.mark.asyncio
    async def test_manage_auth_unknown_action(self, mock_main_module):
        """Test manage_auth with unknown action"""
        result = await mock_main_module.manage_auth("unknown")
        assert "✗ Unknown action" in result
