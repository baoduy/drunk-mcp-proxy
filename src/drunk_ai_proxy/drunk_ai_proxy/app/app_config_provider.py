from typing import TYPE_CHECKING, Any

from drunk_ai_proxy.utils import ConfigYaml, AuthType, McpConfig, LlmConfig, RemoteResourceConfig
from drunk_ai_proxy.utils.env import AUTH_ENABLED, CONFIG_DIR
from drunk_ai_proxy.app.cache_provider import CacheProvider
if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider
    from httpx import Auth


class AppConfigProvider:
    """Provides application configuration."""

    _instance: "AppConfigProvider | None" = None

    def __init__(self) -> None:
        self._configs = ConfigYaml.load_from_file(f"{CONFIG_DIR}/config.yaml")

    def _get_auth_config(
        self,
        provider_name: AuthType | str | None = None,
    ) -> tuple[AuthType | None, dict[str, Any] | None]:
        """Get the authentication configuration for a given provider name."""
        auth_config = self._configs.auth
        if auth_config is None:
            return (None, None)
        name = auth_config.normalize_provider_name(provider_name)

        config = auth_config[name]
        return (name, config)

    def _get_auth_provider_names(self) -> list[str]:
        """Get a list of available authentication provider names."""
        auth_config = self._configs.auth
        if auth_config is None:
            return []
        auth_data = auth_config.model_dump(exclude_none=True, by_alias=True)
        auth_data.pop("default_provider", None)
        return list(auth_data.keys())
    
    def get_fast_mcp_auth_provider(
        self,
        provider_name: AuthType | None = None,
    ) -> "AuthProvider | None":
        """Get the FastMCP authentication provider configuration."""
        if not AUTH_ENABLED:
            return None

        name, config = self._get_auth_config(provider_name)
        if config is None:
            return None

        match name:
            case AuthType.BASIC:
                from drunk_ai_proxy.auth.api_auth_provider import ApiKeyAuthProvider
                return ApiKeyAuthProvider(**config)
            case AuthType.JWT:
                from fastmcp.server.auth.providers.jwt import JWTVerifier
                return JWTVerifier(**config)
            case AuthType.AZURE:
                 from fastmcp.server.auth.providers.azure import AzureProvider
                 return AzureProvider(**config,client_storage=CacheProvider.get_oauth_store())
            case AuthType.AUTH0:
                 from fastmcp.server.auth.providers.auth0 import Auth0Provider
                 return Auth0Provider(**config,client_storage=CacheProvider.get_oauth_store())
            case AuthType.AWS:
                 from fastmcp.server.auth.providers.aws import AWSCognitoProvider
                 return AWSCognitoProvider(**config,client_storage=CacheProvider.get_oauth_store())
            case AuthType.DISCORD:
                from fastmcp.server.auth.providers.discord import DiscordProvider
                return DiscordProvider(**config,client_storage=CacheProvider.get_oauth_store())
            case AuthType.GITHUB:
                from fastmcp.server.auth.providers.github import GitHubProvider
                return GitHubProvider(**config,client_storage=CacheProvider.get_oauth_store())
            case AuthType.GOOGLE:
                from fastmcp.server.auth.providers.google import GoogleProvider
                return GoogleProvider(**config,client_storage=CacheProvider.get_oauth_store())
            case AuthType.IN_MEMORY:
                from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider
                return InMemoryOAuthProvider(**config)
            case AuthType.INTROSPECTION:
                from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier
                return IntrospectionTokenVerifier(**config)
            case AuthType.OCI:
                 from fastmcp.server.auth.providers.oci import OCIProvider
                 return OCIProvider(**config,client_storage=CacheProvider.get_oauth_store())
            case AuthType.SUPABASE:
                from fastmcp.server.auth.providers.supabase import SupabaseProvider
                return SupabaseProvider(**config)
            case _:
                raise ValueError(f"Unsupported authentication provider type: {name} in {self._get_auth_provider_names()}")

    def get_client_auth_handler(
        self,
        provider_name: AuthType | None = None,
        auth_passthrough: bool = False,
    ) -> "Auth | None":
        """Get the client authentication handler configuration."""
        if auth_passthrough:
            from drunk_ai_proxy.auth import AuthPassThrough
            return AuthPassThrough()

        name, config = self._get_auth_config(provider_name)
        if config is None:
            return None

        match name:
            case AuthType.BASIC:
                from fastmcp.client.auth import BearerAuth
                return BearerAuth(**config)
            case AuthType.AZURE:
                from drunk_ai_proxy.auth import HttpxAzureOauth
                return HttpxAzureOauth(client_id=config["client_id"], client_secret=config["client_secret"], tenant_id=config["tenant_id"],token_storage=CacheProvider.get_oauth_store())
            case _:
                raise ValueError(f"Unsupported authentication provider type: {name} in {self._get_auth_provider_names()}")

    def get_mcp_configs(self) -> list["McpConfig"]:
        """Get the list of MCP server configurations."""
        return [mcp for mcp in self._configs.mcp if mcp.enabled] if self._configs.mcp else []

    def get_llm_configs(self) -> list["LlmConfig"]:
        """Get the list of LLM provider configurations."""
        return [llm for llm in self._configs.llm if llm.enabled] if self._configs.llm else []

    def get_remote_resources(self) -> list[RemoteResourceConfig]:
        """Get the list of remote resource configurations.
        
        Returns:
            List of RemoteResourceConfig instances, or empty list if none configured.
        """
        return self._configs.remote_resources if self._configs.remote_resources else []

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