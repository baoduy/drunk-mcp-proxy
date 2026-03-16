# Changelog

All notable changes to the drunk-mcp-proxy project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- On-demand remote skill resources provider for MCP nested `skills.remote_resources` with URL grouping by skill root and cache-backed fetch behavior.
- New tests for remote skill resource grouping, cache reads, and fail-open behavior in `tests/test_remote_resources_provider.py`.
- Added a user-invocable `Architecture Reviewer` custom agent at `.github/agents/architecture-reviewer.agent.md` for repository structure, layering, security, and naming/folder architecture audits.
- Added an improved, timestamped `Architecture Reviewer` agent variant at `.github/agents/architecture-reviewer-20260313-082355.agent.md` with tighter scope controls, clearer evidence-first output contract, and a direct handoff to `Feature Planner`.
- Added import-linter bootstrap guardrails via `src/drunk_ai_proxy/.importlinter` and a non-blocking CI workflow at `.github/workflows/architecture-lint.yml`.
- Added configuration-driven URI verification tests for `data/config.yaml` remote skill/prompt/agent entries to validate name normalization and generated MCP URI conventions.
- Added `docs/drunk_ai_proxy/architecture/drunk-ai-proxy-module-reference.md` with a code-verified architecture, runtime flow, config dependencies, extension points, and common failure modes for `src/drunk_ai_proxy`.
- Added a dedicated diagram set under `docs/drunk_ai_proxy/architecture/diagrams/drunk_ai_proxy-*.md` including one system-level diagram and focused diagrams for `app`, `auth`, `middleware`, `proxies`, `utils`, and proxy subpackages (`llm`, `mcp`, `prompt`, `agent`).
- Added `docs/drunk_ai_proxy/architecture/drunk-ai-proxy-route-appendix.md` with consolidated server, MCP, LLM HTTP, and WebSocket route mapping.
- Added `docs/drunk_ai_proxy/development/drunk-ai-proxy-operator-runbook.md` with startup checks, incident triage, and operational verification steps.

### Changed

- Refactored Swagger and LLM/MCP proxy internals for stricter class-first architecture: extracted OpenAPI component builders into `app/swagger_schemas.py`, introduced `RemoteProviderBootstrap` and injected shared HTTP client dependencies through MCP providers, introduced `LlmModelCatalog` plus `LlmEndpointMixin` to slim `LlmProxiesProvider`, and added typed alias cleanup in `app_config_provider`, `env_resolver`, and `anthropic_provider`.
- Simplified MCP proxy config construction to instantiate a FastMCP route for every configured `mcp` entry without pre-filtering no-spec configs; each route now relies on `_add_mcp_proxy`, `_add_open_api_proxy`, and resource provider adders to attach capabilities independently.
- Completed phased architecture refactor implementation for `src/drunk_ai_proxy/drunk_ai_proxy`: consolidated middleware assembly on `MiddlewareProvider` canonical path, introduced class-first utility facades (`EnvResolver`, `ConfigYamlUriBuilder`, `ResourcePathNamespaceResolver`, `EnvConfig` snapshot), extracted SRP helpers in server/LLM/MCP provider flows, and added auth registry extension hook.
- Aligned MCP remote-resource wiring with protocol-based cache dependency injection (`TokenStore`) across remote providers and on-demand fetch service, removing direct proxy-layer coupling to concrete cache storage implementations.
- Segregated LLM provider capabilities by introducing `MountableLlmProvider` while keeping endpoint-only providers compatible.
- Extended Swagger schema output to expose mounted LLM sub-app native documentation endpoints (`/openapi.json`, `/docs`) for framework-native discovery.

- Extended `PromptTemplate` with `from_markdown_content(...)` and refactored remote prompt parsing to use in-memory markdown parsing instead of temporary files.
- Merged `drunk_ai_client.client` runtime/adapter logic into `drunk_ai_client.main` so the stdio client now has a single module entry surface.
- Extended MCP config to support nested `skills`, `prompts`, and `agents` sections with `dirs` and `remote_resources`.
- Switched Code Mode control from global environment toggle to per-route MCP config via `mcp[].codemode_enabled`.
- Reorganized documentation into module-based roots under `docs/drunk_ai_proxy` and `docs/drunk_ai_client`, archived loose legacy docs into `docs/drunk_ai_proxy/legacy`, and converted top-level `docs/README.md` + `docs/INDEX.md` into module routers.
- Updated `.github/agents/architecture-reviewer-20260313-082355.agent.md` to always produce a timestamped architecture recommendation report under `docs/drunk_ai_proxy/architecture/reviews/architecture-review-<timestamp>.md` after each review.
- Refactored OpenAPI MCP configuration to use nested `open_api` fields (`spec_file`, `base_url`, `filters`, `spec_data`) and removed redundant top-level OpenAPI fields from `McpConfig`.
- Consolidated OpenAPI MCP proxy creation into `McpProxyProvider` and removed the separate `proxies/mcp/openapi_provider.py` implementation.
- Updated MCP and prompt provider wiring to use effective multi-directory accessors for local resources.
- Updated prompt loading to support scanning multiple prompt directories.
- Updated skill resource URI naming to include the configured root namespace for paths under `skills/<name>` (for example `skill://dknet/<skill>/SKILL.md`).
- Updated agent resource naming and URIs to include the configured root namespace for paths under `agents/<name>` (for example `agent://dknet/test-generator.agent.md` and `.../_manifest`).
- Consolidated skill/prompt/agent resource provider implementations under `proxies/resource/` and switched MCP skill mounting to `SkillsDirectoryProvider` from that unified package.
- Switched MCP agent mounting to `AgentsDirectoryProvider` from `proxies/resource/` and removed remaining legacy provider modules (`agent_provider`, `custom_agents_directory_provider`, `custom_skills_directory_provider`) with corresponding unit test migration.
- Added explicit `description` metadata for all `Field(...)` declarations in `utils/config_yaml.py` to improve schema clarity and generated docs.
- Updated MCP static provider documentation to reference YAML-based config loading (`config.yaml`) instead of legacy `config.json` wording.
- Added `import-linter` to `src/drunk_ai_proxy` development dependencies.
- Removed legacy MCP JSON-schema validation from `McpConfig` and now rely on Pydantic model/validator-based config validation.
- Completed phased architecture refactor plan for app/auth/llm/mcp/utils: introduced `AuthTypeRegistry`, `LlmRouter` + `LlmRequestDispatcher`, `McpServerFactory`, `AppConfigReader`, and `EnvReader`, with compatibility shims preserved for existing imports and patch targets.
- Split configuration concerns by moving YAML model definitions into `utils/config_yaml_models.py` and reducing `utils/config_yaml.py` to a loader-focused `ConfigYaml` surface with backward-compatible re-exports.
- Completed phased `drunk_ai_client` refactor: introduced class-first runtime orchestration (`StdioBridgeApplication`, `ClientCliEntrypoint`), split sync/config/models into dedicated modules, added protocol-based resource sync abstractions, centralized DRY path/content helpers, and added `FastMCP.from_client` composition with compatibility fallback to manual proxy mounting.

