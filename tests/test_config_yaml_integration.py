"""
Integration tests for ConfigYaml loading and validation.

These tests verify that the YAML configuration system works end-to-end,
including file loading, environment variable resolution, and validation.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.tools.config_yaml import ConfigYaml, McpConfig, AuthConfig, LlmConfig


class TestConfigYamlIntegration:
    """Integration tests for loading complete config.yaml files."""

    @patch.dict(
        os.environ,
        {
            "API_KEY": "test-api-key-123",
            "OPENAI_API_KEY": "test-openai-key-456",
            "AZURE_TENANT_ID": "test-tenant-789",
        },
    )
    def test_load_complete_config_file(self, monkeypatch):
        """Test loading a complete config.yaml file with all sections."""
        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch CONFIG_DIR to use temp directory
            monkeypatch.setattr("src.tools.config_yaml.CONFIG_DIR", tmpdir)
            
            # Create the openapi directory and spec file
            openapi_dir = Path(tmpdir) / "openapi"
            openapi_dir.mkdir(parents=True, exist_ok=True)
            spec_file = openapi_dir / "test-api.json"
            spec_file.write_text('{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}, "paths": {}}')
            
            yaml_content = """
auth:
  defaultProvider: basic
  basic:
    base_url: null
    token: $API_KEY
  jwt:
    base_url: null
    jwks_uri: https://login.microsoftonline.com/common/discovery/keys
    issuer: https://sts.windows.net/$AZURE_TENANT_ID/
    audience: api://test-audience

llm:
  - enabled: true
    websocket: true
    provider: openai
    base_url: https://api.openai.com/v1
    api_key: $OPENAI_API_KEY
    
  - enabled: false
    websocket: false
    provider: test-provider
    base_url: https://test.example.com
    api_key: test-key

mcp:
  - path: /
    spec_type: mcp
    mcpServers:
      memory-server:
        enabled: true
        transport: stdio
        command: npx
        args: ["@modelcontextprotocol/server-memory"]
        
  - path: /api/v1
    spec_type: openapi
    spec_file: openapi/test-api.json
    base_url: https://api.example.com
    filters:
      methods:
        - GET
        - POST
      tags:
        - public
    auth:
      pass_through: true
"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(yaml_content)
                f.flush()
                temp_file = f.name

            try:
                config = ConfigYaml.load_from_file(temp_file)

                # Verify auth configuration
                assert config.auth is not None
                assert config.auth.default_provider == "basic"
                assert config.auth.basic is not None
                assert config.auth.basic.token == "test-api-key-123"  # Resolved from env
                assert config.auth.jwt is not None
                assert "test-tenant-789" in config.auth.jwt.issuer  # Resolved from env

                # Verify LLM configuration
                assert config.llm is not None
                assert len(config.llm) == 2
                assert config.llm[0].enabled is True
                assert config.llm[0].websocket is True
                assert config.llm[0].provider == "openai"
                assert config.llm[0].api_key == "test-openai-key-456"  # Resolved from env
                assert config.llm[1].enabled is False
                assert config.llm[1].websocket is False

                # Verify MCP configuration
                assert config.mcp is not None
                assert len(config.mcp) == 2
                
                # First MCP config (root with inline servers)
                mcp_root = config.mcp[0]
                assert mcp_root.path == "/"
                assert mcp_root.spec_type == "mcp"
                assert mcp_root.mcp_servers is not None
                assert "memory-server" in mcp_root.mcp_servers
                
                # Second MCP config (OpenAPI with spec file)
                mcp_api = config.mcp[1]
                assert mcp_api.path == "/api/v1"
                assert mcp_api.spec_type == "openapi"
                assert mcp_api.spec_file == "openapi/test-api.json"
                assert mcp_api.base_url == "https://api.example.com"
                assert mcp_api.filters is not None
                assert mcp_api.filters.methods == ["GET", "POST"]
                assert mcp_api.filters.tags == ["public"]
                assert mcp_api.auth is not None
                assert mcp_api.auth.pass_through is True

            finally:
                os.unlink(temp_file)

    @patch.dict(os.environ, {"TEST_TOKEN": "my-secret-token"})
    def test_env_var_resolution_across_sections(self):
        """Test that environment variables are resolved across all config sections."""
        yaml_content = """
auth:
  defaultProvider: basic
  basic:
    token: $TEST_TOKEN

llm:
  - enabled: true
    provider: test
    base_url: https://api.test.com
    api_key: $TEST_TOKEN

mcp:
  - path: /test
    spec_type: mcp
    mcpServers:
      test-server:
        enabled: true
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)

            # Verify env var resolved in auth
            assert config.auth.basic.token == "my-secret-token"

            # Verify env var resolved in llm
            assert config.llm[0].api_key == "my-secret-token"

        finally:
            os.unlink(temp_file)

    def test_mcp_config_validation_requires_spec_or_servers(self):
        """Test that MCP config requires either spec_file or mcp_servers."""
        yaml_content = """
