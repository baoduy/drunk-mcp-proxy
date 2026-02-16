"""
Unit tests for SpecConfig data model.

Tests validation, loading, and error handling for proxy configuration.
"""

import json
import os
import tempfile

import pytest
from pydantic import ValidationError

from tools.spec_config import SpecConfig


class TestSpecConfigValidation:
    """Test Pydantic validation for SpecConfig fields."""

    def test_valid_openapi_config(self):
        """Test creating a valid OpenAPI config."""
        config = SpecConfig.model_validate({
            "path": "/test-api",
            "spec_file": "api.openapi.json",
            "spec_type": "openapi",
            "base_url": "http://localhost:5000"
        })

        assert config.path == "/test-api"
        assert config.spec_file == "api.openapi.json"
        assert config.spec_type == "openapi"
        assert config.base_url == "http://localhost:5000"
        assert config.tags is None

    def test_valid_mcp_config(self):
        """Test creating a valid MCP config."""
        config = SpecConfig.model_validate({
            "path": "/test-mcp",
            "spec_file": "mcp.json",
            "spec_type": "mcp"
        })

        assert config.path == "/test-mcp"
        assert config.spec_file == "mcp.json"
        assert config.spec_type == "mcp"
        assert config.base_url is None

    def test_config_with_optional_fields(self):
        """Test config with all optional fields."""
        config = SpecConfig.model_validate({
            "path": "/api",
            "spec_file": "test.json",
            "spec_type": "mcp",
            "tags": ["internal", "debug"]
        })

        assert config.path == "/api"
        assert config.tags == {"internal", "debug"}

    def test_missing_required_path(self):
        """Test validation fails when path is missing."""
        with pytest.raises(ValidationError) as exc_info:
            SpecConfig.model_validate({
                "spec_file": "test.json",
                "spec_type": "mcp"
            })

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)

    def test_missing_required_spec_file(self):
        """Test validation fails when spec_file is missing."""
        with pytest.raises(ValidationError) as exc_info:
            SpecConfig.model_validate({
                "path": "/test",
                "spec_type": "mcp"
            })

        errors = exc_info.value.errors()
        # Check for spec_file field name
        assert any(e["loc"] == ("spec_file",) for e in errors)

    def test_missing_required_spec_type(self):
        """Test validation fails when spec_type is missing."""
        with pytest.raises(ValidationError) as exc_info:
            SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "test.json"
            })

        errors = exc_info.value.errors()
        # Check for spec_type field name
        assert any(e["loc"] == ("spec_type",) for e in errors)

    def test_empty_path_field(self):
        """Test validation fails when path is empty."""
        with pytest.raises(ValidationError) as exc_info:
            SpecConfig.model_validate({
                "path": "",
                "spec_file": "test.json",
                "spec_type": "mcp"
            })

        errors = exc_info.value.errors()
        assert any("empty" in str(e["msg"]).lower() for e in errors)

    def test_empty_spec_file_field(self):
        """Test validation fails when spec_file is empty."""
        with pytest.raises(ValidationError) as exc_info:
            SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "   ",
                "spec_type": "mcp"
            })

        errors = exc_info.value.errors()
        assert any("empty" in str(e["msg"]).lower() for e in errors)

    def test_invalid_spec_type(self):
        """Test validation fails for invalid spec_type."""
        with pytest.raises(ValidationError) as exc_info:
            SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "test.json",
                "spec_type": "invalid"
            })

        errors = exc_info.value.errors()
        assert any("openapi" in str(e["msg"]).lower() or "mcp" in str(e["msg"]).lower() for e in errors)

    def test_openapi_requires_base_url(self):
        """Test that OpenAPI spec requires base_url."""
        with pytest.raises(ValidationError) as exc_info:
            SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "test.json",
                "spec_type": "openapi"
            })

        errors = exc_info.value.errors()
        assert any("base_url" in str(e["msg"]).lower() for e in errors)

    def test_mcp_does_not_require_base_url(self):
        """Test that MCP spec does not require base_url."""
        config = SpecConfig.model_validate({
            "path": "/test",
            "spec_file": "test.json",
            "spec_type": "mcp"
        })

        assert config.base_url is None


