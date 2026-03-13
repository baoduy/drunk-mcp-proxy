"""Unit tests for MCP proxy builder codemode wiring."""

from __future__ import annotations

from unittest.mock import Mock, patch

from drunk_ai_proxy.proxies.mcp.base_provider import McpProxyConfig
from drunk_ai_proxy.proxies.mcp.mcp_proxy_builder import McpProxyBuilder
from drunk_ai_proxy.utils.config_yaml import McpConfig


class TestMcpProxyBuilderCreateFastMcpServer:
    """Tests for create_fastmcp_server codemode behavior."""

    @patch("drunk_ai_proxy.proxies.mcp.mcp_proxy_builder.FastMCP")
    def test_create_fastmcp_server_without_codemode_transforms(self, mock_fastmcp: Mock) -> None:
        """Do not pass transforms when codemode is disabled."""
        server = Mock()
        mock_fastmcp.return_value = server

        result = McpProxyBuilder.create_fastmcp_server("demo", "1.0.0", False)

        assert result == server
        mock_fastmcp.assert_called_once_with("demo", version="1.0.0")

    @patch("drunk_ai_proxy.proxies.mcp.mcp_proxy_builder.FastMCP")
    @patch("drunk_ai_proxy.proxies.mcp.mcp_proxy_builder.McpProxyBuilder.get_transforms")
    def test_create_fastmcp_server_with_codemode_transforms(
        self,
        mock_get_transforms: Mock,
        mock_fastmcp: Mock,
    ) -> None:
        """Pass transforms when codemode is enabled."""
        transforms = [Mock()]
        mock_get_transforms.return_value = transforms
        server = Mock()
        mock_fastmcp.return_value = server

        result = McpProxyBuilder.create_fastmcp_server("demo", "1.0.0", True)

        assert result == server
        mock_get_transforms.assert_called_once_with(True)
        mock_fastmcp.assert_called_once_with("demo", version="1.0.0", transforms=transforms)


class TestMcpProxyBuilderBuildConfigs:
    """Tests for root codemode_enabled selection."""

    @patch("drunk_ai_proxy.proxies.mcp.mcp_proxy_builder.McpProxyBuilder.create_fastmcp_server")
    def test_build_mcp_proxy_configs_uses_root_codemode_enabled(
        self,
        mock_create_fastmcp_server: Mock,
    ) -> None:
        """Use root route codemode_enabled when creating shared root server."""
        root_server = Mock()
        mock_create_fastmcp_server.return_value = root_server

        root_config = Mock(spec=McpConfig)
        root_config.path = "/"
        root_config.codemode_enabled = False
        root_config.spec_data = {"mcpServers": {}}
        root_config.get_prompt_dirs.return_value = []

        provider = Mock()
        provider.get_mcp_proxy_config.return_value = McpProxyConfig(path="/", mcp_server=root_server)

        result = McpProxyBuilder.build_mcp_proxy_configs(
            configs=[root_config],
            provider_factory=lambda config, root_mcp: provider,
            server_name="test-server",
            server_version="2.0.0",
        )

        mock_create_fastmcp_server.assert_called_once_with("test-server", "2.0.0", False)
        assert result[0].path == "/"
        assert result[0].mcp_server == root_server