mcp:
  - path: /broken
    spec_type: mcp
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="For MCP spec type, either spec_file or mcp_servers must be provided"):
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_openapi_config_validation_requires_base_url(self):
        """Test that OpenAPI config requires base_url."""
        yaml_content = """
mcp:
  - path: /broken
    spec_type: openapi
    spec_file: openapi/test.json
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="base_url is required for OpenAPI spec type"):
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_openapi_config_validation_requires_spec_file(self):
        """Test that OpenAPI config requires spec_file."""
        yaml_content = """
mcp:
  - path: /broken
    spec_type: openapi
    base_url: https://api.example.com
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="spec_file is required for OpenAPI spec type"):
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    @patch.dict(os.environ, {"VAR1": "value1", "VAR2": "value2"})
    def test_multiple_env_vars_in_single_value(self):
        """Test resolving multiple environment variables in a single value."""
        yaml_content = """
auth:
  defaultProvider: basic
  basic:
    token: ${VAR1}-${VAR2}

mcp:
  - path: /test
    spec_type: mcp
    mcpServers:
      test:
        enabled: true
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            assert config.auth.basic.token == "value1-value2"
        finally:
            os.unlink(temp_file)


class TestConfigYamlMigrationFromJson:
    """Tests verifying migration from old JSON config to new YAML config."""

    @patch.dict(os.environ, {"API_KEY": "test-key"})
    def test_auth_section_equivalent_to_auth_json(self):
        """Test that YAML auth section is equivalent to old auth.json format."""
        # Old auth.json format:
        # {
        #   "defaultProvider": "bearer",
        #   "bearer": {"token": "$API_KEY"}
        # }
        
        # New YAML format uses 'basic' instead of 'bearer'
        yaml_content = """
auth:
  defaultProvider: basic
  basic:
    token: $API_KEY
    
mcp:
  - path: /test
    spec_type: mcp
    mcpServers:
      test: {enabled: true}
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            
            # Verify it works like the old auth.json
            assert config.auth.default_provider == "basic"
            assert config.auth.basic.token == "test-key"
            
            # Can access auth config via dict-like interface
            basic_config = config.auth["basic"]
            assert basic_config is not None
            assert basic_config["token"] == "test-key"
            
        finally:
            os.unlink(temp_file)

    def test_mcp_section_equivalent_to_config_json(self, monkeypatch):
        """Test that YAML mcp section is equivalent to old config.json format."""
        # Old config.json had array of specs with spec_file and spec_type
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch CONFIG_DIR to use temp directory
            monkeypatch.setattr("src.tools.config_yaml.CONFIG_DIR", tmpdir)
            
            # Create the openapi directory and spec file
            openapi_dir = Path(tmpdir) / "openapi"
            openapi_dir.mkdir(parents=True, exist_ok=True)
            spec_file = openapi_dir / "test.json"
            spec_file.write_text('{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}, "paths": {}}')
            
            yaml_content = """
mcp:
  - path: /api
    spec_type: openapi
    spec_file: openapi/test.json
    base_url: https://api.example.com
    filters:
      methods: [GET, POST]
      tags: [public]
"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(yaml_content)
                f.flush()
                temp_file = f.name

            try:
                config = ConfigYaml.load_from_file(temp_file)
                
                # Verify it works like the old config.json
                assert len(config.mcp) == 1
                assert config.mcp[0].path == "/api"
                assert config.mcp[0].spec_type == "openapi"
                assert config.mcp[0].spec_file == "openapi/test.json"
                assert config.mcp[0].base_url == "https://api.example.com"
                assert config.mcp[0].filters.methods == ["GET", "POST"]
                assert config.mcp[0].filters.tags == ["public"]
                
            finally:
                os.unlink(temp_file)

    @patch.dict(os.environ, {"OPENAI_KEY": "sk-test123"})
    def test_llm_section_equivalent_to_llm_json(self):
        """Test that YAML llm section is equivalent to old llm.json format."""
        # Old llm.json was an array of provider configs
        yaml_content = """
