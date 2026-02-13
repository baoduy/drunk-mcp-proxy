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
import hmac
import secrets
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from validation import validate_auth_config


# Auth configuration file
AUTH_CONFIG_FILE = os.environ.get("MCP_AUTH_CONFIG_FILE", "data/auth.json")

# Lock for auth config file operations to prevent race conditions
_auth_lock = asyncio.Lock()


def load_auth_config() -> Dict[str, Any]:
    """Load authentication configuration from file."""
    if not os.path.exists(AUTH_CONFIG_FILE):
        return {"enabled": False, "api_keys": {}}
    
    try:
        with open(AUTH_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Validate configuration against schema
        if not validate_auth_config(config):
            print(f"Warning: Auth configuration validation failed for '{AUTH_CONFIG_FILE}'")
        
        return config
    except Exception as e:
        print(f"Warning: Error loading auth config: {e}")
        return {"enabled": False, "api_keys": {}}


async def save_auth_config_async(config: Dict[str, Any]) -> None:
    """Save authentication configuration to file asynchronously."""
    async with _auth_lock:  # Prevent race conditions on concurrent writes
        def _save():
            try:
                # Validate before saving
                if not validate_auth_config(config):
                    raise ValueError("Auth configuration validation failed")
                
                # Ensure parent directory exists
                auth_path = Path(AUTH_CONFIG_FILE)
                auth_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Atomic write: write to temp file and rename
                temp_file = str(auth_path) + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(config, f, indent=2)
                os.replace(temp_file, str(auth_path))
            except Exception as e:
                print(f"Error saving auth config: {e}")
                raise
        
        # Run file I/O in thread pool to avoid blocking event loop
        await asyncio.to_thread(_save)


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
    config = load_auth_config()
    
    # If auth is disabled, allow all requests
    if not config.get("enabled", False):
        return True, "anonymous"
    
    if not api_key:
        return False, None
    
    api_keys = config.get("api_keys", {})
    key_hash = hash_api_key(api_key)
    
    # Check if the hash matches any stored key using constant-time comparison
    for client_name, stored_hash in api_keys.items():
        if hmac.compare_digest(stored_hash, key_hash):
            return True, client_name
    
    return False, None


async def create_api_key(client_name: str) -> str:
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
    await save_auth_config_async(config)
    
    return api_key


async def revoke_api_key(client_name: str) -> bool:
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
        await save_auth_config_async(config)
        return True
    
    return False


async def enable_authentication() -> None:
    """Enable authentication for the proxy server."""
    config = load_auth_config()
    config["enabled"] = True
    await save_auth_config_async(config)


async def disable_authentication() -> None:
    """Disable authentication for the proxy server."""
    config = load_auth_config()
    config["enabled"] = False
    await save_auth_config_async(config)


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    config = load_auth_config()
    return config.get("enabled", False)
