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

### Python Version & Modern Syntax (Critical)

- **Python Version**: 3.10+ required. Do not write code compatible with Python 3.8 or 3.9.
- **Modern Union Types**: Always use `X | Y` syntax, never `Union[X, Y]` or `Optional[X]`.
  - **✅ GOOD**: `def get(self) -> str | None:`
  - **❌ BAD**: `def get(self) -> Optional[str]:` or `def get(self) -> Union[str, None]:`
- **Modern Generic Types**: Use lowercase built-in generics: `list[str]`, `dict[str, int]`, never `List[str]`, `Dict[str, int]`.
- **Pattern Matching**: Use `match/case` for complex conditional logic (Python 3.10+ feature).
  ```python
  match status:
      case 200:
          return "OK"
      case 404:
          return "Not Found"
      case _:
          return "Unknown"
  ```
- **Parenthesized Context Managers**: Use for multi-line context managers:
  ```python
  with (
      open("file1.txt") as f1,
      open("file2.txt") as f2
  ):
      data = f1.read()
      f2.write(data)
  ```
- **F-strings Only**: Never use `%` formatting or `str.format()`. Always use f-strings:
  - **✅ GOOD**: `f"User {user.name} logged in"`
  - **❌ BAD**: `"User %s logged in" % user.name` or `"User {} logged in".format(user.name)`

### Framework Version Compliance (Critical)

**All code must follow the latest stable conventions of these frameworks:**

- **FastMCP**: Use the current `fastmcp` API patterns. Do not use deprecated methods. Check `fastmcp` documentation for latest patterns for resources, tools, and prompts.
- **Pydantic**: This project uses Pydantic v2. Never use v1 patterns:
  - **✅ GOOD (v2)**: `from pydantic import BaseModel, Field` with `model_config = ConfigDict(...)` 
  - **❌ BAD (v1)**: `from pydantic import BaseModel` with `class Config:` inner class
  - **✅ GOOD**: `Field(default=None, description="...")` for field metadata
  - **❌ BAD**: `Field(default=...)` without description or using deprecated parameters
- **FastAPI**: Follow current FastAPI best practices:
  - Use `APIRouter` for modular routes
  - Use `Depends()` for dependency injection
  - Define proper response models with Pydantic schemas
  - Use `HTTPException` with proper status codes
- **Uvicorn**: Use `uvicorn.run()` with current configuration options. No legacy ASGI server patterns.

### Python PEP 8 Compliance
- **Line Length**: Maximum 100 characters per line (enforced by `flake8`).
- **Indentation**: Use 4 spaces per indentation level. Never use tabs.
- **Whitespace**: Two blank lines between top-level definitions, one blank line between method definitions.
- **Trailing Whitespace**: Remove all trailing whitespace.
- **Blank Lines in Functions**: Use blank lines sparingly within functions to separate logical sections.

### Modern Pydantic v2 Patterns (Critical)

This project uses **Pydantic v2** exclusively. Never use v1 patterns:

- **✅ GOOD (v2)**:
  ```python
  from pydantic import BaseModel, Field, ConfigDict

  class User(BaseModel):
      model_config = ConfigDict(populate_by_name=True)
      
      name: str = Field(..., description="User name")
      email: str = Field(..., description="Email address")
      age: int | None = Field(default=None, description="User age")
  ```

- **❌ BAD (v1)**:
  ```python
  from pydantic import BaseModel
  
  class User(BaseModel):
      name: str
      email: str
      age: Optional[int] = None
      
      class Config:
          populate_by_name = True
  ```

- **Key v2 Differences**:
  - No inner `Config` class – use `model_config = ConfigDict(...)`
  - Use `field_validator` decorator, not `@validator`
  - Use `model_validate` / `model_dump` instead of `parse_obj` / `dict()`
  - `Json` type is `Json` from `pydantic.json`, not `pydantic.Json`
  - `ValidationError` import from `pydantic` directly
  - Use `field_serializer` / `field_validator` instead of `@validator` with `pre=True`

### Modern FastAPI Patterns (Critical)

Follow these FastAPI best practices:

- **✅ GOOD - Modern FastAPI**:
  ```python
  from fastapi import APIRouter, Depends, HTTPException, status
  from pydantic import BaseModel
  
  router = APIRouter(prefix="/api", tags=["items"])
  
  class ItemCreate(BaseModel):
      name: str
      price: float
  
  async def get_current_user() -> User:
      # Dependency function
      return user
  
  @router.post("/items", response_model=Item)
  async def create_item(
      item: ItemCreate,
      user: User = Depends(get_current_user)
  ) -> Item:
      """Create new item."""
      return await item_service.create(item, user)
  ```

- **❌ BAD - Legacy Patterns**:
  ```python
  from fastapi import FastAPI, Depends
  app = FastAPI()  # Should use APIRouter for modularity
  
  # Missing response_model
  @app.post("/items")
  async def create_item(item: dict):  # Should use Pydantic model
      return service.create(item)
  
  # Using old-style dependency without async
  def get_user():  # Should be async when I/O is involved
      return db.get_user()
  ```

- **Key Rules**:
  - Use `APIRouter` for all route definitions, not directly on `FastAPI`
  - Define explicit `response_model` for all endpoints
  - Use Pydantic v2 models for request/response schemas
  - Dependencies should be async when they perform I/O
  - Use proper HTTP status codes (`status.HTTP_201_CREATED`, etc.)
  - Always include docstrings for OpenAPI documentation

### Modern Async/Await Patterns

Use modern async patterns (Python 3.11+):

- **✅ GOOD - TaskGroup (3.11+)**:
  ```python
  import asyncio
  
  async def fetch_all(urls: list[str]) -> list[str]:
      async with asyncio.TaskGroup() as tg:
          tasks = [tg.create_task(fetch(url)) for url in urls]
      return [task.result() for task in tasks]
  ```

- **✅ GOOD - gather with return_exceptions**:
  ```python
  import asyncio
  
  async def fetch_all_safe(urls: list[str]) -> list[str | Exception]:
      results = await asyncio.gather(
          *[fetch(url) for url in urls],
          return_exceptions=True
      )
      return results
  ```

- **❌ BAD - Legacy patterns**:
  ```python
  # Don't use asyncio.wait or manual task management
  tasks = [asyncio.create_task(fetch(url)) for url in urls]
  await asyncio.wait(tasks)  # No TaskGroup
  ```

### Enhanced Python Best Practices

#### Consistency Requirements (Critical)

**Every class in the codebase must follow these standards:**

