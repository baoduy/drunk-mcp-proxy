"""
Authentication module for MCP Proxy Server
Implements security best practices for MCP authentication including:
- API key validation
- Per-client authorization
- Secure token management
"""

import os
import json
import hashlib
import secrets
from typing import Optional, Dict, Any
from functools import wraps


# Auth configuration file
AUTH_CONFIG_FILE = os.environ.get("MCP_AUTH_CONFIG_FILE", "auth.json")


def load_auth_config() -> Dict[str, Any]:
    """Load authentication configuration from file."""
    if not os.path.exists(AUTH_CONFIG_FILE):
        return {"enabled": False, "api_keys": {}}
    
    try:
        with open(AUTH_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Error loading auth config: {e}")
        return {"enabled": False, "api_keys": {}}


def save_auth_config(config: Dict[str, Any]) -> None:
    """Save authentication configuration to file."""
    try:
        with open(AUTH_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving auth config: {e}")
        raise


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_api_key(api_key: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate an API key against stored hashes.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        Tuple of (is_valid, client_name)
    """
    if not api_key:
        return False, None
    
    config = load_auth_config()
    
    # If auth is disabled, allow all requests
    if not config.get("enabled", False):
        return True, "anonymous"
    
    api_keys = config.get("api_keys", {})
    key_hash = hash_api_key(api_key)
    
    # Check if the hash matches any stored key
    for client_name, stored_hash in api_keys.items():
        if stored_hash == key_hash:
            return True, client_name
    
    return False, None


def create_api_key(client_name: str) -> str:
    """
    Create a new API key for a client.
    
    Args:
        client_name: Name of the client
        
    Returns:
        The generated API key (plain text, only shown once)
    """
    config = load_auth_config()
    
    if "api_keys" not in config:
        config["api_keys"] = {}
    
    # Generate and hash the key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Store the hash
    config["api_keys"][client_name] = key_hash
    save_auth_config(config)
    
    return api_key


def revoke_api_key(client_name: str) -> bool:
    """
    Revoke an API key for a client.
    
    Args:
        client_name: Name of the client
        
    Returns:
        True if key was revoked, False if not found
    """
    config = load_auth_config()
    
    if client_name in config.get("api_keys", {}):
        del config["api_keys"][client_name]
        save_auth_config(config)
        return True
    
    return False


def enable_authentication() -> None:
    """Enable authentication for the proxy server."""
    config = load_auth_config()
    config["enabled"] = True
    save_auth_config(config)


def disable_authentication() -> None:
    """Disable authentication for the proxy server."""
    config = load_auth_config()
    config["enabled"] = False
    save_auth_config(config)


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    config = load_auth_config()
    return config.get("enabled", False)


def require_auth(func):
    """
    Decorator to require authentication for a function.
    Extracts API key from environment or context.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get API key from environment variable or kwargs
        api_key = os.environ.get("MCP_API_KEY") or kwargs.get("api_key")
        
        is_valid, client_name = validate_api_key(api_key)
        
        if not is_valid:
            raise PermissionError("Invalid or missing API key")
        
        # Add client name to kwargs for logging/tracking
        kwargs["client_name"] = client_name
        
        return await func(*args, **kwargs)
    
    return wrapper