class TestSpecConfigLoadSpecFile:
    """Test loading spec files into spec_data."""

    def test_load_valid_json_spec(self):
        """Test loading a valid JSON spec file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test spec file
            spec_data = {"openapi": "3.0.0", "info": {"title": "Test API"}}
            spec_file = os.path.join(tmpdir, "test.openapi.json")
            with open(spec_file, "w") as f:
                json.dump(spec_data, f)

            # Create config and load spec
            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "test.openapi.json",
                "spec_type": "openapi",
                "base_url": "http://localhost"
            })

            config._load_spec_file(tmpdir)

            assert config.spec_data is not None
            assert config.spec_data["openapi"] == "3.0.0"
            assert config.spec_data["info"]["title"] == "Test API"

    def test_load_spec_file_not_found(self):
        """Test loading non-existent spec file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "nonexistent.json",
                "spec_type": "mcp"
            })

            with pytest.raises(FileNotFoundError) as exc_info:
                config._load_spec_file(tmpdir)

            assert "nonexistent.json" in str(exc_info.value)

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises JSONDecodeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid JSON file
            spec_file = os.path.join(tmpdir, "invalid.json")
            with open(spec_file, "w") as f:
                f.write("{ invalid json }")

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "invalid.json",
                "spec_type": "mcp"
            })

            with pytest.raises(json.JSONDecodeError):
                config._load_spec_file(tmpdir)

    def test_load_non_dict_json(self):
        """Test loading JSON array instead of object raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create JSON array file
            spec_file = os.path.join(tmpdir, "array.json")
            with open(spec_file, "w") as f:
                json.dump([1, 2, 3], f)

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "array.json",
                "spec_type": "mcp"
            })

            with pytest.raises(ValueError) as exc_info:
                config._load_spec_file(tmpdir)

            assert "json object" in str(exc_info.value).lower()

    def test_load_empty_json_object(self):
        """Test loading empty JSON object raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty JSON object
            spec_file = os.path.join(tmpdir, "empty.json")
            with open(spec_file, "w") as f:
                json.dump({}, f)

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "empty.json",
                "spec_type": "mcp"
            })

            with pytest.raises(ValueError) as exc_info:
                config._load_spec_file(tmpdir)

            assert "no data" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()