1. **Logger Pattern** - Always:
   - `from logging import Logger`
   - `self._logger: Logger = setup_logging(__name__)` in `__init__`
   - Use `self._logger.info()`, `self._logger.error()`, etc.
   - Log only exception types: `self._logger.error("Failed: %s", type(e).__name__)`

2. **Type Hints** - Always:
   - Avoid `Any` type - use specific types or `Protocol`
   - Use `dict[str, str]` not `dict[str, Any]`
   - Use union types: `str | int | None`
   - Type all function parameters and return values

3. **Dependency Injection** - Always:
   - Pass dependencies to `__init__`, never use globals
   - Store as private attributes: `self._dependency`
   - Use `Protocol` for interface dependencies
   - Validate critical dependencies on initialization

4. **Naming Conventions** - Always:
   - Private attributes: `self._attribute_name`
   - Public methods: `def method_name(self) -> ReturnType:`
   - Constants: `CONSTANT_NAME`
   - Classes: `ClassName`

5. **Documentation** - Always:
   - Module docstring at top
   - Google-style docstrings for all public classes/methods
   - Type hints serve as inline documentation
   - Document "why", not "what"

### Code Organization
- **One class per file** (with exceptions for small related classes).
- **Class-first modules**: For new development, structure each module around one primary class and keep orchestration logic in class methods.
- **Group related methods** together within a class.
- **Keep files under 500 lines** where possible.
- **Keep public APIs minimal** and expose only what callers need.
- **Favor composition** and small interfaces over deep inheritance chains.
- **Aim for high cohesion** within modules and low coupling between modules.

Use modern async patterns (Python 3.11+):

- **✅ GOOD - TaskGroup (3.11+)**:
  ```python
  import asyncio
  
  async def fetch_all(urls: list[str]) -> list[str]:
      async with asyncio.TaskGroup() as tg:
          tasks = [tg.create_task(fetch(url)) for url in urls]
      return [task.result() for task in tasks]
  ```

- **✅ GOOD - gather with return_exceptions**:
  ```python
  import asyncio
  
  async def fetch_all_safe(urls: list[str]) -> list[str | Exception]:
      results = await asyncio.gather(
          *[fetch(url) for url in urls],
          return_exceptions=True
      )
      return results
  ```

- **❌ BAD - Legacy patterns**:
  ```python
  # Don't use asyncio.wait or manual task management
  tasks = [asyncio.create_task(fetch(url)) for url in urls]
  await asyncio.wait(tasks)  # No TaskGroup
  ```

### Formatting & Syntax
- **Docstrings**: Use Google-style docstrings for all modules, classes, and functions.
  ```python
  def my_function(param1: str, timeout: int = 30) -> bool:
      """Description of the function.

      Args:
          param1: Description of param1.
          timeout: Request timeout in seconds. Defaults to 30.

      Returns:
          True if successful, False otherwise.

      Raises:
          ValueError: If param1 is empty.
          TimeoutError: If request exceeds timeout.
      """
  ```
- **Module Docstrings**: Include at the top of each file (after `from __future__ import annotations`):
  ```python
  """Module description explaining its purpose and main components."""
  ```
- **Quotes**: Prefer double quotes `"` for strings. Use single quotes for docstring delimiters only if the string contains double quotes.
- **Imports**:
  - Use absolute imports based on the `src` directory structure **without the `src` prefix** (e.g., `from tools.env import ...` NOT `from src.tools.env import ...`).
  - When working in the `src` folder, imports should be relative to `src/` as the root.
  - **Important**: When patching in tests, ensure the patch path matches how the module is imported in the code under test (use the `src`-relative path without `src.` prefix).
  - Group imports in order: Standard library, Third-party, Local application. Separate each group with a blank line.
  - Use `from __future__ import annotations` at the top of files (after module docstring).
  - Avoid wildcard imports (`from module import *`). Always import explicitly.
  - Use alphabetical order within each import group for consistency.

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `McpProxyProvider`, `AuthConfig`).
- **Functions/Variables**: `snake_case` (e.g., `create_proxy`, `auth_config`).
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `SERVER_NAME`, `MAX_RETRY_ATTEMPTS`).
- **Private members**: Prefix with `_` (e.g., `_create_skill_proxy`, `_internal_cache`).
- **Protected members**: Use `_` prefix for convention (e.g., `_protected_method`).
- **Special methods**: Use double underscores only for magic methods (e.g., `__init__`, `__str__`).
- **Meaningful names**: Avoid single-letter variables except in loops (`for i in range(10)`). Prefer `user_config`, `max_attempts`, etc.

### Typing & Type Hints
- **Type Hints**: Mandatory for all function signatures (arguments and return types).
- **Module-level Types**: Import at the top:
  ```python
  from typing import Protocol
  from collections.abc import Callable, Sequence, Mapping
  ```

#### Avoiding `Any` Type (Critical)

**Rule**: Avoid `typing.Any` as much as possible. Always prefer specific types. `Any` allows legacy patterns and prevents type safety.

- **❌ BAD - Using `Any`**:
  ```python
  from typing import Any
  
  def process_data(data: Any) -> Any:
      return data["result"]
  
  def handle_response(response: Any) -> dict[str, Any]:
      return {"status": response.status}
  ```

- **✅ GOOD - Using Specific Types**:
  ```python
  from typing import Protocol
  from starlette.responses import Response
  
  class DataDict(Protocol):
      """Protocol for data dictionary."""
      def __getitem__(self, key: str) -> str | int | bool: ...
  
  def process_data(data: dict[str, str | int]) -> str | int:
      """Process data with known structure."""
      return data["result"]
  
  def handle_response(response: Response) -> dict[str, int]:
      """Handle Starlette response object."""
      return {"status": response.status_code}
  ```

- **When You Must Use `Any`**: Only in these rare cases, and always add a comment explaining why:
  1. **External JSON/YAML data** where structure is truly unknown:
     ```python
     import json
     
     def load_external_json(path: str) -> dict[str, object]:
         """Load external JSON with unknown structure.
         
         Note: Use object instead of Any when possible.
         """
         with open(path) as f:
             return json.load(f)  # Returns dict[str, Any] from json
     ```
  2. **Generic wrapper functions** that truly work with any type:
     ```python
     from typing import TypeVar
     
     T = TypeVar("T")
     
     def identity(value: T) -> T:
         """Return value unchanged (better than Any)."""
         return value
     ```

- **Better Alternatives to `Any`**:
  - Use `object` for unknown types that need minimal operations
  - Use `TypeVar` for generic functions
  - Use `Protocol` to define expected interface
  - Use union types: `str | int | bool | None`
  - Use concrete library types: `Request`, `Response`, `FastAPI`, etc.

