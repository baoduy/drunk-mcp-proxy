"""
Unit tests for ConfigYaml configuration loader.

Tests the loading, parsing, and validation of YAML configuration files
using Pydantic models.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from drunk_ai_proxy.utils.config_yaml import (
    AuthConfig,
    BearerAuthConfig,
    ConfigYaml,
    JwtAuthConfig,
    LlmConfig,
    McpAuthConfig,
    McpConfig,
    OpenApiFilters,
    McpServerConfig,
    RemoteResourceConfig,
)


class TestBearerAuthConfig:
    """Tests for BearerAuthConfig model."""

    def test_bearer_auth_config_with_values(self) -> None:
        """Test creating BearerAuthConfig with valid values."""
        config = BearerAuthConfig(base_url="https://example.com", token="secret-token")
        assert config.base_url == "https://example.com"
        assert config.token == "secret-token"

    def test_bearer_auth_config_optional_fields(self) -> None:
        """Test BearerAuthConfig with optional fields."""
        config = BearerAuthConfig()
        assert config.base_url is None
        assert config.token is None

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_bearer_auth_config_resolves_env_vars(self) -> None:
        """Test that BearerAuthConfig resolves environment variables."""
        config = BearerAuthConfig(base_url="https://example.com", token="$API_KEY")
        assert config.token == "test-api-key"

    @patch.dict(os.environ, {}, clear=True)
    def test_bearer_auth_config_missing_env_var_raises_error(self) -> None:
        """Test that BearerAuthConfig raises error for missing environment variable."""
        with pytest.raises(ValueError, match="Environment variable 'API_KEY'"):
            BearerAuthConfig(base_url="https://example.com", token="$API_KEY")


class TestJwtAuthConfig:
    """Tests for JwtAuthConfig model."""

    def test_jwt_auth_config_with_values(self) -> None:
        """Test creating JwtAuthConfig with valid values."""
        config = JwtAuthConfig(
            jwks_uri="https://login.example.com/keys",
            issuer="https://example.com",
            audience="api://example",
        )
        assert config.jwks_uri == "https://login.example.com/keys"
        assert config.issuer == "https://example.com"
        assert config.audience == "api://example"

    @patch.dict(os.environ, {"TENANT_ID": "abc123", "AUDIENCE": "api://my-app"})
    def test_jwt_auth_config_resolves_env_vars(self) -> None:
        """Test that JwtAuthConfig resolves environment variables."""
        config = JwtAuthConfig(
            issuer="https://sts.windows.net/$TENANT_ID/",
            audience="$AUDIENCE",
        )
        assert config.issuer == "https://sts.windows.net/abc123/"
        assert config.audience == "api://my-app"


class TestLlmConfig:
    """Tests for LlmConfig model."""

    def test_llm_config_required_fields(self) -> None:
        """Test LlmConfig with required fields."""
        config = LlmConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
        )
        assert config.provider == "openai"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.enabled is True
        assert config.websocket is False
        assert config.api_key is None

    def test_llm_config_with_api_key(self) -> None:
        """Test LlmConfig with API key."""
        config = LlmConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
        )
        assert config.api_key == "sk-test-key"

    def test_llm_config_with_websocket_enabled(self) -> None:
        """Test LlmConfig with websocket support flag."""
        config = LlmConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            websocket=True,
        )
        assert config.websocket is True

    def test_llm_config_enabled_field(self) -> None:
        """Test LlmConfig enabled field."""
        config_enabled = LlmConfig(
            enabled=True,
            provider="openai",
            base_url="https://api.openai.com/v1",
        )
        assert config_enabled.enabled is True

        config_disabled = LlmConfig(
            enabled=False,
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
        )
        assert config_disabled.enabled is False

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-actual-key"})
    def test_llm_config_resolves_env_vars(self) -> None:
        """Test that LlmConfig resolves environment variables."""
        config = LlmConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="$OPENAI_API_KEY",
        )
        assert config.api_key == "sk-actual-key"


class TestMcpConfig:
    """Tests for McpConfig model."""

    def test_mcp_config_required_fields(self) -> None:
        """Test McpConfig with required fields."""
        mcp_servers = {
            "test-server": {
                "enabled": True,
                "command": "npx",
                "args": ["@playwright/mcp@0.0.64"],
                "transport": "stdio",
            }
        }
        config = McpConfig(path="/api", mcp_servers=mcp_servers)
        assert config.path == "/api"
        assert config.spec_type == "mcp"
        assert config.open_api is None

    def test_mcp_config_with_openapi_spec(self) -> None:
        """Test McpConfig with OpenAPI specification."""
        config = McpConfig(
            path="/deepsea",
            spec_type="openapi",
            open_api={
                "spec_file": "openapi/deepsea.openapi.json",
                "base_url": "http://localhost:5000",
            },
        )
        assert config.path == "/deepsea"
        assert config.open_api is not None
        assert config.open_api.spec_file == "openapi/deepsea.openapi.json"
        assert config.spec_type == "openapi"
        assert config.open_api.base_url == "http://localhost:5000"

    def test_mcp_config_with_filters(self) -> None:
        """Test McpConfig with filtering options."""
        filters = OpenApiFilters(methods=["GET", "POST"], tags=["CurrencyPairs"])
        config = McpConfig(
            path="/deepsea",
            spec_type="openapi",
            open_api={
                "spec_file": "openapi/deepsea.openapi.json",
                "base_url": "http://localhost:5000",
                "filters": filters.model_dump(exclude_none=True),
            },
        )
        assert config.open_api is not None
        assert config.open_api.filters is not None
        assert config.open_api.filters.methods == ["GET", "POST"]
        assert config.open_api.filters.tags == ["CurrencyPairs"]

    def test_mcp_config_with_skills_dirs(self) -> None:
        """Test McpConfig with skills.dirs."""
        mcp_servers = {
            "test-server": {
                "enabled": True,
                "command": "npx",
                "args": ["@playwright/mcp@0.0.64"],
                "transport": "stdio",
            }
        }
        config = McpConfig(
            path="/",
            spec_type="mcp",
            skills={"dirs": ["skills"]},
            mcp_servers=mcp_servers,
        )
        assert config.get_skill_dirs() == ["skills"]

    def test_mcp_config_with_mcp_servers(self) -> None:
        """Test McpConfig with inline mcpServers configuration."""
        mcp_servers = {
            "server-memory": {
                "enabled": True,
                "timeout": 60,
                "command": "npx",
                "args": ["@playwright/mcp@0.0.64"],
                "transport": "stdio",
            }
        }
        config = McpConfig(
            path="/",
            spec_type="mcp",
            mcpServers=mcp_servers,
        )
        assert config.mcp_servers == mcp_servers

    def test_mcp_config_with_auth(self) -> None:
        """Test McpConfig with authentication."""
        auth = McpAuthConfig(pass_through=True)
        config = McpConfig(
            path="/deepsea",
            spec_type="openapi",
            open_api={
                "spec_file": "openapi/deepsea.openapi.json",
                "base_url": "http://localhost:5000",
            },
            auth=auth,
        )
        assert config.auth is not None
        assert config.auth.pass_through is True

    @patch.dict(os.environ, {"SPEC_TITLE": "Test Spec"})
    def test_mcp_config_resolves_env_vars_in_spec_file(self, monkeypatch) -> None:
        """Test that McpConfig resolves env vars in loaded spec data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setattr("drunk_ai_proxy.utils.config_yaml.CONFIG_DIR", tmpdir)
            openapi_dir = Path(tmpdir) / "openapi"
            openapi_dir.mkdir(parents=True, exist_ok=True)
            spec_file = openapi_dir / "test-spec.json"
            spec_file.write_text(
                '{"openapi":"3.0.0","info":{"title":"$SPEC_TITLE","version":"1.0"},"paths":{}}'
            )

            config = McpConfig(
                path="/api",
                spec_type="openapi",
                open_api={
                    "spec_file": "openapi/test-spec.json",
                    "base_url": "http://localhost:5000",
                },
            )

            assert config.open_api is not None
            assert config.open_api.spec_data is not None
            assert config.open_api.spec_data["info"]["title"] == "Test Spec"