llm:
  - enabled: true
    provider: openai
    base_url: https://api.openai.com/v1
    api_key: $OPENAI_KEY
    
mcp:
  - path: /test
    spec_type: mcp
    mcpServers:
      test: {enabled: true}
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            
            # Verify it works like the old llm.json
            assert len(config.llm) == 1
            assert config.llm[0].enabled is True
            assert config.llm[0].provider == "openai"
            assert config.llm[0].base_url == "https://api.openai.com/v1"
            assert config.llm[0].api_key == "sk-test123"
            
        finally:
            os.unlink(temp_file)


class TestConfigYamlEdgeCases:
    """Test edge cases and error conditions in YAML config."""

    def test_empty_config_file(self):
        """Test that empty config file is handled properly."""
        yaml_content = ""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration file is empty"):
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_non_dict_config_file(self):
        """Test that non-dict config file raises error."""
        yaml_content = "- item1\n- item2"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Configuration file must contain a YAML mapping"):
                ConfigYaml.load_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_missing_config_file(self):
        """Test that missing config file raises error."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            ConfigYaml.load_from_file("/nonexistent/config.yaml")

    def test_config_with_only_auth(self):
        """Test config with only auth section."""
        yaml_content = """
auth:
  defaultProvider: basic
  basic:
    token: test-token
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
            assert config.auth.default_provider == "basic"
            assert config.llm is None or len(config.llm) == 0
            assert config.mcp is None or len(config.mcp) == 0
            
        finally:
            os.unlink(temp_file)

    @patch.dict(os.environ, {"LLM_KEY": "test-llm-key"})
    def test_config_with_only_llm(self):
        """Test config with only llm section."""
        yaml_content = """
llm:
  - enabled: true
    provider: test-provider
    base_url: https://test.com
    api_key: $LLM_KEY
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
            assert len(config.llm) == 1
            assert config.llm[0].api_key == "test-llm-key"
            assert config.auth is None
            assert config.mcp is None or len(config.mcp) == 0
            
        finally:
            os.unlink(temp_file)

    def test_config_with_only_mcp(self):
        """Test config with only mcp section."""
        yaml_content = """
mcp:
  - path: /test
    spec_type: mcp
    mcpServers:
      test-server:
        enabled: true
        command: test
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
            assert config.auth is None
            assert config.llm is None or len(config.llm) == 0
            
        finally:
            os.unlink(temp_file)


class TestConfigYamlMcpServersFieldAlias:
    """Test that mcpServers (camelCase) is properly aliased to mcp_servers (snake_case)."""

    def test_camelcase_mcpservers_in_yaml(self):
        """Test that camelCase 'mcpServers' in YAML is accepted."""
        yaml_content = """
mcp:
  - path: /test
    spec_type: mcp
    mcpServers:
      test-server:
        enabled: true
        transport: stdio
        command: node
        args: ["server.js"]
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            
            # Should be accessible via snake_case property
            assert config.mcp[0].mcp_servers is not None
            assert "test-server" in config.mcp[0].mcp_servers
            assert config.mcp[0].mcp_servers["test-server"]["command"] == "node"
            
        finally:
            os.unlink(temp_file)

    def test_snakecase_mcp_servers_also_works(self):
        """Test that snake_case 'mcp_servers' also works in YAML."""
        yaml_content = """
mcp:
  - path: /test
    spec_type: mcp
    mcp_servers:
      test-server:
        enabled: true
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_file = f.name

        try:
            config = ConfigYaml.load_from_file(temp_file)
            
            # Should be accessible via snake_case property
            assert config.mcp[0].mcp_servers is not None
            assert "test-server" in config.mcp[0].mcp_servers
            
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
