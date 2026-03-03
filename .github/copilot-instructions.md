# Copilot Instructions for Drunk MCP Proxy

## Quick Orientation

**Drunk MCP Proxy** is a Python 3.10+ FastAPI/Starlette gateway that fronts multiple MCP (Model Context Protocol) servers and LLM providers. The app composition is **config-driven**—configuration loaded from `data/config.yaml` (not JSON), then providers are instantiated and mounted as sub-applications.

**Key entry point**: `src/main.py` → `src/app/starlette_app.py` → provider instances mounted via Starlette.

## Essential Patterns & Conventions

### Project Structure & Imports
- **Layout**: `src/` based, with `src/app/`, `src/auth_providers/`, `src/proxies/`, `src/tools/`, `tests/`.
- **Imports**: Use **relative imports from `src/` root** (no `src.` prefix), e.g. `from app.config_provider import ConfigProvider`, `from tools.env import SERVER_NAME`.
- **When patching in tests**: Match import path as used in code, e.g. `@patch("src.proxies.llm_proxies_provider.AppConfigProvider.get_instance")`.

### Configuration & Environment
- **Config file**: `data/config.yaml` with three root sections: `auth`, `llm`, `mcp`.
- **Field naming**: Use `snake_case` in YAML, NOT camelCase (e.g., `default_provider`, `mcp_servers`).
- **Config loading**: `AppConfigProvider.get_instance()` loads once at startup; use `.get_*_config()` methods to retrieve typed sections.
- **Environment variables**: Checked via `src/tools/env.py`; override via OS env (e.g., `FASTMCP_AUTH_ENABLED`, `MCP_OAUTH_STORAGE_TYPE`).

### Testing & Mocking
- **Run tests**: `python -m pytest` (adds current directory and `src/` to `sys.path` via `conftest.py`).
- **Mocking environment**: Use `monkeypatch.setattr()` to override module-level variables; mocking both regular and async functions.
- **Mocking FastAPI apps**: Use `@patch()` on provider methods like `_get_openai_client()` or `_get_fastapi_app()` to inject fake clients/apps; use `TestClient` from `starlette.testclient`.
- **Request mocking**: Create `Mock()` objects with `.headers`, `.json()`, `.form()` as needed; monkeypatch provider methods that return client instances.

### Error Handling & Security
- **Logging errors**: Log **only the exception type**, not the full message: `logger.error("%s: %s", context, type(e).__name__)` to prevent sensitive info exposure (API keys, paths, etc. in logs).
- **Sanitizing errors**: Use `_sanitize_error_message()` when returning error responses to clients; return generic "An error occurred" unless error is explicitly user-actionable.
- **Auth middleware**: Optional; enabled via `FASTMCP_AUTH_ENABLED=true`. Auth provider is injected via dependency in FastAPI (`Depends(FastAuthMiddleware(auth_provider))`).

### Architecture & Providers
- **Provider pattern**: Each provider (LLM, MCP, Static, OpenAPI, Swagger) is mounted as a sub-app via `provider.mount(app, route_prefix)`.
- **FastAPI endpoints**: Providers create internal FastAPI instances and mount them; use `app.add_api_route()` for route registration.
- **Dependency injection**: Pass dependencies via `dependencies=[Depends(...)]` at FastAPI instantiation. Skip dependencies list if auth is `None` to avoid validation errors.
- **Caching**: `CacheProvider.get_oauth_store()` is a singleton; storage backend (memory/sqlite/redis) is env-driven; encryption wrapping is automatic if key is set.

### Docstrings & Code Style
- **Docstrings**: Google-style for all public functions/classes/modules (see `AGENTS.md` for format).
- **String quotes**: Use double quotes `"` consistently.
- **Type hints**: Required for all function signatures (args and return type).

## Debugging & Common Issues

1. **Import errors in tests**: Ensure tests run with `python -m pytest` so `src/` is in `sys.path`.
2. **Config loading fails**: Check that `OAUTH_STORAGE_ENCRYPTION_KEY`, `CONFIG_DIR`, etc. are set or mocked in tests.
3. **FastAPI dependency validation fails**: If passing `None` or invalid dependencies, FastAPI rejects them; only add dependencies to list when they're valid (check `auth is not None` first).
4. **Stale test references**: When methods are removed/renamed, update test calls and mocks; don't call deleted private methods like `_collect_forward_headers()`.

## Key Files to Know

- **Configuration**: `data/config.yaml` (source), `src/tools/config_yaml.py` (models), `src/app/app_config_provider.py` (loader).
- **Server setup**: `src/app/starlette_app.py` (Starlette app factory), `src/app/server.py` (server lifecycle).
- **Providers**: `src/proxies/llm_proxies_provider.py` (LLM endpoints), `src/proxies/mcp_proxy_provider.py` (MCP routing), `src/proxies/mcp_base_provider.py` (base MCP provider).
- **Utilities**: `src/tools/env.py` (env vars), `src/tools/env_resolver.py` (resolution logic), `src/tools/logging_config.py` (logging setup).
- **Tests**: `tests/conftest.py` (pytest setup), `tests/test_*.py` (unit tests for respective modules).

## Workflow Commands

```bash
# Install in editable mode with dev deps
pip install -e ".[dev]"

# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_llm_proxies_provider.py

# Run with coverage
python -m pytest --cov=src

# Type checking
pyright

# Linting
flake8 src tests
```

---

**For detailed guidelines**, refer to `AGENTS.md` (comprehensive developer instructions).
