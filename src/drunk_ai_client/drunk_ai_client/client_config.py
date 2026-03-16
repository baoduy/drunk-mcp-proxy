"""Configuration models and loaders for the Drunk AI stdio client."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class ClientConfig:
    """Configuration for remote MCP connection."""

    url: str
    api_key: str | None = None
    skill_dir: Path | None = None
    agents_dir: Path | None = None
    allows_overwrite: bool = False
    sync_enabled: bool = True
    use_from_client: bool = True

    @classmethod
    def from_env(cls) -> "ClientConfig":
        """Load client configuration from CLI arguments and environment variables.

        Returns:
            A validated client configuration object.

        Raises:
            ValueError: If the URL is missing or invalid.
        """
        return ClientConfigLoader.load()


class ClientConfigLoader:
    """Loads and validates runtime configuration for the stdio bridge client."""

    @classmethod
    def load(cls) -> ClientConfig:
        """Load configuration from CLI args and environment variables.

        Returns:
            A validated client configuration object.

        Raises:
            ValueError: If the URL is missing or invalid.
        """
        parser = argparse.ArgumentParser(
            description="FastMCP stdio bridge to remote MCP endpoint"
        )
        parser.add_argument("--url", help="Remote MCP endpoint URL")
        parser.add_argument("--api-key", help="Bearer token for authentication")
        args = parser.parse_args()

        url = args.url or cls._get_env_string("API_URL")
        if not url:
            raise ValueError("API_URL environment variable or --url argument required")

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url} (must be http:// or https://)")

        api_key = args.api_key or cls._get_env_string("API_KEY")

        skill_dir: Path | None = None
        skill_dir_value = cls._get_env_string("SKILL_DIR")
        if skill_dir_value:
            skill_dir = Path(skill_dir_value).expanduser()
            skill_dir.mkdir(parents=True, exist_ok=True)

        agents_dir: Path | None = None
        agents_dir_value = cls._get_env_string("AGENTS_DIR")
        if agents_dir_value:
            agents_dir = Path(agents_dir_value).expanduser()
            agents_dir.mkdir(parents=True, exist_ok=True)

        return ClientConfig(
            url=url,
            api_key=api_key,
            skill_dir=skill_dir,
            agents_dir=agents_dir,
            allows_overwrite=cls._get_env_bool("ALLOWS_OVERWRITE", False),
            sync_enabled=cls._get_env_bool("SYNC_ENABLED", True),
            use_from_client=cls._get_env_bool("FASTMCP_FROM_CLIENT_ENABLED", True),
        )

    @staticmethod
    def _get_env_string(name: str) -> str | None:
        """Return the environment value for a name using upper then lower case.

        Args:
            name: Environment variable name to check.

        Returns:
            The environment variable value if found, otherwise None.
        """
        value = os.getenv(name.upper())
        if value:
            return value

        value = os.getenv(name.lower())
        if value:
            return value

        return None

    @staticmethod
    def _get_env_int(key: str, default: int = 0) -> int:
        """Parse an integer environment variable with fallback default.

        Args:
            key: Environment variable key.
            default: Default integer used if parsing fails.

        Returns:
            Parsed integer value or the provided default.
        """
        try:
            return int(ClientConfigLoader._get_env_string(key) or str(default))
        except ValueError:
            return default

    @staticmethod
    def _get_env_bool(key: str, default: bool = False) -> bool:
        """Parse a boolean environment variable with permissive string values.

        Args:
            key: Environment variable key.
            default: Default boolean used if key is absent or invalid.

        Returns:
            Parsed boolean value or the provided default.
        """
        value = ClientConfigLoader._get_env_string(key)
        if value is not None:
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default
