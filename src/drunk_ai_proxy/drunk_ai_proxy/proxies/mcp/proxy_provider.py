"""MCP Proxy Provider module.

This module provides a class for creating FastMCP instances from MCP configurations.
"""
from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from drunk_ai_proxy.proxies.mcp.base_provider import McpBaseProvider, McpProxyConfig
from drunk_ai_proxy.utils import McpConfig, audit_log
from drunk_ai_proxy.utils.env import SERVER_NAME, SERVER_VERSION, CONFIG_DIR
from drunk_ai_proxy.proxies.mcp.mcp_proxy_builder import McpProxyBuilder

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)

class McpProxyProvider(McpBaseProvider):
    """Provider class for creating FastMCP instances from MCP configurations."""

    def __init__(self, config: McpConfig, root_mcp: FastMCP | None = None) -> None:
        super().__init__(config)
        self.root_mcp = root_mcp
        self.mcp: FastMCP | None = None

    def _create_proxy(self, mcp: FastMCP) -> None:
        if self.config.spec_data is None:
            if getattr(self.config, "prompt_dir", None):
                logger.info(

                    "Skipping MCP spec proxy creation for prompt-only config '%s'",
                    self.config.path,
                )
            else:
                logger.warning(
                    "spec_data or mcp_servers is required for MCP config '%s'",
                    self.config.path,
                )
            return None
        
        logger.info("Creating proxy for MCP config: %s", self.config.path)
        from fastmcp.server import create_proxy
        proxy = create_proxy(self.config.spec_data, name=self.config.path)
        mcp.mount(proxy)
    
    def create_proxy(self) -> FastMCP:
        """
        Create and return a FastMCP instance based on the MCP configuration.
        
        Returns:
            FastMCP instance with mounted MCP proxy
        """
        if self.mcp is not None:
            return self.mcp

        self.mcp = (
            self.root_mcp
            if self.config.path == "/" and self.root_mcp is not None
            else McpProxyBuilder.create_fastmcp_server(
                f"{SERVER_NAME}{self.config.path}",
                SERVER_VERSION,
            )
        )
        self.mcp.auth = self._get_app_auth_provider()
        self._create_proxy(self.mcp)
        self._create_skill_proxy(self.mcp)
        self._create_prompt_proxy(self.mcp)
        self._create_agent_proxy(self.mcp)

        return self.mcp
    
    def _create_prompt_proxy(self, mcp: FastMCP) -> None:
        """Create and mount prompt provider if prompt_dir is configured.
        
        Args:
            mcp: FastMCP instance to mount prompt provider to.
        """
        prompt_dir = getattr(self.config, "prompt_dir", None)
        if prompt_dir is None:
            return

        prompt_path = Path(prompt_dir)
        if not prompt_path.is_absolute():
            prompt_path = Path(CONFIG_DIR) / prompt_path

        if not prompt_path.exists() or not prompt_path.is_dir():
            logger.warning(
                "Skipping prompt provider for path '%s' because prompt_dir does not exist: %s",
                self.config.path,
                prompt_path,
            )
            return

        md_file_count = sum(1 for _ in prompt_path.rglob("*.md"))
        if md_file_count < 1:
            logger.warning(
                "Skipping prompt provider for path '%s' because prompt_dir must contain at least 1 markdown file (found=%d)",
                self.config.path,
                md_file_count,
            )
            return
        
        try:
            from drunk_ai_proxy.proxies.prompt.prompt_provider import McpPromptProvider
            
            # Register prompts directly into the active MCP server so prompts/list includes them.
            prompt_provider = McpPromptProvider(self.config)
            loaded_prompt_count = prompt_provider.register_to_mcp(mcp)
            
            logger.info(
                "Registered %d prompt(s) for path '%s' from directory: %s",
                loaded_prompt_count,
                self.config.path,
                prompt_dir
            )
        except Exception as e:
            logger.error(
                "Failed to create prompt provider for path '%s': %s",
                self.config.path,
                type(e).__name__
            )
            audit_log(
                logger=logger,
                event="mcp_prompt_provider_failed",
                status="failure",
                resource=self.config.path,
                details={"error_type": type(e).__name__},
            )

    @staticmethod
    def create_mcp_proxies_configs(configs: list[McpConfig]) -> list[McpProxyConfig]:
        """
        Create MCP proxy configurations from a list of McpConfig instances.
        
        This method handles the special case of root MCP ("/") which serves as
        the main MCP server, and creates individual FastMCP instances for other paths.
        
        Args:
            configs: List of MCP McpConfig instances
            
        Returns:
            List of McpProxyConfig instances with initialized FastMCP servers
        """
        return McpProxyBuilder.build_mcp_proxy_configs(
            configs=configs,
            provider_factory=lambda config, root_mcp: McpProxyProvider(
                config,
                root_mcp=root_mcp,
            ),
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
        )
