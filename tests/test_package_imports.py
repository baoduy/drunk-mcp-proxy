"""
Unit tests for src/app/__init__.py and src/tools/__init__.py modules.

Tests package initialization and exports.
"""


class TestAppPackageImports:
    """Test suite for app package imports."""

    def test_import_mcp_proxy_server(self):
        """Test importing MCPProxyServer from app package."""
        from src.app import MCPProxyServer
        assert MCPProxyServer is not None
        assert MCPProxyServer.__name__ == "MCPProxyServer"

    def test_app_all_exports(self):
        """Test __all__ contains expected exports."""
        import src.app as app
        assert "MCPProxyServer" in app.__all__
        assert "CacheProvider" in app.__all__
        assert "GlobalAuthProvider" in app.__all__
        assert len(app.__all__) == 3


class TestToolsPackageImports:
    """Test suite for tools package imports."""

    def test_import_spec_config(self):
        """Test importing SpecConfig from tools package."""
        from src.tools import SpecConfig
        assert SpecConfig is not None
        assert SpecConfig.__name__ == "SpecConfig"

    def test_import_cache(self):
        """Test importing Cache from app package."""
        from src.app.cache_provider import CacheProvider
        assert CacheProvider is not None
        assert CacheProvider.__name__ == "CacheProvider"

    def test_tools_all_exports(self):
        """Test __all__ contains expected exports."""
        import src.tools as tools
        assert "SpecConfig" in tools.__all__
        assert "AuthConfig" in tools.__all__
        assert "AuthProviderType" in tools.__all__
        # Cache is exported from app, not tools
        assert len(tools.__all__) == 3