- **Union Types**: Use `Type1 | Type2` syntax (Python 3.10+) instead of `Union[Type1, Type2]`.
- **Optional Types**: Use `Type | None` instead of `Optional[Type]`.
- **Generic Types**: Use `list[str]` instead of `List[str]` (Python 3.9+).
- **Protocols**: Define interfaces using `Protocol` for better type checking without inheritance:
  ```python
  from typing import Protocol

  class ConfigProvider(Protocol):
      """Protocol for config providers."""
      
      def get_config(self, key: str) -> dict[str, str | int]: ...
      def set_config(self, key: str, value: dict[str, str | int]) -> None: ...
  ```
- **Type Aliases**: Create meaningful aliases for complex types:
  ```python
  AuthToken = str
  ConfigDict = dict[str, str | int | bool]  # Specific, not Any
  Callback = Callable[[str], None]
  HeadersDict = dict[str, str]
  ```

- **✅ GOOD - Using Specific Types**:
  ```python
  from typing import Protocol
  from starlette.responses import Response
  
  class DataDict(Protocol):
      """Protocol for data dictionary."""
      def __getitem__(self, key: str) -> str | int | bool: ...
  
  def process_data(data: dict[str, str | int]) -> str | int:
      """Process data with known structure."""
      return data["result"]
  
  def handle_response(response: Response) -> dict[str, int]:
      """Handle Starlette response object."""
      return {"status": response.status_code}
  ```

- **When You Must Use `Any`**: Only in these rare cases:
  1. **External JSON/YAML data** where structure is truly unknown:
     ```python
     import json
     
     def load_external_json(path: str) -> dict[str, object]:
         """Load external JSON with unknown structure.
         
         Note: Use object instead of Any when possible.
         """
         with open(path) as f:
             return json.load(f)  # Returns dict[str, Any] from json
     ```
  2. **Generic wrapper functions** that truly work with any type:
     ```python
     from typing import TypeVar
     
     T = TypeVar("T")
     
     def identity(value: T) -> T:
         """Return value unchanged (better than Any)."""
         return value
     ```

- **Better Alternatives to `Any`**:
  - Use `object` for unknown types that need minimal operations
  - Use `TypeVar` for generic functions
  - Use `Protocol` to define expected interface
  - Use union types: `str | int | bool | None`
  - Use concrete library types: `Request`, `Response`, `FastAPI`, etc.

- **Union Types**: Use `Type1 | Type2` syntax (Python 3.10+) instead of `Union[Type1, Type2]`.
- **Optional Types**: Use `Type | None` instead of `Optional[Type]`.
- **Generic Types**: Use `list[str]` instead of `List[str]` (Python 3.9+).
- **Protocols**: Define interfaces using `Protocol` for better type checking without inheritance:
  ```python
  from typing import Protocol

  class ConfigProvider(Protocol):
      """Protocol for config providers."""
      
      def get_config(self, key: str) -> dict[str, str | int]: ...
      def set_config(self, key: str, value: dict[str, str | int]) -> None: ...
  ```
- **Type Aliases**: Create meaningful aliases for complex types:
  ```python
  AuthToken = str
  ConfigDict = dict[str, str | int | bool]  # Specific, not Any
  Callback = Callable[[str], None]
  HeadersDict = dict[str, str]
  ```

### Error Handling
- Use specific exception types (e.g., `ValueError`, `FileNotFoundError`, `TimeoutError`) instead of generic `Exception`.
- Create custom exceptions that inherit from appropriate base classes:
  ```python
  class ConfigError(ValueError):
      """Raised when configuration is invalid."""
      pass

  class AuthenticationError(Exception):
      """Raised when authentication fails."""
      pass
  ```
- Always provide meaningful error messages:
  ```python
  if not username:
      raise ValueError("username cannot be empty")
  ```
- Log errors using the project's logging configuration:
  ```python
  from tools.logging_config import setup_logging
  logger = setup_logging(__name__)
  logger.error("Operation failed: %s", type(e).__name__)
  ```
- Use context managers for resource cleanup:
  ```python
  with open(filename) as f:
      content = f.read()
  # File is automatically closed
  ```

### Context Managers & Resource Management
- Implement `__enter__` and `__exit__` for classes managing resources:
  ```python
  class DatabaseConnection:
      def __enter__(self):
          self.connection = self._connect()
          return self.connection
      
      def __exit__(self, exc_type, exc_val, exc_tb):
          if self.connection:
              self.connection.close()
          return False  # Don't suppress exceptions
  ```
- Use `contextlib` for simple cases:
  ```python
  from contextlib import contextmanager

  @contextmanager
  def managed_resource():
      resource = acquire()
      try:
          yield resource
      finally:
          release(resource)
  ```

### Async/Await Patterns
- **Async Functions**: Prefix async functions with `async def`:
  ```python
  async def fetch_data(url: str) -> dict:
      """Fetch data asynchronously."""
      async with aiohttp.ClientSession() as session:
          async with session.get(url) as response:
              return await response.json()
  ```
- **Awaiting Calls**: Always `await` async functions. Never call async functions without `await`.
- **Exception Handling in Async**: Wrap async operations in try-except:
  ```python
  try:
      result = await async_operation()
  except asyncio.TimeoutError:
      logger.error("Operation timed out")
  ```
- **Concurrent Operations**: Use `asyncio.gather()` or `asyncio.TaskGroup` for concurrent tasks:
  ```python
  # Python 3.11+
  async with asyncio.TaskGroup() as tg:
      task1 = tg.create_task(async_func1())
      task2 = tg.create_task(async_func2())
  ```

---

## 3.1. Consistent Component Patterns

### Logger Pattern (Standard Convention)

**All classes must follow this exact pattern for logging:**

```python
"""Module docstring."""

from __future__ import annotations

from logging import Logger
from tools.logging_config import setup_logging


class MyClass:
    """Class description."""
    
    def __init__(self, config: dict[str, str]):
        """Initialize MyClass.
        
        Args:
            config: Configuration dictionary.
        """
        self._logger: Logger = setup_logging(__name__)
        self._config = config
    
    def process(self) -> None:
        """Process something."""
        self._logger.info("Starting process")
        try:
            result = self._do_work()
            self._logger.debug("Process completed: %s", result)
        except Exception as e:
            # Log only exception type, not message (security)
            self._logger.error("Process failed: %s", type(e).__name__)
            raise
```

**Key Rules for Loggers:**

