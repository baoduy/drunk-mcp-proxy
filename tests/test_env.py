"""
Unit tests for src/tools/env.py module.

Tests environment variable configuration loading and defaults.
"""

import os
import pytest


class TestEnvConfiguration:
    """Test suite for environment configuration module."""

    def test_config_dir_default(self):
        """Test CONFIG_DIR defaults to 'data' when not set."""
        # Clear the environment variable if it exists
        env_backup = os.environ.pop("FASTMCP_CONFIG_DIR", None)
        
        try:
            # Reimport to get fresh defaults
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.CONFIG_DIR == "data"
        finally:
            # Restore environment
            if env_backup is not None:
                os.environ["FASTMCP_CONFIG_DIR"] = env_backup

    def test_config_dir_custom(self):
        """Test CONFIG_DIR reads from FASTMCP_CONFIG_DIR environment variable."""
        os.environ["FASTMCP_CONFIG_DIR"] = "/custom/path"
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.CONFIG_DIR == "/custom/path"
        finally:
            os.environ.pop("FASTMCP_CONFIG_DIR", None)

    def test_schema_dir_default(self):
        """Test SCHEMA_DIR defaults to 'schemas' when not set."""
        env_backup = os.environ.pop("FASTMCP_SCHEMA_DIR", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.SCHEMA_DIR == "schemas"
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_SCHEMA_DIR"] = env_backup

    def test_log_level_default(self):
        """Test LOG_LEVEL defaults to 'INFO' when not set."""
        env_backup = os.environ.pop("FASTMCP_LOG_LEVEL", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.LOG_LEVEL == "INFO"
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_LOG_LEVEL"] = env_backup

    def test_log_level_custom(self):
        """Test LOG_LEVEL reads from FASTMCP_LOG_LEVEL and converts to uppercase."""
        os.environ["FASTMCP_LOG_LEVEL"] = "debug"
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.LOG_LEVEL == "DEBUG"
        finally:
            os.environ.pop("FASTMCP_LOG_LEVEL", None)

    def test_server_name_default(self):
        """Test SERVER_NAME defaults to 'drunk-ai-proxy' when not set."""
        env_backup = os.environ.pop("FASTMCP_SERVER_NAME", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.SERVER_NAME == "drunk-ai-proxy"
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_SERVER_NAME"] = env_backup

    def test_server_name_strips_whitespace(self):
        """Test SERVER_NAME strips leading/trailing whitespace."""
        os.environ["FASTMCP_SERVER_NAME"] = "  my-server  "
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.SERVER_NAME == "my-server"
        finally:
            os.environ.pop("FASTMCP_SERVER_NAME", None)

    def test_server_version_default(self):
        """Test SERVER_VERSION defaults to '1.0.0' when not set."""
        env_backup = os.environ.pop("FASTMCP_SERVER_VERSION", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.SERVER_VERSION == "1.0.0"
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_SERVER_VERSION"] = env_backup

    def test_cors_allow_origins_default(self):
        """Test CORS_ALLOW_ORIGINS defaults to empty string when not set."""
        env_backup = os.environ.pop("FASTMCP_CORS_ALLOW_ORIGINS", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.CORS_ALLOW_ORIGINS == ""
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_CORS_ALLOW_ORIGINS"] = env_backup

    def test_cors_allow_origins_custom(self):
        """Test CORS_ALLOW_ORIGINS reads from environment and strips whitespace."""
        os.environ["FASTMCP_CORS_ALLOW_ORIGINS"] = "  https://example.com  "
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.CORS_ALLOW_ORIGINS == "https://example.com"
        finally:
            os.environ.pop("FASTMCP_CORS_ALLOW_ORIGINS", None)

    def test_host_default(self):
        """Test HOST defaults to '0.0.0.0' when not set."""
        env_backup = os.environ.pop("FASTMCP_HOST", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.HOST == "0.0.0.0"
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_HOST"] = env_backup

    def test_port_default(self):
        """Test PORT defaults to 9123 when not set."""
        env_backup = os.environ.pop("FASTMCP_PORT", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.PORT == 9123
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_PORT"] = env_backup

    def test_port_custom_valid(self):
        """Test PORT reads valid integer from environment."""
        os.environ["FASTMCP_PORT"] = "8080"
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.PORT == 8080
        finally:
            os.environ.pop("FASTMCP_PORT", None)

    def test_port_invalid_defaults(self):
        """Test PORT defaults to 9123 when invalid value provided."""
        os.environ["FASTMCP_PORT"] = "invalid"
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.PORT == 9123
        finally:
            os.environ.pop("FASTMCP_PORT", None)

    def test_oauth_storage_encryption_key_default(self):
        """Test OAUTH_STORAGE_ENCRYPTION_KEY defaults to empty string."""
        env_backup = os.environ.pop("FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY", None)
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.OAUTH_STORAGE_ENCRYPTION_KEY == ""
        finally:
            if env_backup is not None:
                os.environ["FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY"] = env_backup

    def test_oauth_storage_encryption_key_custom(self):
        """Test OAUTH_STORAGE_ENCRYPTION_KEY reads from environment and strips whitespace."""
        os.environ["FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY"] = "  test-key-123  "
        
        try:
            import importlib
            import src.tools.env as env_module
            importlib.reload(env_module)
            
            assert env_module.OAUTH_STORAGE_ENCRYPTION_KEY == "test-key-123"
        finally:
            os.environ.pop("FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY", None)

    def test_get_env_bool_false_values(self):
        """Test get_env_bool with false values."""
        from src.tools.env import get_env_bool

        os.environ["TEST_BOOL"] = "0"
        assert get_env_bool("TEST_BOOL", True) is False

        os.environ["TEST_BOOL"] = "false"
        assert get_env_bool("TEST_BOOL", True) is False

        os.environ["TEST_BOOL"] = "no"
        assert get_env_bool("TEST_BOOL", True) is False

        os.environ["TEST_BOOL"] = "off"
        assert get_env_bool("TEST_BOOL", True) is False

        os.environ.pop("TEST_BOOL", None)

    def test_get_env_bool_default_for_invalid(self):
        """Test get_env_bool returns default for invalid/empty values."""
        from src.tools.env import get_env_bool

        os.environ["TEST_BOOL"] = "maybe"
        assert get_env_bool("TEST_BOOL", True) is True
        assert get_env_bool("TEST_BOOL", False) is False

        os.environ["TEST_BOOL"] = ""
        assert get_env_bool("TEST_BOOL", True) is True

        os.environ.pop("TEST_BOOL", None)
