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
  - Use absolute imports based on the `src` directory structure **without the `src` prefix** (e.g., `from tools.env import ...` NOT `from src.tools.env import ...`).
  - When working in the `src` folder, imports should be relative to `src/` as the root.
  - **Important**: When patching in tests, ensure the patch path matches how the module is imported in the code under test (use the `src`-relative path without `src.` prefix).
  - Group imports: Standard library, Third-party, Local application.
  - Use `from __future__ import annotations` at the top of files.

### Design Principles: DRY & Single Responsibility

- **Don't Repeat Yourself (DRY)**: Avoid code duplication by extracting common logic into reusable helper methods or functions.
  - Group related functionality into private methods (prefixed with `_`).
  - Use these methods from public methods to maintain a single source of truth.
  - Example: Instead of validating the same logic in multiple methods, create a `_validate_input()` method.

- **Single Responsibility Principle (SRP)**: Each method/function should have a single, well-defined responsibility.
  - If a method does multiple unrelated things, split it into smaller, focused methods.
  - Method names should clearly indicate their purpose (e.g., `_extract_path()`, `_validate_token()`, `_log_result()`).
  - This improves testability, maintainability, and reusability.

- **Example Pattern**:
  ```python
  class DataProcessor:
      def process(self, data: str) -> Result:
          """Orchestrate the processing workflow."""
          parsed = self._parse_input(data)
          validated = self._validate_data(parsed)
          return self._compute_result(validated)
      
      def _parse_input(self, data: str) -> dict:
          """Parse input data into structured format."""
          # Focused, reusable logic
      
      def _validate_data(self, data: dict) -> dict:
          """Validate data and raise exceptions if invalid."""
          # Single responsibility: validation
      
      def _compute_result(self, data: dict) -> Result:
          """Compute and return the final result."""
          # Single responsibility: computation
  ```

### Typing
- **Type Hints**: Mandatory for all function signatures (arguments and return types).
- **Avoid broad `Any`**: Prefer concrete library types (e.g., FastAPI/Starlette/websockets classes) and `Protocol` for interface-style typing. Use `Any` only when dynamic data is unavoidable, and keep that scope minimal.
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

### Test Coverage & Updates

- **Updated Tests Required**: Whenever you modify or refactor a class (add methods, change signatures, extract helper methods), you **must** update the corresponding unit tests.
  - Create tests for new methods, especially private helper methods that are extracted for DRY/SRP.
  - Update existing tests if method behavior or signatures change.
  - Ensure test coverage for all branches and edge cases.
  - Example: If you refactor a large method into smaller helper methods (following SRP), create unit tests for each helper method to ensure they work correctly in isolation.

- **Test Organization**: Organize tests into classes that mirror the code structure:
  ```python
  class TestMyClass:
      """Test suite for MyClass."""
      
      class TestInit:
          """Tests for __init__ method."""
          def test_initialization_default(self): ...
      
      class TestPrivateMethod:
          """Tests for _private_method."""
          def test_valid_input(self): ...
          def test_invalid_input(self): ...
      
      class TestPublicMethod:
          """Tests for public_method."""
          def test_basic_workflow(self): ...
          def test_error_handling(self): ...
  ```

- **Test Execution**: Run tests after any code changes:
  ```bash
  python -m pytest tests/test_your_module.py -v
  python -m pytest --cov=src tests/
  ```

## 6. Common Issues & Fixes

- **Import Errors in Tests**: If you encounter `ModuleNotFoundError`, ensure you are running tests with `python -m pytest`.
- **Pydantic Validation Errors in Tests**: This often happens if the code tries to load the real `auth.json` which requires environment variables. **Fix**: Mock `GlobalAuthProvider.get_auth_provider` or `AuthConfig.load_from_file` to return a dummy config or `None`.