1. **Import**: Always `from logging import Logger` and `from tools.logging_config import setup_logging`
2. **Initialization**: Create in `__init__` as `self._logger: Logger = setup_logging(__name__)`
3. **Naming**: Always use `_logger` (private attribute) with type hint `Logger`
4. **Usage**: Reference as `self._logger.info()`, `self._logger.error()`, etc.
5. **Error Logging**: Log only exception type: `self._logger.error("Context: %s", type(e).__name__)`
6. **Never**: Do not log full exception messages (may contain secrets/paths)
7. **Never**: Do not pass logger as parameter; each class creates its own

**❌ BAD - Inconsistent Logger Usage**:
```python
class BadClass:
    def __init__(self):
        # Wrong: different naming, no type hint
        self.log = setup_logging(__name__)
        
    def process(self):
        # Wrong: logs full exception message
        try:
            risky_operation()
        except Exception as e:
            self.log.error(f"Failed: {str(e)}")  # May leak secrets!
```

**❌ BAD - Passing Logger as Parameter**:
```python
# Don't do this
class BadClass:
    def __init__(self, logger: Logger):  # Wrong pattern
        self._logger = logger

# Usage is inconsistent
logger = setup_logging("main")
obj = BadClass(logger)
```

**✅ GOOD - Consistent Logger Pattern**:
```python
class GoodClass:
    """Properly implemented class with standard logger."""
    
    def __init__(self, timeout: int = 30):
        """Initialize GoodClass.
        
        Args:
            timeout: Operation timeout in seconds.
        """
        self._logger: Logger = setup_logging(__name__)
        self._timeout = timeout
        self._logger.debug("Initialized with timeout=%d", timeout)
    
    def process(self, data: dict[str, str]) -> bool:
        """Process data.
        
        Args:
            data: Input data dictionary.
            
        Returns:
            True if successful.
            
        Raises:
            ValueError: If data is invalid.
        """
        self._logger.info("Processing data")
        try:
            self._validate(data)
            result = self._execute(data)
            self._logger.debug("Processing completed successfully")
            return result
        except ValueError as e:
            # Log only type, not message
            self._logger.error("Validation failed: %s", type(e).__name__)
            raise
        except Exception as e:
            # Generic error logging
            self._logger.error("Processing error: %s", type(e).__name__)
            raise
```

### Logging Sensitive Data Safely

**When you need to log sensitive information** (for debugging, audit trails, or identifying which credential is being used), **never log the full value**. Use truncation to show only the last 4 characters.

**What counts as sensitive data:**
- API keys and authentication tokens
- OAuth tokens and refresh tokens
- Session IDs and cookies
- Connection strings with credentials
- Private keys and certificates
- User passwords (never log, even truncated)
- Personal data (emails, phone numbers, addresses)

**❌ BAD - Logging Full Sensitive Values**:
```python
class BadService:
    """Service with unsafe logging."""
    
    def __init__(self, api_key: str, auth_token: str):
        self._logger: Logger = setup_logging(__name__)
        self._api_key = api_key
        
        # DANGER: Exposes full API key in logs!
        self._logger.info(f"Initialized with API key: {api_key}")
        
        # DANGER: Full token visible in logs!
        self._logger.debug("Auth token: %s", auth_token)
    
    def authenticate(self, password: str) -> bool:
        """Authenticate user."""
        # DANGER: Password in logs!
        self._logger.info(f"Authenticating with password: {password}")
        return True
```

**✅ GOOD - Safe Logging with Truncation**:
```python
class GoodService:
    """Service with safe logging practices."""
    
    def __init__(self, api_key: str, auth_token: str):
        """Initialize service.
        
        Args:
            api_key: API authentication key.
            auth_token: Bearer authentication token.
        """
        self._logger: Logger = setup_logging(__name__)
        self._api_key = api_key
        self._auth_token = auth_token
        
        # Safe: Shows last 4 chars only
        self._logger.info("Initialized with api_key=...%s", api_key[-4:])
        self._logger.debug("Using auth_token=...%s", auth_token[-4:])
    
    def authenticate(self, password: str) -> bool:
        """Authenticate user."""
        # Safe: Never log passwords, even truncated
        self._logger.info("Authentication attempt")
        return True
    
    def _mask_sensitive(self, value: str | None, show_chars: int = 4) -> str:
        """Mask sensitive value showing only last N characters.
        
        Args:
            value: Sensitive string to mask.
            show_chars: Number of characters to show at end.
            
        Returns:
            Masked string like '...XXXX' or '[None]' if value is None.
        """
        if value is None:
            return "[None]"
        if len(value) <= show_chars:
            return "..." + "*" * len(value)  # Don't expose short values
        return "..." + value[-show_chars:]
    
    def process_request(self, session_id: str | None) -> dict[str, str]:
        """Process request with session.
        
        Args:
            session_id: User session identifier.
            
        Returns:
            Response dictionary.
        """
        # Safe: Uses helper to handle None and truncation
        masked = self._mask_sensitive(session_id)
        self._logger.info("Processing request with session_id=%s", masked)
        return {"status": "ok"}
```

**Key Rules for Logging Sensitive Data:**

1. **Default to last 4 characters**: Use `value[-4:]` for tokens, API keys, session IDs
2. **Use `...` prefix**: Format as `...XXXX` to clearly indicate truncation
3. **Never log passwords**: Even truncated. Log "Authentication attempt" instead
4. **Add descriptive context**: Use `"api_key=...1234"` not just `"...1234"`
5. **Handle None gracefully**: Check for None before slicing: `value[-4:] if value else '[None]'`
6. **Use helper methods**: Create `_mask_sensitive()` for consistent formatting
7. **Consider data length**: For very short values (< 4 chars), mask entirely: `"...****"`
8. **Be consistent**: Use the same pattern across all classes and modules

**When to use truncation vs. complete omission:**
- **Use truncation**: When you need to identify which credential ("using key ...1234 vs ...5678")
- **Complete omission**: For passwords, PINs, or when the identifier isn't needed for debugging
- **Never log**: Social security numbers, credit card numbers, health records

### Configuration Injection Pattern (Standard Convention)

**All classes should receive dependencies via constructor injection:**