class TestMcpServerConfig:
    """Tests for McpServerConfig model."""

    @patch.dict(
        os.environ,
        {
            "CMD": "npx",
            "TOKEN": "secret-token",
            "HOST": "example.com",
        },
    )
    def test_mcp_server_config_resolves_env_vars(self) -> None:
        """Test that McpServerConfig resolves env vars in args and env."""
        config = McpServerConfig(
            command="$CMD",
            args=["$CMD", "--host", "$HOST"],
            env={
                "TOKEN": "$TOKEN",
                "URL": "https://$HOST/api",
            },
        )

        assert config.command == "npx"
        assert config.args == ["npx", "--host", "example.com"]
        assert config.env == {"TOKEN": "secret-token", "URL": "https://example.com/api"}


class TestAuthConfig:
    """Tests for AuthConfig model."""

    @patch.dict(os.environ, {"API_KEY": "test-key"})
    def test_auth_config_with_basic(self) -> None:
        """Test AuthConfig with Basic authentication."""
        config = AuthConfig(
            default_provider="basic",
            basic=BearerAuthConfig(token="$API_KEY"),
        )
        assert config.default_provider == "basic"
        assert config.basic is not None
        assert config.basic.token == "test-key"

    @patch.dict(os.environ, {"TENANT_ID": "abc123"})
    def test_auth_config_with_jwt(self) -> None:
        """Test AuthConfig with JWT authentication."""
        config = AuthConfig(
            default_provider="jwt",
            jwt=JwtAuthConfig(
                issuer="https://sts.windows.net/$TENANT_ID/",
            ),
        )
        assert config.default_provider == "jwt"
        assert config.jwt is not None
        assert config.jwt.issuer is not None and "abc123" in config.jwt.issuer


