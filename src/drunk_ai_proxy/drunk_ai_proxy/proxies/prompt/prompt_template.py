"""Prompt Template module for markdown-based prompt definitions.

This module provides a class for loading and rendering markdown prompt templates
with YAML frontmatter parameter definitions.
"""

from __future__ import annotations

from typing import Any, cast
from pathlib import Path

import yaml

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class PromptTemplate:
    """Represents a prompt template loaded from a markdown file.
    
    A prompt template consists of:
    - YAML frontmatter with optional role, description, and parameter type definitions
    - Markdown content body with {param} placeholders for string interpolation
    
    The template validates parameter types at render time and interpolates
    values using Python's str.format() method. The role field defines
    the persona or system context for the prompt, defaulting to "user".
    
    Allowed roles: "user", "system", "assistant".
    FastMCP-compatible roles: "user", "assistant" (falls back to "user" if invalid).
    """
    
    # Allowed role values in prompt definitions
    ALLOWED_ROLES: set[str] = {"user", "system", "assistant"}
    
    # FastMCP-compatible roles (what FastMCP library accepts)
    FASTMCP_ROLES: set[str] = {"user", "assistant"}
    
    # Map string type names to Python types
    TYPE_MAP: dict[str, type] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "string": str,  # Alternative name for str
        "number": float,  # Alternative name for numeric types
    }
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, str],
        content: str,
        role: object = "user",
        enabled: bool = True
    ):
        """Initialize a PromptTemplate.
        
        Args:
            name: Template name (typically derived from filename).
            description: Human-readable description of the prompt.
            parameters: Dictionary mapping parameter names to type names (e.g., {"topic": "str"}).
            content: Template content with {param} placeholders.
            role: Role for the prompt. Can be "user", "system", or "assistant".
                  If role is not FastMCP-compatible (not "user" or "assistant"),
                  it will be normalized to "user". Defaults to "user".
            enabled: Whether the prompt is enabled and should be loaded. Defaults to True.
        
        Raises:
            ValueError: If role is empty string or non-string type.
        """
        self.name = name
        self.description = description
        self.content = content
        self.enabled = enabled
        
        # Validate role is a string
        if not isinstance(role, str):
            raise ValueError(f"role must be a string, got {type(role).__name__}")
        if not role.strip():
            raise ValueError("role cannot be an empty string")
        
        role = role.strip()
        
        # Normalize role: if it's in ALLOWED_ROLES but not FASTMCP_ROLES,
        # log a warning and fallback to 'user'
        if role not in self.ALLOWED_ROLES:
            logger.warning(
                "Invalid role '%s' in template '%s' (not in %s), falling back to 'user'",
                role,
                name,
                sorted(self.ALLOWED_ROLES)
            )
            role = "user"
        elif role not in self.FASTMCP_ROLES:
            logger.warning(
                "Role '%s' in template '%s' is not FastMCP-compatible, falling back to 'user'",
                role,
                name
            )
            role = "user"
        
        self.role: str = role
        
        # Parse parameter types
        self.parameters: dict[str, type] = {}
        for param_name, type_name in parameters.items():
            param_type = self.TYPE_MAP.get(type_name.lower())
            if param_type is None:
                logger.warning(
                    "Unknown type '%s' for parameter '%s' in template '%s', defaulting to str",
                    type_name,
                    param_name,
                    name
                )
                param_type = str
            self.parameters[param_name] = param_type
        
        logger.debug(
            "Initialized template '%s' with parameters: %s, role='%s'",
            name,
            list(self.parameters.keys()),
            self.role
        )
    
    def render(self, **kwargs: Any) -> str:
        """Render the template with provided parameter values.
        
        Args:
            **kwargs: Parameter values matching the template's parameter definitions.
            
        Returns:
            Rendered template content with interpolated values.
            
        Raises:
            ValueError: If required parameters are missing or types don't match.
            KeyError: If template references undefined parameters.
        """
        if not self.parameters:
            return self.content

        # Validate that all required parameters are provided
        missing_params = set(self.parameters.keys()) - set(kwargs.keys())
        if missing_params:
            raise ValueError(
                f"Missing required parameters for template '{self.name}': {missing_params}"
            )
        
        # Validate parameter types and convert values
        validated_params: dict[str, Any] = {}
        for param_name, param_value in kwargs.items():
            if param_name not in self.parameters:
                logger.warning(
                    "Ignoring unexpected parameter '%s' for template '%s'",
                    param_name,
                    self.name
                )
                continue
            
            expected_type = self.parameters[param_name]
            
            # Type validation
            if not isinstance(param_value, expected_type):
                # Try to convert the value
                try:
                    if expected_type == bool:
                        # Special handling for bool (bool("False") == True)
                        if isinstance(param_value, str):
                            converted_value = param_value.lower() in ("true", "1", "yes")
                        else:
                            converted_value = bool(param_value)
                    else:
                        converted_value = expected_type(param_value)
                    validated_params[param_name] = converted_value
                except (ValueError, TypeError) as e:
                    logger.error(
                        "Type conversion failed for parameter '%s': %s",
                        param_name,
                        type(e).__name__
                    )
                    raise ValueError(
                        f"Parameter '{param_name}' must be of type {expected_type.__name__}, "
                        f"got {type(param_value).__name__}"
                    ) from e
            else:
                validated_params[param_name] = param_value
        
        # Render template with validated parameters
        try:
            return self.content.format(**validated_params)
        except KeyError as e:
            logger.error("Template rendering failed: %s", type(e).__name__)
            raise KeyError(
                f"Template '{self.name}' references undefined parameter: {e}"
            ) from e
    
    @classmethod
    def from_markdown_file(cls, file_path: str, name: str | None = None) -> "PromptTemplate":
        """Load a prompt template from a markdown file with YAML frontmatter.
        
                The file format should be:
        ```markdown
        ---
        description: Human-readable description
        role: user|system|assistant
                enabled: true
        parameters:
          param1: str
          param2: int
        ---
        Template content with {param1} and {param2} placeholders.
        ```
        
        If role is not provided in the frontmatter, it defaults to "user".
        Allowed roles: "user", "system", "assistant".
        
        Args:
            file_path: Path to the markdown file.
            name: Optional template name (defaults to filename stem).
            
        Returns:
            PromptTemplate instance loaded from the file.
            
        Raises:
            ValueError: If file format is invalid or required fields are missing.
            FileNotFoundError: If the file doesn't exist.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            logger.error("Prompt file not found: %s", file_path)
            raise
        except Exception as e:
            logger.error("Failed to read file %s: %s", file_path, type(e).__name__)
            raise ValueError(f"Failed to read prompt file: {file_path}") from e

        template_name = name if name is not None else Path(file_path).stem
        return cls.from_markdown_content(
            content=content,
            name=template_name,
            source=file_path,
        )

    @classmethod
    def from_markdown_content(
        cls,
        content: str,
        name: str,
        source: str = "inline markdown",
    ) -> "PromptTemplate":
        """Load a prompt template from markdown content with YAML frontmatter.

        Args:
            content: Raw markdown content with YAML frontmatter.
            name: Template name.
            source: Source label used in errors and warnings.

        Returns:
            PromptTemplate instance loaded from the markdown content.

        Raises:
            ValueError: If markdown format is invalid or required fields are missing.
        """
        if not content.startswith("---"):
            logger.warning(
                "Prompt source '%s' has no YAML frontmatter; using raw markdown content "
                "with default metadata",
                source,
            )
            return cls(
                name=name,
                description=f"Prompt template '{name}'",
                parameters={},
                content=content,
                role="user",
                enabled=True,
            )

        try:
            end_delimiter_pos = content.index("---", 3)
        except ValueError:
            raise ValueError(
                f"Prompt source '{source}' has unclosed YAML frontmatter "
                "(missing closing '---')"
            ) from None

        frontmatter_str = content[3:end_delimiter_pos].strip()
        template_content = content[end_delimiter_pos + 3:].strip()

        try:
            frontmatter_obj: object = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            logger.error("YAML parsing failed for %s: %s", source, type(e).__name__)
            raise ValueError(f"Invalid YAML frontmatter in '{source}': {e}") from e

        if not isinstance(frontmatter_obj, dict):
            raise ValueError(
                f"Prompt source '{source}' frontmatter must be a YAML mapping (dictionary), "
                f"got {type(frontmatter_obj).__name__}"
            )
        frontmatter = cast(dict[str, Any], frontmatter_obj)

        description_obj: object = frontmatter.get("description")
        if not isinstance(description_obj, str) or not description_obj:
            raise ValueError(
                f"Prompt source '{source}' must have a 'description' field in frontmatter"
            )
        description = description_obj

        parameters_obj: object = frontmatter.get("parameters", {})
        if not isinstance(parameters_obj, dict):
            raise ValueError(
                f"Prompt source '{source}' 'parameters' field must be a dictionary, "
                f"got {type(parameters_obj).__name__}"
            )
        raw_parameters = cast(dict[object, object], parameters_obj)
        parameters: dict[str, str] = {}
        for param_name, type_name in raw_parameters.items():
            parameters[str(param_name)] = str(type_name)

        role_obj: object = frontmatter.get("role", "user")
        if not isinstance(role_obj, str):
            logger.warning(
                "'role' field in '%s' must be a string, got %s; falling back to 'user'",
                source,
                type(role_obj).__name__,
            )
            role = "user"
        else:
            role = role_obj.strip()
            if role not in cls.ALLOWED_ROLES:
                logger.warning(
                    "'role' field in '%s' is invalid ('%s'), falling back to 'user'",
                    source,
                    role,
                )
                role = "user"
            elif role not in cls.FASTMCP_ROLES:
                logger.warning(
                    "'role' field in '%s' is '%s' (not FastMCP-compatible), "
                    "falling back to 'user'",
                    source,
                    role,
                )
                role = "user"

        enabled_obj: object = frontmatter.get("enabled", True)
        if not isinstance(enabled_obj, bool):
            logger.warning(
                "'enabled' field in '%s' must be a bool, got %s; defaulting to True",
                source,
                type(enabled_obj).__name__,
            )
            enabled = True
        else:
            enabled = enabled_obj

        return cls(
            name=name,
            description=description,
            parameters=parameters,
            content=template_content,
            role=role,
            enabled=enabled,
        )
    
    def __repr__(self) -> str:
        """Return string representation of the template."""
        params_str = ", ".join(
            f"{name}: {typ.__name__}" for name, typ in self.parameters.items()
        )
        return f"PromptTemplate(name='{self.name}', parameters=[{params_str}], role='{self.role}')"
