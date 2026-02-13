"""
JSON Schema validation module for configuration files.
Validates mcp.json, proxies.json, and auth.json against their schemas.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    print("Warning: jsonschema package not installed. Schema validation disabled.")
    print("Install with: pip install jsonschema")


# Schema file paths
SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
MCP_SCHEMA = SCHEMA_DIR / "mcp.schema.json"
PROXIES_SCHEMA = SCHEMA_DIR / "proxies.schema.json"
AUTH_SCHEMA = SCHEMA_DIR / "auth.schema.json"


def load_schema(schema_path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON schema from file."""
    if not schema_path.exists():
        print(f"Warning: Schema file not found: {schema_path}")
        return None
    
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading schema from {schema_path}: {e}")
        return None


def validate_config(config: Dict[str, Any], schema_path: Path, config_name: str = "config") -> bool:
    """
    Validate a configuration dictionary against a JSON schema.
    
    Args:
        config: Configuration dictionary to validate
        schema_path: Path to the JSON schema file
        config_name: Name of the config (for error messages)
    
    Returns:
        True if validation passes, False otherwise
    """
    if not JSONSCHEMA_AVAILABLE:
        return True  # Skip validation if jsonschema not installed
    
    schema = load_schema(schema_path)
    if schema is None:
        return True  # Skip validation if schema can't be loaded
    
    try:
        validate(instance=config, schema=schema)
        return True
    except ValidationError as e:
        print(f"Validation error in {config_name}:")
        print(f"  Path: {' -> '.join(str(p) for p in e.path) if e.path else 'root'}")
        print(f"  Error: {e.message}")
        return False
    except Exception as e:
        print(f"Unexpected error validating {config_name}: {e}")
        return False


def validate_mcp_config(config: Dict[str, Any]) -> bool:
    """Validate MCP server configuration (mcp.json)."""
    return validate_config(config, MCP_SCHEMA, "mcp.json")


def validate_proxies_config(config: Dict[str, Any]) -> bool:
    """Validate dynamic proxies configuration (proxies.json)."""
    return validate_config(config, PROXIES_SCHEMA, "proxies.json")


def validate_auth_config(config: Dict[str, Any]) -> bool:
    """Validate authentication configuration (auth.json)."""
    return validate_config(config, AUTH_SCHEMA, "auth.json")


def get_schema_errors(config: Dict[str, Any], schema_path: Path) -> list:
    """
    Get detailed validation errors for a configuration.
    
    Returns:
        List of error messages
    """
    if not JSONSCHEMA_AVAILABLE:
        return []
    
    schema = load_schema(schema_path)
    if schema is None:
        return []
    
    validator = Draft7Validator(schema)
    errors = []
    
    for error in validator.iter_errors(config):
        path = ' -> '.join(str(p) for p in error.path) if error.path else 'root'
        errors.append(f"At {path}: {error.message}")
    
    return errors