### Fixed

- Fixed inbound auth initialization to auto-enable when `auth.default_provider` is configured and `FASTMCP_AUTH_ENABLED` is unset, while still honoring explicit `FASTMCP_AUTH_ENABLED=false` overrides.
- Fixed MCP proxy config filtering so routes with only nested remote resources (for example `/remotes`) are still mounted at `/<path>/mcp` even when `mcp_servers` is not configured.
- Fixed MCP proxy config filtering so local-only resource routes (for example `/locals` with `skills/prompts/agents` dirs) are mounted at `/<path>/mcp` when `mcp_servers` is not configured.
- Fixed prompt template parsing to support markdown prompts without YAML frontmatter by returning full content with default metadata instead of failing.
- Fixed remote prompt rendering for markdown files without YAML frontmatter by falling back to raw markdown template content with default prompt metadata.
- Fixed remote prompt registration to omit companion `prompt://<name>/_manifest` resources so prompts are registered and used without manifest requirements.
- Fixed MCP proxy configuration building to always create a FastMCP instance for configured MCP routes (including `/remotes`) without pre-validating local prompt/resource directories.
- Fixed remote skill resource URI mapping to follow FastMCP SkillProvider convention by exposing primary skill files as `skill://<skill-name>/SKILL.md`.
- Fixed remote agent resource URI mapping to follow `agent://<path>/<file_name>.agent.md` naming convention.
- Fixed on-demand remote prompt registration to avoid FastMCP prompt rejection for `**kwargs`, restoring visibility of `prompts.remote_resources` entries in prompt listings.
- Fixed remote URI builders for skills, agents, and prompts to prioritize configured `name` when provided; URL-based name inference is now only used as fallback.
- Fixed fallback URL name derivation to use parent folder only for `SKILL.md` and filename stem for non-skill files (e.g. `QUICK-REFERENCE.md` -> `quick-reference`).
- Fixed remote skill manifest URI generation to preserve full namespaced skill names (for example `skill://dotnet/ef-core/_manifest` instead of truncating to `skill://dotnet/_manifest`).
- Fixed prompt template rendering for files with no declared `parameters` so content is returned verbatim (literal `{...}` text is preserved instead of raising render errors).
- MCP config validation now accepts nested `prompts.dirs` as a valid prompt-only MCP configuration.
- MCP config validation now enforces unified resource structure (`skills.dirs`, `prompts.dirs`, `agents.dirs`) and rejects legacy keys (`skill_dir`, `prompt_dir`, `agents_dir`).
- Fixed prompt registration for relative `prompts.dirs` so MCP prompt provider no longer resolves paths as `data/data/...`, restoring prompt discovery in mounted MCP routes.
- Consolidated auth-header middleware ownership by removing the unused duplicate FastMCP middleware module and its dedicated tests; Starlette middleware in `app/middleware_provider.py` remains the canonical runtime path.
- Restored backward-compatible module-level middleware helper symbols in `app/middleware_provider.py` (`_parse_csv`, `_create_*`) used by existing tests and patch-based integrations.
- Preserved `CONFIG_DIR` monkeypatch compatibility for config model spec-file loading after the `config_yaml` model split.

### Removed

- Removed legacy schema artifact `schemas/mcp.schema.json` and schema directory runtime wiring from Docker image build.
- Removed `FASTMCP_SCHEMA_DIR` environment variable from runtime configuration, templates, and documentation.
- Removed `FASTMCP_CODEMODE_ENABLED` environment variable from runtime configuration; Code Mode is now configured per MCP route.

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
- **Code Mode**: Toggleable code mode for development.

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
| `FASTMCP_LLM_ROUTE_PREFIX` | `/api/v1` | LLM API route prefix |
| `FASTMCP_LOG_LEVEL` | `INFO` | Logging level |
| `FASTMCP_SERVER_TRANSPORT` | `streamable-http` | MCP transport protocol |
| `FASTMCP_HOST` | `0.0.0.0` | Bind host |
| `FASTMCP_PORT` | `9123` | Bind port |
| `FASTMCP_AUTH_ENABLED` | `false` | Authentication toggle |
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