class TestConfigYamlLoading:
    """Tests for ConfigYaml loading and parsing."""

    def test_load_config_yaml_from_file(self) -> None:
        """Test loading ConfigYaml from actual config.yaml file."""
        config_file = "data/config.yaml"
        
        # Skip test if config file doesn't exist
        if not os.path.exists(config_file):
            pytest.skip(f"Config file {config_file} not found")

        # Set required environment variables
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "FASTMCP_API_KEY": "test-key",
                "OPENROUTER_API_KEY": "test-key",
                "OPENAI_API_KEY": "test-key",
                "AZURE_TENANT_ID": "test-tenant",
                "AZURE_CLIENT_ID": "test-client-id",
                "AZURE_CLIENT_SECRET": "test-client-secret",
                "NVIDIA_API_KEY": "test-key",
                "ALPHAVANTAGE_API_KEY": "test-key",
                "OUTLINE_API_KEY": "test-key",
            },
        ):
            config = ConfigYaml.load_from_file(config_file)

            assert config.auth is not None
            assert config.auth.default_provider == "basic"
            assert config.llm is not None
            assert len(config.llm) == 6
            assert config.mcp is not None
            assert len(config.mcp) == 5

    def test_load_config_yaml_missing_file(self) -> None:
        """Test that loading missing YAML file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ConfigYaml.load_from_file("data/nonexistent.yaml")

    def test_load_config_yaml_invalid_yaml(self) -> None:
        """Test that invalid YAML raises an error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content:")
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(Exception):  # yaml.YAMLError
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_load_config_yaml_empty_file(self) -> None:
        """Test that empty YAML file raises ValueError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("")
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration file is empty"):
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_load_config_yaml_not_mapping(self) -> None:
        """Test that YAML file with non-mapping content raises ValueError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("- item1\n- item2\n")
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="must contain a YAML mapping"):
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)


