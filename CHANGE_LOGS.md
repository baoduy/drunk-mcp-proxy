# Changelog

All notable changes to the drunk-mcp-proxy project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- On-demand remote skill resources provider for MCP nested `skills.remote_resources` with URL grouping by skill root and cache-backed fetch behavior.
- New tests for remote skill resource grouping, cache reads, and fail-open behavior in `tests/test_remote_resources_provider.py`.

### Changed

- Extended MCP config to support nested `skills`, `prompts`, and `agents` sections with `dirs` and `remote_resources`.
- Refactored OpenAPI MCP configuration to use nested `open_api` fields (`spec_file`, `base_url`, `filters`, `spec_data`) and removed redundant top-level OpenAPI fields from `McpConfig`.
- Updated MCP and prompt provider wiring to use effective multi-directory accessors for local resources.
- Updated prompt loading to support scanning multiple prompt directories.
- Updated skill resource URI naming to include the configured root namespace for paths under `skills/<name>` (for example `skill://dknet/<skill>/SKILL.md`).
- Updated agent resource naming and URIs to include the configured root namespace for paths under `agents/<name>` (for example `agent://dknet/test-generator.agent.md` and `.../_manifest`).
- Consolidated skill/prompt/agent resource provider implementations under `proxies/resource/` and switched MCP skill mounting to `SkillsDirectoryProvider` from that unified package.
- Switched MCP agent mounting to `AgentsDirectoryProvider` from `proxies/resource/` and removed remaining legacy provider modules (`agent_provider`, `custom_agents_directory_provider`, `custom_skills_directory_provider`) with corresponding unit test migration.
- Added explicit `description` metadata for all `Field(...)` declarations in `utils/config_yaml.py` to improve schema clarity and generated docs.

### Fixed

- MCP config validation now accepts nested `prompts.dirs` as a valid prompt-only MCP configuration.
- MCP config validation now enforces unified resource structure (`skills.dirs`, `prompts.dirs`, `agents.dirs`) and rejects legacy keys (`skill_dir`, `prompt_dir`, `agents_dir`).
- Fixed prompt registration for relative `prompts.dirs` so MCP prompt provider no longer resolves paths as `data/data/...`, restoring prompt discovery in mounted MCP routes.

## [0.2.0] - 2026-03-11

### Added

#### Agent Ecosystem
- **Agent Provider** (`proxies/agent/agent_provider.py`): Exposes markdown agent files as MCP resources via `agent://` URI scheme. Each agent includes content and a JSON manifest with file hash, size, and metadata.
- **Custom Agents Directory Provider** (`proxies/agent/custom_agents_directory_provider.py`): Recursively scans directories for `.md` agent files with YAML frontmatter. Supports flat (`root/*.md`) and namespaced (`root/namespace/*.md`) layouts with deduplication, enabled/disabled filtering, and optional reload on each request.
- Agent frontmatter fields: `description` (string), `enabled` (boolean, default: true).
- Example agents provided in `data/agents/` covering core (planning, analysis), tools (test-generator, code-refactor), and dotnet categories.

#### Remote Resource Synchronization
- **Remote Resource Sync Task** (`app/tasks/remote_resource_sync_task.py`): Background asyncio task that downloads remote files (HTTPS only) into local config directories at startup and periodically based on TTL.
- TTL-based cache freshness checking, file extension allowlisting, max file size enforcement, retry support, and parallel downloads per bundle.
- Configuration via `remote_resources` section in `config.yaml` with `name`, `to_dir`, and `paths` (list of HTTPS URLs).
- Configurable environment variables: `REMOTE_RESOURCE_TTL_HOURS` (default: 24), `REMOTE_RESOURCE_ALLOWED_EXTENSIONS` (default: `.md,.yaml,.yml,.json,.py,.js,.ts`), `REMOTE_RESOURCE_MAX_SIZE_MB` (default: 10), `REMOTE_RESOURCE_RETRY_ATTEMPTS` (default: 2).

#### Prompt System
- **Prompt Template** (`proxies/prompt/prompt_template.py`): Markdown prompt templates with YAML frontmatter, typed parameters (`str`, `int`, `float`, `bool`), role support (`user`/`assistant`/`system`), and `str.format()` interpolation with type validation.
- **Prompt Loader** (`proxies/prompt/prompt_loader.py`): Recursive directory scanner for `.md` prompt files. Handles name sanitization, deduplication, and disabled prompts.
- **MCP Prompt Provider** (`proxies/prompt/prompt_provider.py`): Dynamically registers prompts with FastMCP using `mcp.prompt()` decorator. Builds `inspect.Signature` objects for parameter metadata exposure. Supports both standalone `create_proxy()` and `register_to_mcp()` for mounting into existing FastMCP instances.
- Example prompts in `data/prompts/custom/` (ask-topic, code-review, generate-tests, explain-concept, generate-code).

#### Skills System
- **Custom Skills Directory Provider** (`proxies/mcp/custom_skills_directory_provider.py`): Discovers skill directories containing `SKILL.md` files and mounts them as FastMCP resources. Supports flat and namespaced layouts.
- Example skills in `data/skills/dknet/` covering .NET patterns (aspcore-idempotency, slimbus-messaging, fw-extensions, efcore-specifications, efcore-repos, efcore-abstractions).

