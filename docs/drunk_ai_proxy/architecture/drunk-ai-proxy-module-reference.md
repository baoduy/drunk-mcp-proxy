# `src/drunk_ai_proxy` Module Reference

## Scope

This document describes the runtime architecture and module responsibilities for the Python package under `src/drunk_ai_proxy/drunk_ai_proxy`.

It is based on current implementation and tests in:
- `src/drunk_ai_proxy/drunk_ai_proxy/**`
- `tests/test_*.py`

## Package Map

- `main.py`, `__main__.py`: process entry points.
- `app/`: server bootstrap, Starlette app construction, middleware assembly, lifespan, cache, auth factories.
- `auth/`: custom auth providers/handlers (`ApiKeyAuthProvider`, Azure outbound auth, pass-through).
- `middleware/`: concrete HTTP middleware implementations (auth header, rate limit, security headers, FastAPI auth dependency).
- `proxies/`: MCP, OpenAPI, prompt, agent, and LLM proxy providers.
- `utils/`: config models, env var resolution, security helpers, protocol interfaces, serialization.

## Runtime Flow

### Startup flow

1. `drunk_ai_proxy.main.main()` creates `MCPProxyServer` and calls `run()`.
2. `MCPProxyServer.async_run()`:
   - loads singleton config via `AppConfigProvider.get_instance()` (reads `data/config.yaml`),
   - builds MCP services via `StaticProxiesProvider.get_config_services()`,
   - builds LLM service via `LlmProxiesProvider(...)`,
   - stores enabled `remote_resources` configs,
   - starts Uvicorn with `StarletteApp.build()`.
3. `StarletteApp.build()` mounts:
   - MCP apps at `/<path>/mcp` (root path mounts at `/mcp`),
   - LLM app at `FASTMCP_LLM_ROUTE_PREFIX` (default `/api/v1`),
   - health routes (`/health`, `/`).
4. App lifespan is managed by `AppLifespanManager.lifespans()`, including background `RemoteResourceSyncTask` for enabled bundles.

### Request flows

#### MCP requests

- Request enters Starlette middleware pipeline (`CORS`, request-size/security headers, optional auth-header and rate-limit middleware).
- Request is routed to mounted FastMCP app (`/mcp` or `/<namespace>/mcp`).
- `McpProxyProvider`-created FastMCP instance proxies:
  - MCP spec (`spec_type: mcp`) via `fastmcp.server.create_proxy`, or
  - OpenAPI spec (`spec_type: openapi`) via `OpenAPIProvider` with optional route filters.

#### LLM HTTP requests

- LLM FastAPI app serves endpoints:
  - `POST /chat/completions`,
  - `POST /messages` (Anthropic compatibility),
  - `POST /embeddings`, `POST /audio/transcriptions`, `POST /audio/translations`,
  - `POST /images/generations`,
  - `GET /models`, `GET /providers`.
- Model IDs are expected as `provider_model` and routed by `LlmBaseProvider.parse_model_id()`.

#### LLM WebSocket responses flow

- `LlmProxiesProvider` registers `WebSocket /responses`.
- `LlmWebSocketProvider`:
  - reads provider from `model`,
  - uses native backend websocket when `provider.websocket=true`, otherwise HTTP fallback,
  - uses per-client/per-provider backend connection pooling,
  - returns standardized websocket error objects for invalid/failed forwarding.

## Configuration Dependencies

## `data/config.yaml`

Top-level sections loaded by `ConfigYaml`:
- `auth`
- `llm`
- `mcp`
- `remote_resources`

Important model behaviors:
- Environment variables (`$VAR`, `${VAR}`) are resolved during model validation.
- `mcp` entries are filtered by `enabled` before use.
- `llm` entries are filtered by `enabled` before use.
- Legacy MCP keys (`skill_dir`, `prompt_dir`, `agents_dir`) are rejected; use `skills.dirs`, `prompts.dirs`, `agents.dirs`.
- OpenAPI config uses nested `open_api` (`spec_file`, `base_url`, `filters`).

### Environment variables

Main runtime variables are centralized in `utils/env.py`, including:
- server/runtime: `FASTMCP_HOST`, `FASTMCP_PORT`, `FASTMCP_LOG_LEVEL`, `FASTMCP_SERVER_NAME`, `FASTMCP_SERVER_VERSION`, `FASTMCP_SERVER_TRANSPORT`, `FASTMCP_LLM_ROUTE_PREFIX`
- auth/rate limiting: `FASTMCP_AUTH_ENABLED`, `FASTMCP_RATE_LIMIT_ENABLED`, `FASTMCP_RATE_LIMIT_REQUESTS`, `FASTMCP_RATE_LIMIT_WINDOW_SECONDS`
- config root: `FASTMCP_CONFIG_DIR`
- remote sync: `REMOTE_RESOURCE_TTL_HOURS`, `REMOTE_RESOURCE_ALLOWED_EXTENSIONS`, `REMOTE_RESOURCE_MAX_SIZE_MB`, `REMOTE_RESOURCE_RETRY_ATTEMPTS`
- oauth storage: `FASTMCP_OAUTH_STORAGE_TYPE`, `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY`, `FASTMCP_REDIS_CONNECTION_STRING`

