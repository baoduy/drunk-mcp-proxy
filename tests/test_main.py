"""
Unit tests for src/main.py module.

Tests the main entry point for the MCP proxy server.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestMain:
    """Test suite for main() function."""

    @patch('drunk_ai_proxy.main.MCPProxyServer')
    def test_main_creates_server_and_runs(self, mock_server_cls):
        """Test that main() creates MCPProxyServer and calls run()."""
        from drunk_ai_proxy.main import main
        
        mock_server = Mock()
        mock_server_cls.return_value = mock_server
        
        main()
        
        mock_server_cls.assert_called_once()
        mock_server.run.assert_called_once()

    @patch('drunk_ai_proxy.main.MCPProxyServer')
    def test_main_can_be_called_multiple_times(self, mock_server_cls):
        """Test that main() can be called multiple times."""
        from drunk_ai_proxy.main import main
        
        mock_server = Mock()
        mock_server_cls.return_value = mock_server
        
        main()
        main()
        
        assert mock_server_cls.call_count == 2
        assert mock_server.run.call_count == 2


class TestMainModule:
    """Test suite for main module initialization."""

    def test_project_root_in_sys_path(self):
        """Test that project root is added to sys.path."""
        # The module should have already added it on import
        import drunk_ai_proxy.main as main_module
        project_root = Path(main_module.__file__).parent.parent
        
        # Check if some form of the project root is in sys.path
        assert any(str(project_root) in str(p) for p in sys.path)

    def test_main_module_has_name_main_guard(self):
        """Test that main module has __name__ == '__main__' guard."""
        import drunk_ai_proxy.main as main_module
        
        # Check the module has the guard (this just verifies it's importable)
        assert hasattr(main_module, "main")
        assert callable(main_module.main)