```python
from typing import Protocol


class ConfigProvider(Protocol):
    """Protocol for configuration providers."""
    def get(self, key: str) -> str | None: ...


class ServiceClass:
    """Service with injected dependencies."""
    
    def __init__(
        self,
        config: ConfigProvider,
        api_key: str,
        timeout: int = 30
    ):
        """Initialize service.
        
        Args:
            config: Configuration provider instance.
            api_key: API authentication key.
            timeout: Request timeout in seconds.
        """
        self._logger: Logger = setup_logging(__name__)
        self._config = config
        self._api_key = api_key
        self._timeout = timeout
        # Safe: Log last 4 chars of API key for debugging
        self._logger.debug("Service initialized with api_key=...%s", api_key[-4:])
    
    def execute(self) -> dict[str, str]:
        """Execute service operation."""
        endpoint = self._config.get("endpoint")
        if not endpoint:
            raise ValueError("Endpoint not configured")
        return self._make_request(endpoint)
```

**Key Rules for Dependency Injection:**

1. **Constructor Parameters**: All dependencies passed to `__init__`
2. **Private Attributes**: Store as `self._attribute_name`
3. **Type Hints**: Always specify parameter and attribute types
4. **Validation**: Validate critical dependencies in `__init__` or first use
5. **No Globals**: Never access global state directly; inject it
6. **Protocol Types**: Prefer `Protocol` types for dependencies over concrete classes

### Singleton Pattern (Standard Convention)

**For classes that should have only one instance (like config providers):**

```python
class ConfigManager:
    """Singleton configuration manager.
    
    Ensures only one instance exists throughout the application lifecycle.
    """
    
    _instance: "ConfigManager | None" = None
    _initialized: bool = False
    
    def __new__(cls) -> "ConfigManager":
        """Create or return existing singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration (only once).
        
        Args:
            config_path: Path to configuration file.
        """
        # Prevent re-initialization
        if ConfigManager._initialized:
            return
        
        self._logger: Logger = setup_logging(__name__)
        self._config_path = config_path
        self._config: dict[str, str | int] = self._load_config()
        ConfigManager._initialized = True
        self._logger.info("ConfigManager initialized")
    
    def _load_config(self) -> dict[str, str | int]:
        """Load configuration from file."""
        # Implementation
        return {}

# Usage - always returns same instance
config1 = ConfigManager()
config2 = ConfigManager()
assert config1 is config2  # True
```

### Factory Pattern (Standard Convention)

**For creating objects based on configuration or type:**

```python
from abc import ABC, abstractmethod
from typing import Protocol


class Handler(ABC):
    """Abstract base for handlers."""
    
    @abstractmethod
    def handle(self, request: dict[str, str]) -> dict[str, str]:
        """Handle request."""
        pass


class HttpHandler(Handler):
    """HTTP-specific handler."""
    
    def __init__(self, timeout: int):
        self._logger: Logger = setup_logging(__name__)
        self._timeout = timeout
    
    def handle(self, request: dict[str, str]) -> dict[str, str]:
        """Handle HTTP request."""
        self._logger.debug("Handling HTTP request")
        return {"status": "ok"}


class GrpcHandler(Handler):
    """gRPC-specific handler."""
    
    def __init__(self, timeout: int):
        self._logger: Logger = setup_logging(__name__)
        self._timeout = timeout
    
    def handle(self, request: dict[str, str]) -> dict[str, str]:
        """Handle gRPC request."""
        self._logger.debug("Handling gRPC request")
        return {"status": "ok"}


class HandlerFactory:
    """Factory for creating protocol handlers."""
    
    # Type mapping for available handlers
    _handlers: dict[str, type[Handler]] = {
        "http": HttpHandler,
        "grpc": GrpcHandler,
    }
    
    def __init__(self):
        """Initialize factory."""
        self._logger: Logger = setup_logging(__name__)
    
    @classmethod
    def create(cls, protocol: str, timeout: int = 30) -> Handler:
        """Create handler for specified protocol.
        
        Args:
            protocol: Protocol type (http, grpc).
            timeout: Handler timeout in seconds.
            
        Returns:
            Handler instance for the protocol.
            
        Raises:
            ValueError: If protocol is not supported.
        """
        handler_class = cls._handlers.get(protocol)
        if not handler_class:
            raise ValueError(f"Unsupported protocol: {protocol}")
        return handler_class(timeout=timeout)
    
    @classmethod
    def register(cls, protocol: str, handler_class: type[Handler]) -> None:
        """Register new handler type.
        
        Args:
            protocol: Protocol name.
            handler_class: Handler class to register.
        """
        cls._handlers[protocol] = handler_class


# Usage
handler = HandlerFactory.create("http", timeout=60)
result = handler.handle({"url": "https://example.com"})
```



---

## 4. Design Principles: SOLID & DRY

### OOP & Modularity Principles

- **Guideline**: Prefer composition over inheritance unless the relationship is a strict is-a, and keep modules cohesive with small, intentional public interfaces.
- **Project Rule (Strict)**: New modules must be implemented with class-based design first. Avoid module-level procedural functions for core logic unless they are tiny pure utility helpers.
- **Bad Example**:
  ```python
  class ReportService:
      def __init__(self):
          self.db = Database()
          self.mailer = Mailer()

      def create_and_send(self, user_id: int) -> None:
          report = self.db.fetch_report(user_id)
          self.mailer.send(report)
          self._cleanup_temp_files()

      def _cleanup_temp_files(self) -> None:
          pass
  ```
- **Good Example**:
  ```python
  class ReportRepository(Protocol):
      def fetch_report(self, user_id: int) -> str: ...


  class Mailer(Protocol):
      def send(self, report: str) -> None: ...


  class ReportService:
      def __init__(self, repository: ReportRepository, mailer: Mailer) -> None:
          self._repository = repository
          self._mailer = mailer

      def send_report(self, user_id: int) -> None:
          report = self._repository.fetch_report(user_id)
          self._mailer.send(report)
  ```

### SOLID Principles

#### 1. Single Responsibility Principle (SRP)
Each class, function, or module should have **one reason to change**, focusing on a single responsibility.

- **Guideline**: A function should do one thing well.
- **Bad Example**:
  ```python
  class UserManager:
      def create_user(self, name: str, email: str) -> None:
          # Validate input
          if not name or not email:
              raise ValueError("Invalid input")
          # Connect to database
          self.db.execute("INSERT INTO users...")
          # Send email notification
          self.mail.send(email, "Welcome!")
          # Log activity
          logger.info(f"User {name} created")
  ```
- **Good Example**:
  ```python
  class UserManager:
      def __init__(self, db: Database, notifier: Notifier, logger: Logger):
          self.db = db
          self.notifier = notifier
          self.logger = logger
      
      def create_user(self, name: str, email: str) -> User:
          """Create a user (orchestration only)."""
          self._validate_input(name, email)
          user = self._save_to_database(name, email)
          self.notifier.notify_user_created(user)
          self._log_creation(user)
          return user
      
      def _validate_input(self, name: str, email: str) -> None:
          """Validate user input."""
          if not name or not email:
              raise ValueError("Invalid input")
      
      def _save_to_database(self, name: str, email: str) -> User:
          """Save user to database."""
          return self.db.create(User(name=name, email=email))
      
      def _log_creation(self, user: User) -> None:
          """Log user creation."""
          self.logger.info(f"User {user.name} created")
  ```

