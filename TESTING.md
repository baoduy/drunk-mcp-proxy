# Testing Documentation

## Overview

This document describes the testing approach for the drunk-mcp-proxy project. The test suite achieves **93% code coverage**, exceeding the 90% target.

## Test Infrastructure

### Dependencies

The following testing dependencies are included in `requirements.txt`:

- **pytest** (>=7.0.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Support for async/await test functions
- **pytest-cov** (>=4.0.0): Code coverage reporting

### Configuration

Test configuration is defined in `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=90
    -v
```

## Test Structure

### Test Directory Organization

```
tests/
├── __init__.py                  # Test package init
├── test_auth.py                 # Authentication module tests
├── test_validation.py           # Validation module tests
├── test_main.py                 # Main module unit tests
└── test_main_integration.py     # Main module integration tests
```

### Test Files

#### `test_auth.py`

Tests for the `src/auth.py` module covering:

- **Configuration Management**: Loading and saving auth config
- **API Key Generation**: Secure key generation and hashing
- **API Key Validation**: Key validation with timing attack prevention
- **CRUD Operations**: Create, revoke API keys
- **Authentication State**: Enable/disable authentication

**Coverage**: 99% (82 statements, 1 missed)

**Key Test Classes**:
- `TestLoadAuthConfig`: Config loading with various scenarios
- `TestSaveAuthConfigAsync`: Async config saving with atomic writes
- `TestGenerateApiKey`: API key generation validation
- `TestHashApiKey`: SHA-256 hashing consistency
- `TestValidateApiKey`: Key validation logic
- `TestCreateApiKey`: API key creation workflow
- `TestRevokeApiKey`: API key revocation
- `TestEnableAuthentication`: Auth enable/disable
- `TestIsAuthEnabled`: Auth status checks

#### `test_validation.py`

Tests for the `src/validation.py` module covering:

- **Schema Loading**: JSON schema file loading
- **Config Validation**: Validation against JSON schemas
- **Error Handling**: Graceful handling of missing schemas
- **Format Checking**: URI format validation
- **Error Reporting**: Detailed validation error messages

**Coverage**: 87% (60 statements, 8 missed)

**Key Test Classes**:
- `TestLoadSchema`: Schema file loading
- `TestValidateConfig`: Generic config validation
- `TestValidateMcpConfig`: MCP server config validation
- `TestValidateProxiesConfig`: Proxy config validation
- `TestValidateAuthConfig`: Auth config validation
- `TestGetSchemaErrors`: Detailed error reporting

#### `test_main.py`

Unit tests for the `src/main.py` module covering:

- **Configuration Loading**: MCP and proxy config loading
- **Error Handling**: Invalid JSON, missing files
- **File Operations**: Async proxy config saving
- **Proxy Mounting**: Proxy server mounting logic
- **Initialization**: Static and dynamic proxy initialization

**Key Test Classes**:
- `TestLoadConfig`: Config file loading
- `TestLoadProxies`: Proxy file loading
- `TestSaveProxyAsync`: Async proxy saving
- `TestMountProxy`: Proxy mounting
- `TestInitializeStaticProxies`: Static proxy initialization
- `TestInitializeDynamicProxies`: Dynamic proxy initialization

#### `test_main_integration.py`

Integration tests for `src/main.py` tool functions:

- **Tool Functions**: Direct testing of MCP tool functions
- **Conflict Detection**: Static/dynamic proxy conflicts
- **Error Scenarios**: Mount failures, missing params
- **Authentication Management**: All auth actions
- **Server Information**: Server info reporting

**Key Test Class**:
- `TestToolFunctions`: Comprehensive tool function tests using mocked FastMCP

**Coverage**: Combined main.py coverage is 93% (173 statements, 12 missed)

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=src --cov-report=term-missing --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/test_auth.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_auth.py::TestValidateApiKey -v
```

### Run Specific Test

```bash
pytest tests/test_auth.py::TestValidateApiKey::test_validate_api_key_valid_key -v
```

### View HTML Coverage Report

After running tests with `--cov-report=html`:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Code Coverage Summary

| Module | Statements | Missed | Coverage |
|--------|-----------|--------|----------|
| `src/auth.py` | 82 | 1 | 99% |
| `src/main.py` | 173 | 12 | 93% |
| `src/validation.py` | 60 | 8 | 87% |
| **TOTAL** | **315** | **21** | **93.33%** |

### Uncovered Lines

#### `src/auth.py`
- Line 125: Rarely executed edge case in config initialization

#### `src/main.py`
- Lines 54-55: System exit for custom config file errors
- Line 112: Client factory inner function
- Lines 323-336: `__main__` block (module entry point)

#### `src/validation.py`
- Lines 13-17: ImportError handling for missing jsonschema (optional dependency)
- Lines 68-70: Generic exception handling in validation

## Testing Best Practices

### 1. Test Independence

Each test is independent and doesn't rely on state from other tests:

```python
@pytest.fixture
def temp_auth_file(tmp_path):
    """Create a temporary auth config file"""
    auth_file = tmp_path / "auth.json"
    return str(auth_file)
```

### 2. Mocking External Dependencies

External dependencies are mocked to isolate unit tests:

```python
with patch('auth.load_auth_config', return_value=config):
    is_valid, client = validate_api_key(api_key)
    assert is_valid is True
```

### 3. Async Testing

Async functions are properly tested with pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_save_auth_config_success(self, temp_auth_file):
    await save_auth_config_async(config)
    assert os.path.exists(temp_auth_file)
```

### 4. Edge Case Coverage

Tests cover both happy paths and error scenarios:

```python
def test_validate_api_key_invalid_key(self):
    """Test validation with invalid API key"""
    is_valid, client = validate_api_key("wrong-key")
    assert is_valid is False
```

### 5. Integration Testing

Integration tests verify component interactions:

```python
@pytest.fixture
def mock_main_module():
    """Fixture that reloads main module with mocked FastMCP"""
    mock_fastmcp = MockFastMCP()
    with patch('fastmcp.FastMCP', return_value=mock_fastmcp):
        import main as reloaded_main
        yield reloaded_main
```

## Continuous Integration

### GitHub Actions

Tests should be run in CI/CD pipelines:

```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=src --cov-report=xml --cov-fail-under=90
```

### Pre-commit Hooks

Consider adding pre-commit hooks to run tests:

```bash
# .git/hooks/pre-commit
#!/bin/sh
pytest tests/ --cov=src --cov-fail-under=90
```

## Adding New Tests

When adding new functionality:

1. **Write tests first** (TDD approach recommended)
2. **Aim for high coverage** (minimum 90%)
3. **Test edge cases** and error conditions
4. **Use descriptive test names** that explain what's being tested
5. **Keep tests focused** - one concept per test
6. **Mock external dependencies** to ensure test isolation

### Example Test Structure

```python
class TestNewFeature:
    """Tests for new feature"""
    
    def test_feature_success(self):
        """Test feature succeeds in normal case"""
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = new_feature(input_data)
        
        # Assert
        assert result == expected_output
    
    def test_feature_error_handling(self):
        """Test feature handles errors gracefully"""
        with pytest.raises(ValueError):
            new_feature(invalid_input)
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure PYTHONPATH is set:

```bash
export PYTHONPATH=/path/to/drunk-mcp-proxy/src:$PYTHONPATH
pytest
```

### Async Test Warnings

If you see warnings about async tests, ensure pytest-asyncio is installed:

```bash
pip install pytest-asyncio
```

### Coverage Not Reaching 90%

1. Check which lines are missing: `pytest --cov=src --cov-report=term-missing`
2. View HTML report for detailed analysis: `pytest --cov=src --cov-report=html`
3. Add tests for uncovered code paths

## Future Improvements

1. **Performance Tests**: Add performance benchmarks for critical paths
2. **Security Tests**: Add specific security vulnerability tests
3. **Integration Tests**: Add end-to-end integration tests with real MCP servers
4. **Mutation Testing**: Use mutation testing to verify test quality
5. **Property-Based Testing**: Use Hypothesis for property-based testing

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [FastMCP documentation](https://github.com/jlowin/fastmcp)
