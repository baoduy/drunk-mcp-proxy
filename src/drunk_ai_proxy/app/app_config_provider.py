from typing import TYPE_CHECKING, Any

from drunk_ai_proxy.utils import ConfigYaml, AuthType, McpConfig, LlmConfig
from drunk_ai_proxy.utils.env import AUTH_ENABLED, CONFIG_DIR

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider
    from httpx import Auth


class AppConfigProvider:
    """Provides application configuration."""

    _instance: "AppConfigProvider | None" = None

    def __init__(self) -> None:
        self.config_path = ConfigYaml.load_from_file(f"{CONFIG_DIR}/config.yaml")

    def get_auth_config(
        self,
        provider_name: AuthType | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Get the authentication configuration for a given provider name."""
        auth_config = self.config_path.auth
        if auth_config is None:
            return ("", None)
        name = provider_name or auth_config.default_provider
        if name is None:
            raise ValueError(
                "No provider name specified and no default provider configured"
            )

        config = auth_config[name]
        return (name, config)

    def get_fast_mcp_auth_provider(
        self,
        provider_name: AuthType | None = None,
    ) -> "AuthProvider | None":
        """Get the FastMCP authentication provider configuration."""
        if not AUTH_ENABLED:
            return None

        name, config = self.get_auth_config(provider_name)
        if config is None:
            return None

        match name:
            case AuthType.BASIC:
                from drunk_ai_proxy.auth.api_auth_provider import ApiKeyAuthProvider
                return ApiKeyAuthProvider(**config)
            case AuthType.JWT:
                from fastmcp.server.auth.providers.jwt import JWTVerifier
                return JWTVerifier(**config)
            case _:
                raise ValueError(f"Unsupported authentication provider type: {name}")

    def get_client_auth_handler(
        self,
        provider_name: AuthType | None = None,
        auth_passthrough: bool = False,
    ) -> "Auth | None":
        """Get the client authentication handler configuration."""
        if auth_passthrough:
            from drunk_ai_proxy.auth import AuthPassThrough
            return AuthPassThrough()

        name, config = self.get_auth_config(provider_name)
        if config is None:
            return None

        match name:
            case AuthType.BASIC:
                from fastmcp.client.auth import BearerAuth
                return BearerAuth(**config)
            case AuthType.AZURE:
                from drunk_ai_proxy.auth import HttpxAzureOauth
                return HttpxAzureOauth(**config, scope=" ".join(config.get("scopes", [])))
            case _:
                raise ValueError(f"Unsupported authentication provider type: {name}")

    def get_mcp_configs(self) -> list["McpConfig"]:
        """Get the list of MCP server configurations."""
        return [mcp for mcp in self.config_path.mcp if mcp.enabled] if self.config_path.mcp else []

    def get_llm_configs(self) -> list["LlmConfig"]:
        """Get the list of LLM provider configurations."""
        return [llm for llm in self.config_path.llm if llm.enabled] if self.config_path.llm else []

    @classmethod
    def get_instance(cls) -> "AppConfigProvider":
        """Get the singleton instance of AppConfigProvider.

        Returns:
            Singleton AppConfigProvider instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_provider() -> AppConfigProvider:
    """Get the full application configuration."""
    return AppConfigProvider.get_instance()