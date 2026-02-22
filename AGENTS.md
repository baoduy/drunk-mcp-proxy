# Drunk MCP Proxy - Development Guidelines

This document provides instructions and guidelines for AI agents and developers working on the Drunk MCP Proxy project.

## 1. Environment & Setup

- **Python Version**: 3.10+
- **Project Type**: Python application using `setuptools` with `src/` layout.
- **Dependency Management**: `pyproject.toml`.
- **Key Libraries**: `fastmcp`, `pydantic`, `fastapi`, `uvicorn`.

### Installation
To install the project in editable mode with development dependencies:
```bash
pip install -e ".[dev]"
```

## 2. Build, Lint & Test Commands

### Running Tests
Use `pytest` to run tests. **Always use `python -m pytest`** to ensure the current directory is added to `sys.path`.

- **Run all tests:**
  ```bash
  python -m pytest
  ```

- **Run a single test file:**
  ```bash
  python -m pytest tests/test_mcp_proxy_provider.py
  ```

- **Run a specific test class:**
  ```bash
  python -m pytest tests/test_mcp_proxy_provider.py::TestMcpProxyProviderCreateProxy
  ```

- **Run a single test method:**
  ```bash
  python -m pytest tests/test_mcp_proxy_provider.py::TestMcpProxyProviderCreateProxy::test_create_proxy_returns_cached_mcp
  ```

- **Run with coverage:**
  ```bash
  python -m pytest --cov=src
  ```

### Linting & Type Checking
- **Linting (flake8):**
  ```bash
  flake8 src tests
  ```

- **Type Checking (pyright):**
  ```bash
  pyright
  ```

## 3. Code Style & Conventions

### Formatting & Syntax
- **Docstrings**: Use Google-style docstrings for all modules, classes, and functions.
  ```python
  def my_function(param1: str) -> bool:
      """Description of the function.

      Args:
          param1: Description of param1.

      Returns:
          True if successful, False otherwise.
      """
  ```
- **Quotes**: Prefer double quotes `"` for strings.
- **Imports**:
  - Use absolute imports based on the `src` directory structure (e.g., `from tools.env import ...`).
  - **Important**: When patching in tests, ensure the patch path matches how the module is imported in the code under test.
  - Group imports: Standard library, Third-party, Local application.
  - Use `from __future__ import annotations` at the top of files.

### Typing
- **Type Hints**: Mandatory for all function signatures (arguments and return types).
- Use `Optional[Type]` or `Type | None` for nullable types.
- Use `Any` sparingly.

### Naming
- **Classes**: `PascalCase` (e.g., `McpProxyProvider`).
- **Functions/Variables**: `snake_case` (e.g., `create_proxy`, `auth_config`).
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `SERVER_NAME`).
- **Private members**: Prefix with `_` (e.g., `_create_skill_proxy`).

### Error Handling
- Use specific exception types (e.g., `ValueError`, `FileNotFoundError`) instead of generic `Exception`.
- Log errors using the project's logging configuration:
  ```python
  from tools.logging_config import setup_logging
  logger = setup_logging(__name__)
  logger.error("Something went wrong: %s", details)
  ```

## 4. Project Structure

```text
src/
  app/              # Core application logic (auth, server, cache)
  auth_providers/   # Authentication provider implementations
  fastmcp/          # FastMCP library extensions/customizations
  middleware/       # HTTP middleware
  proxies/          # MCP proxy implementations (static, openapi)
  tools/            # Utilities (config, env, logging)
tests/              # Unit and integration tests
data/               # Configuration files (auth.json, etc.)
```

## 5. Testing Guidelines

- **Mocking**: Use `unittest.mock` (`Mock`, `patch`, `MagicMock`).
- **Environment Variables**: Use the `monkeypatch` fixture to safely modify environment variables in tests.
- **Fixtures**: Use `pytest` fixtures for setup/teardown.
- **Isolation**: Ensure tests do not depend on the actual filesystem or external services unless explicitly intended (integration tests). Patch file I/O and network calls.
- **Config Loading**: When testing components that load configuration (like `GlobalAuthProvider`), mock the loading mechanism to prevent reading actual config files or requiring real environment variables.

## 6. Common Issues & Fixes

- **Import Errors in Tests**: If you encounter `ModuleNotFoundError`, ensure you are running tests with `python -m pytest`.
- **Pydantic Validation Errors in Tests**: This often happens if the code tries to load the real `auth.json` which requires environment variables. **Fix**: Mock `GlobalAuthProvider.get_auth_provider` or `AuthConfig.load_from_file` to return a dummy config or `None`.
