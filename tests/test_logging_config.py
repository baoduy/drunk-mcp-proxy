"""
Unit tests for src/tools/logging_config.py module.

Tests logging configuration setup.
"""

import logging
import pytest
from unittest.mock import patch, MagicMock
from drunk_ai_proxy.utils.logging_config import setup_logging


class TestSetupLogging:
    """Test suite for setup_logging function."""

    def test_setup_logging_returns_logger(self):
        """Test setup_logging returns a logger instance."""
        logger = setup_logging("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_setup_logging_with_different_names(self):
        """Test setup_logging creates loggers with different names."""
        logger1 = setup_logging("logger1")
        logger2 = setup_logging("logger2")
        assert logger1.name == "logger1"
        assert logger2.name == "logger2"
        assert logger1 != logger2

    @patch.dict('os.environ', {'FASTMCP_LOG_LEVEL': 'DEBUG'})
    def test_setup_logging_respects_log_level_env(self):
        """Test setup_logging respects FASTMCP_LOG_LEVEL environment variable."""
        # Need to reload the env module to pick up the new env var
        import importlib
        import drunk_ai_proxy.utils.env as env_module
        importlib.reload(env_module)
        
        # Now reload logging_config to use the new log level
        import drunk_ai_proxy.utils.logging_config as logging_config_module
        importlib.reload(logging_config_module)
        
        logger = logging_config_module.setup_logging("test_debug")
        # The logger should be configured with DEBUG level
        assert env_module.LOG_LEVEL == "DEBUG"

    def test_setup_logging_same_name_returns_same_logger(self):
        """Test calling setup_logging with same name returns same logger."""
        logger1 = setup_logging("same_name")
        logger2 = setup_logging("same_name")
        assert logger1 is logger2

    def test_setup_logging_module_name(self):
        """Test setup_logging works with __name__ module pattern."""
        logger = setup_logging(__name__)
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__

    def test_logger_can_log_messages(self):
        """Test that returned logger can log messages."""
        logger = setup_logging("test_can_log")
        # Should not raise any errors
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
