"""MCP Prompt Provider for dynamically loading and serving prompt templates.

This module provides a provider that loads markdown-based prompt templates
and exposes them via MCP protocol using FastMCP's prompt decorator.
"""

from __future__ import annotations

import inspect
from logging import Logger
from typing import Any

from fastmcp import FastMCP
from fastmcp.prompts import Message

from drunk_ai_proxy.proxies.mcp.base_provider import McpBaseProvider
from drunk_ai_proxy.proxies.prompt.prompt_loader import PromptLoader
from drunk_ai_proxy.proxies.prompt.prompt_template import PromptTemplate
from drunk_ai_proxy.utils import McpConfig
from drunk_ai_proxy.utils.env import SERVER_NAME, SERVER_VERSION
from drunk_ai_proxy.utils.logging_config import setup_logging


class McpPromptProvider(McpBaseProvider):
    """Provider for serving prompt templates via MCP protocol.
    
    This provider loads markdown prompt templates from a configured directory
    and dynamically registers them as MCP prompts using FastMCP decorators.
    """
    
    def __init__(self, config: McpConfig):
        """Initialize the McpPromptProvider.
        
        Args:
            config: MCP configuration containing prompt_dir.
        
        Raises:
            ValueError: If prompt_dir is not configured or is invalid.
        """
        super().__init__(config)
        self._logger: Logger = setup_logging(__name__)
        self._mcp: FastMCP | None = None
        self._templates: dict[str, PromptTemplate] = {}
        
        # Validate that prompt_dir is configured
        if not self.config.prompt_dir:
            raise ValueError(
                f"prompt_dir must be configured for prompt provider at path '{self.config.path}'"
            )
        
        # Initialize the prompt loader
        try:
            self._loader = PromptLoader(self.config.prompt_dir)
            self._logger.info(
                "Initialized prompt provider for path '%s' with directory: %s",
                self.config.path,
                self.config.prompt_dir
            )
        except (FileNotFoundError, ValueError) as e:
            self._logger.error(
                "Failed to initialize prompt loader: %s",
                type(e).__name__
            )
            raise
    
    def _load_templates(self) -> None:
        """Load all prompt templates from the configured directory."""
        if self._templates:
            # Already loaded
            return
        
        self._logger.info("Loading prompt templates for path '%s'", self.config.path)
        self._templates = self._loader.load_prompts()
        
        if not self._templates:
            self._logger.warning(
                "No prompt templates loaded for path '%s'. "
                "Check that markdown files exist in: %s",
                self.config.path,
                self.config.prompt_dir
            )
    
    def _create_prompt_function(
        self,
        template: PromptTemplate
    ) -> Any:
        """Create a prompt function for a template.
        
        This method creates a callable that accepts template parameters
        and returns a list of Message objects. Each message uses the template's
        configured role.
        
        Args:
            template: The PromptTemplate to wrap.
            
        Returns:
            A callable function that renders the template and returns Message objects.
        """
        # Create function that matches template's parameter signature
        def prompt_func(**kwargs: Any) -> list[Message]:
            """Dynamic prompt function returning list of Message objects."""
            try:
                rendered_content = template.render(**kwargs)
                # Return a list with a single Message using the template's role
                return [Message(content=rendered_content, role=template.role)]
            except (ValueError, KeyError) as e:
                self._logger.error(
                    "Failed to render prompt '%s': %s",
                    template.name,
                    type(e).__name__
                )
                raise
        
        # Set function metadata
        prompt_func.__name__ = template.name
        prompt_func.__doc__ = template.description
        
        # Build annotations dict for type hints
        annotations: dict[str, type] = {}
        for param_name, param_type in template.parameters.items():
            annotations[param_name] = param_type
        annotations["return"] = list[Message]
        prompt_func.__annotations__ = annotations

        # FastMCP inspects callable signatures for prompt metadata/listing.
        params = [
            inspect.Parameter(
                name=param_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=param_type,
            )
            for param_name, param_type in template.parameters.items()
        ]
        prompt_func.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
            parameters=params,
            return_annotation=list[Message],
        )
        
        return prompt_func
    
    def _register_prompts(self, mcp: FastMCP) -> None:
        """Register all loaded templates as MCP prompts.
        
        Args:
            mcp: FastMCP instance to register prompts with.
        """
        if not self._templates:
            self._logger.info("No templates to register for path '%s'", self.config.path)
            return
        
        self._logger.info(
            "Registering %d prompt(s) for path '%s'",
            len(self._templates),
            self.config.path
        )
        
        for template_name, template in self._templates.items():
            try:
                # Create the prompt function
                prompt_func = self._create_prompt_function(template)
                
                # Register with FastMCP using the prompt decorator
                mcp.prompt(prompt_func)
                
                self._logger.debug(
                    "Registered prompt '%s' with parameters: %s",
                    template_name,
                    list(template.parameters.keys())
                )
                
            except Exception as e:
                self._logger.error(
                    "Failed to register prompt '%s': %s",
                    template_name,
                    type(e).__name__
                )
                # Continue with other prompts
                continue
        
        self._logger.info(
            "Successfully registered prompts for path '%s'",
            self.config.path
        )

    def register_to_mcp(self, mcp: FastMCP) -> int:
        """Register loaded prompt templates directly into an existing FastMCP server.

        Args:
            mcp: Active FastMCP server instance.

        Returns:
            Number of prompt templates loaded for registration.
        """
        self._load_templates()
        self._register_prompts(mcp)
        return len(self._templates)
    
    def create_proxy(self) -> FastMCP:
        """Create and return a FastMCP instance with registered prompts.
        
        This method creates a new FastMCP server, loads prompt templates,
        and registers them as MCP prompts.
        
        Returns:
            FastMCP instance with registered prompt templates.
        """
        if self._mcp is not None:
            return self._mcp
        
        self._logger.info("Creating FastMCP instance for path '%s'", self.config.path)
        
        # Create FastMCP instance
        self._mcp = FastMCP(
            name=f"{SERVER_NAME}{self.config.path}",
            version=SERVER_VERSION
        )
        
        # Set authentication provider
        self._mcp.auth = self._get_app_auth_provider()
        
        # Load templates and register prompts
        self._load_templates()
        self._register_prompts(self._mcp)
        
        return self._mcp
    
    def get_mcp_prompts(self) -> dict[str, PromptTemplate]:
        """Get all loaded prompt templates.
        
        Returns:
            Dictionary mapping prompt names to PromptTemplate instances.
        """
        if not self._templates:
            self._load_templates()
        return self._templates.copy()
