# Testing Guide

## Overview

drunk-mcp-proxy uses pytest for testing. The test suite covers unit tests, integration tests, and end-to-end scenarios.

## Running Tests

### Basic Test Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_server.py

# Run specific test
pytest tests/test_server.py::test_server_creation

# Run tests matching pattern
pytest -k "test_auth"
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=src

# HTML coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Terminal coverage report
pytest --cov=src --cov-report=term-missing
```

### Test Categories

```bash
# Run only unit tests (fast)
pytest tests/test_*.py -m "not integration"

# Run only integration tests
pytest tests/test_*_integration.py
```

## Test Structure

### Test Organization

```
tests/
├── test_server.py              # Server initialization tests
├── test_mcp_proxy_provider.py  # MCP proxy tests
├── test_openapi_mcp_provider.py # OpenAPI conversion tests
├── test_auth_provider.py       # Auth provider tests
├── test_azure_oauth.py         # Azure OAuth tests
├── test_spec_config.py         # Configuration tests
├── test_env_resolver.py        # Environment variable tests
├── test_starlette_app.py       # ASGI app tests
└── test_main_integration.py    # Integration tests
```

### Test Naming Convention

- Files: `test_<module>.py`
- Classes: `Test<Component>`
- Methods: `test_<behavior>_<condition>`

Example:
```python
def test_server_creation_with_auth():
    """Test server creates successfully with auth enabled"""
    pass
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from src.app.server import MCPProxyServer


def test_basic_server_creation():
    """Test basic server creation"""
    server = MCPProxyServer()
    assert server is not None
    assert server.host == "0.0.0.0"
    assert server.port == 9123
```

### Using Fixtures

```python
@pytest.fixture
def sample_config():
    """Provide sample configuration"""
    return {
        "path": "/",
        "spec_file": "mcp/test.json",
        "spec_type": "mcp"
    }


def test_with_config(sample_config):
    """Test using fixture"""
    assert sample_config["spec_type"] == "mcp"
```

### Async Tests

```python
import pytest


@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality"""
    result = await some_async_function()
    assert result is not None
```

### Mocking

```python
from unittest.mock import Mock, patch


def test_with_mock():
    """Test with mocked dependency"""
    mock_provider = Mock()
    mock_provider.create_services.return_value = {"service": "data"}
    
    result = some_function(mock_provider)
    assert result is not None
    mock_provider.create_services.assert_called_once()


@patch('src.app.auth_provider.GlobalAuthProvider')
def test_with_patch(mock_auth):
    """Test with patched class"""
    mock_auth.create_provider.return_value = Mock()
    result = some_function_using_auth()
    assert result is not None
```

## Common Test Scenarios

### Testing Configuration Loading

```python
def test_load_config():
    """Test configuration loading"""
    from src.proxies.config_provider import ProxyConfigProvider
    
    provider = ProxyConfigProvider(config_dir="data")
    configs = provider.load_configs()
    
    assert len(configs) > 0
    assert all(config.spec_type in ["mcp", "openapi"] for config in configs)
```

### Testing Environment Variable Resolution

```python
import os


def test_env_var_resolution():
    """Test environment variable substitution"""
    os.environ["TEST_VAR"] = "test_value"
    
    from src.tools.env_resolver import EnvResolver
    
    result = EnvResolver.resolve("Value is $TEST_VAR")
    assert result == "Value is test_value"
    
    # Cleanup
    del os.environ["TEST_VAR"]
```

### Testing Auth Providers

```python
@pytest.mark.asyncio
async def test_jwt_auth():
    """Test JWT authentication"""
    from src.app.auth_provider import GlobalAuthProvider
    
    config = {
        "defaultProvider": "jwt",
        "jwt": {
            "secret": "test-secret",
            "algorithm": "HS256"
        }
    }
    
    auth = GlobalAuthProvider.create_provider(config)
    assert auth is not None
```

### Testing HTTP Endpoints

```python
from starlette.testclient import TestClient


def test_health_endpoint():
    """Test health check endpoint"""
    from src.app.starlette_app import create_app
    
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=term-missing

markers =
    integration: Integration tests (slower)
    unit: Unit tests (fast)
    auth: Authentication tests
```

### conftest.py

Common fixtures and configuration:

```python
import pytest
import os


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment"""
    os.environ["FASTMCP_LOG_LEVEL"] = "DEBUG"
    os.environ["FASTMCP_AUTH_ENABLED"] = "false"
    yield
    # Cleanup after all tests


@pytest.fixture
def sample_mcp_config():
    """Sample MCP configuration"""
    return {
        "path": "/",
        "spec_file": "mcp/test.json",
        "spec_type": "mcp",
        "base_url": None
    }


@pytest.fixture
def sample_openapi_config():
    """Sample OpenAPI configuration"""
    return {
        "path": "/api",
        "spec_file": "openapi/test.yaml",
        "spec_type": "openapi",
        "base_url": "https://api.example.com"
    }
```

## Best Practices

### Do's

✅ **Write descriptive test names**
```python
def test_auth_provider_validates_jwt_token_successfully():
    pass
```

✅ **Use fixtures for common setup**
```python
@pytest.fixture
def auth_config():
    return {"provider": "jwt", "secret": "test"}
```

✅ **Test edge cases**
```python
def test_handles_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.json")
```

✅ **Mock external dependencies**
```python
@patch('httpx.AsyncClient.get')
async def test_api_call(mock_get):
    mock_get.return_value = Mock(status_code=200)
```

✅ **Clean up after tests**
```python
@pytest.fixture
def temp_file():
    file = create_temp_file()
    yield file
    os.remove(file)  # Cleanup
```

### Don'ts

❌ **Don't rely on test execution order**
```python
# Bad: Depends on previous test
def test_b():
    assert shared_state == "from_test_a"  # Fragile!
```

❌ **Don't test implementation details**
```python
# Bad: Testing internal variable names
def test_internal():
    assert obj._internal_var == 5  # Too specific
```

❌ **Don't make tests too complex**
```python
# Bad: Too much logic in test
def test_complex():
    # 50 lines of setup...
    # Multiple assertions...
    # Complex calculations...
```

❌ **Don't leave debug code**
```python
# Bad: Leftover debug statements
def test_something():
    import pdb; pdb.set_trace()  # Remove before commit!
    print("Debug:", value)  # Remove before commit!
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Scheduled daily runs

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Debugging Test Failures

### Local Debugging

```bash
# Run with extra output
pytest -vv --tb=long

# Run with print statements visible
pytest -s

# Drop into debugger on failure
pytest --pdb

# Run last failed tests
pytest --lf
```

### Common Issues

**Issue: Import errors**
```bash
# Solution: Install package in editable mode
pip install -e ".[dev]"
```

**Issue: Async test failures**
```python
# Solution: Add pytest-asyncio marker
@pytest.mark.asyncio
async def test_async():
    pass
```

**Issue: Environment conflicts**
```bash
# Solution: Isolate test environment
pytest --env-override FASTMCP_AUTH_ENABLED=false
```

## Test Coverage Goals

- **Overall**: 80%+ coverage
- **Core modules**: 90%+ coverage
- **Critical paths**: 100% coverage

View current coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

## Related Documentation

- [Development Guide](guide.md)
- [Troubleshooting](troubleshooting.md)
- [Contributing Guidelines](guide.md#contributing-guidelines)