class TestSpecConfigMCPSchemaValidation:
    """Test MCP spec validation against JSON schema."""

    def test_load_valid_mcp_spec(self):
        """Test loading a valid MCP spec that conforms to schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid MCP spec
            mcp_spec = {
                "mcpServers": {
                    "test-server": {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["@modelcontextprotocol/server-memory"]
                    }
                }
            }
            spec_file = os.path.join(tmpdir, "mcp.json")
            with open(spec_file, "w") as f:
                json.dump(mcp_spec, f)

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "mcp.json",
                "spec_type": "mcp"
            })

            # Should not raise any exception
            config._load_spec_file(tmpdir)
            assert config.spec_data["mcpServers"]["test-server"]["transport"] == "stdio"  # type: ignore[index]

    def test_load_invalid_mcp_spec_missing_mcpServers(self):
        """Test loading MCP spec without required mcpServers field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid MCP spec (missing mcpServers)
            invalid_spec = {
                "someOtherField": "value"
            }
            spec_file = os.path.join(tmpdir, "invalid.json")
            with open(spec_file, "w") as f:
                json.dump(invalid_spec, f)

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "invalid.json",
                "spec_type": "mcp"
            })

            with pytest.raises(ValueError) as exc_info:
                config._load_spec_file(tmpdir)

            assert "schema" in str(exc_info.value).lower()
            assert "mcpservers" in str(exc_info.value).lower()

    def test_load_invalid_mcp_spec_missing_transport(self):
        """Test loading MCP spec without required transport field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid MCP spec (missing transport)
            invalid_spec = {
                "mcpServers": {
                    "test-server": {
                        "command": "npx"
                    }
                }
            }
            spec_file = os.path.join(tmpdir, "invalid.json")
            with open(spec_file, "w") as f:
                json.dump(invalid_spec, f)

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "invalid.json",
                "spec_type": "mcp"
            })

            with pytest.raises(ValueError) as exc_info:
                config._load_spec_file(tmpdir)

            assert "schema" in str(exc_info.value).lower()

    def test_load_mcp_spec_with_http_transport(self):
        """Test loading MCP spec with HTTP transport."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create valid MCP spec with HTTP transport
            mcp_spec = {
                "mcpServers": {
                    "http-server": {
                        "transport": "http",
                        "url": "http://localhost:3000"
                    }
                }
            }
            spec_file = os.path.join(tmpdir, "mcp.json")
            with open(spec_file, "w") as f:
                json.dump(mcp_spec, f)

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "mcp.json",
                "spec_type": "mcp"
            })

            # Should not raise any exception
            config._load_spec_file(tmpdir)
            assert config.spec_data["mcpServers"]["http-server"]["transport"] == "http"  # type: ignore[index]

    def test_openapi_spec_not_validated_against_mcp_schema(self):
        """Test that OpenAPI specs are not validated against MCP schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an OpenAPI spec (not an MCP spec)
            openapi_spec = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {}
            }
            spec_file = os.path.join(tmpdir, "openapi.json")
            with open(spec_file, "w") as f:
                json.dump(openapi_spec, f)

            config = SpecConfig.model_validate({
                "path": "/test",
                "spec_file": "openapi.json",
                "spec_type": "openapi",
                "base_url": "http://localhost"
            })

            # Should not raise MCP schema validation error
            config._load_spec_file(tmpdir)
            assert config.spec_data["openapi"] == "3.0.0"  # type: ignore[index]


class TestSpecConfigLoadFromFile:
    """Test loading multiple configs from a configuration file."""

    def test_load_multiple_configs(self):
        """Test loading multiple valid configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create spec files
            openapi_spec = {"openapi": "3.0.0", "info": {"title": "API"}}
            mcp_spec = {
                "mcpServers": {
                    "test": {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["test-mcp-server"]
                    }
                }
            }

            with open(os.path.join(tmpdir, "api.openapi.json"), "w") as f:
                json.dump(openapi_spec, f)
            with open(os.path.join(tmpdir, "mcp.json"), "w") as f:
                json.dump(mcp_spec, f)

            # Create config file
            config_data = [
                {
                    "path": "/api",
                    "spec_file": "api.openapi.json",
                    "spec_type": "openapi",
                    "base_url": "http://localhost:5000"
                },
                {
                    "path": "/mcp",
                    "spec_file": "mcp.json",
                    "spec_type": "mcp"
                }
            ]
            config_file = os.path.join(tmpdir, "config.json")
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            # Load configs
            configs = SpecConfig.load_from_file(config_file)

            assert len(configs) == 2
            assert configs[0].path == "/api"
            assert configs[0].spec_data["openapi"] == "3.0.0"  # type: ignore[index]
            assert configs[1].path == "/mcp"
            assert configs[1].spec_data["mcpServers"] is not None  # type: ignore[index]

    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent config file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            SpecConfig.load_from_file("/nonexistent/config.json")

        assert "config.json" in str(exc_info.value).lower()

    def test_load_invalid_config_format(self):
        """Test loading config file that's not a JSON array."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "config.json")
            with open(config_file, "w") as f:
                json.dump({"not": "an array"}, f)

            with pytest.raises(ValueError) as exc_info:
                SpecConfig.load_from_file(config_file)

            assert "array" in str(exc_info.value).lower()

    def test_load_config_with_invalid_entry(self):
        """Test loading config with validation error in one entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid spec file
            spec = {"test": "data"}
            with open(os.path.join(tmpdir, "test.json"), "w") as f:
                json.dump(spec, f)

            # Create config with invalid entry (missing base_url for openapi)
            config_data = [
                {
                    "path": "/invalid",
                    "spec_file": "test.json",
                    "spec_type": "openapi"
                    # Missing base_url - should fail
                }
            ]
            config_file = os.path.join(tmpdir, "config.json")
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            # Should raise validation error
            with pytest.raises(ValidationError):
                SpecConfig.load_from_file(config_file)

    def test_load_config_skips_non_dict_entries(self):
        """Test that non-dict entries in config array are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create valid MCP spec file
            spec = {
                "mcpServers": {
                    "valid": {
                        "transport": "stdio",
                        "command": "node",
                        "args": ["server.js"]
                    }
                }
            }
            with open(os.path.join(tmpdir, "test.json"), "w") as f:
                json.dump(spec, f)

            # Create config with mixed entries
            config_data = [
                "not a dict",
                123,
                {
                    "path": "/valid",
                    "spec_file": "test.json",
                    "spec_type": "mcp"
                }
            ]
            config_file = os.path.join(tmpdir, "config.json")
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            # Should load only the valid entry
            configs = SpecConfig.load_from_file(config_file)
            assert len(configs) == 1
            assert configs[0].path == "/valid"


class TestSpecConfigFieldNames:
    """Test Pydantic field names work correctly."""

    def test_snake_case_field_names(self):
        """Test that snake_case field names are used."""
        config = SpecConfig.model_validate({
            "path": "/test",
            "spec_file": "test.json",
            "spec_type": "mcp",
            "base_url": "http://localhost"
        })

        assert config.spec_file == "test.json"
        assert config.spec_type == "mcp"
        assert config.base_url == "http://localhost"
        assert config.path == "/test"

    def test_all_snake_case_fields(self):
        """Test that all fields use snake_case."""
        config = SpecConfig.model_validate({
            "path": "/test",
            "spec_file": "test.json",
            "spec_type": "mcp",
            "tags": ["test"],
            "auth": {
                "azure": {
                    "client_id": "test-id",
                    "client_secret": "test-secret",
                    "tenant_id": "test-tenant",
                    "token_url": "http://localhost/token",
                    "scopes": ["test-scope"]
                }
            }
        })

        assert config.spec_file == "test.json"
        assert config.spec_type == "mcp"
        assert config.path == "/test"
        assert config.auth is not None
        assert config.auth.azure is not None
        assert config.auth.azure.client_id == "test-id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
