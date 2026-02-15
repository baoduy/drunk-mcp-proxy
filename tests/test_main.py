"""
Unit tests for src/main.py module.

Tests the main entry point for the MCP proxy server.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestMain:
    """Test suite for main() function."""

    @patch('src.main.MCPProxyServer')
    def test_main_creates_server_and_runs(self, mock_server_cls):
        """Test that main() creates MCPProxyServer and calls run()."""
        from src.main import main
        
        mock_server = Mock()
        mock_server_cls.return_value = mock_server
        
        main()
        
        mock_server_cls.assert_called_once()
        mock_server.run.assert_called_once()

    @patch('src.main.MCPProxyServer')
    def test_main_can_be_called_multiple_times(self, mock_server_cls):
        """Test that main() can be called multiple times."""
        from src.main import main
        
        mock_server = Mock()
        mock_server_cls.return_value = mock_server
        
        main()
        main()
        
        assert mock_server_cls.call_count == 2
        assert mock_server.run.call_count == 2