#### LLM Proxy Enhancements
- **Anthropic Messages API Compatibility** (`proxies/llm/anthropic_provider.py`): Bidirectional converter between Anthropic Messages API and OpenAI format. Supports text, images (base64/URL), tool use/results, system prompts, streaming SSE events, and parameter mapping (`stop_sequences` -> `stop`, `metadata.user_id` -> `user`).
- **WebSocket Responses API** (`proxies/llm/websocket_provider.py`): Native WebSocket proxy for OpenAI Responses API. Two modes: native backend WebSocket (for providers with `websocket: true`) or HTTP fallback with streaming. Includes `BackendConnectionPool` for per-(client_id, provider_name) connection pooling.
- **WebSocket Transport** (`proxies/llm/websocket_transport.py`): Low-level WebSocket connection management with alive checking and cleanup.
- LLM endpoints: `/chat/completions`, `/messages`, `/responses` (WebSocket), `/embeddings`, `/images/generations`, `/audio/transcriptions`, `/audio/translations`, `/models`, `/providers`.

#### Client
- **Drunk AI Client** (`drunk_ai_client`): STDIO MCP bridge that connects to a remote drunk-mcp-proxy server, syncs skills and agents locally, and exposes them via a local FastMCP STDIO server.
- `ResourceSyncManager` for manifest-based and list-based resource downloading.
- Environment variables: `API_URL` (required), `API_KEY`, `SKILL_DIR`, `AGENTS_DIR`, `ALLOWS_OVERWRITE`.
- Integration with `RegexSearchTransform` and `BM25SearchTransform` for search capabilities.

#### Configuration
- **Unified YAML Configuration** (`utils/config_yaml.py`): Pydantic-based configuration with automatic `$VAR`/`${VAR}` environment variable resolution.
- Top-level sections: `auth`, `llm`, `mcp`, `remote_resources`.
- Auth support for 12 providers: basic, auth0, aws, azure, discord, github, google, in_memory, introspection, jwt, oci, supabase.
- LLM config: `enabled`, `websocket`, `provider`, `base_url`, `api_key`.
- MCP config: `enabled`, `path`, `spec_file`, `spec_type` (mcp/openapi), `base_url`, `skill_dir`, `prompt_dir`, `agents_dir`, `filters`, `auth`, `mcp_servers`, `tags`.

#### Infrastructure
- **App Lifespan Manager** (`app/lifespan.py`): Manages startup/shutdown lifecycle including remote resource sync background tasks and MCP app lifespans with proper error handling for partial startup failures.
- **Security Headers Middleware** (`app/security_headers_middleware.py`): Enhanced HTTP security headers.
- **Swagger Provider** (`app/swagger_provider.py`): Auto-generated API documentation.
- **Code Mode** (`FASTMCP_CODEMODE_ENABLED`): Toggleable code mode for development.

### Changed

- Migrated from JSON to YAML configuration format across the entire project.
- Restructured source code from `src/` flat layout to `src/drunk_ai_proxy/drunk_ai_proxy/` and `src/drunk_ai_client/drunk_ai_client/` package layout.
- Refactored all modules for PEP 8 compliance, consistent naming conventions, and clean code practices.
- Enhanced error sanitization to prevent information leakage through exception messages.
- Improved Docker multi-stage build with health checks.

### Fixed

- OpenAPI MCP provider integration issues (`9ae60b3`).
- Auth validation issues with token caching (`0cc120e`).
- WebSocket connection management and cleanup (`4c1f22b`, `9d7c6c3`).
- Unit test compatibility with new config system (`6a019ba`).
- Security vulnerability: sanitized error messages and logging (`e83ee5c`).

---

## [0.1.0] - 2026-01-15

### Added

- Initial release of drunk-mcp-proxy.
- Core MCP proxy server with static proxy configuration.
- OpenAPI integration for converting specs to MCP tools.
- Basic authentication support (Bearer token, JWT).
- Docker support with multi-stage build.
- Health check endpoint (`/health`).
- CORS middleware configuration.
- Structured logging with configurable levels.
- JSON schema validation for configuration files.
- Comprehensive test suite with 77%+ code coverage.

---

## Key Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `FASTMCP_CONFIG_DIR` | `data` | Configuration/data directory |
| `FASTMCP_SCHEMA_DIR` | `schemas` | JSON schema directory |
| `FASTMCP_LLM_ROUTE_PREFIX` | `/api/v1` | LLM API route prefix |
| `FASTMCP_LOG_LEVEL` | `INFO` | Logging level |
| `FASTMCP_SERVER_TRANSPORT` | `streamable-http` | MCP transport protocol |
| `FASTMCP_HOST` | `0.0.0.0` | Bind host |
| `FASTMCP_PORT` | `9123` | Bind port |
| `FASTMCP_AUTH_ENABLED` | `false` | Authentication toggle |
| `FASTMCP_CODEMODE_ENABLED` | `true` | Code mode toggle |
| `FASTMCP_SWAGGER_ENABLED` | `true` | Swagger UI toggle |
| `FASTMCP_RATE_LIMIT_ENABLED` | — | Rate limiting toggle |
| `FASTMCP_CORS_ALLOW_ORIGINS` | `*` | CORS allowed origins |
| `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY` | — | Fernet key for OAuth token encryption |
| `FASTMCP_REDIS_CONNECTION_STRING` | — | Redis for rate limiting |
| `REMOTE_RESOURCE_TTL_HOURS` | `24` | Remote resource cache TTL |
| `REMOTE_RESOURCE_ALLOWED_EXTENSIONS` | `.md,.yaml,...` | Allowed file extensions for remote sync |
| `REMOTE_RESOURCE_MAX_SIZE_MB` | `10` | Max file size for remote downloads |
| `REMOTE_RESOURCE_RETRY_ATTEMPTS` | `2` | Retry attempts for failed downloads |
| `API_URL` | — | Client: remote MCP endpoint URL |
| `API_KEY` | — | Client/Server: Bearer token |
| `SKILL_DIR` | — | Client: local skills directory |
| `AGENTS_DIR` | — | Client: local agents directory |
| `ALLOWS_OVERWRITE` | — | Client: overwrite local files during sync |
