"""
Unit tests for src/app/__init__.py and src/tools/__init__.py modules.

Tests package initialization and exports.
"""


class TestAppPackageImports:
    """Test suite for app package imports."""

    def test_import_mcp_proxy_server(self):
        """Test importing MCPProxyServer from app package."""
        from drunk_ai_proxy.app import MCPProxyServer
        assert MCPProxyServer is not None
        assert MCPProxyServer.__name__ == "MCPProxyServer"

    def test_app_all_exports(self):
        """Test __all__ contains expected exports."""
        import drunk_ai_proxy.app as app
        assert "MCPProxyServer" in app.__all__
        assert "CacheProvider" in app.__all__
        assert "AppConfigProvider" in app.__all__
        assert "SwaggerProvider" in app.__all__
        # The app module now exports more than just these core items
        assert len(app.__all__) >= 4


class TestToolsPackageImports:
    """Test suite for tools package imports."""

    def test_import_config_yaml(self):
        """Test importing ConfigYaml from tools package."""
        from drunk_ai_proxy.tools import ConfigYaml
        assert ConfigYaml is not None
        assert ConfigYaml.__name__ == "ConfigYaml"

    def test_import_cache(self):
        """Test importing Cache from app package."""
        from drunk_ai_proxy.app.cache_provider import CacheProvider
        assert CacheProvider is not None
        assert CacheProvider.__name__ == "CacheProvider"

    def test_tools_all_exports(self):
        """Test __all__ contains expected exports."""
        import drunk_ai_proxy.tools as tools
        assert "ConfigYaml" in tools.__all__
        assert "AuthConfig" in tools.__all__
        assert "AuthType" in tools.__all__
        # Check other key exports
        assert len(tools.__all__) >= 8  # At least 8 exports expected