#### 2. Open/Closed Principle (OCP)
Software entities should be **open for extension, closed for modification**.

- **Guideline**: Use inheritance, composition, and abstraction to extend behavior without modifying existing code.
- **Bad Example**:
  ```python
  class PaymentProcessor:
      def process(self, payment: dict, method: str) -> bool:
          if method == "credit_card":
              return self._process_credit_card(payment)
          elif method == "paypal":
              return self._process_paypal(payment)
          elif method == "stripe":
              return self._process_stripe(payment)
          # Adding new methods requires modifying this class
  ```
- **Good Example**:
  ```python
  from abc import ABC, abstractmethod

  class PaymentHandler(ABC):
      @abstractmethod
      def process(self, payment: dict) -> bool:
          """Process payment."""
          pass

  class CreditCardHandler(PaymentHandler):
      def process(self, payment: dict) -> bool:
          return self._process_credit_card(payment)

  class PayPalHandler(PaymentHandler):
      def process(self, payment: dict) -> bool:
          return self._process_paypal(payment)

  class PaymentProcessor:
      def __init__(self, handlers: dict[str, PaymentHandler]):
          self.handlers = handlers
      
      def process(self, payment: dict, method: str) -> bool:
          """Process payment using appropriate handler."""
          handler = self.handlers.get(method)
          if not handler:
              raise ValueError(f"Unknown payment method: {method}")
          return handler.process(payment)
  ```

#### 3. Liskov Substitution Principle (LSP)
Subclasses should be **substitutable for their parent classes** without breaking the program.

- **Guideline**: Derived classes must not strengthen preconditions or weaken postconditions.
- **Bad Example**:
  ```python
  class Bird:
      def fly(self) -> str:
          return "Flying"

  class Penguin(Bird):
      def fly(self) -> str:
          raise NotImplementedError("Penguins cannot fly")  # Violates LSP
  ```
- **Good Example**:
  ```python
  class Bird(ABC):
      @abstractmethod
      def move(self) -> str:
          pass

  class FlyingBird(Bird):
      def move(self) -> str:
          return "Flying"

  class Penguin(Bird):
      def move(self) -> str:
          return "Swimming"

  # Now all Bird subclasses properly implement move()
  ```

#### 4. Interface Segregation Principle (ISP)
Clients should not depend on interfaces they don't use. **Prefer many specific interfaces over one general-purpose interface**.

- **Guideline**: Keep interfaces small and focused.
- **Bad Example**:
  ```python
  class DataService(ABC):
      @abstractmethod
      def read(self) -> dict: pass
      
      @abstractmethod
      def write(self, data: dict) -> None: pass
      
      @abstractmethod
      def delete(self) -> None: pass
      
      @abstractmethod
      def notify(self) -> None: pass  # Not all services need notification

  class ReadOnlyService(DataService):
      def read(self) -> dict:
          return {}
      
      def write(self, data: dict) -> None:
          raise NotImplementedError()  # Forced to implement
      
      def delete(self) -> None:
          raise NotImplementedError()  # Forced to implement
      
      def notify(self) -> None:
          raise NotImplementedError()  # Forced to implement
  ```
- **Good Example**:
  ```python
  class Readable(ABC):
      @abstractmethod
      def read(self) -> dict: pass

  class Writable(ABC):
      @abstractmethod
      def write(self, data: dict) -> None: pass

  class Deletable(ABC):
      @abstractmethod
      def delete(self) -> None: pass

  class Notifiable(ABC):
      @abstractmethod
      def notify(self) -> None: pass

  class ReadOnlyService(Readable):
      def read(self) -> dict:
          return {}  # Only implement what's needed

  class FullService(Readable, Writable, Deletable, Notifiable):
      # Implement all interfaces
      pass
  ```

#### 5. Dependency Inversion Principle (DIP)
**High-level modules should not depend on low-level modules**. Both should depend on abstractions.

- **Guideline**: Use dependency injection and abstract classes to decouple components.
- **Bad Example**:
  ```python
  class UserRepository:
      def __init__(self):
          self.db = MySQLDatabase()  # Direct dependency (tight coupling)
      
      def save(self, user: User) -> None:
          self.db.execute(f"INSERT INTO users VALUES (...)")

  class UserService:
      def __init__(self):
          self.repo = UserRepository()  # Depends on concrete implementation
      
      def create_user(self, name: str) -> User:
          user = User(name=name)
          self.repo.save(user)
          return user
  ```
- **Good Example**:
  ```python
  class Repository(ABC):
      @abstractmethod
      def save(self, entity: Any) -> None: pass

  class UserRepository(Repository):
      def __init__(self, db: Database):
          self.db = db  # Injected dependency
      
      def save(self, user: User) -> None:
          self.db.execute(f"INSERT INTO users VALUES (...)")

  class UserService:
      def __init__(self, repo: Repository):  # Depends on abstraction
          self.repo = repo
      
      def create_user(self, name: str) -> User:
          user = User(name=name)
          self.repo.save(user)
          return user

  # Usage:
  db = MySQLDatabase()
  repo = UserRepository(db)
  service = UserService(repo)  # Easy to swap implementations
  ```

### DRY Principle: Don't Repeat Yourself
Avoid code duplication by extracting common logic into reusable functions or methods.

- **Guideline**: If you write the same code more than once, extract it into a helper method.
- **Bad Example**:
  ```python
  class DataProcessor:
      def process_file_a(self, path: str) -> dict:
          content = self._read_file(path)
          if not content:
              raise ValueError("File is empty")
          parsed = json.loads(content)
          if not parsed:
              raise ValueError("Invalid JSON")
          return parsed
      
      def process_file_b(self, path: str) -> dict:
          content = self._read_file(path)
          if not content:
              raise ValueError("File is empty")
          parsed = json.loads(content)
          if not parsed:
              raise ValueError("Invalid JSON")
          return parsed  # Duplicated logic
  ```
- **Good Example**:
  ```python
  class DataProcessor:
      def process_file_a(self, path: str) -> dict:
          return self._load_json_file(path)
      
      def process_file_b(self, path: str) -> dict:
          return self._load_json_file(path)
      
      def _load_json_file(self, path: str) -> dict:
          """Load and validate JSON file."""
          content = self._read_file(path)
          if not content:
              raise ValueError("File is empty")
          parsed = json.loads(content)
          if not parsed:
              raise ValueError("Invalid JSON")
          return parsed
  ```