class TestConfigYamlParsing:
    """Tests for ConfigYaml parsing different configuration structures."""

    def test_parse_minimal_config(self) -> None:
        """Test parsing minimal YAML configuration."""
        yaml_content = "\n".join(
            [
                "mcp:",
                "  - path: /",
                "    spec_type: mcp",
                "    mcpServers:",
                "      test-server:",
                "        enabled: true",
                "        command: npx",
                "        args:",
                "          - \"@playwright/mcp@0.0.64\"",
                "        transport: stdio",
            ]
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            assert config.mcp is not None
            assert len(config.mcp) == 1
            assert config.mcp[0].path == "/"
            assert config.mcp[0].spec_type == "mcp"
        finally:
            os.unlink(temp_file)

    def test_parse_config_with_multiple_llms(self) -> None:
        """Test parsing configuration with multiple LLM providers."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key1",
                "ANTHROPIC_API_KEY": "test-key2",
            },
        ):
            yaml_content = """
llm:
  - enabled: true
    provider: openai
    base_url: https://api.openai.com/v1
    api_key: $OPENAI_API_KEY
  - enabled: true
    provider: anthropic
    base_url: https://api.anthropic.com
    api_key: $ANTHROPIC_API_KEY
"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(yaml_content)
                f.flush()
                temp_file = f.name

            try:
                config = ConfigYaml.load_from_file(temp_file)
                assert config.llm is not None
                assert len(config.llm) == 2
                assert config.llm[0].provider == "openai"
                assert config.llm[1].provider == "anthropic"
                assert config.llm[0].api_key == "test-key1"
                assert config.llm[1].api_key == "test-key2"
            finally:
                os.unlink(temp_file)


class TestRemoteResourceConfig:
    """Tests for RemoteResourceConfig model."""

    def test_remote_resource_config_basic(self) -> None:
        """Test creating RemoteResourceConfig with required fields."""
        config = RemoteResourceConfig(
            name="test-bundle",
            to_dir="prompts/dotnet",
            paths=["https://example.com/file1.md", "https://example.com/file2.md"]
        )
        assert config.name == "test-bundle"
        assert config.enabled is True
        assert config.to_dir == "prompts/dotnet"
        assert len(config.paths) == 2
        assert config.paths[0] == "https://example.com/file1.md"
        assert config.headers is None

    def test_remote_resource_config_with_headers_placeholder(self) -> None:
        """Test RemoteResourceConfig accepts optional headers placeholder field."""
        config = RemoteResourceConfig(
            name="private-bundle",
            to_dir="prompts/private",
            paths=["https://example.com/private.md"],
            headers={"Authorization": "Bearer static-token"},
        )

        assert config.headers is not None
        assert config.headers["Authorization"] == "Bearer static-token"

    def test_remote_resource_config_empty_paths(self) -> None:
        """Test RemoteResourceConfig with empty paths list."""
        config = RemoteResourceConfig(
            name="empty-bundle",
            to_dir="prompts/empty",
            paths=[]
        )
        assert config.name == "empty-bundle"
        assert len(config.paths) == 0

    def test_config_yaml_with_remote_resources(self) -> None:
        """Test ConfigYaml parsing with remote_resources section."""
        yaml_content = "\n".join(
            [
                "remote_resources:",
                "  - name: test-bundle",
                "    enabled: false",
                "    to_dir: prompts/test",
                "    paths:",
                "      - https://example.com/file1.md",
            ]
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            assert config.remote_resources is not None
            assert len(config.remote_resources) == 1
            assert config.remote_resources[0].name == "test-bundle"
            assert config.remote_resources[0].enabled is False
            assert config.remote_resources[0].to_dir == "prompts/test"
            assert len(config.remote_resources[0].paths) == 1
        finally:
            os.unlink(temp_file)

    def test_config_yaml_remote_resource_enabled_defaults_to_true(self) -> None:
        """Test remote_resources enabled defaults to true when omitted."""
        yaml_content = """
remote_resources:
  - name: default-enabled-bundle
    to_dir: prompts/default
    paths:
      - https://example.com/file1.md
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            assert config.remote_resources is not None
            assert len(config.remote_resources) == 1
            assert config.remote_resources[0].enabled is True
        finally:
            os.unlink(temp_file)

    def test_config_yaml_without_remote_resources(self) -> None:
        """Test ConfigYaml when remote_resources section is absent."""
        yaml_content = """
auth:
  default_provider: basic
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            assert config.remote_resources is None
        finally:
            os.unlink(temp_file)

    def test_config_yaml_empty_remote_resources(self) -> None:
        """Test ConfigYaml with empty remote_resources section."""
        yaml_content = """
auth:
  default_provider: basic

remote_resources: []
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            assert config.remote_resources is not None
            assert len(config.remote_resources) == 0
        finally:
            os.unlink(temp_file)

    def test_parse_config_with_mcp_inline_servers(self) -> None:
        """Test parsing configuration with inline MCP servers."""
        yaml_content = """
mcp:
  - path: /
    spec_type: mcp
    mcpServers:
      server-memory:
        enabled: true
        timeout: 60
        command: npx
        args:
          - "@playwright/mcp@0.0.64"
        transport: stdio
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            assert config.mcp is not None
            assert len(config.mcp) == 1
            assert config.mcp[0].mcp_servers is not None
            assert "server-memory" in config.mcp[0].mcp_servers
        finally:
            os.unlink(temp_file)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("drunk_ai_proxy.utils.config_yaml.CONFIG_DIR", "/tmp")
    def test_parse_config_with_complete_structure(self, monkeypatch) -> None:
        """Test parsing configuration with complete auth, llm, and mcp sections."""
        # Create a temporary spec file
        import tempfile
        temp_dir = tempfile.mkdtemp()
        openapi_dir = os.path.join(temp_dir, "openapi")
        os.makedirs(openapi_dir, exist_ok=True)
        spec_file_path = os.path.join(openapi_dir, "api.json")
        with open(spec_file_path, "w") as f:
            f.write('{"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}')
        
        # Patch CONFIG_DIR to use temp directory
        monkeypatch.setattr("drunk_ai_proxy.utils.config_yaml.CONFIG_DIR", temp_dir)
        
        yaml_content = "\n".join(
            [
                "auth:",
                "  default_provider: basic",
                "  basic:",
                "    base_url: null",
                "    token: null",
                "",
                "llm:",
                "  - enabled: true",
                "    provider: openai",
                "    base_url: https://api.openai.com/v1",
                "    api_key: $OPENAI_API_KEY",
                "",
                "mcp:",
                "  - path: /api",
                "    spec_type: openapi",
                "    open_api:",
                "      spec_file: openapi/api.json",
                "      base_url: http://localhost:5000",
                "      filters:",
                "        methods:",
                "          - GET",
                "          - POST",
                "        tags:",
                "          - Test",
                "    auth:",
                "      pass_through: true",
            ]
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)

            # Verify auth section
            assert config.auth is not None
            assert config.auth.default_provider == "basic"

            # Verify llm section
            assert config.llm is not None
            assert len(config.llm) == 1
            assert config.llm[0].provider == "openai"
            assert config.llm[0].api_key == "test-key"

            # Verify mcp section
            assert config.mcp is not None
            assert len(config.mcp) == 1
            mcp = config.mcp[0]
            assert mcp.path == "/api"
            assert mcp.open_api is not None
            assert mcp.open_api.spec_file == "openapi/api.json"
            assert mcp.open_api.base_url == "http://localhost:5000"
            assert mcp.open_api.filters is not None
            assert mcp.open_api.filters.methods == ["GET", "POST"]
            assert mcp.open_api.filters.tags == ["Test"]
            assert mcp.auth is not None
            assert mcp.auth.pass_through is True
        finally:
            os.unlink(temp_file)
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigYamlEnvVarResolution:
    """Tests for environment variable resolution in ConfigYaml."""

    def test_env_var_missing_basic_token(self) -> None:
        """Test that missing environment variable raises error."""
        yaml_content = """
auth:
  default_provider: basic
  basic:
    token: $MISSING_API_KEY
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError, match="MISSING_API_KEY"):
                    ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_env_var_with_braces_syntax(self) -> None:
        """Test environment variable resolution with ${VAR} syntax."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            yaml_content = """
llm:
  - enabled: true
    provider: openai
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(yaml_content)
                f.flush()
                temp_file = f.name

            try:
                config = ConfigYaml.load_from_file(temp_file)
                assert config.llm is not None
                assert config.llm[0].api_key == "sk-test"
            finally:
                os.unlink(temp_file)

    def test_env_var_interpolation_in_url(self) -> None:
        """Test environment variable interpolation within URLs."""
        with patch.dict(os.environ, {"TENANT_ID": "my-tenant"}):
            yaml_content = """
auth:
  default_provider: jwt
  jwt:
    issuer: https://sts.windows.net/${TENANT_ID}/
"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(yaml_content)
                f.flush()
                temp_file = f.name

            try:
                config = ConfigYaml.load_from_file(temp_file)
                assert config.auth is not None
                assert config.auth.jwt is not None
                assert config.auth.jwt.issuer == "https://sts.windows.net/my-tenant/"
            finally:
                os.unlink(temp_file)
