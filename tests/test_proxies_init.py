"""
Unit tests for src/proxies/__init__.py module.

Tests lazy loading of proxy modules.
"""

import pytest


class TestProxiesPackageImports:
    """Test suite for proxies package lazy imports."""

    def test_import_mcp_proxy_config(self):
        """Test lazy import of McpProxyConfig."""
        from src.proxies import McpProxyConfig
        assert McpProxyConfig is not None
        assert McpProxyConfig.__name__ == "McpProxyConfig"

    def test_import_proxy_config_provider(self):
        """Test lazy import of ProxyConfigProvider."""
        from src.proxies import ProxyConfigProvider
        assert ProxyConfigProvider is not None
        assert ProxyConfigProvider.__name__ == "ProxyConfigProvider"

    def test_import_openapi_mcp_provider(self):
        """Test lazy import of OpenApiMcpProvider."""
        from src.proxies import OpenApiMcpProvider
        assert OpenApiMcpProvider is not None
        assert OpenApiMcpProvider.__name__ == "OpenApiMcpProvider"

    def test_import_nonexistent_attribute(self):
        """Test that importing non-existent attribute raises AttributeError."""
        import src.proxies as proxies
        with pytest.raises(AttributeError) as exc_info:
            _ = proxies.NonExistentClass
        assert "has no attribute 'NonExistentClass'" in str(exc_info.value)

    def test_all_exports(self):
        """Test __all__ contains expected exports."""
        import src.proxies as proxies
        assert "McpProxyConfig" in proxies.__all__
        assert "ProxyConfigProvider" in proxies.__all__
        assert "OpenApiMcpProvider" in proxies.__all__