---

## 4. Common Design Patterns

### 1. Singleton Pattern
Ensure a class has only one instance and provide a global point of access.

```python
class Logger:
    _instance: "Logger | None" = None
    
    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def log(self, message: str) -> None:
        print(f"[LOG] {message}")

# Usage:
logger1 = Logger()
logger2 = Logger()
assert logger1 is logger2  # Same instance
```

### 2. Factory Pattern
Create objects without specifying their exact classes.

```python
from abc import ABC, abstractmethod

class PaymentHandler(ABC):
    @abstractmethod
    def process(self, amount: float) -> bool: pass

class CreditCardHandler(PaymentHandler):
    def process(self, amount: float) -> bool:
        return True

class PayPalHandler(PaymentHandler):
    def process(self, amount: float) -> bool:
        return True

class PaymentHandlerFactory:
    """Factory for creating payment handlers."""
    
    _handlers: dict[str, type[PaymentHandler]] = {
        "credit_card": CreditCardHandler,
        "paypal": PayPalHandler,
    }
    
    @classmethod
    def create(cls, method: str) -> PaymentHandler:
        """Create a payment handler."""
        handler_class = cls._handlers.get(method)
        if not handler_class:
            raise ValueError(f"Unknown payment method: {method}")
        return handler_class()

# Usage:
handler = PaymentHandlerFactory.create("credit_card")
```

### 3. Adapter Pattern
Convert the interface of a class into another interface clients expect.

```python
class LegacyPaymentSystem:
    def charge(self, card_number: str, amount: float) -> None:
        print(f"Charging ${amount} to {card_number}")

class PaymentHandler(ABC):
    @abstractmethod
    def process(self, amount: float) -> bool: pass

class LegacyPaymentAdapter(PaymentHandler):
    """Adapt LegacyPaymentSystem to PaymentHandler interface."""
    
    def __init__(self, legacy: LegacyPaymentSystem, card: str):
        self.legacy = legacy
        self.card = card
    
    def process(self, amount: float) -> bool:
        try:
            self.legacy.charge(self.card, amount)
            return True
        except Exception:
            return False

# Usage:
legacy = LegacyPaymentSystem()
adapter = LegacyPaymentAdapter(legacy, "1234-5678-9012-3456")
adapter.process(99.99)
```

### 4. Observer Pattern
Define a one-to-many dependency where when one object changes state, all dependents are notified.

```python
from typing import Callable

class EventBus:
    """Simple event bus implementation."""
    
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
    
    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to an event."""
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)
    
    def unsubscribe(self, event: str, callback: Callable) -> None:
        """Unsubscribe from an event."""
        if event in self._subscribers:
            self._subscribers[event].remove(callback)
    
    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to all subscribers."""
        if event in self._subscribers:
            for callback in self._subscribers[event]:
                callback(*args, **kwargs)

# Usage:
bus = EventBus()

def on_user_created(user_id: int) -> None:
    print(f"Sending welcome email to user {user_id}")

bus.subscribe("user_created", on_user_created)
bus.emit("user_created", 123)  # Notifies all subscribers
```

### 5. Decorator Pattern
Attach additional responsibilities to an object dynamically.

```python
from functools import wraps

def log_execution(func: Callable) -> Callable:
    """Decorator to log function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Executing {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Completed {func.__name__}")
        return result
    return wrapper

def measure_time(func: Callable) -> Callable:
    """Decorator to measure execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper

@log_execution
@measure_time
def slow_operation() -> None:
    import time
    time.sleep(1)

slow_operation()
```

### 6. Dependency Injection Pattern
Inject dependencies into a class rather than creating them internally.

```python
class Database:
    def query(self, sql: str) -> list:
        return []

class UserRepository:
    def __init__(self, db: Database):  # Injected
        self.db = db
    
    def find_by_id(self, user_id: int) -> dict | None:
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Usage:
db = Database()
repo = UserRepository(db)
user = repo.find_by_id(1)
```

---

## 5. Enhanced Python Best Practices

### Consistency Requirements (Critical)

**Every class in the codebase must follow these standards:**

1. **Logger Pattern** - Always:
   - `from logging import Logger`
   - `self._logger: Logger = setup_logging(__name__)` in `__init__`
   - Use `self._logger.info()`, `self._logger.error()`, etc.
   - Log only exception types: `self._logger.error("Failed: %s", type(e).__name__)`

2. **Type Hints** - Always:
   - Avoid `Any` type - use specific types or `Protocol`
   - Use `dict[str, str]` not `dict[str, Any]`
   - Use union types: `str | int | None`
   - Type all function parameters and return values

3. **Dependency Injection** - Always:
   - Pass dependencies to `__init__`, never use globals
   - Store as private attributes: `self._dependency`
   - Use `Protocol` for interface dependencies
   - Validate critical dependencies on initialization

4. **Naming Conventions** - Always:
   - Private attributes: `self._attribute_name`
   - Public methods: `def method_name(self) -> ReturnType:`
   - Constants: `CONSTANT_NAME`
   - Classes: `ClassName`

5. **Documentation** - Always:
   - Module docstring at top
   - Google-style docstrings for all public classes/methods
   - Type hints serve as inline documentation
   - Document "why", not "what"

### Code Organization
- **One class per file** (with exceptions for small related classes).
- **Class-first modules**: For new development, structure each module around one primary class and keep orchestration logic in class methods.
- **Group related methods** together within a class.
- **Keep files under 500 lines** where possible.
- **Keep public APIs minimal** and expose only what callers need.
- **Favor composition** and small interfaces over deep inheritance chains.
- **Aim for high cohesion** within modules and low coupling between modules.

### Performance
- Use **list comprehensions** for simple transformations:
  ```python
  # Good
  squared = [x ** 2 for x in numbers]
  
  # Less efficient
  squared = []
  for x in numbers:
      squared.append(x ** 2)
  ```
- Use **generators** for large datasets:
  ```python
  def read_large_file(path: str):
      with open(path) as f:
          for line in f:
              yield line.strip()
  ```

### Testing Best Practices
- Write tests **before or alongside** production code (TDD where appropriate).
- Use **descriptive test names**: `test_process_valid_input`, `test_raises_error_on_empty_string`.
- **Test one thing per test method**.
- Use **fixtures** for shared setup.

