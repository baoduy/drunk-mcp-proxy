from typing import TYPE_CHECKING, Any

from drunk_ai_proxy.utils import ConfigYaml, AuthType, McpConfig, LlmConfig, RemoteResourceConfig
from drunk_ai_proxy.utils.env import AUTH_ENABLED, CONFIG_DIR
from drunk_ai_proxy.app.auth_provider_registry import AuthProviderRegistry
from drunk_ai_proxy.app.client_auth_handler_factory import ClientAuthHandlerFactory
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
        configs = getattr(self, "_configs", None)
        auth_config = configs.auth if configs is not None else None
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
        assert name is not None
        return AuthProviderRegistry.create(
            name=name,
            config=config,
            provider_names=self._get_auth_provider_names(),
        )

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
        assert name is not None
        return ClientAuthHandlerFactory.create(
            name=name,
            config=config,
            provider_names=self._get_auth_provider_names(),
        )

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