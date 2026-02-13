"""
JSON Schema validation module for configuration files.

This module provides JSON schema validation for MCP configuration files,
ensuring that loaded configurations conform to the expected structure
before they're used to create proxies.

Validation Features:
- Validates mcp.json files against mcp.schema.json
- Validates auth.json files against auth.schema.json
- Gracefully handles missing jsonschema package
- Provides detailed error messages with path information

Schema Location:
    schemas/
    ├── mcp.schema.json     - MCP server configuration schema
    └── auth.schema.json    - Authentication configuration schema

Dependencies:
    - jsonschema (optional): If not installed, validation is skipped
"""

import json
from pathlib import Path
from typing import Union

from src.tools.env import SCHEMA_DIR

# Conditional Import: jsonschema is optional
# If not available, validation will be skipped with a warning
try:
    from jsonschema import validate, ValidationError, Draft7Validator, FormatChecker

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    validate = None  # type: ignore
    ValidationError = None  # type: ignore
    Draft7Validator = None  # type: ignore
    FormatChecker = None  # type: ignore

# Type Definitions
# ================
# Recursive type for representing any valid JSON value
JsonValue = Union[str, int, float, bool, None, dict[str, "JsonValue"], list["JsonValue"]]
# Configuration dictionary type
ConfigDict = dict[str, JsonValue]
# Schema dictionary type
SchemaDict = dict[str, JsonValue]

# Schema File Paths
# =================
# Schemas are located in the schemas/ directory at project root
# Override with FASTMCP_SCHEMA_DIR if needed
path = Path(SCHEMA_DIR)
MCP_SCHEMA = path / "mcp.schema.json"
AUTH_SCHEMA = path / "auth.schema.json"


# Schema Loading
# ==============


def load_schema(schema_path: Path) -> SchemaDict | None:
    """
    Load a JSON schema file from disk.

    Reads and parses a JSON schema file, handling errors gracefully.
    Used internally by validation functions to load schema definitions.

    Args:
        schema_path: Path to the JSON schema file

    Returns:
        Parsed schema dictionary, or None if loading fails

    Error Handling:
        - Missing file: Prints warning and returns None
        - Invalid JSON: Prints error and returns None
        - Other errors: Prints error and returns None

    Example:
        schema = load_schema(Path("schemas/mcp.schema.json"))
    """
    # Check if schema file exists
    if not schema_path.exists():
        print(f"Warning: Schema file not found: {schema_path}")
        return None

    try:
        # Read and parse JSON schema
        with open(schema_path, 'r') as f:
            schema: SchemaDict = json.load(f)
            return schema
    except Exception as e:
        print(f"Error loading schema from {schema_path}: {e}")
        return None


# Validation Functions
# ====================


def validate_config(config: ConfigDict, schema_path: Path, config_name: str = "config") -> bool:
    """
    Validate a configuration dictionary against a JSON schema.

    This is the core validation function that checks if a configuration
    conforms to its schema definition. It uses the jsonschema library
    for validation and provides user-friendly error messages.

    Validation Behavior:
        - If jsonschema is not installed: Always returns True (validation skipped)
        - If schema cannot be loaded: Returns True (validation skipped)
        - If validation passes: Returns True
        - If validation fails: Prints error details and returns False

    Error Information:
        The function prints detailed error information including:
        - Path to the invalid field (e.g., "mcpServers -> stock -> command")
        - Validation error message (e.g., "Field is required")

    Args:
        config: Configuration dictionary to validate
        schema_path: Path to the JSON schema file
        config_name: Name for error messages (default: "config")

    Returns:
        True if validation passes or is skipped, False if validation fails

    Example:
        config = {"mcpServers": {...}}
        is_valid = validate_config(config, MCP_SCHEMA, "stock.mcp.json")
        if not is_valid:
            print("Configuration is invalid!")
    """
    # Skip validation if jsonschema package not available
    if not JSONSCHEMA_AVAILABLE:
        return True  # Skip validation if jsonschema not installed

    # Load the schema
    schema = load_schema(schema_path)
    if schema is None:
        return True  # Skip validation if schema can't be loaded

    try:
        # Perform validation with format checking (e.g., email, uri)
        validate(instance=config, schema=schema, format_checker=FormatChecker())
        return True

    except ValidationError as e:
        # Validation failed - print detailed error information
        print(f"Validation error in {config_name}:")
        # Build path string showing where the error occurred
        print(f"  Path: {' -> '.join(str(p) for p in e.path) if e.path else 'root'}")
        print(f"  Error: {e.message}")
        return False

    except Exception as e:
        # Unexpected error during validation
        print(f"Unexpected error validating {config_name}: {e}")
        return False


# Configuration-Specific Validators
# ==================================


def validate_mcp_config(config: ConfigDict) -> bool:
    """
    Validate MCP server configuration (mcp.json).

    Convenience function for validating MCP server configurations.
    Uses the mcp.schema.json schema file.

    Expected Structure:
        {
            "mcpServers": {
                "server_name": {
                    "command": "python",
                    "args": ["server.py"],
                    "env": {...}
                }
            }
        }

    Args:
        config: MCP configuration dictionary to validate

    Returns:
        True if valid or validation skipped, False if invalid

    Example:
        config = load_config_file("stock.mcp.json")
        if validate_mcp_config(config):
            proxy = create_proxy(config)
    """
    return validate_config(config, MCP_SCHEMA, "mcp.json")


def validate_auth_config(config: ConfigDict) -> bool:
    """
    Validate authentication configuration (auth.json).

    Convenience function for validating authentication configurations.
    Uses the auth.schema.json schema file.

    Args:
        config: Auth configuration dictionary to validate

    Returns:
        True if valid or validation skipped, False if invalid

    Example:
        config = load_config_file("auth.json")
        if validate_auth_config(config):
            # Use auth configuration
            pass
    """
    return validate_config(config, AUTH_SCHEMA, "auth.json")