### Documentation
- **Write for clarity**: Assume the reader is unfamiliar with the code.
- **Update documentation** when changing behavior.
- **Use type hints** as documentation for function signatures.
- **Comments for "why"**, not "what": Code should be self-documenting.
  ```python
  # Good: explains the "why"
  if user.age < 18:
      # Minors cannot purchase certain products per local law
      raise PermissionError()
  
  # Bad: explains the "what" (already clear from code)
  if user.age < 18:  # Check if user is under 18
      raise PermissionError()
  ```

## 6. Project Structure

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

## 7. Testing Guidelines

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

## 8. Common Issues & Fixes

- **Import Errors in Tests**: If you encounter `ModuleNotFoundError`, ensure you are running tests with `python -m pytest`.
- **Pydantic Validation Errors in Tests**: This often happens if the code tries to load the real `auth.json` which requires environment variables. **Fix**: Mock `GlobalAuthProvider.get_auth_provider` or `AuthConfig.load_from_file` to return a dummy config or `None`.

---

## 9. Quick Reference Checklist

Use this checklist when writing or reviewing code:

### ✅ Every New Class Should Have:

```python
"""Module docstring explaining purpose."""

from __future__ import annotations

from logging import Logger
from tools.logging_config import setup_logging


class MyNewClass:
    """Class docstring with description."""
    
    def __init__(self, config: dict[str, str], api_token: str, timeout: int = 30):
        """Initialize MyNewClass.
        
        Args:
            config: Configuration dictionary.
            api_token: API authentication token.
            timeout: Operation timeout in seconds.
        """
        # 1. Logger (always first)
        self._logger: Logger = setup_logging(__name__)
        
        # 2. Store dependencies as private attributes with type hints
        self._config = config
        self._api_token = api_token
        self._timeout = timeout
        
        # 3. Log initialization (debug level)
        # Safe: Show last 4 chars of sensitive token
        self._logger.debug(
            "Initialized with timeout=%d, api_token=...%s",
            timeout,
            api_token[-4:]
        )
    
    def public_method(self, data: dict[str, str]) -> str:
        """Public method with clear purpose.
        
        Args:
            data: Input data dictionary.
            
        Returns:
            Processing result.
            
        Raises:
            ValueError: If data is invalid.
        """
        self._logger.info("Processing started")
        try:
            validated = self._validate_input(data)
            result = self._process_data(validated)
            self._logger.debug("Processing completed")
            return result
        except ValueError as e:
            # Log only exception type
            self._logger.error("Validation failed: %s", type(e).__name__)
            raise
    
    def _validate_input(self, data: dict[str, str]) -> dict[str, str]:
        """Private helper with single responsibility.
        
        Args:
            data: Data to validate.
            
        Returns:
            Validated data.
            
        Raises:
            ValueError: If validation fails.
        """
        if not data:
            raise ValueError("Data cannot be empty")
        return data
    
    def _process_data(self, data: dict[str, str]) -> str:
        """Private helper for data processing."""
        return data.get("key", "default")
```

### ✅ Type Hints Checklist:

- [ ] All function parameters have type hints
- [ ] All function return types specified
- [ ] No `Any` types (use specific types or `Protocol`)
- [ ] Use `dict[str, str]` not `dict` or `Dict`
- [ ] Use `list[str]` not `list` or `List`
- [ ] Use `str | None` not `Optional[str]`
- [ ] Use `str | int | bool` instead of `Any`
- [ ] Private attributes have type hints: `self._attr: Type`

### ✅ Logger Usage Checklist:

- [ ] Import: `from logging import Logger`
- [ ] Import: `from tools.logging_config import setup_logging`
- [ ] Initialize in `__init__`: `self._logger: Logger = setup_logging(__name__)`
- [ ] Use consistent naming: `self._logger` (not `self.log`, `self.logger`, etc.)
- [ ] Error logging: `self._logger.error("Context: %s", type(e).__name__)`
- [ ] Never log full exception messages
- [ ] Never pass logger as constructor parameter
- [ ] Sensitive data logged with truncation: `...%s", value[-4:]`
- [ ] Never log full tokens, API keys, passwords, or secrets
- [ ] Use descriptive context: `"api_key=...1234"` not just `"...1234"`

### ✅ SOLID Principles Checklist:

- [ ] **S**RP: Each method has one clear responsibility
- [ ] **O**CP: Can extend without modifying (use abstractions)
- [ ] **L**SP: Subclasses can substitute parent classes
- [ ] **I**SP: Interfaces are small and focused
- [ ] **D**IP: Depend on abstractions, inject dependencies
- [ ] Composition over inheritance unless strict is-a
- [ ] Public APIs are minimal and intentional

### ✅ Code Review Checklist:

- [ ] Module docstring present
- [ ] All public classes/methods have docstrings
- [ ] Type hints on all signatures
- [ ] No `Any` types (or justified with comment)
- [ ] Logger follows standard pattern
- [ ] Dependencies injected via constructor
- [ ] Private attributes use `_` prefix
- [ ] Constants use `UPPER_SNAKE_CASE`
- [ ] No code duplication (DRY principle)
- [ ] Error messages are meaningful
- [ ] Tests updated for new/changed code
- [ ] No hardcoded paths, API keys, or secrets
- [ ] Sensitive values logged safely (truncated to last 4 chars: `...XXXX`)
- [ ] Passwords never logged (even truncated)
- [ ] Imports grouped: stdlib, third-party, local

### ✅ Testing Checklist:

- [ ] Test file mirrors source file name: `test_my_module.py`
- [ ] Tests organized in classes by component
- [ ] Each test has descriptive name: `test_process_valid_input`
- [ ] All public methods have tests
- [ ] Edge cases covered
- [ ] Error conditions tested
- [ ] Mocks used for external dependencies
## 10. Change Log Updates

After implementing any new feature, bug fix, or improvement, you **must** update the `CHANGE_LOGS.md` file.

- **Locate the `[Unreleased]` section** at the top of the file.
- **Add your change** under the appropriate heading:
  - `### Added` for new features.
  - `### Changed` for modifications to existing functionality.
  - `### Fixed` for bug fixes.
  - `### Security` for security-related changes.
- **Follow the format**: Use clear, concise descriptions in sentence case. End with a period. Reference issue numbers if applicable.
- **Example**:
  ```markdown
  ### Added
  - New `McpProxyProvider` class for creating MCP proxies with enhanced caching.
  ```
- **Never** commit code without an accompanying change log entry.
- **Responsibility**: The author of the change is responsible for updating the change log.

---

- [ ] Run with: `python -m pytest tests/test_my_module.py -v`