## Module Responsibilities

### `app/`

- `server.py`: orchestrates startup and composition.
- `starlette_app.py`: builds Starlette app, mounts services, health routes, optional Swagger.
- `app_config_provider.py`: singleton typed config access + auth provider selection.
- `auth_provider_registry.py`: FastMCP auth provider factory by `AuthType`.
- `client_auth_handler_factory.py`: outbound auth handler factory for upstream client auth.
- `cache_provider.py`: singleton OAuth token store + TTL cache store abstraction.
- `lifespan.py`: startup/shutdown context for mounted MCP apps and remote sync task lifecycle.
- `middleware_provider.py`: middleware list composition based on env flags.

### `auth/`

- `api_auth_provider.py`: static bearer token verifier for inbound FastMCP auth.
- `auth_pass_through.py`: outbound auth pass-through handler.
- `httpx_oauth_base.py`, `httpx_azure_oauth.py`: outbound OAuth auth flows for HTTPX clients.

### `middleware/`

- `auth_header.py`: rejects non-anonymous paths without `Authorization` header.
- `rate_limit.py`: fixed-window IP-based limiter using shared cache store.
- `security_headers.py`: response security headers + request size limit.
- `fast_auth.py`: FastAPI dependency wrapper for FastMCP auth providers.

### `proxies/`

- `mcp/`: static MCP + OpenAPI-backed MCP service creation and resource provider registration.
- `llm/`: OpenAI-compatible HTTP endpoints, Anthropic compatibility layer, WebSocket responses routing.
- `prompt/`: markdown prompt loading/parsing and dynamic FastMCP prompt registration.
- `agent/`: markdown agent resource loading and namespace-aware exposure.

### `utils/`

- `config_yaml.py`: typed Pydantic config models, schema validation, spec loading.
- `env.py`, `env_resolver.py`: env access and placeholder resolution.
- `security.py`: sanitization, validation, and audit helpers used across app and providers.
- `serialization.py`: safe object->dict conversion for responses/logging.
- `protocols.py`: protocol interfaces for dependency injection.

## Extension Points

- Add auth types by extending:
  - `AuthType` in `utils/config_yaml.py`,
  - `AuthProviderRegistry.create(...)`,
  - `ClientAuthHandlerFactory.create(...)` (if outbound auth needed).
- Add LLM endpoint behavior in `LlmProxiesProvider` (reuse `_call_openai_endpoint` and known-param sets).
- Add resource formats by extending provider registration in `McpProxyProvider` (`_add_skill_proxy`, `_add_prompt_proxy`, `_add_agent_proxy`).
- Add middleware in `app/middleware_provider.py` and keep order deterministic.

## Common Failure Modes

- Invalid model IDs (`model` not in `provider_model` format) return 400 in LLM endpoints.
- Missing/empty auth header on protected paths returns 401 from `AuthHeaderMiddleware`.
- Rate-limit quota exceedance returns 429 with `Retry-After`.
- OpenAPI entries missing `open_api.base_url` or `open_api.spec_file` fail config validation.
- Missing `data/config.yaml` fails startup (`FileNotFoundError`).
- Remote resource sync rejects non-HTTPS URLs, non-allowlisted extensions, oversized files, and out-of-root destination directories.

## Security Notes

- Error responses are sanitized with generic/actionable messages.
- Logs avoid raw exception messages in critical paths (error type logging pattern).
- Security headers and request size limiting are applied globally (either explicit middleware list or automatic fallback in app build).
- OAuth token storage supports encryption wrapper when `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY` is set.

## Testing and Verification

Use repository-standard commands:

```bash
python -m pytest
python -m pytest tests/test_mcp_proxy_provider.py tests/test_llm_proxies_provider.py -q
flake8 src tests
pyright
```

## Diagrams

- System diagram: `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-system.md`
- Package diagrams:
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-app.md`
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-auth.md`
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-middleware.md`
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-proxies.md`
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-utils.md`
- Proxy subpackage diagrams:
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-proxies-llm.md`
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-proxies-mcp.md`
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-proxies-prompt.md`
  - `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-proxies-agent.md`
