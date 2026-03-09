"""Prompt Loader module for discovering and loading prompt templates.

This module provides functionality to scan a directory for markdown prompt
templates and load them into PromptTemplate instances.
"""

from __future__ import annotations

import re
from logging import Logger
from pathlib import Path

from drunk_ai_proxy.proxies.prompt.prompt_template import PromptTemplate
from drunk_ai_proxy.utils.env import CONFIG_DIR
from drunk_ai_proxy.utils.logging_config import setup_logging


class PromptLoader:
    """Loads prompt templates from a directory structure.
    
    This class scans a specified directory (recursively) for markdown files
    with YAML frontmatter and loads them as PromptTemplate instances.
    """
    
    def __init__(self, prompt_dir: str):
        """Initialize the PromptLoader.
        
        Args:
            prompt_dir: Path to directory containing prompt markdown files.
                       Can be absolute or relative to the data directory.
        
        Raises:
            ValueError: If prompt_dir is None or empty.
            FileNotFoundError: If the directory doesn't exist.
        """
        self._logger: Logger = setup_logging(__name__)
        
        if not prompt_dir:
            raise ValueError("prompt_dir cannot be None or empty")
        
        # Convert to Path object for easier manipulation
        self._prompt_dir = Path(prompt_dir)
        
        # If relative path, resolve against data directory
        if not self._prompt_dir.is_absolute():
            self._prompt_dir = Path(CONFIG_DIR) / self._prompt_dir
        
        # Validate directory exists
        if not self._prompt_dir.exists():
            raise FileNotFoundError(
                f"Prompt directory does not exist: {self._prompt_dir}"
            )
        
        if not self._prompt_dir.is_dir():
            raise ValueError(
                f"Prompt directory path is not a directory: {self._prompt_dir}"
            )
        
        self._logger.info("Initialized PromptLoader with directory: %s", self._prompt_dir)
    
    @staticmethod
    def _sanitize_prompt_name(name: str) -> str:
        """Sanitize prompt name to be valid identifier.
        
        Converts filename to a valid prompt name by:
        - Converting to lowercase
        - Replacing spaces and special chars with underscores
        - Keeping only alphanumeric, underscores, and hyphens
        
        Args:
            name: Original filename stem.
            
        Returns:
            Sanitized prompt name.
        """
        # Convert to lowercase
        name = name.lower()
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Keep only alphanumeric, underscores, and hyphens
        name = re.sub(r"[^a-z0-9_-]", "", name)
        # Remove leading/trailing underscores or hyphens
        name = name.strip("_-")
        return name
    
    def load_prompts(self) -> dict[str, PromptTemplate]:
        """Scan directory and load all prompt templates.
        
        This method recursively scans the configured directory for markdown
        files (*.md), attempts to parse them as prompt templates, and returns
        a dictionary keyed by prompt name.
        
        Malformed files are logged but don't prevent loading of valid templates.
        
        Returns:
            Dictionary mapping prompt names to PromptTemplate instances.
        """
        prompts: dict[str, PromptTemplate] = {}
        normalized_names: dict[str, str] = {}
        
        # Find all markdown files recursively
        md_files = list(self._prompt_dir.rglob("*.md"))
        
        if not md_files:
            self._logger.warning(
                "No markdown files (*.md) found in prompt directory: %s",
                self._prompt_dir
            )
            return prompts
        
        self._logger.info(
            "Found %d markdown file(s) in %s",
            len(md_files),
            self._prompt_dir
        )
        
        # Load each file as a prompt template
        for md_file in md_files:
            try:
                # Calculate relative path and create prompt name
                rel_path = md_file.relative_to(self._prompt_dir)
                
                # Use relative path (without extension) as base name
                # This allows namespacing prompts in subdirectories
                # e.g., category/action.md -> category_action
                name_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                raw_name = "_".join(name_parts)
                prompt_name = self._sanitize_prompt_name(raw_name)
                
                # Load the template
                template = PromptTemplate.from_markdown_file(
                    str(md_file),
                    name=prompt_name
                )

                if not template.enabled:
                    self._logger.info(
                        "Prompt '%s' is disabled; skipping (file: %s)",
                        prompt_name,
                        md_file.relative_to(self._prompt_dir)
                    )
                    continue
                
                # Check for name collisions
                normalized_name = prompt_name.replace("-", "_")
                if normalized_name in normalized_names:
                    self._logger.warning(
                        "Duplicate prompt name '%s' conflicts with '%s' (file: %s). Skipping.",
                        prompt_name,
                        normalized_names[normalized_name],
                        md_file
                    )
                    continue
                
                prompts[prompt_name] = template
                normalized_names[normalized_name] = prompt_name
                self._logger.debug(
                    "Loaded prompt '%s' from %s",
                    prompt_name,
                    md_file.relative_to(self._prompt_dir)
                )
                
            except ValueError as e:
                # Log parsing errors but continue with other files
                self._logger.error(
                    "Failed to parse prompt file %s: %s",
                    md_file.name,
                    type(e).__name__
                )
                self._logger.debug("Parse error details: %s", str(e))
                continue
            except Exception as e:
                # Catch unexpected errors
                self._logger.error(
                    "Unexpected error loading %s: %s",
                    md_file.name,
                    type(e).__name__
                )
                continue
        
        if prompts:
            self._logger.info(
                "Successfully loaded %d prompt template(s): %s",
                len(prompts),
                ", ".join(prompts.keys())
            )
        else:
            self._logger.warning(
                "No valid prompt templates loaded from %s",
                self._prompt_dir
            )
        
        return prompts
